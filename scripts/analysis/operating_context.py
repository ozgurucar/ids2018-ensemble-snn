"""Operating-point context from the run records.

For every model of the primary T = 12 experiment (and the T = 4 / T = 8 runs):
  * per-day test FPR and ADR at the 5% budget (diagnostics.per_recorded_day),
  * decision ablations at tau = 5%: raw logits, prior offset only, full rule
    (prior offset + temperature), each with its own 5% threshold,
  * argmax operating points: uncalibrated argmax and prior-corrected argmax,
  * test NLL / multiclass Brier after calibration, binary AP and standardized
    partial AUC; probability-calibration NLL before/after temperature where the
    per-run calibration.json is stored; ECE is not in the records and cannot be
    computed without per-row test probabilities,
  * where the missed attacks are at each budget (share that is Infiltration),
  * the model ranking at tau = 1%, 5%, 10%.

    python scripts/analysis/operating_context.py [--summary T12=...]
"""
import argparse
import json

import numpy as np

from records import (CLASSES, CONFLICTED, MODEL_NAMES, OUT, ROOT, TAUS, add_summary_argument, describe, load, macro_f1, write)

ORDER = ("esnn", "ann", "encoded_ann", "rf", "catboost", "xgb")
RUN_DIRS = {"T12": ROOT / "results/v3/experiments/group_ce/runs", "T12_weighted": ROOT / "results/v3/experiments/group_weighted/runs"}


def summarize_test(t):
    return {"fpr": t["fpr"], "adr": t["adr"], "macro_f1_13": t["macro_f1"], "macro_f1_11": macro_f1(t, CONFLICTED)}


