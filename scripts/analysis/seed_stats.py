"""Item 1: seed-level statistics for the pre-declared comparisons.

Reads only the run records (summary.json per_seed). For each pre-declared
comparison (E-SNN vs matched ANN, E-SNN vs Enc-ANN, E-SNN vs XGBoost, all at
T = 12) and each budget tau in {5%, 1%} it reports

  * per-seed values and per-seed paired differences (pairing by seed number),
  * Welch t-test and Welch-Satterthwaite 95% CI of the difference of means,
  * paired t-test and t-based 95% CI of the mean paired difference,
  * Holm-adjusted p-values within each (metric, tau) family of three
    comparisons, and across all six (3 comparisons x 2 budgets) per metric,
  * the minimal difference detectable with 80% power at alpha = 0.05 given the
    observed spread (Welch, two-sided).

Metrics: 13-class macro-F1 and 11-class macro-F1 (without FTP-BruteForce and
DoS-SlowHTTPTest). Everything else is labelled exploratory and unadjusted.
Time-window "no difference" claims get a Welch TOST with a stated margin.

Seeds vary initialisation and data order only; the split seed is fixed, so
none of these intervals covers partition variance. Rows within the test set
are dependent, so no row-level test is attempted.

Rerun with more seeds (e.g. when the v5 5-seed records arrive):
    python scripts/analysis/seed_stats.py --summary T12=results/v5/seeds/summary.json
"""
import argparse
import itertools

import numpy as np
from scipy import stats

from records import MODEL_NAMES, add_summary_argument, describe, fmt, load, point, write, OUT

PRIMARY_LABEL = "T12"
DECLARED = [("esnn", "ann"), ("esnn", "encoded_ann"), ("esnn", "xgb"), ("esnn", "ple_mlp")]
TAUS = ["0.05", "0.01"]
METRICS = ["macro_f1_13", "macro_f1_11"]
TOST_MARGIN = 0.02


def holm(pvalues):
    p = np.asarray(pvalues, float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[idx]))
        adj[idx] = running
    return adj.tolist()


def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = np.sqrt(va + vb)
    diff = a.mean() - b.mean()
    if se == 0:
        return {"diff": float(diff), "se": 0.0, "df": None, "ci95": [float(diff)] * 2, "t": None, "p": 0.0 if diff else 1.0, "mde80": 0.0}
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    t = diff / se
    p = 2 * stats.t.sf(abs(t), df)
    half = stats.t.ppf(0.975, df) * se
    mde = (stats.t.ppf(0.975, df) + stats.t.ppf(0.8, df)) * se
    return {"diff": float(diff), "se": float(se), "df": float(df), "ci95": [float(diff - half), float(diff + half)],
            "t": float(t), "p": float(p), "mde80": float(mde)}


def paired(a_by_seed, b_by_seed):
    seeds = sorted(set(a_by_seed) & set(b_by_seed))
    d = np.array([a_by_seed[s] - b_by_seed[s] for s in seeds])
    out = {"seeds": seeds, "differences": d.tolist(), "n": len(d), "mean": float(d.mean()) if len(d) else None}
    if len(d) < 2:
        return {**out, "p": None, "ci95": None}
    sd = d.std(ddof=1)
    se = sd / np.sqrt(len(d))
    half = stats.t.ppf(0.975, len(d) - 1) * se
    p = float(2 * stats.t.sf(abs(d.mean() / se), len(d) - 1)) if se > 0 else (0.0 if d.mean() else 1.0)
    return {**out, "sd": float(sd), "ci95": [float(d.mean() - half), float(d.mean() + half)], "p": p,
            "wins": int((d > 0).sum()), "losses": int((d < 0).sum())}


def tost(a, b, margin):
    """Welch two one-sided tests for |mean(a) - mean(b)| < margin."""
    w = welch(a, b)
    if w["df"] is None:
        return {"margin": margin, "p": 0.0 if abs(w["diff"]) < margin else 1.0, "ci90": w["ci95"], "equivalent": abs(w["diff"]) < margin}
    p_low = stats.t.sf((w["diff"] + margin) / w["se"], w["df"])
    p_up = stats.t.cdf((w["diff"] - margin) / w["se"], w["df"])
    half = stats.t.ppf(0.95, w["df"]) * w["se"]
    p = float(max(p_low, p_up))
    return {"margin": margin, "diff": w["diff"], "ci90": [w["diff"] - half, w["diff"] + half], "p": p, "equivalent_at_0.05": p < 0.05}


