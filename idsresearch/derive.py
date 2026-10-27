"""Derive a model-only experiment from an existing prepared one.

Partitions, preprocessing and prepared arrays are reused byte for byte; only
fields that act after preprocessing may change. The parent manifest digest and
every array hash are checked first, and the parent identity is recorded.
"""
from pathlib import Path
import shutil

from .config import Config
from .provenance import digest, environment, file_hash, read_json, source_manifest, write_json

# Fields that do not touch partitioning, preprocessing or calibration rules.
# Seeds never touch the partition (tests/test_contracts.py); dropped features are removed
# from the prepared arrays at load time, after preprocessing.
MODEL_ONLY = {"steps", "populations", "hidden", "models", "epochs", "patience", "dropout", "lr", "alpha", "branches",
              "seeds", "drop_features", "ple_bins"}


def derive(parent, out, changes, link=True):
    parent, out = Path(parent), Path(out)
    if (out/"manifest.json").exists():
        raise ValueError("Derived experiment already exists; choose a new directory")
    if set(changes) - MODEL_ONLY:
        raise ValueError(f"Only model fields may change: {sorted(set(changes) - MODEL_ONLY)}")
    manifest = read_json(parent/"manifest.json")
    if digest({k: v for k, v in manifest.items() if k != "experiment_id"}) != manifest["experiment_id"]:
        raise ValueError("Parent manifest was modified after preparation")
    for name, expected in manifest["array_hashes"].items():
        if file_hash(parent/name) != expected:
            raise ValueError(f"Parent array changed: {name}")
    if file_hash(parent/"feature-group-audit.json") != manifest["feature_audit_sha256"]:
        raise ValueError("Parent feature audit was modified")
    config = Config(**{**manifest["config"], **changes}).validate()
    out.mkdir(parents=True, exist_ok=True)
    for name in [*manifest["array_hashes"], "preprocessor.joblib", "feature-group-audit.json", "audit.json"]:
        source = (parent/name).resolve()
        if link:
            (out/name).symlink_to(source)
        else:
            shutil.copy2(source, out/name)
    current = environment()
    if current["packages"] != manifest["preparation_environment"]["packages"]:
        raise ValueError("Package versions differ from the parent preparation; restore its lock file")
    derived = {**manifest, "config": config.dictionary(), "sources": source_manifest(),
               "preparation_environment": current,
               "parent": {"experiment_id": manifest["experiment_id"], "changes": changes,
                          "sources": manifest["sources"], "preprocessor_sha256": file_hash(parent/"preprocessor.joblib")}}
    derived.pop("experiment_id")
    derived["experiment_id"] = digest(derived)
    write_json(out/"manifest.json", derived)
    return derived
