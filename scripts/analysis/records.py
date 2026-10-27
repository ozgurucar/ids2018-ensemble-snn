"""Shared loader for the immutable run records (summary.json files).

Every analysis in scripts/analysis/ reads per-seed records only through this
module, so that new 5-seed results (results/v5/...) can be added on the
command line without code changes:

    --summary T12=results/v5/seeds/summary.json

A label groups records that share the same experimental setting (same
partitions, same T, same loss). Records from several files under one label are
merged by (model, seed). If a seed is already present, the new record is
skipped when its metrics are identical (deterministic re-run) and reported as a
conflict otherwise; the first record is kept.
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "analysis"

CLASSES = ("Benign", "Bot", "DDoS-HOIC", "DDoS-LOIC-UDP", "DDoS-LOIC-HTTP",
           "DoS-GoldenEye", "DoS-Hulk", "DoS-SlowHTTPTest", "DoS-Slowloris",
           "FTP-BruteForce", "Infiltration", "SSH-Bruteforce", "Web Attacks")
CONFLICTED = ("FTP-BruteForce", "DoS-SlowHTTPTest")
INFILTRATION = "Infiltration"
TAUS = ("0.01", "0.05", "0.1")
MODEL_NAMES = {"esnn": "E-SNN", "ann": "Matched ANN", "encoded_ann": "Enc-ANN",
               "rf": "Random forest", "catboost": "CatBoost", "xgb": "XGBoost", "ple_mlp": "PLE-MLP"}

DEFAULT_SUMMARIES = [
    ("T12", "results/v3/experiments/group_ce/summary.json"),
    ("T4", "results/v4/steps/summary_T4.json"),
    ("T8", "results/v4/steps/summary_T8.json"),
    ("T12_weighted", "results/v3/experiments/group_weighted/summary.json"),
    ("T8_wide", "results/v4/wide/summary_wide.json"),
    ("T8_screen_wide", "results/v4/variants/summary_wide.json"),
    ("T8_screen_weighted_fusion", "results/v4/variants/summary_weighted_fusion.json"),
    ("T8_screen_fast_lr", "results/v4/variants/summary_fast_lr.json"),
    ("T8_screen_pop8", "results/v4/variants/summary_pop8.json"),
    ("T8_screen_population_only", "results/v4/variants/summary_population_only.json"),
]


def add_summary_argument(parser):
    parser.add_argument("--summary", action="append", default=[], metavar="LABEL=PATH",
                        help="extra summary.json to merge under LABEL (repeatable), e.g. T12=results/v5/seeds/summary.json")
    parser.add_argument("--no-defaults", action="store_true", help="use only the --summary files")


def load(extra=(), defaults=True):
    specs = list(DEFAULT_SUMMARIES) if defaults else []
    for item in extra:
        label, _, path = item.partition("=")
        if not path:
            raise SystemExit(f"--summary expects LABEL=PATH, got {item!r}")
        specs.append((label, path))
    data, sources, conflicts = {}, {}, []
    for label, path in specs:
        p = Path(path)
        p = p if p.is_absolute() else ROOT / p
        summary = json.loads(p.read_text())
        sources.setdefault(label, []).append(str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p))
        for model, runs in summary["per_seed"].items():
            slot = data.setdefault(label, {}).setdefault(model, {})
            for run in runs:
                seed = int(run["seed"])
                if seed in slot:
                    old = slot[seed]["operating_points"]["0.05"]["test"]["macro_f1"]
                    new = run["operating_points"]["0.05"]["test"]["macro_f1"]
                    if abs(old - new) > 1e-12:
                        conflicts.append({"label": label, "model": model, "seed": seed, "kept": old, "skipped": new, "file": str(p)})
                    continue
                slot[seed] = run
    return data, sources, conflicts


def per_class(test):
    return {row["class"]: row for row in test["per_class"]}


def macro_f1(test, exclude=()):
    pc = per_class(test)
    return float(np.mean([pc[c]["f1"] for c in CLASSES if c not in exclude]))


def adr_excluding(test, exclude=(INFILTRATION,)):
    cm = np.asarray(test["confusion_matrix"], dtype=float)
    keep = [i for i, c in enumerate(CLASSES) if c != "Benign" and c not in exclude]
    rows = cm[keep]
    return float(1 - rows[:, 0].sum() / rows.sum())


def metrics(test):
    """Point metrics of one test evaluation."""
    return {
        "macro_f1_13": float(test["macro_f1"]),
        "macro_f1_11": macro_f1(test, CONFLICTED),
        "macro_f1_10": macro_f1(test, CONFLICTED + (INFILTRATION,)),
        "adr": float(test["adr"]),
        "adr_excl_infiltration": adr_excluding(test),
        "fpr": float(test["fpr"]),
    }


def point(run, tau):
    return metrics(run["operating_points"][tau]["test"])


def describe(values):
    """Mean, sample s.d. and t-based 95% CI of the mean."""
    from scipy import stats
    v = np.asarray(values, dtype=float)
    n = len(v)
    mean = float(v.mean())
    sd = float(v.std(ddof=1)) if n > 1 else None
    if n > 1:
        half = float(stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n))
        ci = [mean - half, mean + half]
    else:
        ci = None
    return {"n": n, "mean": mean, "sd": sd, "ci95": ci, "values": [float(x) for x in v]}


def write(name, payload):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(payload, indent=1, default=float))
    return path


def fmt(x, d=3):
    return "--" if x is None else f"{x:.{d}f}"
