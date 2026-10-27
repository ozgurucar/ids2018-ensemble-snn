"""Neuromorphic-hardware energy *estimate* per flow for the seed-42 checkpoints.

Counts, per flow, on the 4,400 flows in app/samples/demo_flows.csv (1,600 benign,
7 x 400 attack), passed through the frozen preprocessor as in app/detector.py:
  * synaptic events per layer = presynaptic spikes x fan-out (binary inputs only),
  * LIF neuron state updates = LIF neurons x time steps x branches,
  * dense work (LayerNorm, fusion meta-network, ANN layers) in MACs / elements.
Then applies published per-operation energies (Loihi, Davies et al. 2018, Table 2;
45 nm arithmetic, Horowitz 2014, Fig. 1.1.9). Nothing here is a measurement.

Run from the repository root:
  ~/.cache/ids-run-venv/bin/python scripts/energy_loihi.py
"""
import json, sys, platform
from collections import defaultdict
from pathlib import Path
import numpy as np, pandas as pd, torch
from torch import nn
import snntorch as snn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "app"))
from idsresearch.config import Config
from idsresearch.data import CLASSES
from idsresearch.models import build, SpikeBranch
from detector import Detector, CONFIG

CACHE = Path.home() / ".cache/ids-v4"
CKPT = {
    ("esnn", 4): ROOT / "app/models/esnn_t4.pt",
    ("esnn", 8): CACHE / "steps/v4/group_ce_T8/runs/esnn-42/model.pt",
    ("esnn", 12): ROOT / "app/models/esnn.pt",
    ("encoded_ann", 4): CACHE / "steps/v4/group_ce_T4/runs/encoded_ann-42/model.pt",
    ("encoded_ann", 8): CACHE / "steps/v4/group_ce_T8/runs/encoded_ann-42/model.pt",
    ("encoded_ann", 12): CACHE / "v3/ids2018-v3/experiments/group_ce/runs/encoded_ann-42/model.pt",
    ("ann", 12): CACHE / "v3/ids2018-v3/experiments/group_ce/runs/ann-42/model.pt",
}

# ---- per-operation energies (pJ) ---------------------------------------------
# Davies et al., IEEE Micro 38(1):82-99, 2018, Table 2 "Loihi pre-silicon performance
# and energy measurements", values at 0.75 V.
LOIHI = {"E_syn_op_min": 23.6, "E_neuron_update_active": 81.0, "E_neuron_update_inactive": 52.0,
         "E_spike_within_tile": 1.7, "E_tile_hop_EW": 3.0, "E_tile_hop_NS": 4.0,
         "E_syn_update_pairwise_STDP": 120.0}
# Horowitz, ISSCC 2014, Fig. 1.1.9 "Rough energy costs for various operations in 45nm 0.9V".
H45 = {"fp32_add": 0.9, "fp32_mult": 3.7, "int8_add": 0.03, "int8_mult": 0.2, "int32_add": 0.1, "int32_mult": 3.1}
MAC_FP32 = H45["fp32_add"] + H45["fp32_mult"]      # 4.6 pJ
MAC_INT8 = H45["int8_add"] + H45["int8_mult"]      # 0.23 pJ
AC_FP32 = H45["fp32_add"]                          # 0.9 pJ
# Hoeppner et al., arXiv:2103.08392v2 (2022), Table I, SpiNNaker 2 test chip, PL2 (0.5 V, 200 MHz);
# dynamic energy per event only, baseline power excluded.
SPINN2 = {"e_syn": 200.0, "e_neur": 1500.0}
SRAM32K_PER_FP32_WEIGHT = 20.0 / 2  # Horowitz Fig. 1.1.9: 32 KB cache, 64-bit access, 20 pJ
LN_MAC_EQ = 4   # assumed MAC-equivalents per LayerNorm element (mean, variance, normalise, affine)


def sample():
    det = Detector("esnn")
    frame = pd.read_csv(ROOT / "app/samples/demo_flows.csv", low_memory=False)
    return np.asarray(det.features(frame), dtype=np.float32)


def count(model, X):
    acc = defaultdict(lambda: defaultdict(float))
    handles = []
    def make(name):
        def hook(module, inputs, outputs):
            a = acc[name]
            if isinstance(module, snn.Leaky):
                s = outputs[0]
                a["spikes"] += float(s.sum()); a["slots"] += s.numel(); a["calls"] += 1
                a["width"] = s.shape[-1]
            elif isinstance(module, nn.Linear):
                x = inputs[0]; a["calls"] += 1; a["fan_out"] = module.out_features
                if bool(((x == 0) | (x == 1)).all()):
                    nnz = float(x.count_nonzero())
                    a["input_spikes"] += nnz; a["syn_events"] += nnz * module.out_features
                else:
                    a["macs"] += x.numel() * module.out_features
            elif isinstance(module, nn.LayerNorm):
                a["ln_elements"] += outputs.numel()
        return hook
    for name, m in model.named_modules():
        if isinstance(m, (snn.Leaky, nn.Linear, nn.LayerNorm)):
            handles.append(m.register_forward_hook(make(name)))
    with torch.no_grad():
        model.eval()(torch.tensor(X))
    for h in handles:
        h.remove()
    n = len(X)
    return {k: {kk: (vv / n if kk not in ("fan_out", "width", "calls") else vv) for kk, vv in v.items()} for k, v in acc.items()}


