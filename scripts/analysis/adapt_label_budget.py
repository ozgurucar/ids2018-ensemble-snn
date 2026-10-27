"""CIC-IDS2017 adaptation with explicit label accounting and matched FAR.

Re-runs the protocol of scripts/finetune_cic2017.py (same data loading, same
group split, same budgets, same training code, imported unchanged) and scores
every trained model under four decision-rule variants:

  orig       temperature on <=100k LABELLED 2017 calibration flows, threshold
             on benign alarm-calibration flows (the published setting;
             reproduces results/cross_dataset/finetune_cic2017.json)
  budget_T   temperature fitted only on the labelled budget (in-sample for the
             fitted model), threshold on benign alarm-calibration flows
  no_T       no temperature (T = 1), threshold on benign alarm-calibration flows
  strict     temperature and threshold both from the labelled budget only
             (threshold = 5% benign order statistic of in-sample budget scores;
             biased low, so test FAR is expected to overshoot)

For each run it records the labels used:
  labelled_flows      flows with a class label (budget + temperature rows)
  benign_only_flows   flows that must be known to be benign but need no
                      attack label (alarm-threshold rows)

and two matched-FAR views computed on the test ROC of the alarm score:
  dr_at_test_far_5pct, dr_at_test_far_1pct  (threshold set on test benign;
  an oracle view used only for comparison, never for a decision)

results/cross_dataset/finetune_cic2017.json is left as it is. Output: results/analysis/adapt_label_budget.json

    python scripts/analysis/adapt_label_budget.py ~/.cache/ids-x17/combine.csv --seeds 42 43 44
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "app"), str(ROOT / "scripts"), str(HERE)]
import finetune_cic2017 as F  # noqa: E402
from detector import Detector  # noqa: E402
from idsresearch.decision import alarm_score, prior_offset, temperature_fit, threshold_fit  # noqa: E402
from idsresearch.groups import fingerprint, group_partition  # noqa: E402
from records import OUT, write  # noqa: E402
from sklearn.metrics import f1_score  # noqa: E402

VARIANTS = ("orig", "budget_T", "no_T", "strict")


def dr_at_far(score, attack, far):
    benign = score[~attack]
    t = threshold_fit(benign, far)["threshold"]
    return float((score[attack] > t).mean()), float((benign > t).mean())


def fit_temperature(logits, y, offset):
    usable = (y >= 0) & (offset[np.maximum(y, 0)] > F.MASK / 2)
    return temperature_fit(logits[usable] + offset, y[usable]), int(usable.sum())


def score_variants(logits_fn, offset, Zc, yc, prob_idx, alarm_idx, Zb, yb, Zt, yt, lt, present, frozen_temperature=None):
    Lc, Lt = logits_fn(Zc), logits_fn(Zt)
    Lb = logits_fn(Zb) if Zb is not None else None
    benign_alarm = alarm_idx[yc[alarm_idx] == 0]
    attack = lt != "BENIGN"
    out = {}
    for v in VARIANTS:
        if frozen_temperature is not None and v != "orig":
            continue
        labelled = 0 if Zb is None else len(yb)
        if frozen_temperature is not None:
            T, tinfo = frozen_temperature, {"fit": "2018 frozen"}
        elif v == "orig":
            t, n = fit_temperature(Lc[prob_idx], yc[prob_idx], offset)
            T, tinfo = t["temperature"], {"fit": "2017 calibration (labelled)", "n": n, "nll_before": t["nll_before"], "nll_after": t["nll_after"]}
            labelled += n
        elif v in ("budget_T", "strict"):
            t, n = fit_temperature(Lb, yb, offset)
            T, tinfo = t["temperature"], {"fit": "labelled budget (in-sample)", "n": n, "nll_before": t["nll_before"], "nll_after": t["nll_after"]}
        else:
            T, tinfo = 1.0, {"fit": "none"}
        if v == "strict":
            ben = Lb[yb == 0]
            rule = threshold_fit(alarm_score((ben + offset) / T), F.TAU, 50)
            benign_only = 0
        else:
            rule = threshold_fit(alarm_score((Lc[benign_alarm] + offset) / T), F.TAU, 1000)
            benign_only = len(benign_alarm)
        z = (Lt + offset) / T
        s = alarm_score(z)
        alarm = s > rule["threshold"]
        pred = np.where(alarm, z[:, 1:].argmax(1) + 1, 0)
        classed = yt >= 0
        d5, f5 = dr_at_far(s, attack, 0.05)
        d1, f1 = dr_at_far(s, attack, 0.01)
        per = {lab: float(alarm[lt == lab].mean()) for lab in sorted(np.unique(lt))}
        out[v] = {"temperature": T, "temperature_info": tinfo, "threshold": rule["threshold"],
                  "calibration_fpr": rule["empirical_calibration_fpr"], "threshold_benign_support": rule["benign_support"],
                  "labelled_flows": labelled, "benign_only_flows": benign_only,
                  "far": float(alarm[~attack].mean()), "detection_rate": float(alarm[attack].mean()),
                  "detection_rate_excl_portscan": float(alarm[attack & (yt != F.PORTSCAN)].mean()),
                  "macro_f1": float(f1_score(yt[classed], pred[classed], labels=present, average="macro", zero_division=0)),
                  "dr_at_test_far_5pct": d5, "achieved_test_far_5pct": f5, "dr_at_test_far_1pct": d1, "achieved_test_far_1pct": f1,
                  "alarm_rate_per_label": per}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv")
    ap.add_argument("--out", default="adapt_label_budget.json")
    ap.add_argument("--budgets", type=float, nargs="+", default=[0.001, 0.01, 0.05])
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    ap.add_argument("--split-seed", type=int, default=2017)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--methods", nargs="+", default=["esnn_t4_finetune", "xgb_scratch", "xgb_continue"])
    args = ap.parse_args()
    # Same fixed settings as the published run (finetune_cic2017.py defaults).
    lr, batch, min_steps, min_epochs, trees, extra = 1e-4, 256, 300, 5, 400, 100
    torch.set_num_threads(args.threads)
    t0 = time.perf_counter()

    esnn, xgbd = Detector("esnn_t4"), Detector("xgb")
    frame, raw_label, family = F.load(args.csv, esnn.input_columns)
    raw_label = raw_label.to_numpy()
    y = F.to_index(family)
    X = frame[esnn.input_columns].apply(pd.to_numeric, errors="coerce").astype(np.float32)
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    del frame
    groups = fingerprint(X)
    Z = np.concatenate([esnn.preprocessor.transform(X.iloc[s:s + 200000]) for s in range(0, len(X), 200000)])
    del X
    pool, cal, test = group_partition(groups, (0.5, 0.1, 0.4), args.split_seed)
    prob_local, alarm_local = group_partition(groups[cal], (.5, .5), args.split_seed + 177)
    rng = np.random.default_rng(args.split_seed + 178)
    prob_local = np.sort(rng.choice(prob_local, min(len(prob_local), 100000), replace=False))
    Zc, yc = Z[cal], y[cal]
    Zt, yt, lt = Z[test], y[test], raw_label[test]
    present = sorted(int(c) for c in np.unique(yt[yt >= 0]))
    print(f"loaded {len(y)} rows in {time.perf_counter() - t0:.0f}s; test {len(test)}", flush=True)

    report = {"protocol": "as scripts/finetune_cic2017.py (same split seeds, budgets, schedules); decision-rule variants: " + ", ".join(VARIANTS),
              "variants": {"orig": "T on <=100k labelled 2017 calibration flows; threshold on benign alarm-cal flows",
                           "budget_T": "T on the labelled budget only (in-sample); threshold on benign alarm-cal flows",
                           "no_T": "T = 1; threshold on benign alarm-cal flows",
                           "strict": "T and 5% threshold both from the labelled budget only (in-sample)"},
              "matched_far": "dr_at_test_far_*: DR at the threshold that gives exactly that FAR on test benign (oracle comparison view)",
              "runs": []}

    def rec(method, budget, seed, fn, offset, Zb=None, yb=None, frozen_T=None, info=None):
        res = score_variants(fn, offset, Zc, yc, prob_local, alarm_local, Zb, yb, Zt, yt, lt, present, frozen_T)
        report["runs"].append({"method": method, "budget": budget, "seed": seed, "budget_size": 0 if yb is None else int(len(yb)), "info": info, "variants": res})
        print(f"{method:17s} b={budget:<6} s={seed} " + " | ".join(f"{v}: FAR={r['far']:.4f} DR={r['detection_rate']:.4f} DR@5={r['dr_at_test_far_5pct']:.4f} T={r['temperature']:.3f}" for v, r in res.items()), flush=True)
        write(args.out, report)

    for name, det in (("esnn_t4", esnn), ("xgb", xgbd)):
        rec(f"frozen_recal_{name}", 0.0, None, lambda Z_, d=det: np.concatenate([d.logits(Z_), np.full((len(Z_), 1), np.log(1e-12))], 1),
            np.r_[det.offset, F.MASK], frozen_T=det.temperature)

    booster = xgbd.model["estimator"].get_booster()
    for budget in args.budgets:
        for seed in args.seeds:
            idx = F.stratified_budget(y, pool, budget, np.random.default_rng(seed * 1000 + int(budget * 1e5)))
            Zb, yb = Z[idx], y[idx]
            bc = np.bincount(yb, minlength=F.K)
            offset = prior_offset(bc, bc, np.ones(F.K))
            if "esnn_t4_finetune" in args.methods:
                model, info = F.finetune_esnn(esnn, esnn.config, Zb, yb, seed, lr, batch, min_steps, min_epochs)
                rec("esnn_t4_finetune", budget, seed, lambda Z_, m=model: F.esnn_logits(m, Z_), offset, Zb, yb, info={"epochs": info["epochs"]})
            if "xgb_scratch" in args.methods:
                fn, info = F.xgb_scratch(Zb, yb, seed, trees, args.threads)
                rec("xgb_scratch", budget, seed, fn, offset, Zb, yb, info=info)
            if "xgb_continue" in args.methods:
                fn, info = F.xgb_continue(booster, Zb, yb, seed, extra, args.threads)
                off = offset.copy(); off[F.PORTSCAN] = F.MASK
                rec("xgb_continue", budget, seed, fn, off, Zb, yb, info=info)
    report["seconds_total"] = time.perf_counter() - t0
    write(args.out, report)


if __name__ == "__main__":
    main()
