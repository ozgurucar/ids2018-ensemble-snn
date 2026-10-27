"""Item 4: one consistent per-flow energy table (estimates, not measurements).

Operation counts come from forward hooks on the seed-42 checkpoints
(scripts/energy_loihi.py: count, esnn_energy, dense_energy, CKPT), on two
inputs:

  demo      app/samples/demo_flows.csv (1,600 benign + 7 x 400 attack flows,
            NOT class balanced; reproduces results/v4/energy_loihi.json)
  test_mix  per-class counts measured on flows sampled from the four raw
            CSE-CIC-IDS2018 days that are available locally, then averaged
            with the class weights of the test partition (Table I, 83.8%
            benign), renormalised over the measured classes

Cost models, all in pJ, Horowitz 2014 (45 nm) and Davies et al. 2018 (Loihi):

  45nm_optimistic  ACs x 0.9 + MACs x 4.6 (what the paper's Table VI uses)
  45nm_complete    + LayerNorm (4 MAC-eq per element, all models)
                   + E-SNN membrane updates (1 FP32 MAC per LIF neuron per
                     step for decay-and-integrate; threshold compare and reset
                     not charged) + readout integrator updates (1 MAC each)
  45nm_complete_sram  + one 32 KB SRAM weight read (10 pJ) per AC and MAC
  int8             ACs x 0.03 + (MACs + 4 x LN + membrane + readout) x 0.23
  loihi            E-SNN only: synaptic events 23.6, neuron updates 81, spike
                   routing 1.7, LayerNorm and fusion on a 45 nm FP32 host
                   (identical to scripts/energy_loihi.py)

The paper should use 45nm_complete for every model (one ANN number,
0.40 uJ), and report Loihi and the SRAM/INT8 variants as sensitivity.

    python scripts/analysis/energy_unified.py [--per-class 1500] [--skip-test-mix]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "app"), str(ROOT / "scripts"), str(HERE)]
import energy_loihi as EL  # noqa: E402
from idsresearch.config import Config  # noqa: E402
from idsresearch.data import ALIASES, CLASSES  # noqa: E402
from idsresearch.models import build  # noqa: E402
from detector import CONFIG, Detector  # noqa: E402
from records import OUT, write  # noqa: E402

RAW = Path.home() / ".cache/ids-v4/raw"
TEST_SUPPORT = {"Benign": 2699900, "Bot": 54821, "DDoS-HOIC": 134836, "DDoS-LOIC-UDP": 324, "DDoS-LOIC-HTTP": 115366,
                "DoS-GoldenEye": 8362, "DoS-Hulk": 92601, "DoS-SlowHTTPTest": 11441, "DoS-Slowloris": 2451,
                "FTP-BruteForce": 7049, "Infiltration": 32470, "SSH-Bruteforce": 61742, "Web Attacks": 179}
H = EL.H45
AC, MAC, SRAM, LN = EL.AC_FP32, EL.MAC_FP32, EL.SRAM32K_PER_FP32_WEIGHT, EL.LN_MAC_EQ
AC8, MAC8 = H["int8_add"], EL.MAC_INT8


def raw_sample(per_class, seed=2026):
    """Sample up to per_class rows per (day, class) from the local raw days."""
    rng = np.random.default_rng(seed)
    frames = []
    for f in sorted(RAW.glob("*.csv")):
        labels = pd.read_csv(f, usecols=["Label"], low_memory=False)["Label"].astype(str).str.strip().str.casefold()
        keep = []
        for lab in labels.unique():
            if lab not in ALIASES:
                continue
            idx = np.flatnonzero((labels == lab).to_numpy())
            keep.append(rng.choice(idx, min(per_class, len(idx)), replace=False))
        keep = np.sort(np.concatenate(keep))
        keep_set = set((keep + 1).tolist())  # +1: header line
        frame = pd.read_csv(f, skiprows=lambda i: i != 0 and i not in keep_set, low_memory=False)
        frame.columns = frame.columns.str.strip()
        frame["__class"] = frame["Label"].astype(str).str.strip().str.casefold().map(lambda s: CLASSES[ALIASES[s]])
        frame["__day"] = f.stem
        frames.append(frame)
        print(f"sampled {len(frame)} rows from {f.name}: {frame['__class'].value_counts().to_dict()}", flush=True)
    return pd.concat(frames, ignore_index=True)


def load_models(n_features):
    base = Config.read(CONFIG)
    out = {}
    for (name, T), path in EL.CKPT.items():
        cfg = Config(**{**base.dictionary(), "steps": T})
        model = build(name, n_features, len(CLASSES), cfg)
        model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        out["ann" if name == "ann" else f"{name}_T{T}"] = (name, T, model)
    return out


def raw_counts(name, T, model, X):
    layers = EL.count(model, X)
    if name == "esnn":
        e = EL.esnn_energy(model, layers, T)
        c = e["counts"]
        return {"acs": c["synaptic_events"], "macs": c["host_dense_macs"], "ln_elements": c["layernorm_elements"],
                "membrane_updates": c["lif_neuron_updates"], "readout_updates": c["readout_compartment_updates"],
                "input_spikes": c["input_spikes"], "hidden_spikes": c["hidden_spikes"], "hidden_sparsity": c["hidden_sparsity"],
                "loihi_total_uJ": e["total_uJ"], "loihi_on_chip_uJ": e["loihi_uJ"], "loihi_host_uJ": e["host_dense_uJ"]}
    d = EL.dense_energy(layers)["counts"]
    return {"acs": d["accumulates"], "macs": d["macs"], "ln_elements": d["layernorm_elements"],
            "membrane_updates": 0.0, "readout_updates": 0.0}


def energies(c):
    opt = c["acs"] * AC + c["macs"] * MAC
    state = (c["membrane_updates"] + c["readout_updates"]) * MAC
    ln = c["ln_elements"] * LN * MAC
    complete = opt + ln + state
    out = {"45nm_optimistic_uJ": opt * 1e-6, "45nm_layernorm_uJ": ln * 1e-6, "45nm_membrane_readout_uJ": state * 1e-6,
           "45nm_complete_uJ": complete * 1e-6,
           "45nm_complete_sram_uJ": (complete + (c["acs"] + c["macs"]) * SRAM) * 1e-6,
           "int8_uJ": (c["acs"] * AC8 + (c["macs"] + c["ln_elements"] * LN + c["membrane_updates"] + c["readout_updates"]) * MAC8) * 1e-6,
           "loihi_uJ": c.get("loihi_total_uJ")}
    return out


def weighted(per_class, weights):
    keys = [k for k, v in next(iter(per_class.values())).items() if isinstance(v, (int, float)) and v is not None]
    tot = sum(weights.values())
    return {k: float(sum(weights[c] * per_class[c][k] for c in weights) / tot) for k in keys}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-class", type=int, default=1500, help="rows per (day, class) from the raw days")
    ap.add_argument("--skip-test-mix", action="store_true")
    args = ap.parse_args()
    torch.set_num_threads(4)
    det = Detector("esnn")
    demo = np.asarray(det.features(pd.read_csv(ROOT / "app/samples/demo_flows.csv", low_memory=False)), dtype=np.float32)
    models = load_models(demo.shape[1])

    result = {"demo": {}, "test_mix": {}, "per_class_counts": {}}
    for key, (name, T, model) in models.items():
        c = raw_counts(name, T, model, demo)
        result["demo"][key] = {"counts": c, "energy": energies(c)}
        print("demo", key, {k: round(v, 4) for k, v in result["demo"][key]["energy"].items() if v is not None}, flush=True)

    if not args.skip_test_mix:
        frame = raw_sample(args.per_class)
        X = np.asarray(det.features(frame), dtype=np.float32)
        cls = frame["__class"].to_numpy()
        measured = sorted(set(cls), key=CLASSES.index)
        weights = {c: TEST_SUPPORT[c] for c in measured}
        coverage = sum(weights.values()) / sum(TEST_SUPPORT.values())
        result["test_mix_sample"] = {"days": sorted(frame["__day"].unique().tolist()), "rows_per_class": {c: int((cls == c).sum()) for c in measured},
                                     "measured_classes": measured, "weights": weights, "test_rows_covered": coverage,
                                     "benign_weight_after_renormalisation": weights["Benign"] / sum(weights.values()),
                                     "missing_classes": [c for c in CLASSES if c not in measured]}
        for key, (name, T, model) in models.items():
            pcs = {c: raw_counts(name, T, model, X[cls == c]) for c in measured}
            result["per_class_counts"][key] = pcs
            c = weighted(pcs, weights)
            # Loihi total is linear in the counts, so the weighted mean of per-class totals is exact.
            result["test_mix"][key] = {"counts": c, "energy": energies(c)}
            print("test_mix", key, {k: round(v, 4) for k, v in result["test_mix"][key]["energy"].items() if v is not None}, flush=True)

    result["constants_pJ"] = {"AC_fp32": AC, "MAC_fp32": MAC, "AC_int8": AC8, "MAC_int8": MAC8, "SRAM_per_weight": SRAM,
                              "layernorm_mac_eq_per_element": LN, "membrane_update": "1 FP32 MAC per LIF neuron per step",
                              "loihi": EL.LOIHI}
    result["assumptions"] = [
        "Estimates from operation counts and published per-operation energies, not measurements.",
        "Membrane update = decay multiply + input add = 1 MAC; threshold compare and reset are not charged (lower bound for the E-SNN).",
        "LayerNorm = 4 MAC-equivalents per element for every model that has it (E-SNN per time step, ANN and Enc-ANN once).",
        "Encoding (spike generation), preprocessing, activations, control and static power are excluded for all models.",
        "INT8 row uses int8 adds for accumulates and int8 MACs elsewhere (as results/v4/energy_loihi.json); it is the like-for-like point for Loihi's <=9-bit weights.",
        "SRAM variant charges one 32 KB SRAM read (20 pJ per 64 bit -> 10 pJ per FP32 weight) per AC and MAC; membrane-state traffic is not charged.",
        "Enc-ANN has no spiking layers, so it has no Loihi row; its hardware-style cost is the SRAM variant.",
        "test_mix: per-class counts on flows from the locally available raw days (02-14, 02-15, 02-21, 03-02), weighted by test-partition support of the measured classes; classes from other days are not measured and their weight is redistributed.",
    ]
    path = write("energy_unified.json", result)

    # ---------------------------------------------------------------- markdown
    order = ["esnn_T4", "esnn_T8", "esnn_T12", "encoded_ann_T4", "encoded_ann_T8", "encoded_ann_T12", "ann"]
    names = {"esnn_T4": "E-SNN, T = 4", "esnn_T8": "E-SNN, T = 8", "esnn_T12": "E-SNN, T = 12", "encoded_ann_T4": "Enc-ANN, T = 4",
             "encoded_ann_T8": "Enc-ANN, T = 8", "encoded_ann_T12": "Enc-ANN, T = 12", "ann": "Matched ANN"}
    L = ["# Unified per-flow energy (item 4)", "", f"Script `scripts/analysis/energy_unified.py`; JSON `results/analysis/energy_unified.json`. Estimates, not measurements.", ""]
    for sample in ("test_mix", "demo"):
        if not result[sample]:
            continue
        L += [f"## Sample: {sample}", ""]
        if sample == "test_mix":
            s = result["test_mix_sample"]
            L += [f"Measured classes {', '.join(s['measured_classes'])}; they cover {s['test_rows_covered']:.1%} of test rows; benign weight {s['benign_weight_after_renormalisation']:.1%}. Missing: {', '.join(s['missing_classes'])}.", ""]
        L += ["| Model | ACs | MACs | LN el. | Membrane+readout upd. | 45 nm optimistic | 45 nm complete | 45 nm complete + SRAM | INT8 | Loihi |", "|---|---|---|---|---|---|---|---|---|---|"]
        for k in order:
            c, e = result[sample][k]["counts"], result[sample][k]["energy"]
            loihi = "--" if e["loihi_uJ"] is None else f"{e['loihi_uJ']:.2f}"
            L.append(f"| {names[k]} | {c['acs']:,.0f} | {c['macs']:,.0f} | {c['ln_elements']:,.0f} | {c['membrane_updates'] + c['readout_updates']:,.0f} | "
                     f"{e['45nm_optimistic_uJ']:.3f} | {e['45nm_complete_uJ']:.3f} | {e['45nm_complete_sram_uJ']:.3f} | {e['int8_uJ']:.4f} | {loihi} |")
        a = result[sample]["ann"]["energy"]
        L += ["", "Ratios to the matched ANN under the same cost model (E-SNN / ANN):", ""]
        for k in ("esnn_T4", "esnn_T8", "esnn_T12", "encoded_ann_T4", "encoded_ann_T12"):
            e = result[sample][k]["energy"]
            L.append(f"- {names[k]}: optimistic {e['45nm_optimistic_uJ'] / a['45nm_optimistic_uJ']:.2f}, complete {e['45nm_complete_uJ'] / a['45nm_complete_uJ']:.2f}, "
                     f"complete+SRAM {e['45nm_complete_sram_uJ'] / a['45nm_complete_sram_uJ']:.2f}, INT8 {e['int8_uJ'] / a['int8_uJ']:.2f}"
                     + (f", Loihi vs ANN 45 nm complete {e['loihi_uJ'] / a['45nm_complete_uJ']:.1f}x" if e["loihi_uJ"] else ""))
        L.append("")
    if result["per_class_counts"]:
        L += ["## Per-class synaptic events per flow (E-SNN T = 12, test_mix sample)", "", "| Class | ACs | hidden sparsity |", "|---|---|---|"]
        for c, v in result["per_class_counts"]["esnn_T12"].items():
            L.append(f"| {c} | {v['acs']:,.0f} | {v['hidden_sparsity']:.3f} |")
    (OUT / "energy_unified_table.md").write_text("\n".join(L) + "\n")
    print(path)
    print("\n".join(L))


if __name__ == "__main__":
    main()
