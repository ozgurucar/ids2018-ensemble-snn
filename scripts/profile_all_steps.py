"""Operation counts for every neural checkpoint on one sample of up to 400 flows per label and day (single CPU thread)."""
import json, sys, platform
from pathlib import Path
import joblib, numpy as np, pandas as pd, torch
sys.path.insert(0, "code")
from idsresearch.config import Config
from idsresearch.data import CLASSES
from idsresearch.models import build
from idsresearch.profile import measure

torch.set_num_threads(1)
parts = []
for f in sorted(Path("raw").glob("*.csv")):
    d = pd.read_csv(f, low_memory=False); d.columns = d.columns.str.strip()
    d = d[d["Label"].astype(str).str.casefold() != "label"]
    for _, g in d.groupby("Label"):
        parts.append(g.sample(min(len(g), 400), random_state=7))
sample = pd.concat(parts).sample(frac=1, random_state=7)
sample.to_csv("demo_flows.csv", index=False)
pre = joblib.load("v3/ids2018-v3/experiments/group_ce/preprocessor.joblib")
X = sample[pre.input_columns_].apply(pd.to_numeric, errors="coerce").astype(np.float32).replace([np.inf, -np.inf], np.nan).fillna(0)
X = pre.transform(X)
base = Config(**json.load(open("v3/ids2018-v3/experiments/group_ce/manifest.json"))["config"])
runs = {("esnn", 12): "v3/ids2018-v3/experiments/group_ce/runs/esnn-42", ("encoded_ann", 12): "v3/ids2018-v3/experiments/group_ce/runs/encoded_ann-42",
        ("ann", 12): "v3/ids2018-v3/experiments/group_ce/runs/ann-42"}
for T in (4, 8):
    for m in ("esnn", "encoded_ann"):
        runs[(m, T)] = f"steps/v4/group_ce_T{T}/runs/{m}-42"
out = {"machine": platform.platform(), "rows": len(X), "threads": 1}
for (m, T), path in runs.items():
    cfg = Config(**{**base.dictionary(), "steps": T})
    model = build(m, X.shape[1], len(CLASSES), cfg)
    model.load_state_dict(torch.load(Path(path)/"model.pt", map_location="cpu", weights_only=True))
    r = measure(model, X, "cpu", iterations=10)
    r["energy_pj_45nm"] = 0.9*r["sop_proxy_per_sample"] + 4.6*r["mac_proxy_per_sample"]
    out[f"{m}_T{T}"] = r
    print(m, T, {k: round(v, 3) if isinstance(v, float) else v for k, v in r.items() if k in ("parameters", "spikes_per_sample", "lif_sparsity", "sop_proxy_per_sample", "mac_proxy_per_sample", "energy_pj_45nm", "amortized_us_per_sample")}, flush=True)
json.dump(out, open("efficiency_cpu_v4.json", "w"), indent=2)
