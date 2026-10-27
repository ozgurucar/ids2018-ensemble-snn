"""Item 7: Dst Port ablation (v5 noport_T4) in-distribution and on CIC-IDS2017.

1. Copies the Kaggle records (summary.json, manifest.json, seed-42
   calibration.json; no checkpoints) into results/v5/noport/.
2. In-distribution: with-port vs without-port per-seed statistics at
   tau = 5% and 1% (13- and 11-class macro-F1, ADR, ADR excl. Infiltration):
   Welch test and seed-paired differences, plus per-class F1 differences.
   With-port references: E-SNN and Enc-ANN at T = 4 (results/v4/steps/summary_T4.json),
   XGBoost from results/v3/experiments/group_ce/summary.json (trees do not depend on T).
3. Transfer: the seed-42 no-port checkpoints and their with-port counterparts
   on CIC-IDS2017 with the protocol of scripts/cross_dataset_cic2017.py
   (frozen 2018 prior offset, temperature and 5% threshold; then the threshold
   refitted on a random half of 2017 benign flows, evaluated on the other half
   and all attacks; rng seed 2017), plus label-free ROC AUC and DR at an
   exact 5% test FAR. The no-port models see the 70 preprocessed columns minus
   Dst Port (dropped by index after preprocessor.transform). The with-port
   Enc-ANN T = 4 has no calibration record locally, so it is skipped.

    python scripts/analysis/noport.py ~/.cache/ids-x17/combine.csv [--src ~/.cache/ids-v5/noport/v5/noport_T4]
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "app"), str(ROOT / "scripts"), str(HERE)]
import cross_dataset_cic2017 as C  # noqa: E402
from detector import CONFIG, Detector  # noqa: E402
from idsresearch.config import Config  # noqa: E402
from idsresearch.data import CLASSES  # noqa: E402
from idsresearch.decision import alarm_score, threshold_fit  # noqa: E402
from idsresearch.models import build  # noqa: E402
from idsresearch.training import neural_logits, tree_proba  # noqa: E402
from records import OUT, describe, per_class, point, write  # noqa: E402
from seed_stats import holm, paired, welch  # noqa: E402

DEST = ROOT / "results/v5/noport"
WITH_PORT = {"esnn": ("results/v4/steps/summary_T4.json", "esnn"), "encoded_ann": ("results/v4/steps/summary_T4.json", "encoded_ann"),
             "xgb": ("results/v3/experiments/group_ce/summary.json", "xgb")}
METRICS = ("macro_f1_13", "macro_f1_11", "adr", "adr_excl_infiltration", "fpr")
NAMES = {"esnn": "E-SNN (T=4)", "encoded_ann": "Enc-ANN (T=4)", "xgb": "XGBoost"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def copy_records(src):
    DEST.mkdir(parents=True, exist_ok=True)
    for name in ("summary.json", "manifest.json"):
        shutil.copy2(src / name, DEST / name)
    for run in sorted((src / "runs").iterdir()):
        (DEST / "runs" / run.name).mkdir(parents=True, exist_ok=True)
        shutil.copy2(run / "calibration.json", DEST / "runs" / run.name / "calibration.json")


class Scorer:
    """Frozen model + 2018 decision rule, with optional Dst Port removal."""

    def __init__(self, name, model_kind, checkpoint, calibration, steps, drop_port):
        self.pre = joblib.load(ROOT / "app/models/preprocessor.joblib")
        rule = json.loads(Path(calibration).read_text())
        if sha(checkpoint) != rule["checkpoint_sha256"]:
            raise ValueError(f"{checkpoint} does not match {calibration}")
        self.offset = np.asarray(rule["training_prior_offset"])
        self.temperature = rule["temperature"]["temperature"]
        self.threshold = rule["thresholds"]["0.05"]["threshold"]
        cols = list(self.pre.columns_)
        self.keep = [i for i, c in enumerate(cols) if not (drop_port and c == "Dst Port")]
        self.kind = model_kind
        if model_kind == "xgb":
            self.model = joblib.load(checkpoint)
        else:
            cfg = Config(**{**Config.read(CONFIG).dictionary(), "steps": steps})
            self.model = build(model_kind, len(self.keep), len(CLASSES), cfg)
            self.model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
            self.model.eval()
        self.name = name

    def score(self, frame):
        X = np.concatenate([self.pre.transform(frame.iloc[s:s + 200000]) for s in range(0, len(frame), 200000)])[:, self.keep]
        if self.kind == "xgb":
            z = np.log(np.maximum(tree_proba(self.model, X).astype(float), 1e-12))
        else:
            with torch.no_grad():
                z = neural_logits(self.model, X, 4096, "cpu").astype(float)
        return alarm_score((z + self.offset) / self.temperature)


def transfer(scorer, frame, label):
    attack = (label != "BENIGN").to_numpy()
    s = scorer.score(frame)
    alarm = s > scorer.threshold
    rng = np.random.default_rng(2017)
    benign_idx = np.flatnonzero(~attack)
    fit = np.zeros(len(frame), bool)
    fit[rng.choice(benign_idx, len(benign_idx) // 2, replace=False)] = True
    local = float(np.quantile(s[fit], 0.95))
    la = s > local
    t5 = threshold_fit(s[~attack], 0.05)["threshold"]
    return {"false_alarm_rate": float(alarm[~attack].mean()), "detection_rate": float(alarm[attack].mean()),
            "recal_false_alarm_rate": float(la[~attack & ~fit].mean()), "recal_detection_rate": float(la[attack].mean()),
            "recal_per_label": {v: float(la[(label == v).to_numpy() & ~fit].mean()) for v in sorted(label.unique())},
            "roc_auc": float(roc_auc_score(attack, s)), "dr_at_exact_test_far_5pct": float((s[attack] > t5).mean())}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv")
    ap.add_argument("--src", default=str(Path.home() / ".cache/ids-v5/noport/v5/noport_T4"))
    ap.add_argument("--skip-transfer", action="store_true")
    args = ap.parse_args()
    src = Path(args.src)
    copy_records(src)
    torch.set_num_threads(8)

    nop = json.loads((DEST / "summary.json").read_text())["per_seed"]
    man = json.loads((DEST / "manifest.json").read_text())
    out = {"sources": {"noport": "results/v5/noport/summary.json", **{m: p for m, (p, _) in WITH_PORT.items()}},
           "config": {k: man["config"].get(k) for k in ("drop_features", "steps", "models", "seeds")}, "in_distribution": {}, "per_class_f1_diff": {}}

    # ---------------- in-distribution
    tests = []
    for model, (path, key) in WITH_PORT.items():
        wp = {int(r["seed"]): r for r in json.loads((ROOT / path).read_text())["per_seed"][key]}
        np_ = {int(r["seed"]): r for r in nop[model]}
        for tau in ("0.05", "0.01"):
            for m in METRICS:
                A = {s: point(r, tau)[m] for s, r in np_.items()}
                B = {s: point(r, tau)[m] for s, r in wp.items()}
                res = {"model": model, "tau": tau, "metric": m, "noport": describe(list(A.values())), "with_port": describe(list(B.values())),
                       "welch": welch(list(A.values()), list(B.values())), "paired": paired(A, B)}
                out["in_distribution"].setdefault(model, {}).setdefault(tau, {})[m] = res
                if m in ("macro_f1_13", "macro_f1_11"):
                    tests.append(res)
            pc = {c: float(np.mean([per_class(r["operating_points"][tau]["test"])[c]["f1"] for r in np_.values()])
                           - np.mean([per_class(r["operating_points"][tau]["test"])[c]["f1"] for r in wp.values()])) for c in CLASSES}
            out["per_class_f1_diff"].setdefault(model, {})[tau] = pc
    # Holm over the three models within each (metric, tau).
    for tau in ("0.05", "0.01"):
        for m in ("macro_f1_13", "macro_f1_11"):
            fam = [t for t in tests if t["tau"] == tau and t["metric"] == m]
            for k in ("welch", "paired"):
                for t, p in zip(fam, holm([t[k]["p"] for t in fam])):
                    t[k]["p_holm3"] = p

    # ---------------- transfer
    if not args.skip_transfer:
        frame, label, _ = C.load(args.csv, Detector("esnn").input_columns)
        frame = frame.apply(pd.to_numeric, errors="coerce").astype(np.float32).replace([np.inf, -np.inf], np.nan).fillna(0)
        enc_wp_ckpt = Path.home() / ".cache/ids-v4/steps/v4/group_ce_T4/runs/encoded_ann-42/model.pt"
        enc_wp_cal = enc_wp_ckpt.parent / "calibration.json"
        scorers = {
            "esnn_T4_noport": ("esnn", src / "runs/esnn-42/model.pt", DEST / "runs/esnn-42/calibration.json", 4, True),
            "esnn_T4_port": ("esnn", ROOT / "app/models/esnn_t4.pt", ROOT / "app/models/esnn_t4_calibration.json", 4, False),
            "xgb_noport": ("xgb", src / "runs/xgb-42/model.joblib", DEST / "runs/xgb-42/calibration.json", 4, True),
            "xgb_port": ("xgb", ROOT / "app/models/xgb.joblib", ROOT / "app/models/xgb_calibration.json", 4, False),
            "encoded_ann_T4_noport": ("encoded_ann", src / "runs/encoded_ann-42/model.pt", DEST / "runs/encoded_ann-42/calibration.json", 4, True),
        }
        if enc_wp_cal.exists():
            scorers["encoded_ann_T4_port"] = ("encoded_ann", enc_wp_ckpt, enc_wp_cal, 4, False)
        out["transfer_skipped"] = [] if enc_wp_cal.exists() else ["encoded_ann_T4_port: no calibration.json for the with-port Enc-ANN T=4 checkpoint locally"]
        out["transfer"] = {}
        for key, (kind, ck, cal, T, drop) in scorers.items():
            r = transfer(Scorer(key, kind, ck, cal, T, drop), frame, label)
            out["transfer"][key] = r
            print(key, {k: round(v, 4) for k, v in r.items() if isinstance(v, float)}, flush=True)
            write("noport.json", out)
        old = json.loads((ROOT / "results/cross_dataset/cic2017.json").read_text())["models"]
        out["transfer_check_vs_cic2017_json"] = {
            k: abs(out["transfer"][k]["false_alarm_rate"] - old[o]["false_alarm_rate"]) + abs(out["transfer"][k]["recal_detection_rate"] - old[o]["site_recalibrated_5pct"]["detection_rate_all_attacks"])
            for k, o in (("esnn_T4_port", "esnn_t4"), ("xgb_port", "xgb"))}
    write("noport.json", out)

    # ---------------- markdown table
    L = ["# Dst Port ablation (item 7)", "", "Script `scripts/analysis/noport.py`; JSON `results/analysis/noport.json`; records copied to `results/v5/noport/`.", "",
         "## In-distribution (three seeds; diff = without port minus with port, points x 0.01)", "",
         "| Model | tau | metric | with port | without port | diff | Welch 95% CI | p Welch (Holm 3) | paired diffs | p paired (Holm 3) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for model in WITH_PORT:
        for tau in ("0.05", "0.01"):
            for m in METRICS[:4]:
                r = out["in_distribution"][model][tau][m]
                w, p = r["welch"], r["paired"]
                hw = f" ({w['p_holm3']:.3f})" if "p_holm3" in w else ""
                hp = f" ({p['p_holm3']:.3f})" if "p_holm3" in p else ""
                L.append(f"| {NAMES[model]} | {tau} | {m} | {r['with_port']['mean']:.4f} ± {r['with_port']['sd']:.4f} | {r['noport']['mean']:.4f} ± {r['noport']['sd']:.4f} | "
                         f"{w['diff']:+.4f} | [{w['ci95'][0]:+.3f}, {w['ci95'][1]:+.3f}] | {w['p']:.3f}{hw} | {', '.join(f'{x:+.3f}' for x in p['differences'])} | {p['p']:.3f}{hp} |")
    L += ["", "## Per-class F1 difference at tau = 5% (without minus with port, mean over seeds)", "", "| Class | " + " | ".join(NAMES[m] for m in WITH_PORT) + " |", "|---|---|---|---|"]
    for c in CLASSES:
        L.append(f"| {c} | " + " | ".join(f"{out['per_class_f1_diff'][m]['0.05'][c]:+.3f}" for m in WITH_PORT) + " |")
    if "transfer" in out:
        L += ["", "## CIC-IDS2017 transfer (seed 42)", "", "| Model | FAR (2018 thr.) | DR (2018 thr.) | Recal. FAR | Recal. DR | ROC AUC | DR at exact 5% test FAR |", "|---|---|---|---|---|---|---|"]
        for k, r in out["transfer"].items():
            L.append(f"| {k} | {r['false_alarm_rate']:.3f} | {r['detection_rate']:.3f} | {r['recal_false_alarm_rate']:.3f} | {r['recal_detection_rate']:.3f} | {r['roc_auc']:.3f} | {r['dr_at_exact_test_far_5pct']:.3f} |")
        labels = sorted(next(iter(out["transfer"].values()))["recal_per_label"])
        L += ["", "Recalibrated per-label alarm rate:", "", "| Label | " + " | ".join(out["transfer"]) + " |", "|---|" + "---|" * len(out["transfer"])]
        for lab in labels:
            L.append(f"| {lab} | " + " | ".join(f"{out['transfer'][k]['recal_per_label'][lab]:.3f}" for k in out["transfer"]) + " |")
        L += ["", f"Skipped: {out['transfer_skipped']}. With-port reproduction check vs cic2017.json (sum abs diff): {out['transfer_check_vs_cic2017_json']}."]
    (OUT / "noport_table.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
