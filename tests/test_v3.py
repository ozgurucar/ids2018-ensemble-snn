from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import torch
from scipy.stats import binom
from idsresearch.config import Config
from idsresearch.decision import prior_offset, log_probabilities, alarm_score, temperature_fit, threshold_fit
from idsresearch.groups import fingerprint, group_partition, group_audit
from idsresearch.data import CLASSES


def test_corrected_posterior_recovers_known_population_distribution():
    full = np.array([90., 10.]); sample = np.array([50., 50.]); weights = np.array([.3, 4.])
    likelihood = np.array([[.2, .8], [.7, .3], [.1, .9]])
    observed = likelihood * sample * weights
    z = np.log(observed)+prior_offset(full, sample, weights)
    target = likelihood*full
    target /= target.sum(1, keepdims=True)
    np.testing.assert_allclose(np.exp(log_probabilities(z)), target)


def test_stable_alarm_score_preserves_extreme_order():
    z = np.array([[-40, 0, -2], [-50, 0, -2]], dtype=np.float32)
    assert alarm_score(z)[0] < alarm_score(z)[1]
    p = np.exp(log_probabilities(z)).astype(np.float32)
    assert 1-p[0,0] == 1-p[1,0]


def test_np_order_statistic_is_minimal_and_handles_insufficient_support():
    s = np.arange(1000.)
    r = threshold_fit(s, .05, method="np_reference", delta=.05)
    k = r["order_statistic"]
    assert binom.sf(k-1, len(s), .95) <= .05
    assert binom.sf(k-2, len(s), .95) > .05
    with pytest.raises(ValueError, match="Insufficient"):
        threshold_fit(np.arange(10.), .01, method="np_reference")


def test_empirical_threshold_ties_do_not_increase_budget():
    s = np.r_[np.zeros(90), np.ones(10)]
    r = threshold_fit(s, .05)
    assert (s > r['threshold']).mean() <= .05


def test_temperature_reduces_nll_without_using_test():
    y = np.r_[np.zeros(80, int), np.ones(20, int)]
    z = np.tile([5., 0.], (100, 1))
    t = temperature_fit(z, y)
    assert t['nll_after'] < t['nll_before']
    assert t['temperature'] > 1


def test_groups_join_signed_zero_and_conflicting_labels_without_leakage():
    X = pd.DataFrame({'a': np.repeat(np.arange(100.), 2), 'b': 0.})
    X.loc[1, 'b'] = -0.
    groups = fingerprint(X)
    y = np.tile([0, 1], 100)
    split = group_partition(groups, (.6, .1, .1, .2), 2026)
    assert len(set(np.concatenate(split))) == len(X)
    sets = [set(map(tuple, groups[idx].tolist())) for idx in split]
    for i in range(4):
        for j in range(i):
            assert not sets[i] & sets[j]
    audit = group_audit(groups, y, ['benign','attack'])
    assert audit['conflicting_groups'] == 100
    assert audit['empirical_representation_error_floor'] == .5


def test_absent_training_class_cannot_be_revived_by_prior_correction():
    offset = prior_offset([99, 1, 0], [10, 1, 0], [1, 1, 0])
    assert offset[2] < -1e8
    with pytest.raises(ValueError):
        prior_offset([99, 1, 1], [10, 1, 0], [1,1,0])


def test_epoch_resume_matches_uninterrupted_cpu_training(tmp_path, monkeypatch):
    from idsresearch.training import train_neural
    import idsresearch.provenance as provenance
    rng = np.random.default_rng(33)
    X = rng.random((104, 16)).astype(np.float32)
    y = np.arange(104) % 13
    cfg = Config(epochs=3, patience=4, hidden=(8,4), steps=3, dropout=.2, batch_size=26, loss='ce')
    full, info = train_neural('ann', X, y, X, y, cfg, 22, 'cpu')
    original = provenance.write_json
    def interrupt(path, value):
        original(path, value)
        raise KeyboardInterrupt('simulated interruption after durable epoch')
    monkeypatch.setattr(provenance, 'write_json', interrupt)
    checkpoint = tmp_path/'resume.pt'
    with pytest.raises(KeyboardInterrupt):
        train_neural('ann', X, y, X, y, cfg, 22, 'cpu', checkpoint)
    monkeypatch.setattr(provenance, 'write_json', original)
    resumed, second = train_neural('ann', X, y, X, y, cfg, 22, 'cpu', checkpoint)
    assert info['history'] == second['history']
    for k, v in full.state_dict().items():
        assert torch.equal(v, resumed.state_dict()[k])


def test_focal_rejects_ce_posterior_correction():
    with pytest.raises(ValueError, match='focal'):
        Config(loss='focal').validate()


def test_encoded_ann_control_receives_identical_codes_and_learns():
    from idsresearch.models import EncodedANN, FixedEncoder
    cfg = Config(hidden=(16,8), steps=4, dropout=0.)
    model = EncodedANN(16,13,'temporal',cfg)
    X = torch.rand(26,16)
    assert torch.equal(model.encoder(X), FixedEncoder('temporal',4,4)(X))
    torch.nn.functional.cross_entropy(model(X), torch.arange(26)%13).backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())


@pytest.mark.parametrize('name', ['rf','xgb','catboost'])
def test_tree_ce_is_unweighted_and_class_mapping_is_preserved(name):
    from idsresearch.training import train_tree, tree_proba
    X = np.random.default_rng(21).random((36,5)).astype(np.float32)
    y = np.tile([0,4,12],12)
    cfg = Config(loss='ce',rf_trees=3,xgb_trees=3,catboost_trees=3)
    model, info = train_tree(name, X,y,cfg,22)
    p = tree_proba(model,X)
    np.testing.assert_allclose(p.sum(1),1,atol=1e-6)
    assert np.flatnonzero(p.sum(0)).tolist() == [0,4,12]
    assert info['class_weights'] == [1.]*13


def test_compact_archive_excludes_large_artifacts(tmp_path):
    from idsresearch.suite import compact_archive
    import zipfile
    run = tmp_path/'experiments/group_ce/runs/esnn-42'
    run.mkdir(parents=True)
    for name in ('evaluated.json','model.pt','model.joblib','test_proba.npy','resume.json'):
        (run/name).write_bytes(b'{}')
    path = compact_archive(tmp_path)
    with zipfile.ZipFile(path) as z:
        assert z.namelist() == ['experiments/group_ce/runs/esnn-42/evaluated.json']


def test_detection_recall_is_distinct_from_correct_family_recall():
    from idsresearch.evaluation_v3 import diagnostic
    # One benign false alarm and one detected attack assigned the wrong family.
    y = np.array([0, 0, 1, 1])
    pred = np.array([0, 2, 2, 0])
    z = np.zeros((4, len(CLASSES)))
    z[np.arange(4), pred] = 2.
    result = diagnostic(y, pred, z, np.repeat(np.datetime64('2018-02-14'), 4), 0.)
    assert result['per_class']['Benign']['alarm_rate'] == .5
    assert result['per_class']['Benign']['alarm_recall'] is None
    assert result['per_class']['Bot']['alarm_recall'] == .5
    assert result['per_class']['Bot']['correct_family_recall'] == 0.
