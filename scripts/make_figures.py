"""Build the paper figures from the result files in results/.

    ~/.cache/ids-run-venv/bin/python scripts/make_figures.py [--png] [--skip-tikz]

Outputs (paper/figures/):
  fig_architecture.pdf  compiled from fig_architecture.tex with tectonic (skipped if tectonic is absent)
  fig_steps.pdf         macro-F1 and estimated energy per flow (two cost models) versus T
  fig_transfer.pdf      per-attack alarm rate on CIC-IDS2017 after site recalibration
  fig_finetune.pdf      only if results/cross_dataset/finetune_cic2017.json exists
  figure_data.json      every number that was plotted, with its source file

No result is hardcoded: all values are read from the JSON files below.
"""
import argparse
import ast
import json
import math
import shutil
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
RES = ROOT / "results"

STEPS = {4: RES / "v4/steps/summary_T4.json", 8: RES / "v4/steps/summary_T8.json",
         12: RES / "v3/experiments/group_ce/summary.json"}
BASELINE = RES / "v3/experiments/group_ce/summary.json"
EFF_45NM = RES / "v4/efficiency_cpu_v4.json"
EFF_LOIHI = RES / "v4/energy_loihi.json"
TRANSFER = RES / "cross_dataset/cic2017.json"
FINETUNE = RES / "cross_dataset/finetune_cic2017.json"
BUDGET = "0.05"

# Okabe-Ito palette (colourblind safe); every series also differs in marker,
# line style or hatch so the figures stay readable in grayscale.
BLUE, VERM, ORANGE, GREEN, SKY, BLACK, GRAY = ("#0072B2", "#D55E00", "#E69F00", "#009E73",
                                                "#56B4E9", "#000000", "#7F7F7F")
SINGLE = 3.5  # IEEE column width in inches

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
    "ytick.major.width": 0.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "xtick.direction": "out", "ytick.direction": "out", "lines.linewidth": 1.1,
    "lines.markersize": 4, "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 300,
    "legend.frameon": False, "axes.grid": True, "grid.linewidth": 0.35, "grid.color": "#D9D9D9",
    "axes.axisbelow": True, "hatch.linewidth": 0.5,
})

record = {}


def load(path):
    with open(path) as f:
        return json.load(f)


def save(fig, name, png):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight", pad_inches=0.015)
    if png:
        (OUT / "preview").mkdir(exist_ok=True)
        fig.savefig(OUT / "preview" / f"{name}.png", bbox_inches="tight", pad_inches=0.015, dpi=300)
    plt.close(fig)
    print("wrote", OUT / f"{name}.pdf")