def by_seed(data, label, model, tau, metric):
    runs = data.get(label, {}).get(model, {})
    return {s: point(r, tau)[metric] for s, r in sorted(runs.items())}


def compare(data, a, b, tau, metric):
    (la, ma), (lb, mb) = a, b
    A, B = by_seed(data, la, ma, tau, metric), by_seed(data, lb, mb, tau, metric)
    if len(A) < 2 or len(B) < 2:
        return None
    return {"a": f"{la}:{ma}", "b": f"{lb}:{mb}", "tau": tau, "metric": metric,
            "a_values": A, "b_values": B, "a_summary": describe(list(A.values())), "b_summary": describe(list(B.values())),
            "welch": welch(list(A.values()), list(B.values())), "paired": paired(A, B)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_summary_argument(ap)
    ap.add_argument("--primary-label", default=PRIMARY_LABEL)
    ap.add_argument("--out", default="seed_stats")
    args = ap.parse_args()
    data, sources, conflicts = load(args.summary, not args.no_defaults)
    L = args.primary_label

    # Per-model descriptive statistics for every label with >= 1 seed.
    models = {}
    for label, by_model in data.items():
        for model in by_model:
            for tau in ["0.01", "0.05", "0.1"]:
                for metric in METRICS + ["adr", "fpr"]:
                    v = list(by_seed(data, label, model, tau, metric).values())
                    models.setdefault(label, {}).setdefault(model, {}).setdefault(tau, {})[metric] = describe(v)

    # Confirmatory family.
    confirmatory = []
    for metric in METRICS:
        for tau in TAUS:
            fam = [compare(data, (L, a), (L, b), tau, metric) for a, b in DECLARED]
            fam = [f for f in fam if f]
            for key in ("welch", "paired"):
                adj = holm([f[key]["p"] for f in fam])
                for f, p in zip(fam, adj):
                    f[key]["p_holm_family_declared"] = p
            confirmatory.extend(fam)
        # Holm across both budgets (6 tests) per metric.
        sub = [f for f in confirmatory if f["metric"] == metric]
        for key in ("welch", "paired"):
            adj = holm([f[key]["p"] for f in sub])
            for f, p in zip(sub, adj):
                f[key]["p_holm_family6"] = p

    # Exploratory, unadjusted.
    exploratory = []
    pairs = [((L, "esnn"), (L, m)) for m in ("rf", "catboost")]
    pairs += [((L, "encoded_ann"), (L, m)) for m in ("ann", "rf", "catboost", "xgb")]
    pairs += [((L, "xgb"), (L, m)) for m in ("rf", "catboost")]
    for T in ("T4", "T8"):
        pairs += [((T, "esnn"), (L, "esnn")), ((T, "encoded_ann"), (L, "encoded_ann")), ((T, "esnn"), (T, "encoded_ann")),
                  ((T, "esnn"), (L, "ann")), ((T, "esnn"), (L, "xgb"))]
    pairs += [(("T8_wide", "esnn"), ("T8", "esnn")), (("T12_weighted", "esnn"), (L, "esnn")), (("T12_weighted", "ann"), (L, "ann"))]
    for (a, b), metric, tau in itertools.product(pairs, METRICS, ["0.05", "0.01", "0.1"]):
        c = compare(data, a, b, tau, metric)
        if c:
            exploratory.append(c)

    # Equivalence (TOST) for the time-window claim.
    equivalence = []
    for (a, b), metric, tau in itertools.product([(("T4", "esnn"), (L, "esnn")), (("T8", "esnn"), (L, "esnn")),
                                                   (("T4", "encoded_ann"), (L, "encoded_ann")), (("T8", "encoded_ann"), (L, "encoded_ann"))],
                                                  METRICS, ["0.05", "0.01"]):
        A = list(by_seed(data, *a, tau, metric).values())
        B = list(by_seed(data, *b, tau, metric).values())
        if len(A) > 1 and len(B) > 1:
            equivalence.append({"a": ":".join(a), "b": ":".join(b), "tau": tau, "metric": metric, **tost(A, B, TOST_MARGIN)})

    payload = {"sources": sources, "seed_conflicts": conflicts, "primary_label": L,
               "declared_comparisons": [f"{a} - {b}" for a, b in DECLARED], "declared_taus": TAUS, "metrics": METRICS,
               "notes": ["Seeds vary initialisation and order only; split seed 2026 is fixed, so partition variance is not covered.",
                         "Paired differences pair runs by seed number; tree and neural seeds control different random streams, so pairing is nominal.",
                         "Holm family_declared: the declared comparisons (four with PLE-MLP) within one (metric, tau). family6: the three comparisons at both declared taus, per metric.",
                         "mde80: smallest true difference a two-sided Welch test at alpha 0.05 would detect with 80% power given the observed s.d. (normal-theory approximation).",
                         f"TOST margin {TOST_MARGIN} macro-F1 (2 points), Welch, alpha 0.05; equivalence needs the 90% CI inside the margin."],
               "models": models, "confirmatory": confirmatory, "exploratory_unadjusted": exploratory, "equivalence_tost": equivalence}
    path = write(f"{args.out}.json", payload)

    # ---------------------------------------------------------------- markdown
    lines = [f"# Seed-level statistics (item 1)", "",
             f"Generated by `scripts/analysis/seed_stats.py` from {', '.join(sum(sources.values(), []))}.",
             f"JSON: `results/analysis/{args.out}.json`. Seed conflicts: {len(conflicts)}.", "",
             "## Pre-declared comparisons ({L})", "",
             "Differences are first model minus second model, in macro-F1 points x 100 would be the paper's 'points'. CI: 95%.", "",
             "| Metric | tau | Comparison | Mean diff | Welch 95% CI | p Welch | p Holm (declared) | Paired diffs (by seed) | Paired 95% CI | p paired | p Holm (declared) | MDE80 |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for f in confirmatory:
        w, pr = f["welch"], f["paired"]
        lines.append(f"| {f['metric']} | {f['tau']} | {f['a'].split(':')[1]} - {f['b'].split(':')[1]} | {w['diff']:+.4f} | "
                     f"[{w['ci95'][0]:+.3f}, {w['ci95'][1]:+.3f}] | {w['p']:.3f} | {w['p_holm_family_declared']:.3f} | "
                     f"{', '.join(f'{x:+.3f}' for x in pr['differences'])} | [{pr['ci95'][0]:+.3f}, {pr['ci95'][1]:+.3f}] | "
                     f"{pr['p']:.3f} | {pr['p_holm_family_declared']:.3f} | {w['mde80']:.3f} |")
    lines += ["", "## Per-model seeds (T = 12, tau = 5%)", "", "| Model | 13-class seeds | mean [95% CI] | 11-class seeds | mean [95% CI] |", "|---|---|---|---|---|"]
    for m in ("esnn", "ann", "encoded_ann", "rf", "catboost", "xgb"):
        r = models[L].get(m)
        if not r:
            continue
        a, b = r["0.05"]["macro_f1_13"], r["0.05"]["macro_f1_11"]
        lines.append(f"| {MODEL_NAMES[m]} | {', '.join(f'{x:.3f}' for x in a['values'])} | {a['mean']:.3f} [{a['ci95'][0]:.3f}, {a['ci95'][1]:.3f}] | "
                     f"{', '.join(f'{x:.3f}' for x in b['values'])} | {b['mean']:.3f} [{b['ci95'][0]:.3f}, {b['ci95'][1]:.3f}] |")
    lines += ["", "## Time-window equivalence (Welch TOST, margin 0.02)", "", "| a | b | metric | tau | diff | 90% CI | p TOST | equivalent? |", "|---|---|---|---|---|---|---|---|"]
    for e in equivalence:
        lines.append(f"| {e['a']} | {e['b']} | {e['metric']} | {e['tau']} | {e['diff']:+.4f} | [{e['ci90'][0]:+.3f}, {e['ci90'][1]:+.3f}] | {e['p']:.3f} | {'yes' if e['equivalent_at_0.05'] else 'no'} |")
    lines += ["", "## Exploratory (unadjusted Welch), tau = 5%", "", "| a | b | metric | diff | 95% CI | p |", "|---|---|---|---|---|---|"]
    for f in exploratory:
        if f["tau"] == "0.05":
            w = f["welch"]
            lines.append(f"| {f['a']} | {f['b']} | {f['metric']} | {w['diff']:+.4f} | [{w['ci95'][0]:+.3f}, {w['ci95'][1]:+.3f}] | {w['p']:.3f} |")
    (OUT / f"{args.out}_table.md").write_text("\n".join(lines) + "\n")
    print(path)
    print("\n".join(lines[:20]))


if __name__ == "__main__":
    main()
