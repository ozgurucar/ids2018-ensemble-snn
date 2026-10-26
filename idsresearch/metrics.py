import numpy as np
from sklearn.metrics import accuracy_score, average_precision_score, confusion_matrix, f1_score, roc_auc_score
from .data import CLASSES


def softmax(logits):
    e = np.exp(logits-logits.max(axis=1, keepdims=True))
    return e/e.sum(axis=1, keepdims=True)


def fit_alarm_threshold(y_calibration, proba_calibration, tau, min_benign=1):
    """Smallest threshold in score order with empirical benign FPR <= tau.

    Uses only benign calibration scores; no rare-class multipliers or test labels.
    The strict '>' decision deals conservatively with ties.
    """
    scores = 1-proba_calibration[y_calibration == 0, 0]
    if len(scores) < min_benign:
        raise ValueError(f"Need at least {min_benign} benign calibration rows; got {len(scores)}")
    allowed = int(np.floor(tau*len(scores)))
    threshold = float(np.sort(scores)[len(scores)-allowed-1])
    achieved = float((scores > threshold).mean())
    return {"threshold": threshold, "tau": tau, "benign_support": len(scores),
            "empirical_calibration_fpr": achieved, "decision": "attack_score > threshold",
            "fit_partition": "calibration", "guarantee": "Empirical calibration constraint only; no test or deployment guarantee."}


def predict(proba, threshold):
    attack = 1-proba[:, 0] > threshold
    return np.where(attack, proba[:, 1:].argmax(1)+1, 0)


def evaluate(y, pred, proba):
    cm = confusion_matrix(y, pred, labels=np.arange(len(CLASSES)))
    support = cm.sum(1)
    rows = []
    for c, name in enumerate(CLASSES):
        tp, fp, fn = int(cm[c, c]), int(cm[:, c].sum()-cm[c, c]), int(cm[c].sum()-cm[c, c])
        binary = y == c
        rows.append({"class": name, "support": int(support[c]), "tp": tp, "fp": fp, "fn": fn,
                     "precision": tp/(tp+fp) if tp+fp else 0., "recall": tp/(tp+fn) if tp+fn else None,
                     "f1": 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
                     "roc_auc": float(roc_auc_score(binary, proba[:, c])) if 0 < binary.sum() < len(y) else None,
                     "average_precision": float(average_precision_score(binary, proba[:, c])) if 0 < binary.sum() < len(y) else None})
    attacks, benign = y != 0, y == 0
    return {"macro_f1": float(f1_score(y, pred, labels=np.arange(len(CLASSES)), average="macro", zero_division=0)),
            "macro_f1_present_classes": float(f1_score(y, pred, labels=np.flatnonzero(support), average="macro", zero_division=0)),
            "weighted_f1": float(f1_score(y, pred, average="weighted", zero_division=0)),
            "accuracy": float(accuracy_score(y, pred)),
            "adr": float((pred[attacks] != 0).mean()) if attacks.any() else None,
            "fpr": float((pred[benign] != 0).mean()) if benign.any() else None,
            "n": len(y), "per_class": rows, "confusion_matrix": cm.tolist(),
            "absent_test_classes": [CLASSES[i] for i in np.flatnonzero(support == 0)]}


def aggregate(rows):
    result = {}
    for key in ("macro_f1", "weighted_f1", "accuracy", "adr", "fpr"):
        values = [r[key] for r in rows if r[key] is not None]
        result[key] = {"mean": float(np.mean(values)) if values else None,
                       "std": float(np.std(values, ddof=1)) if len(values) > 1 else None,
                       "n": len(values), "values": values}
    return result
