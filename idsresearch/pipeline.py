from dataclasses import replace
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
import torch
from .config import Config
from .data import CLASSES, PARTS, Preprocessor, audit, counts, load, partition, training_subset
from .metrics import aggregate, evaluate, fit_alarm_threshold, predict, softmax
from .models import build
from .provenance import assert_sources, digest, environment, file_hash, read_json, source_manifest, write_json
from .training import neural_logits, train_neural, train_tree, tree_proba


def prepare(data_path, config, out, timestamp_format, time_review=None):
    out = Path(out)
    if (out/"manifest.json").exists():
        raise ValueError("Experiment already prepared; choose a new output directory")
    raw = load(data_path, timestamp_format, config.max_files)
    report = audit(raw)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out/"audit.json", report)
    if config.provenance == "real":
        review = read_json(time_review) if time_review else {}
        if (review.get("dataset_id") != raw.report["dataset_id"] or review.get("timestamp_status") != "verified"
                or not review.get("evidence") or not review.get("reviewer")):
            if config.timestamp_policy != "recorded_unverified":
                raise ValueError("Timestamp evidence must be reviewed for this exact dataset_id. Audit saved; provide a reviewed file with timestamp_status=verified, reviewer and evidence. Do not change status without checking the source timestamps.")
            review = {"dataset_id": raw.report["dataset_id"], "timestamp_status": "unverified",
                      "policy": "recorded_unverified", "reviewer": None,
                      "evidence": "Automatic run on recorded CSV timestamps. Parsing is checked; capture-clock semantics and AM/PM are not independently verified. No timestamp repair is applied.",
                      "interpretation": "Exploratory temporal results; normal paper export remains blocked."}
    else:
        marker = Path(data_path)/"SYNTHETIC.json"
        if not marker.exists():
            raise ValueError("Synthetic provenance requires the synthetic generator marker")
        review = {"timestamp_status": "synthetic", "evidence": "Generated timestamps; not real-data evidence"}
    splits, split_report = partition(raw, config)
    full_train = splits["train"].copy()
    keep = training_subset(raw.y[full_train], config.train_cap, config.rare_preserve, config.split_seed)
    splits["train"] = full_train[keep]
    from .groups import fingerprint, group_audit
    feature_groups = fingerprint(raw.X)
    write_json(out/"feature-group-audit.json", group_audit(feature_groups, raw.y, CLASSES))
    preprocessing = Preprocessor(config).fit(raw.X.iloc[splits["train"]])
    joblib.dump(preprocessing, out/"preprocessor.joblib")
    array_hashes = {}
    for part, index in splits.items():
        # Transform in chunks so full test/validation copies need not coexist.
        destination = out/f"{part}_X.npy"
        arr = np.lib.format.open_memmap(destination, mode="w+", dtype="float32", shape=(len(index), len(preprocessing.columns_)))
        for start in range(0, len(index), 100000):
            arr[start:start+100000] = preprocessing.transform(raw.X.iloc[index[start:start+100000]])
        arr.flush()
        del arr
        for suffix, values in (("y", raw.y[index]), ("ids", raw.ids[index]), ("time", raw.time[index]), ("groups", feature_groups[index])):
            np.save(out/f"{part}_{suffix}.npy", values, allow_pickle=False)
        array_hashes.update({p.name: file_hash(p) for p in out.glob(f"{part}_*.npy")})
    from .groups import fingerprint
    transformed_train = fingerprint(pd.DataFrame(np.load(out/"train_X.npy", mmap_mode="r")))
    transformed_keys = np.unique(transformed_train)
    split_report["transformed_feature_overlap_with_train"] = {}
    for part in ("tune", "calibration", "test"):
        features = np.load(out/f"{part}_X.npy", mmap_mode="r")
        h = fingerprint(pd.DataFrame(features))
        split_report["transformed_feature_overlap_with_train"][part] = {
            "rows": int(np.isin(h, transformed_keys).sum()), "total": len(features),
            "note": "Train-fitted projection and quantile clipping may collapse distinct raw feature groups."}
    split_report["train_before_cap"] = counts(raw.y[full_train])
    split_report["train_after_cap"] = counts(raw.y[splits["train"]])
    split_report["discarded_training_rows"] = len(full_train)-len(keep)
    split_report["training_subset_id"] = digest(raw.ids[splits["train"]].tolist())
    feature_hashes = pd.util.hash_pandas_object(raw.X, index=False).to_numpy()
    train_hashes = np.unique(feature_hashes[splits["train"]])
    split_report["feature_row_hash_overlap_with_train"] = {
        part: {"rows": int(np.isin(feature_hashes[index], train_hashes).sum()), "total": len(index)}
        for part, index in splits.items() if part != "train"
    }
    manifest = {"schema": 3, "config": config.dictionary(), "dataset": raw.report,
                "timestamp_review": review, "split": split_report, "preprocessing": preprocessing.report(),
                "array_hashes": array_hashes, "sources": source_manifest(), "preparation_environment": environment(),
                "classes": list(CLASSES), "feature_audit_sha256": file_hash(out/"feature-group-audit.json")}
    manifest["experiment_id"] = digest(manifest)
    write_json(out/"manifest.json", manifest)
    print(f"Prepared {out}: {len(raw.y)} source rows retained; {len(keep)} training rows", flush=True)
    return manifest


def arrays(out, part):
    return np.load(Path(out)/f"{part}_X.npy", mmap_mode="r"), np.load(Path(out)/f"{part}_y.npy", allow_pickle=False)


