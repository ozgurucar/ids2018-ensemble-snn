from dataclasses import replace
import numpy as np
import pandas as pd
import pytest
import torch
from idsresearch.config import Config
from idsresearch.data import CLASSES, PARTS, Raw, Preprocessor, counts, load, partition, training_subset
from idsresearch.metrics import fit_alarm_threshold, predict, evaluate
from idsresearch.models import FixedEncoder, SpikeBranch, build
from idsresearch.pipeline import prepare, train, score, summarize, validated
from idsresearch.provenance import read_json, write_json
from idsresearch.reporting import export, readiness
from idsresearch.synthetic import generate

torch.set_num_threads(1)


@pytest.fixture
def raw(tmp_path):
    return load(generate(tmp_path/"csv", 40), "%Y-%m-%d %H:%M:%S")


@pytest.mark.parametrize("mode", ["within_class_time", "global_time", "random"])
def test_four_disjoint_partitions_cover_rows(raw, mode):
    indices, _ = partition(raw, Config(split=mode))
    all_indices = np.concatenate(list(indices.values()))
    assert len(np.unique(all_indices)) == len(raw.y) == len(all_indices)
    if mode != "random":
        for c in np.unique(raw.y):
            times = [raw.time[idx][raw.y[idx] == c] for idx in indices.values()]
            present = [t for t in times if len(t)]
            assert all(a.max() < b.min() for a, b in zip(present, present[1:]))


def test_no_silent_session_fallback(raw):
    with pytest.raises(ValueError, match="four time blocks"):
        partition(raw, Config(split="time_groups"))