def misses(t):
    cm = np.asarray(t["confusion_matrix"], float)
    missed = cm[1:, 0]
    total = missed.sum()
    inf = CLASSES.index("Infiltration") - 1
    return {"missed_attacks": int(total), "missed_infiltration": int(missed[inf]),
            "infiltration_share_of_misses": float(missed[inf] / total) if total else None,
            "attack_rows": int(cm[1:].sum()), "infiltration_rows": int(cm[inf + 1].sum()),
            "infiltration_share_of_attacks": float(cm[inf + 1].sum() / cm[1:].sum()),
            "missed_by_class": {CLASSES[i + 1]: int(m) for i, m in enumerate(missed) if m}}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_summary_argument(ap)
    args = ap.parse_args()
    data, sources, conflicts = load(args.summary, not args.no_defaults)
    out = {"sources": sources, "seed_conflicts": conflicts, "ece": "not available: records hold no per-row test probabilities (test arrays are on Kaggle only)"}

    for label in ("T12", "T4", "T8", "T12_weighted", "T8_wide"):
        if label not in data:
            continue
        res = {}
        for model in ORDER:
            runs = data[label].get(model)
            if not runs:
                continue
            r = {"per_day": {}, "ablation": {}, "argmax": {}, "probabilistic": {}, "misses": {}}
            days = sorted(next(iter(runs.values()))["diagnostics"]["per_recorded_day"])
            for d in days:
                rows = [run["diagnostics"]["per_recorded_day"][d] for run in runs.values()]
                r["per_day"][d] = {"benign": rows[0]["benign"], "attack": rows[0]["attack"],
                                   "fpr": describe([x["fpr"] for x in rows]), "adr": describe([x["adr"] for x in rows])}
            means = {d: v["fpr"]["mean"] for d, v in r["per_day"].items()}
            allv = [run["diagnostics"]["per_recorded_day"][d]["fpr"] for run in runs.values() for d in days]
            r["per_day_fpr_range_of_seed_means"] = [min(means.values()), max(means.values())]
            r["per_day_fpr_range_all_seeds"] = [min(allv), max(allv)]
            r["per_day_argmin_argmax"] = [min(means, key=means.get), max(means, key=means.get)]
            for name in ("raw", "prior_only"):
                r["ablation"][name] = {k: describe([summarize_test(run["decision_ablations"][name]["test"])[k] for run in runs.values()])
                                       for k in ("fpr", "adr", "macro_f1_13", "macro_f1_11")}
            r["ablation"]["full"] = {k: describe([summarize_test(run["operating_points"]["0.05"]["test"])[k] for run in runs.values()])
                                     for k in ("fpr", "adr", "macro_f1_13", "macro_f1_11")}
            for name in ("uncalibrated", "corrected_argmax"):
                r["argmax"][name] = {k: describe([summarize_test(run[name])[k] for run in runs.values()]) for k in ("fpr", "adr", "macro_f1_13", "macro_f1_11")}
            dg = lambda k: describe([run["diagnostics"][k] for run in runs.values()])
            r["probabilistic"] = {"test_nll": dg("nll"), "test_multiclass_brier": dg("multiclass_brier"),
                                  "binary_average_precision": dg("binary_average_precision"),
                                  "std_partial_auc_0.01": describe([run["diagnostics"]["standardized_partial_auc"]["0.01"] for run in runs.values()]),
                                  "std_partial_auc_0.05": describe([run["diagnostics"]["standardized_partial_auc"]["0.05"] for run in runs.values()]),
                                  "alarm_cal_nll": describe([run["alarm_calibration_diagnostics"]["nll"] for run in runs.values()])}
            temp = []
            if label in RUN_DIRS:
                for seed in runs:
                    p = RUN_DIRS[label] / f"{model}-{seed}" / "calibration.json"
                    if p.exists():
                        t = json.loads(p.read_text())["temperature"]
                        temp.append({"seed": seed, "temperature": t["temperature"], "nll_before": t["nll_before"], "nll_after": t["nll_after"], "n": t["n"]})
            r["temperature_fit"] = temp
            for tau in TAUS:
                r["misses"][tau] = [misses(run["operating_points"][tau]["test"]) for run in runs.values()]
            res[model] = r
        out[label] = res

    # Rankings (T = 12).
    rank = {}
    for tau in TAUS:
        for key in ("macro_f1_13", "macro_f1_11"):
            vals = {m: np.mean([summarize_test(run["operating_points"][tau]["test"])[key] for run in data["T12"][m].values()]) for m in ORDER}
            rank.setdefault(tau, {})[key] = sorted(vals.items(), key=lambda kv: -kv[1])
    out["ranking_T12"] = {t: {k: [[m, float(v)] for m, v in r] for k, r in d.items()} for t, d in rank.items()}
    order5 = [m for m, _ in rank["0.05"]["macro_f1_13"]]
    out["ranking_same_as_5pct"] = {t: [m for m, _ in rank[t]["macro_f1_13"]] == order5 for t in TAUS}
    write("operating_context.json", out)

    # ---------------------------------------------------------------- markdown
    T = out["T12"]
    L = ["# Operating-point context", "", "Source: run records; script `scripts/analysis/operating_context.py`; JSON `results/analysis/operating_context.json`.", "",
         "## Per-day test FPR at the 5% budget (T = 12, mean over seeds)", "",
         "| Day | benign rows | " + " | ".join(MODEL_NAMES[m] for m in ORDER) + " |", "|---|---|" + "---|" * len(ORDER)]
    for d in T["esnn"]["per_day"]:
        L.append(f"| {d} | {T['esnn']['per_day'][d]['benign']:,} | " + " | ".join(f"{T[m]['per_day'][d]['fpr']['mean']:.3f}" for m in ORDER) + " |")
    L.append("| range (seed means) | | " + " | ".join(f"{T[m]['per_day_fpr_range_of_seed_means'][0]:.3f}-{T[m]['per_day_fpr_range_of_seed_means'][1]:.3f}" for m in ORDER) + " |")
    L.append("| range (any seed) | | " + " | ".join(f"{T[m]['per_day_fpr_range_all_seeds'][0]:.3f}-{T[m]['per_day_fpr_range_all_seeds'][1]:.3f}" for m in ORDER) + " |")
    L += ["", "## Decision ablation at tau = 5% (T = 12, mean ± s.d.)", "", "| Model | Rule | FPR | ADR | MF1-13 | MF1-11 |", "|---|---|---|---|---|---|"]
    for m in ORDER:
        for name in ("raw", "prior_only", "full"):
            a = T[m]["ablation"][name]
            L.append(f"| {MODEL_NAMES[m]} | {name} | {a['fpr']['mean']:.3f} | {a['adr']['mean']:.3f} | {a['macro_f1_13']['mean']:.3f} ± {a['macro_f1_13']['sd']:.3f} | {a['macro_f1_11']['mean']:.3f} ± {a['macro_f1_11']['sd']:.3f} |")
    L += ["", "## Argmax operating points (T = 12, mean over seeds)", "", "| Model | Decision | FPR | ADR | MF1-13 | MF1-11 |", "|---|---|---|---|---|---|"]
    for m in ORDER:
        for name in ("uncalibrated", "corrected_argmax"):
            a = T[m]["argmax"][name]
            L.append(f"| {MODEL_NAMES[m]} | {name} | {a['fpr']['mean']:.4f} | {a['adr']['mean']:.3f} | {a['macro_f1_13']['mean']:.3f} ± {a['macro_f1_13']['sd']:.3f} | {a['macro_f1_11']['mean']:.3f} ± {a['macro_f1_11']['sd']:.3f} |")
    L += ["", "## Probabilistic quality (T = 12, mean over seeds)", "",
          "| Model | prob-cal NLL before T | after T | fitted T | test NLL | test Brier | binary AP | std pAUC@1% |", "|---|---|---|---|---|---|---|---|"]
    for m in ORDER:
        p, t = T[m]["probabilistic"], T[m]["temperature_fit"]
        nb = np.mean([x["nll_before"] for x in t]) if t else None
        na = np.mean([x["nll_after"] for x in t]) if t else None
        tt = np.mean([x["temperature"] for x in t]) if t else None
        L.append(f"| {MODEL_NAMES[m]} | {nb:.4f} | {na:.4f} | {tt:.3f} | {p['test_nll']['mean']:.4f} | {p['test_multiclass_brier']['mean']:.4f} | {p['binary_average_precision']['mean']:.4f} | {p['std_partial_auc_0.01']['mean']:.4f} |")
    L += ["", "ECE: " + out["ece"] + ".", "", "## Where the misses are (T = 12, seed means)", "", "| Model | tau | missed attacks | of which Infiltration | share |", "|---|---|---|---|---|"]
    for m in ORDER:
        for tau in TAUS:
            ms = T[m]["misses"][tau]
            L.append(f"| {MODEL_NAMES[m]} | {tau} | {np.mean([x['missed_attacks'] for x in ms]):,.0f} | {np.mean([x['missed_infiltration'] for x in ms]):,.0f} | {np.mean([x['infiltration_share_of_misses'] for x in ms]):.4f} |")
    L += ["", "## Ranking by 13-class macro-F1 (T = 12)", ""]
    for tau in TAUS:
        L.append(f"- tau = {tau}: " + " > ".join(f"{MODEL_NAMES[m]} {v:.3f}" for m, v in rank[tau]["macro_f1_13"]) + f" (same order as 5%: {out['ranking_same_as_5pct'][tau]})")
    L += ["", "## Ranking by 11-class macro-F1 (T = 12)", ""]
    for tau in TAUS:
        L.append(f"- tau = {tau}: " + " > ".join(f"{MODEL_NAMES[m]} {v:.3f}" for m, v in rank[tau]["macro_f1_11"]))
    (OUT / "operating_context_table.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
