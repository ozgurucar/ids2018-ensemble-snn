from dataclasses import asdict, dataclass, field
import json
from pathlib import Path


@dataclass(frozen=True)
class Config:
    schema: int = 3
    development_only: bool = True
    feature_selection: str = "nonconstant"
    prior_correction: bool = True
    probability_calibration: bool = True
    threshold_method: str = "empirical"
    np_delta: float = 0.05
    calibration_fit_cap: int = 100000
    selection_metric: str = "corrected_macro_f1"
    catboost_trees: int = 600
    provenance: str = "real"
    timestamp_policy: str = "require_review"
    split: str = "within_class_time"
    ratios: tuple = (0.6, 0.1, 0.1, 0.2)
    split_seed: int = 2026
    session_gap_minutes: int = 30
    seeds: tuple = (42, 43, 44)
    models: tuple = ("esnn", "ann", "ann_ensemble", "cnn", "rf", "xgb")
    train_cap: int = 500000
    rare_preserve: int = 10000
    scaler: str = "quantile"
    correlation_threshold: float = 0.98
    dominant_fraction: float = 0.98
    hidden: tuple = (128, 64)
    steps: int = 12
    populations: int = 4
    branches: tuple = ("rate", "temporal", "population")
    alpha: float = 0.6
    dropout: float = 0.2
    epochs: int = 35
    patience: int = 10
    batch_size: int = 1024
    lr: float = 0.0004
    weight_decay: float = 0.001
    weight_ceiling: float = 15.0
    loss: str = "weighted_ce"
    focal_gamma: float = 2.0
    taus: tuple = (0.01, 0.05, 0.10)
    primary_tau: float = 0.05
    rf_trees: int = 200
    xgb_trees: int = 400
    min_calibration_benign: int = 1000
    max_files: int | None = None
    selection_note: str = "Pre-specified configuration; alpha is not claimed validation-optimal."

    def validate(self):
        if self.feature_selection not in ("v2", "nonconstant"):
            raise ValueError("Unknown feature selection mode")
        if self.threshold_method not in ("empirical", "np_reference") or not 0 < self.np_delta < 1:
            raise ValueError("Invalid threshold method")
        if self.calibration_fit_cap < 1 or self.catboost_trees < 1:
            raise ValueError("Invalid calibration/tree budget")
        if self.selection_metric not in ("corrected_macro_f1", "nll"):
            raise ValueError("Unknown selection metric")
        if self.prior_correction and self.loss == "focal":
            raise ValueError("CE prior correction is not valid for focal loss")
        if self.schema != 3 or self.provenance not in ("real", "synthetic"):
            raise ValueError("Invalid schema/provenance")
        if self.timestamp_policy not in ("require_review", "recorded_unverified"):
            raise ValueError("Unsupported timestamp policy")
        if self.split not in ("within_class_time", "time_groups", "random", "global_time", "feature_groups"):
            raise ValueError("Unsupported split")
        if len(self.ratios) != 4 or abs(sum(self.ratios) - 1) > 1e-9 or min(self.ratios) <= 0:
            raise ValueError("Four positive train/tune/calibration/test ratios must sum to one")
        if not self.seeds or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Unique seeds required")
        if self.steps < 2 or not 0 <= self.alpha <= 1 or self.populations < 2:
            raise ValueError("Invalid coding configuration")
        if not self.branches or len(set(self.branches)) != len(self.branches):
            raise ValueError("Branches must be unique")
        if set(self.branches) - {"rate", "temporal", "population"}:
            raise ValueError("Unsupported branch")
        if set(self.models) - {"esnn", "ann", "encoded_ann", "ann_ensemble", "cnn", "rf", "xgb", "catboost"}:
            raise ValueError("Unsupported model")
        if self.scaler not in ("quantile", "robust") or self.loss not in ("ce", "weighted_ce", "focal"):
            raise ValueError("Unsupported preprocessing/loss")
        if self.primary_tau not in self.taus or not all(0 < t < 1 for t in self.taus):
            raise ValueError("Primary tau must be in the declared budgets")
        if min(self.train_cap, self.rare_preserve, self.epochs, self.batch_size) < 1:
            raise ValueError("Budgets must be positive")
        return self

    @classmethod
    def read(cls, path):
        return cls(**json.loads(Path(path).read_text())).validate()

    def dictionary(self):
        return asdict(self)
