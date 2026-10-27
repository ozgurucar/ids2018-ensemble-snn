"""Item 2: macro-F1 over identifiable classes, as a co-primary metric.

From the per-class test F1 stored in every run record, for every
(label, model, seed, tau):

  macro_f1_13            13-class macro-F1 as in the paper
  macro_f1_11            without FTP-BruteForce and DoS-SlowHTTPTest, whose
                         feature vectors are almost all label-conflicted
                         (feature-group-audit.json)
  macro_f1_10            additionally without Infiltration
  adr                    attack detection rate (any attack class alarmed)
  adr_excl_infiltration  ADR over attack rows that are not Infiltration
                         (from the stored confusion matrix)

Also writes the per-class F1 table for all six models (CatBoost and
DDoS-LOIC-UDP included).

    python scripts/analysis/identifiable_macro_f1.py [--summary T12=results/v5/.../summary.json]
"""
import argparse

import numpy as np

from records import (CLASSES, MODEL_NAMES, OUT, TAUS, add_summary_argument, describe, load, per_class, point, write)

ORDER = ("esnn", "ann", "encoded_ann", "rf", "catboost", "xgb")
KEYS = ("macro_f1_13", "macro_f1_11", "macro_f1_10", "adr", "adr_excl_infiltration", "fpr")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_summary_argument(ap)
    args = ap.parse_args()
    data, sources, conflicts = load(args.summary, not args.no_defaults)

    per_run, agg = [], {}
    for label, by_model in data.items():
        for model, runs in by_model.items():
            for tau in TAUS:
                for seed, run in sorted(runs.items()):
                    per_run.append({"label": label, "model": model, "seed": seed, "tau": tau, **point(run, tau)})
                agg.setdefault(label, {}).setdefault(model, {})[tau] = {
                    k: describe([r[k] for r in per_run if r["label"] == label and r["model"] == model and r["tau"] == tau]) for k in KEYS}

    # Per-class F1 (mean over seeds) at each tau, primary label.
    perclass = {}
    for model, runs in data["T12"].items():
        for tau in TAUS:
            f1 = {c: float(np.mean([per_class(r["operating_points"][tau]["test"])[c]["f1"] for r in runs.values()])) for c in CLASSES}
            perclass.setdefault(model, {})[tau] = f1

    # Rankings.
    ranking = {}
    for tau in TAUS:
        for k in ("macro_f1_13", "macro_f1_11", "macro_f1_10"):
            order = sorted(ORDER, key=lambda m: -agg["T12"][m][tau][k]["mean"])
            ranking.setdefault(tau, {})[k] = [(m, round(agg["T12"][m][tau][k]["mean"], 4)) for m in order]

    write("identifiable_macro_f1.json", {"sources": sources, "seed_conflicts": conflicts,
          "definition": {"macro_f1_11": "mean per-class test F1 over the 13 classes minus FTP-BruteForce and DoS-SlowHTTPTest",
                         "macro_f1_10": "macro_f1_11 minus Infiltration",
                         "adr_excl_infiltration": "1 - (attack rows predicted Benign)/(attack rows), Infiltration rows removed"},
          "aggregate": agg, "per_run": per_run, "per_class_f1_T12_mean": perclass, "ranking_T12": ranking})

    def ms(d, digits=3):
        return f"{d['mean']:.{digits}f} ± {d['sd']:.{digits}f}" if d["sd"] is not None else f"{d['mean']:.{digits}f}"

    L = ["# Identifiable-class macro-F1 (item 2)", "",
         "Source: per-class test F1 and confusion matrices in the run records (`scripts/analysis/identifiable_macro_f1.py`).",
         "JSON: `results/analysis/identifiable_macro_f1.json` (every label, model, seed and budget).", ""]
    for tau in TAUS:
        L += [f"## T = 12, tau = {float(tau):.0%} (mean ± s.d., three seeds)", "",
              "| Model | MF1 (13 cl.) | MF1 (11 cl.) | MF1 (10 cl., also no Infiltration) | ADR | ADR excl. Infiltration | FPR |", "|---|---|---|---|---|---|---|"]
        for m in ORDER:
            a = agg["T12"][m][tau]
            L.append(f"| {MODEL_NAMES[m]} | {ms(a['macro_f1_13'])} | {ms(a['macro_f1_11'])} | {ms(a['macro_f1_10'])} | {ms(a['adr'])} | {ms(a['adr_excl_infiltration'])} | {a['fpr']['mean']:.3f} |")
        L += ["", "Ranking 13-class: " + " > ".join(f"{MODEL_NAMES[m]} {v:.3f}" for m, v in ranking[tau]["macro_f1_13"]),
              "", "Ranking 11-class: " + " > ".join(f"{MODEL_NAMES[m]} {v:.3f}" for m, v in ranking[tau]["macro_f1_11"]), ""]
    L += ["## Time window and other E-SNN settings (tau = 5% and 1%)", "",
          "| Setting | Model | seeds | MF1-13 @5% | MF1-11 @5% | MF1-13 @1% | MF1-11 @1% | ADR excl. Inf. @5% |", "|---|---|---|---|---|---|---|---|"]
    for label in data:
        for m in ORDER:
            if m not in agg[label]:
                continue
            a, b = agg[label][m]["0.05"], agg[label][m]["0.01"]
            L.append(f"| {label} | {MODEL_NAMES[m]} | {a['macro_f1_13']['n']} | {ms(a['macro_f1_13'])} | {ms(a['macro_f1_11'])} | {ms(b['macro_f1_13'])} | {ms(b['macro_f1_11'])} | {ms(a['adr_excl_infiltration'])} |")
    L += ["", "## Per-class test F1, tau = 5%, T = 12, mean of three seeds", "",
          "| Class | " + " | ".join(MODEL_NAMES[m] for m in ORDER) + " |", "|---|" + "---|" * len(ORDER)]
    for c in CLASSES:
        L.append(f"| {c} | " + " | ".join(f"{perclass[m]['0.05'][c]:.3f}" for m in ORDER) + " |")
    (OUT / "identifiable_macro_f1_table.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