def validated(out):
    manifest = read_json(Path(out)/"manifest.json")
    identity = manifest["experiment_id"]
    if digest({k: v for k, v in manifest.items() if k != "experiment_id"}) != identity:
        raise ValueError("Manifest was modified after preparation")
    assert_sources(manifest)
    if file_hash(Path(out)/"feature-group-audit.json") != manifest["feature_audit_sha256"]:
        raise ValueError("Feature audit was modified")
    if environment()["packages"] != manifest["preparation_environment"]["packages"]:
        raise ValueError("Package versions changed since preparation. Restore the saved environment or prepare a separate experiment.")
    return manifest, Config(**manifest["config"]).validate()


def verify_arrays(out, manifest, parts):
    for name, expected in manifest["array_hashes"].items():
        if name.split("_")[0] in parts and file_hash(Path(out)/name) != expected:
            raise ValueError(f"Prepared data was modified: {name}")


def selected(config, models=None, seeds=None):
    models, seeds = models or config.models, seeds or config.seeds
    if set(models)-set(config.models) or set(seeds)-set(config.seeds):
        raise ValueError("Requested models/seeds must be declared in config before preparation")
    return models, seeds


def train(out, models=None, seeds=None, device="cpu"):
    out = Path(out)
    manifest, config = validated(out)
    models, seeds = selected(config, models, seeds)
    verify_arrays(out, manifest, ("train", "tune"))
    X, y = arrays(out, "train")
    tune_X, tune_y = arrays(out, "tune")
    # This stage never opens calibration or test arrays.
    for model_name in models:
        for seed in seeds:
            run = out/"runs"/f"{model_name}-{seed}"
            status = run/"trained.json"
            if status.exists():
                previous = read_json(status)
                if previous["experiment_id"] == manifest["experiment_id"] and file_hash(run/previous["checkpoint"]) == previous["checkpoint_sha256"]:
                    print(f"Already trained: {run.name}")
                    continue
                raise ValueError(f"Existing run is inconsistent: {run}")
            run.mkdir(parents=True, exist_ok=True)
            if model_name in ("rf", "xgb", "catboost"):
                model, info = train_tree(model_name, X, y, config, seed, tune_X, tune_y)
                proba = tree_proba(model, tune_X)
                checkpoint = "model.joblib"
                joblib.dump(model, run/checkpoint)
            else:
                model, info = train_neural(model_name, X, y, tune_X, tune_y, config, seed, device, run/"resume.pt", [manifest["split"]["train_before_cap"][c] for c in CLASSES])
                proba = softmax(neural_logits(model, tune_X, config.batch_size, device))
                checkpoint = "model.pt"
                torch.save(model.cpu().state_dict(), run/checkpoint)
            info.update({"model": model_name, "seed": seed, "experiment_id": manifest["experiment_id"],
                         "checkpoint": checkpoint, "checkpoint_sha256": file_hash(run/checkpoint),
                         "tune_metrics": evaluate(tune_y, proba.argmax(1), proba),
                         "environment": environment(), "device": device})
            np.save(run/"tune_proba.npy", proba, allow_pickle=False)
            write_json(status, info)
    return out


def load_model(run, info, config, n_features):
    if file_hash(run/info["checkpoint"]) != info["checkpoint_sha256"]:
        raise ValueError("Checkpoint digest does not match frozen training record")
    if info["model"] in ("rf", "xgb", "catboost"):
        # Load only checkpoints generated by this trusted local experiment.
        return joblib.load(run/info["checkpoint"])
    model = build(info["model"], n_features, len(CLASSES), config)
    model.load_state_dict(torch.load(run/info["checkpoint"], map_location="cpu", weights_only=True))
    return model



def summarize(out):
    out = Path(out)
    manifest, config = validated(out)
    rows, missing = {}, []
    for name in config.models:
        for seed in config.seeds:
            file = out/"runs"/f"{name}-{seed}"/"evaluated.json"
            if not file.exists():
                missing.append(f"{name}-{seed}")
                continue
            report = read_json(file)
            if report["experiment_id"] != manifest["experiment_id"]:
                raise ValueError(f"Mismatched result: {file}")
            if report.get("result_id") != digest({k: v for k, v in report.items() if k != "result_id"}):
                raise ValueError(f"Result content changed after evaluation: {file}")
            info = read_json(file.parent/"trained.json")
            if (info["experiment_id"] != manifest["experiment_id"]
                    or info["checkpoint_sha256"] != report["checkpoint_sha256"]
                    or file_hash(file.parent/info["checkpoint"]) != report["checkpoint_sha256"]
                    or file_hash(file.parent/"test_proba.npy") != report["test_proba_sha256"]
                    or file_hash(file.parent/"calibration.json") != report["calibration_sha256"]):
                raise ValueError(f"Result artifacts changed after evaluation: {file}")
            rows.setdefault(name, []).append(report)
    summary = {"experiment_id": manifest["experiment_id"], "provenance": config.provenance,
               "config": config.dictionary(), "missing_runs": missing,
               "aggregate": {name: {str(tau): aggregate([r["operating_points"][str(tau)]["test"] for r in reports]) for tau in config.taus} for name, reports in rows.items()},
               "per_seed": rows, "timestamp_status": manifest["timestamp_review"]["timestamp_status"]}
    write_json(out/"summary.json", summary)
    return summary


def score(out, models=None, seeds=None, device="cpu"):
    from .evaluation_v3 import score_v3
    return score_v3(out, models, seeds, device)
