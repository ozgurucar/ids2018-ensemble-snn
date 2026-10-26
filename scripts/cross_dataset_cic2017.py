"""Out-of-distribution check: score CIC-IDS2017 with the frozen CSE-CIC-IDS2018 detectors.

Nothing is refitted. The preprocessor, prior offset, temperature and the 5%
alarm threshold all come from the 2018 calibration partition. CIC-IDS2017 was
recorded on a different testbed a year earlier, so this measures transfer, not
in-distribution accuracy.

The 2017 MachineLearningCVE export has the same flow features as the 2018
export in the same order, under older names, plus a duplicated
"Fwd Header Length" column, and it lacks "Protocol". Protocol is imputed
from the destination port (17 for common UDP services, 6 otherwise); this
is stated as a limitation wherever the results are reported.

    python scripts/cross_dataset_cic2017.py path/to/combine.csv results/cross_dataset/cic2017.json
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "app")]
from detector import Detector  # noqa: E402

UDP_PORTS = {53, 67, 68, 123, 137, 138, 161, 162, 500, 1900, 5353}
FAMILY = {"BENIGN": "Benign", "DoS Hulk": "DoS-Hulk", "DDoS": "DDoS-LOIC-HTTP", "DoS GoldenEye": "DoS-GoldenEye",
          "DoS slowloris": "DoS-Slowloris", "DoS Slowhttptest": "DoS-SlowHTTPTest", "FTP-Patator": "FTP-BruteForce",
          "SSH-Patator": "SSH-Bruteforce", "Bot": "Bot", "Infiltration": "Infiltration"}


def load(path, columns_2018):
    raw = pd.read_csv(path, low_memory=False)
    raw.columns = [c.strip() for c in raw.columns]
    raw = raw[raw["Label"].notna()]
    label = raw.pop("Label").astype(str).str.strip()
    # pandas renames the repeated header to "Fwd Header Length.1"; drop that copy.
    raw = raw.drop(columns=[c for c in raw.columns if c.endswith(".1")])
    without_protocol = [c for c in columns_2018 if c != "Protocol"]
    if len(raw.columns) != len(without_protocol):
        raise ValueError(f"Expected {len(without_protocol)} feature columns, found {len(raw.columns)}")
    frame = raw.set_axis(without_protocol, axis=1)
    port = pd.to_numeric(frame["Dst Port"], errors="coerce")
    frame.insert(1, "Protocol", np.where(port.isin(UDP_PORTS), 17, 6))
    label = label.str.replace("�", "-", regex=False).str.replace("–", "-", regex=False)
    family = label.map(lambda s: "Web Attacks" if s.startswith("Web Attack") else FAMILY.get(s, s))
    return frame, label, family


def main(csv, out):
    detectors = {name: Detector(name) for name in ("esnn", "esnn_t4", "xgb")}
    frame, label, family = load(csv, detectors["esnn"].input_columns)
    attack = (label != "BENIGN").to_numpy()
    seen = family.isin(set(FAMILY.values()) | {"Web Attacks"}).to_numpy()
    report = {"rows": len(frame), "label_counts": label.value_counts().to_dict(),
              "protocol_imputation": "17 for ports " + ",".join(map(str, sorted(UDP_PORTS))) + ", else 6",
              "threshold": "2018 alarm calibration, 5% benign budget; nothing refitted", "models": {}}
    for name, detector in detectors.items():
        start = time.perf_counter()
        pred = detector.predict(frame)
        alarm = pred["alarm"].to_numpy()
        per_label = {}
        for value in sorted(label.unique()):
            rows = (label == value).to_numpy()
            per_label[value] = {"n": int(rows.sum()), "alarm_rate": float(alarm[rows].mean()),
                                "correct_family": float((pred["prediction"].to_numpy()[rows] == family.to_numpy()[rows]).mean())
                                if value != "BENIGN" and seen[rows].all() else None}
        # Site recalibration: refit only the alarm threshold on half of the 2017 benign
        # flows (benign-only, as an operator could collect), evaluate on the rest.
        rng = np.random.default_rng(2017)
        benign_idx = np.flatnonzero(~attack)
        fit = np.zeros(len(frame), bool)
        fit[rng.choice(benign_idx, len(benign_idx)//2, replace=False)] = True
        score = pred["attack_log_odds"].to_numpy()
        local = float(np.quantile(score[fit], 0.95))
        local_alarm = score > local
        recal = {"threshold": local, "false_alarm_rate": float(local_alarm[~attack & ~fit].mean()),
                 "detection_rate_all_attacks": float(local_alarm[attack].mean()),
                 "per_label": {v: float(local_alarm[((label == v).to_numpy()) & ~fit].mean()) for v in sorted(label.unique()) if (label == v).sum() > 0}}
        report["models"][name] = {"site_recalibrated_5pct": recal,
            "false_alarm_rate": float(alarm[~attack].mean()),
            "detection_rate_all_attacks": float(alarm[attack].mean()),
            "detection_rate_seen_families": float(alarm[attack & seen].mean()),
            "detection_rate_unseen_types": float(alarm[attack & ~seen].mean()) if (attack & ~seen).any() else None,
            "seconds": time.perf_counter() - start, "per_label": per_label}
        m = report["models"][name]
        print(f"{name}: FAR={m['false_alarm_rate']:.4f} DR={m['detection_rate_all_attacks']:.4f} "
              f"seen={m['detection_rate_seen_families']:.4f} unseen={m['detection_rate_unseen_types']} | recalibrated FAR="
              f"{m['site_recalibrated_5pct']['false_alarm_rate']:.4f} DR={m['site_recalibrated_5pct']['detection_rate_all_attacks']:.4f}", flush=True)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:3])