def test_time_group_split_never_cuts_group(raw):
    t = raw.time.copy()
    for c in np.unique(raw.y):
        i = np.flatnonzero(raw.y == c)
        t[i] += (np.arange(len(i))//10).astype("timedelta64[h]")
    data = Raw(raw.X, raw.y, t, raw.ids, raw.report)
    indices, _ = partition(data, Config(split="time_groups"))
    for c in np.unique(raw.y):
        chunks = [t[i][raw.y[i] == c] for i in indices.values()]
        assert all(b.min()-a.max() > np.timedelta64(30, "m") for a, b in zip(chunks, chunks[1:]))


def test_split_independent_of_model_seeds(raw):
    a, _ = partition(raw, Config(seeds=(1, 2, 3)))
    b, _ = partition(raw, Config(seeds=(42, 43, 44)))
    for p in PARTS:
        np.testing.assert_array_equal(a[p], b[p])


def test_rare_training_rows_are_preserved():
    y = np.r_[np.zeros(5000, int), np.ones(8, int), np.full(44, 2)]
    i = training_subset(y, cap=1000, preserve=100, seed=7)
    assert len(i) == 1000
    assert (y[i] == 1).sum() == 8 and (y[i] == 2).sum() == 44
    with pytest.raises(ValueError):
        training_subset(y, cap=20, preserve=100, seed=7)


def test_holdout_cannot_refit_feature_selection(raw):
    split, _ = partition(raw, Config())
    train_X = raw.X.iloc[split["train"]].copy()
    train_X["constant_train"] = 0.
    holdout = raw.X.iloc[split["test"]].copy()
    holdout["constant_train"] = np.arange(len(holdout))
    proc = Preprocessor(Config()).fit(train_X)
    before = proc.report()
    transformed = proc.transform(holdout)
    assert proc.report() == before
    assert "constant_train" not in proc.columns_
    assert transformed.shape[1] == len(proc.columns_)
    assert transformed.min() >= 0 and transformed.max() <= 1


@pytest.mark.parametrize("kind", ["rate", "temporal", "population"])
def test_fixed_encoders_have_no_trainable_parameters(kind):
    encoder = FixedEncoder(kind, steps=12, populations=4)
    x = torch.linspace(0, 1, 24).reshape(4, 6)
    a, b = encoder(x), encoder(x)
    assert list(encoder.parameters()) == []
    assert torch.equal(a, b)
    assert ((a == 0) | (a == 1)).all()
    if kind == "temporal":
        assert (a.sum(0) == 1).all()


@pytest.mark.parametrize("kind", ["rate", "temporal", "population"])
def test_every_branch_linear_learns(kind):
    torch.manual_seed(10)
    model = SpikeBranch(16, len(CLASSES), kind, Config(hidden=(16, 8), dropout=0.))
    x, y = torch.rand(32, 16), torch.arange(32) % len(CLASSES)
    before = [linear.weight.detach().clone() for linear in model.linears]
    optimizer = torch.optim.Adam(model.parameters(), lr=.01)
    torch.nn.functional.cross_entropy(model(x), y).backward()
    for linear in model.linears:
        assert linear.weight.grad is not None
        assert linear.weight.grad.abs().sum() > 0
    optimizer.step()
    assert all(not torch.equal(old, layer.weight) for old, layer in zip(before, model.linears))


def test_forward_does_not_share_membrane_state():
    torch.manual_seed(7)
    m = build("esnn", 16, len(CLASSES), Config(hidden=(16, 8))).eval()
    x = torch.rand(5, 16)
    with torch.no_grad():
        first = m(x)
        m(torch.rand(3, 16))
        assert torch.equal(first, m(x))
        assert torch.allclose(first, torch.cat([m(x[:2]), m(x[2:])]), atol=1e-6)


@pytest.mark.parametrize("tau", [.01, .05, .1])
def test_alarm_constraint_and_ties(tau):
    rng = np.random.default_rng(3)
    proba = rng.dirichlet(np.ones(len(CLASSES)), 200)
    proba[:30] = proba[0]
    y = np.r_[np.zeros(100, int), np.ones(100, int)]
    result = fit_alarm_threshold(y, proba, tau)
    pred = predict(proba, result["threshold"])
    assert (pred[y == 0] != 0).mean() <= tau
    # Rare attack labels cannot affect the threshold.
    y[100:] = 12
    assert fit_alarm_threshold(y, proba, tau) == result


def test_calibration_rejects_insufficient_benign():
    with pytest.raises(ValueError, match="benign"):
        fit_alarm_threshold(np.ones(10), np.ones((10, 13))/13, .1)


def test_absent_classes_are_explicit():
    y = np.array([0, 0, 1, 1])
    p = np.eye(13)[y]
    result = evaluate(y, y, p)
    assert result["macro_f1_present_classes"] == 1
    assert result["macro_f1"] == pytest.approx(2/13)
    assert len(result["absent_test_classes"]) == 11


def test_real_prepare_requires_dataset_bound_time_evidence(tmp_path):
    data = generate(tmp_path/"data", 200)
    with pytest.raises(ValueError, match="Timestamp evidence"):
        prepare(data, Config(), tmp_path/"real", "%Y-%m-%d %H:%M:%S")


def test_end_to_end_test_is_not_opened_during_training(tmp_path):
    data = generate(tmp_path/"data", 200)
    exp = tmp_path/"exp"
    config = Config(provenance="synthetic", models=("esnn", "ann", "rf"), seeds=(42,),
                    epochs=1, hidden=(8, 4), steps=4, batch_size=128, rf_trees=3,
                    train_cap=1000, rare_preserve=10, min_calibration_benign=3)
    prepare(data, config, exp, "%Y-%m-%d %H:%M:%S")
    # Remove test and calibration feature arrays during training: selection must still work.
    for part in ("test", "calibration"):
        (exp/f"{part}_X.npy").rename(exp/f"{part}_X.hidden")
    train(exp)
    for part in ("test", "calibration"):
        (exp/f"{part}_X.hidden").rename(exp/f"{part}_X.npy")
    summary = score(exp)
    assert summary["missing_runs"] == []
    assert not readiness(exp)["numerical_export_allowed"]
    with pytest.raises(ValueError, match="Synthetic"):
        export(exp, tmp_path/"paper")
    export(exp, tmp_path/"draft", draft=True)
    assert "SYNTHETIC" in (tmp_path/"draft/macros.tex").read_text()
    trained = (exp/"runs/esnn-42/trained.json").read_text()
    train(exp)
    assert (exp/"runs/esnn-42/trained.json").read_text() == trained
    manifest = read_json(exp/"manifest.json")
    assert manifest["preprocessing"]["fit_partition"] == "train"
    result_file = exp/"runs/esnn-42/evaluated.json"
    original = result_file.read_bytes()
    result = read_json(result_file)
    result["uncalibrated"]["accuracy"] = .99999
    write_json(result_file, result)
    with pytest.raises(ValueError, match="Result content changed"):
        summarize(exp)
    result_file.write_bytes(original)
    proba_file = exp/"runs/esnn-42/test_proba.npy"
    proba = np.load(proba_file)
    proba[0] = np.roll(proba[0], 1)
    np.save(proba_file, proba)
    with pytest.raises(ValueError, match="Result artifacts changed"):
        summarize(exp)


def test_protocol_comparison_requires_paired_budgets(tmp_path):
    from idsresearch.comparison import compare
    data = generate(tmp_path/"data", 200)
    config = Config(provenance="synthetic", models=("rf",), seeds=(42,),
                    rf_trees=3, train_cap=1000, rare_preserve=10, min_calibration_benign=3)
    for name, cfg in (("time", config), ("random", replace(config, split="random")),
                      ("different_budget", replace(config, split="random", rf_trees=4))):
        prepare(data, cfg, tmp_path/name, "%Y-%m-%d %H:%M:%S")
        train(tmp_path/name)
        score(tmp_path/name)
    paired = compare(tmp_path/"time", tmp_path/"random", tmp_path/"paired.json")
    assert paired["models"]["rf"]["seed_order"] == [42]
    assert paired["models"]["rf"]["summary"]["macro_f1"]["std"] is None
    with pytest.raises(ValueError, match="beyond the split protocol"):
        compare(tmp_path/"time", tmp_path/"different_budget", tmp_path/"invalid.json")


def test_recorded_time_run_remains_unverified_and_cannot_export(tmp_path):
    data = generate(tmp_path/"data", 200)
    config = Config(provenance="real", timestamp_policy="recorded_unverified",
                    models=("rf",), seeds=(42,), rf_trees=3, min_calibration_benign=3)
    exp = tmp_path/"exp"
    manifest = prepare(data, config, exp, "%Y-%m-%d %H:%M:%S")
    assert manifest["timestamp_review"]["timestamp_status"] == "unverified"
    train(exp)
    score(exp)
    with pytest.raises(ValueError, match="timestamp review"):
        export(exp, tmp_path/"paper")
    export(exp, tmp_path/"draft", draft=True)
    assert "DRAFT / REAL" in (tmp_path/"draft/main_table.tex").read_text()


def test_kaggle_discovery_and_explicit_time_format(tmp_path):
    from idsresearch.kaggle import EXPECTED, find_data, detect_time_format
    data = tmp_path/"datasets/solarmainframe/ids-intrusion-csv"
    data.mkdir(parents=True)
    for name in EXPECTED:
        month, day, year = name.removesuffix(".csv").split("-")
        (data/name).write_text(f'Timestamp,Label,f1\n{day}/{month}/{year} 13:45:27,Benign,1\n')
    assert find_data(tmp_path) == data
    assert detect_time_format(data, tmp_path/"check.json") == "%d/%m/%Y %H:%M:%S"
    report = read_json(tmp_path/"check.json")
    assert report["timestamp_status"] == "unverified"
    assert report["files"][0]["timestamp_examples"][0].endswith("13:45:27")
