"""Frozen, test-independent score construction with compact error diagnostics."""
from pathlib import Path
import numpy as np
from scipy.stats import ks_2samp
from sklearn.metrics import average_precision_score, roc_auc_score
from .data import CLASSES, counts
from .decision import prior_offset, temperature_fit, log_probabilities, alarm_score, threshold_fit, predict_logits
from .groups import group_partition
from .metrics import evaluate
from .provenance import read_json, write_json, file_hash, digest, environment


def diagnostic(y, pred, logits, times, threshold):
    scores = alarm_score(logits)
    attack, benign = y != 0, y == 0
    tp = int(((pred != 0) & attack).sum())
    fp = int(((pred != 0) & benign).sum())
    rows = {}
    for c, label in enumerate(CLASSES):
        idx = np.flatnonzero(y == c)
        rows[label] = {"n": len(idx),
                       "alarm_rate": float((pred[idx] != 0).mean()) if len(idx) else None,
                       "alarm_recall": float((pred[idx] != 0).mean()) if c != 0 and len(idx) else None,
                       "correct_family_recall": float((pred[idx] == c).mean()) if len(idx) else None,
                       "score_quantiles": np.quantile(scores[idx], [0, .01, .1, .5, .9, .99, 1]).tolist() if len(idx) else []}
    days = np.asarray(times).astype("datetime64[D]")
    daily = {}
    for day in np.unique(days):
        mask = days == day
        n0, n1 = int((mask & benign).sum()), int((mask & attack).sum())
        daily[str(day)] = {"benign": n0, "attack": n1,
                           "fpr": float((pred[mask & benign] != 0).mean()) if n0 else None,
                           "adr": float((pred[mask & attack] != 0).mean()) if n1 else None}
    p = np.exp(log_probabilities(logits))
    return {"binary_average_precision": float(average_precision_score(attack, scores)) if attack.any() and benign.any() else None,
            "standardized_partial_auc": {str(t): float(roc_auc_score(attack, scores, max_fpr=t)) if attack.any() and benign.any() else None for t in (.01, .05)},
            "alarm_precision": tp/(tp+fp) if tp+fp else None,
            "false_alarms_per_million_benign": fp/int(benign.sum())*1e6 if benign.any() else None,
            "nll": float(-log_probabilities(logits)[np.arange(len(y)), y].mean()),
            "multiclass_brier": float((np.square(p).sum(1)-2*p[np.arange(len(y)),y]+1).mean()),
            "per_class": rows, "per_recorded_day": daily,
            "threshold": threshold, "quantile_levels": [0, .01, .1, .5, .9, .99, 1]}


