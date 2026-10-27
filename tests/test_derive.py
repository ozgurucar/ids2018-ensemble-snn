import numpy as np
import pytest

from idsresearch.config import Config
from idsresearch.derive import derive
from idsresearch.pipeline import prepare, score, train, validated, verify_arrays
from idsresearch.provenance import read_json
from idsresearch.synthetic import generate


@pytest.fixture
def smoke_experiment(tmp_path):
    config = Config(provenance="synthetic", models=("esnn",), seeds=(42,), epochs=1, hidden=(8, 4), steps=4,
                    batch_size=128, train_cap=1000, rare_preserve=10, min_calibration_benign=3)
    prepare(generate(tmp_path/"data", 200), config, tmp_path/"parent", "%Y-%m-%d %H:%M:%S")
    return tmp_path/"parent"


def test_derive_reuses_arrays_and_changes_only_model_fields(smoke_experiment, tmp_path):
    child = derive(smoke_experiment, tmp_path/"t2", {"steps": 2})
    manifest, config = validated(tmp_path/"t2")
    verify_arrays(tmp_path/"t2", manifest, ("train", "tune", "calibration", "test"))
    parent = read_json(smoke_experiment/"manifest.json")
    assert config.steps == 2 and child["parent"]["experiment_id"] == parent["experiment_id"]
    assert child["experiment_id"] != parent["experiment_id"] and child["split"] == parent["split"]
    train(tmp_path/"t2")
    score(tmp_path/"t2")
    assert (tmp_path/"t2"/"runs"/"esnn-42"/"evaluated.json").exists()
    with pytest.raises(ValueError):
        derive(smoke_experiment, tmp_path/"bad", {"split_seed": 1})


def test_derive_rejects_modified_parent(smoke_experiment, tmp_path):
    manifest = read_json(smoke_experiment/"manifest.json")
    name = next(iter(manifest["array_hashes"]))
    np.save(smoke_experiment/name, np.zeros(3), allow_pickle=False)
    with pytest.raises(ValueError):
        derive(smoke_experiment, tmp_path/"t2", {"steps": 2})


def test_dropped_feature_is_removed_after_preprocessing(smoke_experiment, tmp_path):
    from idsresearch.pipeline import arrays
    columns = read_json(smoke_experiment/"manifest.json")["preprocessing"]["selected_columns"]
    derive(smoke_experiment, tmp_path/"noport", {"drop_features": [columns[0]], "seeds": [7]})
    X, _ = arrays(tmp_path/"noport", "train")
    full, _ = arrays(smoke_experiment, "train")
    assert X.shape[1] == full.shape[1]-1
    np.testing.assert_array_equal(X, np.asarray(full)[:, 1:])
    train(tmp_path/"noport")
    assert (tmp_path/"noport"/"runs"/"esnn-7"/"trained.json").exists()
    with pytest.raises(ValueError):
        derive(smoke_experiment, tmp_path/"bad", {"drop_features": ["no such column"]})
        arrays(tmp_path/"bad", "train")


def test_ple_mlp_is_parameter_matched_and_trains(smoke_experiment, tmp_path):
    import torch
    from idsresearch.data import CLASSES
    from idsresearch.models import build
    config = Config(hidden=(128, 64))
    esnn = sum(p.numel() for p in build("esnn", 70, len(CLASSES), config).parameters())
    ple = build("ple_mlp", 70, len(CLASSES), config)
    assert abs(sum(p.numel() for p in ple.parameters())-esnn)/esnn < 0.05
    assert ple(torch.rand(5, 70)).shape == (5, len(CLASSES))
    derive(smoke_experiment, tmp_path/"ple", {"models": ["ple_mlp"]})
    train(tmp_path/"ple")
    score(tmp_path/"ple")
    assert (tmp_path/"ple"/"runs"/"ple_mlp-42"/"evaluated.json").exists()


def test_ple_ensemble_matches_esnn_size_and_trains(smoke_experiment, tmp_path):
    import torch
    from idsresearch.data import CLASSES
    from idsresearch.models import build
    config = Config(hidden=(128, 64))
    esnn = sum(p.numel() for p in build("esnn", 70, len(CLASSES), config).parameters())
    ple = build("ple_ensemble", 70, len(CLASSES), config)
    assert abs(sum(p.numel() for p in ple.parameters())-esnn)/esnn < 0.05
    assert ple(torch.rand(5, 70)).shape == (5, len(CLASSES))
    derive(smoke_experiment, tmp_path/"plee", {"models": ["ple_ensemble"]})
    train(tmp_path/"plee")
    score(tmp_path/"plee")
    assert (tmp_path/"plee"/"runs"/"ple_ensemble-42"/"evaluated.json").exists()