def uj(pj):
    return pj * 1e-6


def esnn_energy(model, layers, T):
    branches = [k for k, m in model.branches.items() if isinstance(m, SpikeBranch)]
    classes = len(CLASSES)
    syn = sum(v.get("syn_events", 0) for v in layers.values())
    lif_updates = sum(v.get("slots", 0) for v in layers.values())
    readout_updates = classes * T * len(branches)        # non-spiking integrator compartments
    input_spikes = sum(v["input_spikes"] for k, v in layers.items() if k.endswith("linears.0"))
    hidden_spikes = sum(v.get("spikes", 0) for v in layers.values())
    ln = sum(v.get("ln_elements", 0) for v in layers.values())
    dense_macs = sum(v.get("macs", 0) for v in layers.values())
    fusion_macs = classes * len(branches) if 0 < model.alpha else 0   # softmax-weighted sum of branch logits
    on_chip_pj = syn * LOIHI["E_syn_op_min"] + (lif_updates + readout_updates) * LOIHI["E_neuron_update_active"] \
        + (input_spikes + hidden_spikes) * LOIHI["E_spike_within_tile"]
    host_ln_pj = ln * LN_MAC_EQ * MAC_FP32
    host_fusion_pj = (dense_macs + fusion_macs) * MAC_FP32
    per_layer = []
    for b in branches:
        names = [f"branches.{b}.linears.{i}" for i in range(len(model.branches[b].linears))] + [f"branches.{b}.readout"]
        for i, nm in enumerate(names):
            src = "encoder" if i == 0 else f"lif{i - 1}"
            per_layer.append({"branch": b, "layer": nm.split(".", 2)[2], "presynaptic": src,
                              "presynaptic_spikes": layers[nm]["input_spikes"], "fan_out": layers[nm]["fan_out"],
                              "synaptic_events": layers[nm]["syn_events"]})
        for i in range(len(model.branches[b].lifs)):
            v = layers[f"branches.{b}.lifs.{i}"]
            per_layer.append({"branch": b, "layer": f"lifs.{i}", "neurons": v["width"], "neuron_updates": v["slots"],
                              "spikes": v["spikes"], "sparsity": 1 - v["spikes"] / v["slots"]})
    lower = syn * LOIHI["E_syn_op_min"] + (lif_updates + readout_updates) * LOIHI["E_neuron_update_inactive"]
    spinn = syn * SPINN2["e_syn"] + (lif_updates + readout_updates) * SPINN2["e_neur"]
    return {
        "loihi_uJ": uj(on_chip_pj), "host_dense_uJ": uj(host_ln_pj + host_fusion_pj),
        "total_uJ": uj(on_chip_pj + host_ln_pj + host_fusion_pj),
        "total_ln_folded_uJ": uj(on_chip_pj + host_fusion_pj),
        "counts": {"synaptic_events": syn, "lif_neuron_updates": lif_updates, "readout_compartment_updates": readout_updates,
                   "input_spikes": input_spikes, "hidden_spikes": hidden_spikes,
                   "hidden_sparsity": 1 - hidden_spikes / lif_updates,
                   "layernorm_elements": ln, "host_dense_macs": dense_macs + fusion_macs},
        "breakdown_uJ": {"loihi_synaptic": uj(syn * LOIHI["E_syn_op_min"]),
                         "loihi_neuron": uj((lif_updates + readout_updates) * LOIHI["E_neuron_update_active"]),
                         "loihi_spike_routing": uj((input_spikes + hidden_spikes) * LOIHI["E_spike_within_tile"]),
                         "host_layernorm": uj(host_ln_pj), "host_fusion": uj(host_fusion_pj)},
        "sensitivity_uJ": {"loihi_all_neuron_updates_at_52pJ_on_chip": uj(lower),
                           "spinnaker2_PL2_on_chip": uj(spinn)},
        "per_layer": per_layer,
    }


