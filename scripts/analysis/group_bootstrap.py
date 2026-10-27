"""Item 8: fingerprint-group bootstrap for the binary operating point.

Seed intervals (seed_stats.py) hold the split fixed. This script resamples the
test partition instead: whole feature-fingerprint groups are drawn with
replacement (Poisson(1) weights per group, so duplicated vectors always move
together), and every replicate re-scores all seeds of all models on the same
draw. That gives intervals for detection rate (DR), false-alarm rate (FAR) and
attack-vs-benign AUC that include test-sampling variance, and paired intervals
for model differences.

Thresholds are the frozen alarm-calibration thresholds from each run's
calibration.json; nothing is refitted. Macro-F1 needs per-row class
predictions, which the runs did not save, so it is not bootstrapped here.

Inputs, outside git because of size:
  * per-row scores runs/<model>-<seed>/test_log_odds.npy from the Kaggle output
    of ozgurucar/ids-v5-seeds,
  * test_y.npy and test_groups.npy from the parent kernel output
    ozgurucar/notebookeb0d7e9071 (hashes checked against the v5 manifest).

    python scripts/analysis/group_bootstrap.py --scores ~/.cache/ids-v5-scores/seeds/v5/seeds5_T4/runs \
        --parent ~/.cache/ids-v5-scores/parent --reps 200
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "results/v5/seeds/runs"
OUT = ROOT / "results/analysis"
TAUS = ["0.05", "0.01"]
PAIRS = [("esnn", "xgb"), ("esnn", "ann"), ("esnn", "ple_mlp"), ("esnn", "encoded_ann"), ("encoded_ann", "ann")]
NAMES = {"esnn": "E-SNN", "ann": "MLP", "encoded_ann": "Enc-ANN", "ple_mlp": "PLE-MLP", "xgb": "XGBoost"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def find(root, name):
    hits = sorted(Path(root).expanduser().rglob(name))
    if not hits:
        raise SystemExit(f"{name} not found under {root}")
    return hits[0]


def weighted_auc(order, attack, w):
    """AUC with row weights; ties are ignored (scores are continuous)."""
    a = attack[order]
    wo = w[order]
    benign_below = np.cumsum(np.where(a, 0.0, wo))
    wa = np.where(a, wo, 0.0)
    return float((wa * benign_below).sum() / (wa.sum() * (wo.sum() - wa.sum())))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scores", required=True, help="directory holding <model>-<seed>/test_log_odds.npy")
    ap.add_argument("--parent", required=True, help="directory holding test_y.npy and test_groups.npy")
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    manifest = json.loads((ROOT / "results/v5/seeds/manifest.json").read_text())
    benign = manifest["classes"].index("Benign")
    arrays = {}
    for name in ("test_y.npy", "test_groups.npy"):
        path = find(args.parent, name)
        digest = sha256(path)
        expected = manifest["array_hashes"][name]
        expected = expected if isinstance(expected, str) else expected.get("sha256")
        if digest != expected:
            raise SystemExit(f"{name}: hash {digest} does not match manifest {expected}")
        arrays[name] = np.load(path, allow_pickle=False)
    attack = arrays["test_y.npy"] != benign
    _, group = np.unique(arrays["test_groups.npy"], return_inverse=True)
    n_groups = int(group.max()) + 1

    runs = {}
    for run in sorted(RUNS.iterdir()):
        model, seed = run.name.rsplit("-", 1)
        calibration = json.loads((run / "calibration.json").read_text())
        point = json.loads((run / "evaluated.json").read_text())["operating_points"]
        score = np.load(Path(args.scores).expanduser() / run.name / "test_log_odds.npy", allow_pickle=False)
        if score.shape != attack.shape:
            raise SystemExit(f"{run.name}: {score.shape} scores for {attack.shape} test rows")
        alarm = {tau: score > calibration["thresholds"][tau]["threshold"] for tau in TAUS}
        for tau in TAUS:  # the stored test metrics must be reproduced exactly
            dr, far = alarm[tau][attack].mean(), alarm[tau][~attack].mean()
            if abs(dr - point[tau]["test"]["adr"]) > 1e-9 or abs(far - point[tau]["test"]["fpr"]) > 1e-9:
                raise SystemExit(f"{run.name} tau={tau}: DR/FAR {dr}/{far} differ from evaluated.json")
        runs.setdefault(model, {})[int(seed)] = {"alarm": alarm, "order": np.argsort(score, kind="stable")}

    def metrics(w):
        out = {}
        wa, wb = w[attack].sum(), w[~attack].sum()
        for model, seeds in runs.items():
            per_seed = []
            for r in seeds.values():
                m = {f"dr_{t}": float(w[attack & r["alarm"][t]].sum() / wa) for t in TAUS}
                m.update({f"far_{t}": float(w[~attack & r["alarm"][t]].sum() / wb) for t in TAUS})
                m["auc"] = weighted_auc(r["order"], attack, w)
                per_seed.append(m)
            out[model] = {k: float(np.mean([m[k] for m in per_seed])) for k in per_seed[0]}
        return out

    point_estimate = metrics(np.ones(len(attack)))
    rng = np.random.default_rng(args.seed)
    reps = []
    for i in range(args.reps):
        reps.append(metrics(rng.poisson(1.0, n_groups).astype(float)[group]))
        if (i + 1) % 20 == 0:
            print(f"{i + 1}/{args.reps} replicates", flush=True)

    keys = list(point_estimate["esnn"])
    ci = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    models = {m: {k: {"point": point_estimate[m][k], "ci95": ci([r[m][k] for r in reps])} for k in keys} for m in runs}
    pairs = {}
    for a, b in PAIRS:
        for k in keys:
            d = np.array([r[a][k] - r[b][k] for r in reps])
            pairs.setdefault(f"{a}-{b}", {})[k] = {"point": point_estimate[a][k] - point_estimate[b][k], "ci95": ci(d),
                                                 "share_le_0": float((d <= 0).mean())}
    payload = {"reps": args.reps, "seed": args.seed, "test_rows": int(len(attack)), "groups": n_groups,
               "seeds_per_model": {m: sorted(s) for m, s in runs.items()},
               "notes": ["Poisson(1) weights per fingerprint group; all seeds and models share each draw.",
                         "Point = mean over seeds on the full test partition; reproduces evaluated.json exactly.",
                         "Thresholds frozen from alarm calibration; the split itself is not redrawn."],
               "models": models, "pairs": pairs}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "group_bootstrap.json").write_text(json.dumps(payload, indent=2))

    pct = lambda x: f"{100 * x:.2f}"
    lines = ["# Fingerprint-group bootstrap (item 8)", "",
             f"Generated by `scripts/analysis/group_bootstrap.py`: {args.reps} replicates over {n_groups:,} test groups "
             f"({len(attack):,} rows). Values are means over seeds; 95% percentile intervals.", "",
             "| Model | DR 5% | FAR 5% | DR 1% | FAR 1% | AUC |", "|---|---|---|---|---|---|"]
    for m in runs:
        c = models[m]
        cell = lambda k, f=pct: f"{f(c[k]['point'])} [{f(c[k]['ci95'][0])}, {f(c[k]['ci95'][1])}]"
        lines.append(f"| {NAMES.get(m, m)} | {cell('dr_0.05')} | {cell('far_0.05')} | {cell('dr_0.01')} | {cell('far_0.01')} | "
                     f"{cell('auc', lambda x: f'{x:.4f}')} |")
    lines += ["", "## Paired differences (percentage points; AUC x 100)", "",
              "| Pair | DR 5% | DR 1% | AUC |", "|---|---|---|---|"]
    for name, p in pairs.items():
        a, b = name.split("-")
        cell = lambda k: f"{100 * p[k]['point']:+.2f} [{100 * p[k]['ci95'][0]:+.2f}, {100 * p[k]['ci95'][1]:+.2f}]"
        lines.append(f"| {NAMES[a]} - {NAMES[b]} | {cell('dr_0.05')} | {cell('dr_0.01')} | {cell('auc')} |")
    (OUT / "group_bootstrap_table.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
