"""Class-balanced software measurements; no joules or neuromorphic claims."""
from pathlib import Path
import time
import numpy as np
import torch
from torch import nn
import snntorch as snn
from .data import counts
from .pipeline import arrays, load_model, validated, verify_arrays
from .provenance import read_json, write_json


def measure(model, X, device, iterations=20):
    model.eval().to(device)
    xb = torch.tensor(X, dtype=torch.float32, device=device)
    activity = {"lif_spikes": 0., "lif_slots": 0, "linear_spike_accumulates": 0., "dense_macs": 0.}
    handles = []
    def hook(module, inputs, outputs):
        if isinstance(module, snn.Leaky):
            spikes = outputs[0]
            activity["lif_spikes"] += float(spikes.sum())
            activity["lif_slots"] += spikes.numel()
        elif isinstance(module, nn.Linear):
            x = inputs[0]
            if bool(((x == 0) | (x == 1)).all()):
                activity["linear_spike_accumulates"] += float(x.count_nonzero())*module.out_features
            else:
                activity["dense_macs"] += x.numel()*module.out_features
        elif isinstance(module, nn.Conv1d):
            activity["dense_macs"] += outputs.numel()*(module.in_channels//module.groups)*module.kernel_size[0]
    for module in model.modules():
        if isinstance(module, (snn.Leaky, nn.Linear, nn.Conv1d)):
            handles.append(module.register_forward_hook(hook))
    with torch.no_grad():
        model(xb)
    for handle in handles:
        handle.remove()
    with torch.no_grad():
        for _ in range(3):
            model(xb)
        if device == "cuda":
            torch.cuda.synchronize()
        durations = []
        for _ in range(iterations):
            begin = time.perf_counter()
            model(xb)
            if device == "cuda":
                torch.cuda.synchronize()
            durations.append(time.perf_counter()-begin)
    return {"device": device, "batch_size": len(X), "iterations": iterations,
            "median_ms_per_batch": float(np.median(durations)*1000),
            "p95_ms_per_batch": float(np.quantile(durations, .95)*1000),
            "amortized_us_per_sample": float(np.median(durations)*1e6/len(X)),
            "parameters": sum(p.numel() for p in model.parameters()),
            "spikes_per_sample": activity["lif_spikes"]/len(X),
            "lif_sparsity": 1-activity["lif_spikes"]/activity["lif_slots"] if activity["lif_slots"] else None,
            "sop_proxy_per_sample": activity["linear_spike_accumulates"]/len(X),
            "mac_proxy_per_sample": activity["dense_macs"]/len(X)}


def profile(out, name, seed, device="cpu", samples_per_class=16):
    out = Path(out)
    manifest, config = validated(out)
    verify_arrays(out, manifest, ("test",))
    X, y = arrays(out, "test")
    rng = np.random.default_rng(config.split_seed)
    index = np.concatenate([rng.choice(np.flatnonzero(y == c), min(samples_per_class, int((y == c).sum())), replace=False) for c in np.unique(y)])
    rng.shuffle(index)
    run = out/"runs"/f"{name}-{seed}"
    info = read_json(run/"trained.json")
    if info["experiment_id"] != manifest["experiment_id"]:
        raise ValueError("Profile/checkpoint provenance mismatch")
    model = load_model(run, info, config, X.shape[1])
    if isinstance(model, dict):
        raise ValueError("Profiling covers neural models only")
    result = measure(model, np.asarray(X[index]), device)
    result.update({"experiment_id": manifest["experiment_id"], "checkpoint_sha256": info["checkpoint_sha256"],
                   "sampling": "class balanced", "sample_support": counts(y[index]),
                   "excluded_costs": ["preprocessing", "transfer", "encoding operations", "LIF state updates", "normalisation", "activation functions", "memory movement"],
                   "interpretation": "Software forward-pass measurements only. No energy measurement; batch-amortized time is not single-flow latency."})
    write_json(run/f"profile-{device}.json", result)
    return result