def score_v3(out, models=None, seeds=None, device="cpu"):
    from .pipeline import validated, selected, verify_arrays, arrays, load_model, summarize
    from .training import neural_logits, tree_proba
    out = Path(out)
    manifest, config = validated(out)
    models, seeds = selected(config, models, seeds)
    verify_arrays(out, manifest, ("calibration", "test"))
    cal_X, cal_y = arrays(out, "calibration")
    groups = np.load(out/"calibration_groups.npy", allow_pickle=False)
    prob_idx, alarm_idx = group_partition(groups, (.5, .5), config.split_seed+177)
    # Random subsampling without class rebalancing for the probability objective.
    rng = np.random.default_rng(config.split_seed+178)
    fit_idx = np.sort(rng.choice(prob_idx, min(len(prob_idx), config.calibration_fit_cap), replace=False))
    separation = {"probability_rows": len(prob_idx), "probability_fit_rows": len(fit_idx),
                  "alarm_rows": len(alarm_idx), "group_overlap": 0,
                  "probability_fit_class_counts": counts(cal_y[fit_idx]),
                  "alarm_class_counts": counts(cal_y[alarm_idx]),
                  "probability_ids_sha256": digest(np.load(out/"calibration_ids.npy")[fit_idx].tolist()),
                  "alarm_ids_sha256": digest(np.load(out/"calibration_ids.npy")[alarm_idx].tolist())}
    full = [manifest["split"]["train_before_cap"][c] for c in CLASSES]
    sample = [manifest["split"]["train_after_cap"][c] for c in CLASSES]
    test_X, test_y = arrays(out, "test")
    test_times = np.load(out/"test_time.npy")
    cal_times = np.load(out/"calibration_time.npy")
    for name in models:
        for seed in seeds:
            run = out/"runs"/f"{name}-{seed}"
            info = read_json(run/"trained.json")
            if info["experiment_id"] != manifest["experiment_id"]:
                raise ValueError("Training/evaluation experiment mismatch")
            if (run/"evaluated.json").exists():
                continue  # summarize below revalidates content and artifact hashes
            model = load_model(run, info, config, cal_X.shape[1])
            def logits(X):
                if name in ("rf", "xgb", "catboost"):
                    return np.log(np.maximum(tree_proba(model, X).astype(float), 1e-12))
                return neural_logits(model, X, config.batch_size, device).astype(float)
            cal_raw = logits(cal_X)
            offset = prior_offset(full, sample, info["class_weights"], config.prior_correction)
            temperature = temperature_fit(cal_raw[fit_idx]+offset, cal_y[fit_idx]) if config.probability_calibration else {"temperature": 1., "fit_partition": "none"}
            cal_z = (cal_raw+offset)/temperature["temperature"]
            cal_score = alarm_score(cal_z)
            thresholds = {str(t): threshold_fit(cal_score[alarm_idx][cal_y[alarm_idx] == 0], t,
                           config.min_calibration_benign, config.threshold_method, config.np_delta) for t in config.taus}
            ablation_rules = {label: threshold_fit(alarm_score(a[alarm_idx])[cal_y[alarm_idx]==0], config.primary_tau,
                                 config.min_calibration_benign, config.threshold_method, config.np_delta)
                               for label, a in (("raw", cal_raw), ("prior_only", cal_raw+offset))}
            rule = {"decision_ablation_thresholds": ablation_rules, "training_prior_offset": offset.tolist(), "temperature": temperature,
                    "partitions": separation, "thresholds": thresholds,
                    "prior_assumption": "CE optimum and unchanged class-conditional features; approximation for fitted models. Full training priors are not deployment priors.",
                    "checkpoint_sha256": info["checkpoint_sha256"]}
            # This record is written before the first test forward pass.
            write_json(run/"calibration.json", rule)
            test_raw = logits(test_X)
            test_z = (test_raw+offset)/temperature["temperature"]
            test_p = np.exp(log_probabilities(test_z))
            decision_ablations = {}
            for label, a, b in (("raw", cal_raw, test_raw), ("prior_only", cal_raw+offset, test_raw+offset)):
                ref = ablation_rules[label]
                # Thresholds depend only on calibration; all ablations are predeclared.
                decision_ablations[label] = {"calibration": ref,
                    "test": evaluate(test_y, predict_logits(b, ref['threshold']), np.exp(log_probabilities(b)))}
            np.save(run/"test_proba.npy", test_p, allow_pickle=False)
            np.save(run/"test_log_odds.npy", alarm_score(test_z), allow_pickle=False)
            points = {tau: {"calibration": t, "test": evaluate(test_y, predict_logits(test_z, t["threshold"]), test_p)} for tau,t in thresholds.items()}
            primary = thresholds[str(config.primary_tau)]["threshold"]
            report = {"model": name, "seed": seed, "experiment_id": manifest["experiment_id"],
                      "checkpoint_sha256": info["checkpoint_sha256"], "provenance": config.provenance,
                      "uncalibrated": evaluate(test_y, test_raw.argmax(1), np.exp(log_probabilities(test_raw))),
                      "corrected_argmax": evaluate(test_y, test_z.argmax(1), test_p),
                      "operating_points": points,
                      "decision_ablations": decision_ablations,
                      "diagnostics": diagnostic(test_y, predict_logits(test_z, primary), test_z, test_times, primary),
                      "alarm_calibration_diagnostics": diagnostic(cal_y[alarm_idx], predict_logits(cal_z[alarm_idx], primary), cal_z[alarm_idx], cal_times[alarm_idx], primary),
                      "benign_calibration_test_ks_distance": float(ks_2samp(cal_score[alarm_idx][cal_y[alarm_idx]==0], alarm_score(test_z)[test_y==0], method="asymp").statistic),
                      "calibration_sha256": file_hash(run/"calibration.json"),
                      "test_proba_sha256": file_hash(run/"test_proba.npy"),
                      "test_partition_id": manifest["split"]["split_id"], "environment": environment(),
                      "interpretation": "Development comparison. KS is descriptive; dependent rows invalidate naive significance claims."}
            report["result_id"] = digest(report)
            write_json(run/"evaluated.json", report)
            print(f"Evaluated v3 development model: {run.name}", flush=True)
    return summarize(out)