def dense_energy(layers):
    acs = sum(v.get("syn_events", 0) for v in layers.values())
    macs = sum(v.get("macs", 0) for v in layers.values())
    ln = sum(v.get("ln_elements", 0) for v in layers.values())
    fp = acs * AC_FP32 + (macs + ln * LN_MAC_EQ) * MAC_FP32
    return {"accel_45nm_uJ": uj(fp), "accel_45nm_linear_only_uJ": uj(acs * AC_FP32 + macs * MAC_FP32),
            "accel_45nm_int8_uJ": uj(acs * H45["int8_add"] + (macs + ln * LN_MAC_EQ) * MAC_INT8),
            # one FP32 weight read per MAC/AC from a 32 KB SRAM: 20 pJ per 64-bit access (Fig. 1.1.9) -> 10 pJ per weight
            "accel_45nm_with_sram_weights_uJ": uj(fp + (acs + macs) * SRAM32K_PER_FP32_WEIGHT),
            "total_uJ": uj(fp), "counts": {"accumulates": acs, "macs": macs, "layernorm_elements": ln}}


def main():
    torch.set_num_threads(1)
    X = sample()
    base = Config.read(CONFIG)
    models = {}
    for (name, T), path in CKPT.items():
        cfg = Config(**{**base.dictionary(), "steps": T})
        model = build(name, X.shape[1], len(CLASSES), cfg)
        model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        layers = count(model, X)
        key = "ann" if name == "ann" else f"{name}_T{T}"
        models[key] = esnn_energy(model, layers, T) if name == "esnn" else dense_energy(layers)
        if name == "encoded_ann":
            models[key]["loihi_uJ"] = None
        models[key]["checkpoint"] = str(path).replace(str(Path.home()), "~")
        print(key, {k: round(v, 4) for k, v in models[key].items() if k.endswith("uJ") and isinstance(v, float)}, flush=True)
    out = {
        "models": models,
        "constants": {"loihi_pJ": LOIHI, "horowitz_45nm_pJ": H45, "mac_fp32_pJ": MAC_FP32, "ac_fp32_pJ": AC_FP32,
                      "mac_int8_pJ": MAC_INT8, "sram32k_per_fp32_weight_pJ": SRAM32K_PER_FP32_WEIGHT, "spinnaker2_PL2_pJ": SPINN2, "layernorm_mac_equivalents_per_element": LN_MAC_EQ},
        "sources": {
            "loihi": "Davies et al., Loihi: A Neuromorphic Manycore Processor with On-Chip Learning, IEEE Micro 38(1):82-99, 2018, "
                     "doi:10.1109/MM.2018.112130359, Table 2 (pre-silicon SDF/SPICE simulation at 0.75 V, stated consistent with early post-silicon characterization)",
            "horowitz": "Horowitz, Computing's Energy Problem (and What We Can Do About It), ISSCC 2014, pp. 10-14, Fig. 1.1.9 (45 nm, 0.9 V)",
            "spinnaker2": "Hoeppner et al., The SpiNNaker 2 Processing Element Architecture for Hybrid Digital Neuromorphic Computing, "
                          "arXiv:2103.08392v2 (2022), Table I (22 nm FDSOI test chip, PL2 0.5 V 200 MHz, baseline power excluded)",
        },
        "assumptions": [
            "Estimate, not a measurement; per-op constants applied to software spike counts.",
            "E_syn = 23.6 pJ is Loihi's minimum energy per synaptic spike op; real per-op cost is higher.",
            "Every LIF neuron is updated every time step at the active energy (81 pJ); 52 pJ (inactive) is a lower-bound sensitivity.",
            "Readout layers receive spikes and are mapped as non-spiking integrator compartments: synaptic events counted on chip, classes x T x branches compartment updates at 81 pJ.",
            "Every emitted spike (encoder input spikes and hidden spikes) pays one within-tile spike (1.7 pJ); tile hops, barrier sync, static power and chip I/O are ignored.",
            "LayerNorm sits between each linear layer and its LIF neuron. It has no native Loihi equivalent; it is charged to a 45 nm FP32 host at 4 MAC-equivalents per element (host_dense_uJ). total_ln_folded_uJ assumes it is folded away, which would change the trained model.",
            "Fusion meta-network (MLP on branch logits) and the softmax-weighted branch sum are dense host MACs at 4.6 pJ.",
            "Input encoding (rate/temporal/population spike generation) and preprocessing are excluded for all models.",
            "ANN and Enc-ANN: 45 nm FP32 digital accelerator, MAC 4.6 pJ, AC 0.9 pJ, LayerNorm 4 MAC-eq/element; GELU, memory traffic and control excluded (Horowitz shows memory access dominates arithmetic).",
            "Loihi's synaptic-op energy includes reading the synapse from on-chip SRAM, while the 4.6 pJ MAC does not; accel_45nm_with_sram_weights_uJ adds one 32 KB SRAM read (10 pJ per FP32 weight) per MAC/AC as a fairer upper reference.",
            "Loihi weights are at most 9 bit, so an INT8 accelerator (MAC 0.23 pJ) is the like-for-like digital comparison and is reported as accel_45nm_int8_uJ.",
        ],
        "sample": {"file": "app/samples/demo_flows.csv", "flows": int(len(X)), "preprocessor": "app/models/preprocessor.joblib",
                   "machine": platform.platform()},
    }
    (ROOT / "results/v4/energy_loihi.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
