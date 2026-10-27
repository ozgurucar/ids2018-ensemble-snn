"""Software forward-pass profile of the v3 seed-42 neural checkpoints on CPU.

Uses the bundled demo flows (app/samples/demo_flows.csv). Counts are proxies (spike-driven
accumulates vs dense MACs in Linear layers), not energy measurements.
"""
import json
import platform
import sys
from pathlib import Path

import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "app")]
from detector import Detector  # noqa: E402
from idsresearch.data import CLASSES  # noqa: E402
from idsresearch.models import build  # noqa: E402
from idsresearch.profile import measure  # noqa: E402

torch.set_num_threads(1)
detector = Detector("esnn")
X = detector.features(pd.read_csv(ROOT / "app/samples/demo_flows.csv", low_memory=False))
paths = {"esnn": "app/models/esnn.pt", "encoded_ann": "app/models/profile/encoded_ann.pt", "ann": "app/models/profile/ann.pt"}
result = {"machine": platform.platform(), "processor": platform.processor(), "threads": 1, "rows": len(X)}
for name, path in paths.items():
    model = build(name, X.shape[1], len(CLASSES), detector.config)
    model.load_state_dict(torch.load(ROOT / path, map_location="cpu", weights_only=True))
    result[name] = measure(model, X, "cpu", iterations=10)
    print(name, {k: round(v, 4) if isinstance(v, float) else v for k, v in result[name].items()})
(ROOT / "results/v3/efficiency_cpu.json").write_text(json.dumps(result, indent=2))
