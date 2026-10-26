from pathlib import Path
import numpy as np
import pandas as pd
from .data import CLASSES
from .provenance import write_json


def generate(path, n_per_class=80):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(77)
    y = np.repeat(np.arange(len(CLASSES)), n_per_class)
    X = rng.normal(0, .15, (len(y), 16)).astype(np.float32)
    X[np.arange(len(y)), y] += 1
    frame = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])
    frame["Label"] = np.array(CLASSES)[y]
    frame["Timestamp"] = pd.to_datetime("2018-02-14 09:00:00")+pd.to_timedelta(np.tile(np.arange(n_per_class), len(CLASSES)), unit="m")
    frame["Timestamp"] = frame["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    frame.to_csv(path/"SYNTHETIC.csv", index=False)
    write_json(path/"SYNTHETIC.json", {"purpose": "Software verification only; not scientific evidence", "rows": len(frame)})
    return path
