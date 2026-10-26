"""Load the frozen v3 checkpoints and score CICFlowMeter flow records.

The decision rule is the one fitted on the calibration partition during the
v3 run: training-prior offset, temperature scaling, then an alarm threshold
on the attack log-odds at the primary 5% benign FPR budget.
"""
from pathlib import Path
import hashlib
import json

import joblib
import numpy as np
import pandas as pd
import torch

from idsresearch.config import Config
from idsresearch.data import CLASSES, DROP
from idsresearch.decision import alarm_score, log_probabilities
from idsresearch.models import build
from idsresearch.training import neural_logits, tree_proba

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "models"
CONFIG = ROOT.parent / "configs" / "group_ce.json"
TAU = "0.05"
# Spiking checkpoints and the time window each was trained with.
SPIKING = {"esnn": ("esnn.pt", 12), "esnn_t4": ("esnn_t4.pt", 4)}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Detector:
    def __init__(self, name):
        self.name = name
        self.config = Config.read(CONFIG)
        if name in SPIKING:
            self.config = Config(**{**self.config.dictionary(), "steps": SPIKING[name][1]})
        # Only load pickles shipped with this repository by the v3 run.
        self.preprocessor = joblib.load(MODELS / "preprocessor.joblib")
        rule = json.loads((MODELS / f"{name}_calibration.json").read_text())
        checkpoint = MODELS / (SPIKING[name][0] if name in SPIKING else f"{name}.joblib")
        if sha256(checkpoint) != rule["checkpoint_sha256"]:
            raise ValueError(f"{checkpoint.name} does not match its calibration record")
        self.offset = np.asarray(rule["training_prior_offset"])
        self.temperature = rule["temperature"]["temperature"]
        self.threshold = rule["thresholds"][TAU]["threshold"]
        n_features = len(self.preprocessor.columns_)
        if name in SPIKING:
            self.model = build("esnn", n_features, len(CLASSES), self.config)
            self.model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
            self.model.eval()
        else:
            self.model = joblib.load(checkpoint)

    @property
    def input_columns(self):
        return self.preprocessor.input_columns_

    def features(self, frame):
        frame = frame.rename(columns=lambda c: str(c).strip())
        lookup = {c.casefold(): c for c in frame.columns}
        missing = [c for c in self.input_columns if c.casefold() not in lookup]
        if missing:
            raise ValueError(f"Missing columns: {missing[:8]}")
        X = pd.DataFrame({c: pd.to_numeric(frame[lookup[c.casefold()]], errors="coerce") for c in self.input_columns})
        X = X.astype(np.float32).replace([np.inf, -np.inf], np.nan).fillna(0)
        return self.preprocessor.transform(X)

    def logits(self, X):
        if self.name in SPIKING:
            with torch.no_grad():
                return neural_logits(self.model, X, 4096, "cpu").astype(float)
        return np.log(np.maximum(tree_proba(self.model, X).astype(float), 1e-12))

    def predict(self, frame):
        z = (self.logits(self.features(frame)) + self.offset) / self.temperature
        score = alarm_score(z)
        proba = np.exp(log_probabilities(z))
        alarm = score > self.threshold
        attack_class = proba[:, 1:].argmax(1) + 1
        label = np.where(alarm, attack_class, 0)
        return pd.DataFrame({
            "prediction": [CLASSES[i] for i in label],
            "alarm": alarm,
            "attack_log_odds": score.round(3),
            "confidence": proba[np.arange(len(label)), label].round(4),
        })


def true_labels(frame):
    lookup = {str(c).strip().casefold(): c for c in frame.columns}
    if "label" not in lookup:
        return None
    from idsresearch.data import ALIASES
    raw = frame[lookup["label"]].astype(str).str.strip().str.casefold()
    return raw.map(lambda s: CLASSES[ALIASES[s]] if s in ALIASES else s)


__all__ = ["Detector", "true_labels", "CLASSES", "DROP"]