# --------------------------------------------------------------------------- architecture
def architecture(png):
    tex = OUT / "fig_architecture.tex"
    exe = shutil.which("tectonic")
    if exe is None:
        print("tectonic not found; fig_architecture.pdf not rebuilt")
        return
    run = subprocess.run([exe, "--chatter", "minimal", "--outdir", str(OUT), str(tex)],
                         capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(run.stdout + run.stderr)
    print("wrote", OUT / "fig_architecture.pdf")
    if png:
        render_png(OUT / "fig_architecture.pdf")


def render_png(pdf):
    try:
        import pypdfium2
    except ImportError:
        return
    page = pypdfium2.PdfDocument(str(pdf))[0]
    (pdf.parent / "preview").mkdir(exist_ok=True)
    page.render(scale=300 / 72).to_pil().save(pdf.parent / "preview" / (pdf.stem + ".png"))


# --------------------------------------------------------------------------- time window
def mf1(path, model):
    m = load(path)["aggregate"][model][BUDGET]["macro_f1"]
    return m["mean"], m["std"], m["n"]


def energies():
    """Energy per flow (uJ) under the two cost models.

    45nm: Horowitz 45 nm synaptic operations only (0.9 pJ AC, 4.6 pJ MAC), efficiency_cpu_v4.json.
    loihi: E-SNN on published Loihi per-op costs plus host LayerNorm/fusion (total_uJ), and the
           matched ANN on a 45 nm FP32 accelerator with and without SRAM weight reads, energy_loihi.json.
    """
    m = load(EFF_45NM)
    e = {"esnn_45nm": [m[f"esnn_T{T}"]["energy_pj_45nm"] / 1e6 for T in sorted(STEPS)],
         "encoded_ann_45nm": [m[f"encoded_ann_T{T}"]["energy_pj_45nm"] / 1e6 for T in sorted(STEPS)],
         "ann_45nm": m["ann_T12"]["energy_pj_45nm"] / 1e6}
    sources = [EFF_45NM]
    if EFF_LOIHI.exists():
        lo = load(EFF_LOIHI)["models"]
        e["esnn_loihi"] = [lo[f"esnn_T{T}"]["total_uJ"] for T in sorted(STEPS)]
        e["ann_45nm_sram"] = lo["ann"]["accel_45nm_with_sram_weights_uJ"]
        sources.append(EFF_LOIHI)
    else:
        print("  energy_loihi.json not found; panel (b) shows the 45 nm model only")
    return e, sources


def steps(png):
    Ts = sorted(STEPS)
    series = {k: [mf1(STEPS[T], k) for T in Ts] for k in ("esnn", "encoded_ann")}
    ref = {k: mf1(BASELINE, k) for k in ("ann", "xgb")}
    en, en_src = energies()
    record["fig_steps"] = {
        "budget": BUDGET, "T": Ts,
        "macro_f1": {k: [{"mean": m, "sd": s, "n": n} for m, s, n in v] for k, v in series.items()},
        "reference_macro_f1": {k: {"mean": m, "sd": s, "n": n} for k, (m, s, n) in ref.items()},
        "energy_uJ": en, "sources": sorted(str(p.relative_to(ROOT)) for p in {*STEPS.values(), *en_src})}

    style = {"esnn": dict(color=BLUE, marker="o", ls="-", label="E-SNN", mfc=BLUE),
             "encoded_ann": dict(color=VERM, marker="s", ls="--", label="Enc-ANN", mfc="white")}
    refstyle = {"xgb": dict(color=BLACK, ls="-.", lw=0.9, label="XGBoost"),
                "ann": dict(color=GRAY, ls=":", lw=1.2, label="Matched MLP")}
    shift = {"esnn": -0.22, "encoded_ann": 0.22}
    xlim = (Ts[0] - 1.2, Ts[-1] + 1.2)

    fig, (a, b) = plt.subplots(2, 1, figsize=(SINGLE, 3.45), sharex=False,
                               gridspec_kw={"hspace": 0.62, "height_ratios": [1, 1.12]})
    # (a) accuracy
    for k, (m_, _, _) in ref.items():
        a.axhline(m_, **refstyle[k], zorder=1)
    for k, v in series.items():
        a.errorbar([T + shift[k] for T in Ts], [x[0] for x in v], yerr=[x[1] for x in v],
                   capsize=2, elinewidth=0.7, capthick=0.7, mew=0.9, zorder=3, **style[k])
    a.set_xticks(Ts)
    a.set_xlim(*xlim)
    a.set_xlabel("Time window $T$ (steps)")
    a.set_ylabel(f"Macro-F1 at {float(BUDGET):.0%} FAR")
    lo = min(min(x[0] - x[1] for x in v) for v in series.values())
    hi = max(max(x[0] + x[1] for x in v) for v in series.values())
    lo, hi = min(lo, *(m_ for m_, _, _ in ref.values())), max(hi, *(m_ for m_, _, _ in ref.values()))
    a.set_ylim(math.floor((lo - 0.004) * 100) / 100, math.ceil((hi + 0.012) * 100) / 100)
    a.text(0.02, 0.97, "(a)", transform=a.transAxes, fontsize=8, va="top", fontweight="bold")
    handles = [Line2D([], [], **style["esnn"]), Line2D([], [], **style["encoded_ann"]),
               Line2D([], [], **refstyle["ann"]), Line2D([], [], **refstyle["xgb"])]
    a.legend(handles=handles, loc="lower left", ncol=4, bbox_to_anchor=(-0.2, 1.01),
             handlelength=2.2, columnspacing=1.0, handletextpad=0.4)

    # (b) energy under two cost models, log scale, inline labels at the right
    lab = dict(fontsize=7, va="center", ha="left")
    xr = xlim[1] + 0.25
    lines = []
    if "esnn_loihi" in en:
        b.plot(Ts, en["esnn_loihi"], color=BLUE, marker="o", ls="-", mfc=BLUE, mew=0.9, zorder=3)
        lines.append((en["esnn_loihi"][-1], "E-SNN, Loihi costs", BLUE))
    b.plot(Ts, en["esnn_45nm"], color=BLUE, marker="o", ls="--", mfc="white", mew=0.9, zorder=3)
    lines.append((en["esnn_45nm"][-1], "E-SNN, 45 nm AC/MAC", BLUE))
    b.plot(Ts, en["encoded_ann_45nm"], color=VERM, marker="s", ls="--", mfc="white", mew=0.9, zorder=3)
    lines.append((en["encoded_ann_45nm"][-1], "Enc-ANN, 45 nm AC/MAC", VERM))
    if "ann_45nm_sram" in en:
        b.axhline(en["ann_45nm_sram"], color=GRAY, ls="-", lw=0.9, zorder=1)
        b.text(5.2, en["ann_45nm_sram"] * 1.12, "Matched MLP, FP32 MAC + SRAM weight reads",
               color="#4D4D4D", fontsize=6.5, va="bottom", ha="left")
    b.axhline(en["ann_45nm"], **{**refstyle["ann"], "label": None}, zorder=1)
    b.text(5.2, en["ann_45nm"] * 1.12, "Matched MLP, FP32 MAC", color="#4D4D4D", fontsize=6.5,
           va="bottom", ha="left")
    # spread inline labels so they do not collide (log space)
    lines.sort(key=lambda t: t[0])
    ys = [math.log10(y) for y, _, _ in lines]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + 0.25)
    for (y, text, c), ly in zip(lines, ys):
        b.text(xr, 10 ** ly, text, color=c, clip_on=False, **lab)
    b.set_yscale("log")
    b.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda y, _: f"{y:g}"))
    vals = [v for x in en.values() for v in (x if isinstance(x, list) else [x])]
    b.set_ylim(min(vals) / 1.7, max(vals) * 1.7)
    b.set_xticks(Ts)
    b.set_xlim(*xlim)
    b.set_xlabel("Time window $T$ (steps)")
    b.set_ylabel(r"Est. energy per flow ($\mu$J)")
    b.text(0.02, 0.97, "(b)", transform=b.transAxes, fontsize=8, va="top", fontweight="bold")
    # keep both panels the same width; labels live in the right margin
    fig.subplots_adjust(right=0.66)
    save(fig, "fig_steps", png)


