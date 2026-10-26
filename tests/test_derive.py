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