# --------------------------------------------------------------------------- transfer
def seen_families():
    """Labels the cross-dataset script maps to a 2018 class (parsed, not imported)."""
    tree = ast.parse((ROOT / "scripts/cross_dataset_cic2017.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "FAMILY" for t in node.targets):
            return set(ast.literal_eval(node.value))
    raise RuntimeError("FAMILY not found in cross_dataset_cic2017.py")


def transfer(png):
    d = load(TRANSFER)
    counts = d["label_counts"]
    models = [("esnn", "E-SNN ($T=12$)", BLUE, ""), ("esnn_t4", "E-SNN ($T=4$)", SKY, "////"),
              ("xgb", "XGBoost", ORANGE, "....")]
    rates = {k: d["models"][k]["site_recalibrated_5pct"]["per_label"] for k, *_ in models}
    labels = [l for l in rates["esnn"] if l != "BENIGN" and l.lower() != "nan"]
    seen = seen_families()
    # Seen attack types first, then types without a 2018 counterpart; within each, by flow count.
    labels.sort(key=lambda l: (l not in seen, -counts.get(l, 0)))
    far = {k: rates[k]["BENIGN"] for k, *_ in models}
    record["fig_transfer"] = {"labels": labels, "flows": {l: counts.get(l) for l in labels},
                              "alarm_rate": {k: {l: rates[k][l] for l in labels} for k in rates},
                              "benign_far": far, "source": str(TRANSFER.relative_to(ROOT))}

    n = len(labels)
    h = 0.26
    fig, ax = plt.subplots(figsize=(SINGLE - 0.61, 0.33 * n + 0.55))
    for j, (k, name, c, hatch) in enumerate(models):
        ys = [i + (j - 1) * h for i in range(n)]
        xs = [rates[k][l] for l in labels]
        ax.barh(ys, xs, height=h, color=c, edgecolor="black", linewidth=0.4, hatch=hatch, label=name)
        for y, x in zip(ys, xs):  # make zero-height bars visible
            if x < 0.005:
                ax.text(0.008, y, "0" if x == 0 else ("<0.1%" if x < 0.001 else f"{x:.1%}"), fontsize=5.5, color="#555555",
                        va="center", ha="left")
    far_mean = sum(far.values()) / len(far)
    ax.axvline(far_mean, color=VERM, ls="--", lw=0.9, zorder=4)
    ax.text(far_mean + 0.012, -0.72, f"Benign false-alarm rate ({far_mean:.0%})",
            color=VERM, fontsize=7, va="center", ha="left")
    ylabels = []
    for l in labels:
        tag = "" if l in seen else "$^{*}$"
        ylabels.append(f"{l}{tag} ({counts.get(l, 0):,})")
    ax.set_yticks(range(n))
    ax.set_yticklabels(ylabels)
    ax.set_ylim(n - 0.5, -1.05)
    ax.set_xlim(0, 1.0)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Alarm rate on CIC-IDS2017 attack flows")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="lower center", bbox_to_anchor=(0.32, 1.0), ncol=3, handlelength=1.4,
              columnspacing=0.8, handletextpad=0.35)
    save(fig, "fig_transfer", png)


# --------------------------------------------------------------------------- optional fine-tuning
def finetune(png):
    """Optional: attack detection rate on the CIC-IDS2017 test split at the 5% FAR threshold
    versus the share of 2017 labels used. Reads finetune_cic2017.json["summary"], a list of
    {method, budget, seed, detection_rate, far, ...}; seeds are averaged."""
    if not FINETUNE.exists():
        print("finetune_cic2017.json not found; fig_finetune skipped")
        return
    rows = load(FINETUNE).get("summary", [])
    agg = {}
    for r in rows:
        if r.get("detection_rate") is None:
            continue
        agg.setdefault(r["method"], {}).setdefault(float(r["budget"]), []).append(r["detection_rate"])
    style = {"esnn_t4_finetune": dict(color=SKY, marker="o", ls="-", mfc=SKY, label="E-SNN ($T=4$), fine-tuned"),
             "esnn_finetune": dict(color=BLUE, marker="o", ls="-", mfc=BLUE, label="E-SNN ($T=12$), fine-tuned"),
             "xgb_continue": dict(color=ORANGE, marker="D", ls="--", mfc="white", label="XGBoost, continued"),
             "xgb_scratch": dict(color=BLACK, marker="^", ls="-.", mfc="white", label="XGBoost, from scratch")}
    frozen = {"frozen_recal_esnn_t4": dict(color=SKY, ls=":", lw=1.1, label="E-SNN ($T=4$), frozen + recal."),
              "frozen_recal_esnn": dict(color=BLUE, ls=":", lw=1.1, label="E-SNN ($T=12$), frozen + recal."),
              "frozen_recal_xgb": dict(color=ORANGE, ls=":", lw=1.1, label="XGBoost, frozen + recal.")}
    def sd(v):
        m = sum(v) / len(v)
        return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1)) if len(v) > 1 else 0.0
    curves = {k: sorted((b, sum(v) / len(v), len(v), sd(v)) for b, v in d.items() if b > 0)
              for k, d in agg.items() if k in style}
    curves = {k: v for k, v in curves.items() if v}
    if not curves or max(len(v) for v in curves.values()) < 2:
        print("finetune_cic2017.json has fewer than two label budgets yet; fig_finetune skipped")
        return
    fig, ax = plt.subplots(figsize=(SINGLE, 1.75))
    for k, kw in frozen.items():
        if k in agg and 0.0 in agg[k]:
            v = agg[k][0.0]
            ax.axhline(sum(v) / len(v), zorder=1, **kw)
    for k, pts in curves.items():
        ax.errorbar([p[0] * 100 for p in pts], [p[1] for p in pts], yerr=[p[3] for p in pts], capsize=2,
                    elinewidth=0.7, capthick=0.7, mew=0.9, zorder=3, **style[k])
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f"{x:g}%"))
    ax.set_xlabel("Share of CIC-IDS2017 pool labels used for adaptation")
    ax.set_ylabel("Detection rate at 5% FAR")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_ylim(0, 1.02)
    xs = [p[0] * 100 for v in curves.values() for p in v]
    ax.set_xlim(min(xs) / 1.6, max(xs) * 1.6)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.3), ncol=2, fontsize=6.5, handlelength=2.0,
              columnspacing=0.8)
    record["fig_finetune"] = {"curves": {k: [{"budget": b, "detection_rate": m, "sd": e, "n_seeds": n} for b, m, n, e in v]
                                         for k, v in curves.items()},
                              "frozen": {k: agg[k][0.0] for k in frozen if k in agg and 0.0 in agg[k]},
                              "source": str(FINETUNE.relative_to(ROOT))}
    save(fig, "fig_finetune", png)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", action="store_true", help="also write PNG previews to paper/figures/preview/")
    ap.add_argument("--skip-tikz", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if not args.skip_tikz:
        architecture(args.png)
    steps(args.png)
    transfer(args.png)
    finetune(args.png)
    (OUT / "figure_data.json").write_text(json.dumps(record, indent=1))
    print("wrote", OUT / "figure_data.json")


if __name__ == "__main__":
    main()
