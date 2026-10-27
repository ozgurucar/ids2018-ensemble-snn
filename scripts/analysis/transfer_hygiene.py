"""Item 6: CIC-IDS2017 transfer hygiene.

1. Maps the CIC-IDS2017 MachineLearningCVE columns to the CSE-CIC-IDS2018
   names through an explicit name table (NAME_MAP), instead of by position as
   scripts/cross_dataset_cic2017.py does, and checks that the resulting
   feature frame is identical to the positional one and that the frozen
   detectors give identical transfer numbers (results/cross_dataset/cic2017.json).
2. Checks the duplicated 2017 "Fwd Header Length" column.
3. Per-feature two-sample Kolmogorov-Smirnov distance between 2018 benign and
   2017 benign flows, for the 78 detector input columns, with the top shifted
   features. The 2018 reference is benign flows from the raw 2018 days that are
   available locally (~/.cache/ids-v4/raw: 02-14, 02-15, 02-21, 03-02); the
   exact calibration partition cannot be rebuilt without all ten days because
   group assignment depends on the global group order. As a scale reference,
   the same KS is computed between pairs of 2018 days.
   KS is invariant to the monotone log and quantile transforms of the
   preprocessor, so raw-value KS equals model-input KS.

    python scripts/analysis/transfer_hygiene.py ~/.cache/ids-x17/combine.csv [--skip-rescore]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "app"), str(ROOT / "scripts"), str(HERE)]
import cross_dataset_cic2017 as C  # noqa: E402
from detector import Detector  # noqa: E402
from records import OUT, write  # noqa: E402

RAW18 = Path.home() / ".cache/ids-v4/raw"

# CIC-IDS2017 (MachineLearningCVE, stripped header) -> CSE-CIC-IDS2018 name.
NAME_MAP = {
    "Destination Port": "Dst Port", "Flow Duration": "Flow Duration",
    "Total Fwd Packets": "Tot Fwd Pkts", "Total Backward Packets": "Tot Bwd Pkts",
    "Total Length of Fwd Packets": "TotLen Fwd Pkts", "Total Length of Bwd Packets": "TotLen Bwd Pkts",
    "Fwd Packet Length Max": "Fwd Pkt Len Max", "Fwd Packet Length Min": "Fwd Pkt Len Min",
    "Fwd Packet Length Mean": "Fwd Pkt Len Mean", "Fwd Packet Length Std": "Fwd Pkt Len Std",
    "Bwd Packet Length Max": "Bwd Pkt Len Max", "Bwd Packet Length Min": "Bwd Pkt Len Min",
    "Bwd Packet Length Mean": "Bwd Pkt Len Mean", "Bwd Packet Length Std": "Bwd Pkt Len Std",
    "Flow Bytes/s": "Flow Byts/s", "Flow Packets/s": "Flow Pkts/s",
    "Flow IAT Mean": "Flow IAT Mean", "Flow IAT Std": "Flow IAT Std", "Flow IAT Max": "Flow IAT Max", "Flow IAT Min": "Flow IAT Min",
    "Fwd IAT Total": "Fwd IAT Tot", "Fwd IAT Mean": "Fwd IAT Mean", "Fwd IAT Std": "Fwd IAT Std", "Fwd IAT Max": "Fwd IAT Max", "Fwd IAT Min": "Fwd IAT Min",
    "Bwd IAT Total": "Bwd IAT Tot", "Bwd IAT Mean": "Bwd IAT Mean", "Bwd IAT Std": "Bwd IAT Std", "Bwd IAT Max": "Bwd IAT Max", "Bwd IAT Min": "Bwd IAT Min",
    "Fwd PSH Flags": "Fwd PSH Flags", "Bwd PSH Flags": "Bwd PSH Flags", "Fwd URG Flags": "Fwd URG Flags", "Bwd URG Flags": "Bwd URG Flags",
    "Fwd Header Length": "Fwd Header Len", "Bwd Header Length": "Bwd Header Len",
    "Fwd Packets/s": "Fwd Pkts/s", "Bwd Packets/s": "Bwd Pkts/s",
    "Min Packet Length": "Pkt Len Min", "Max Packet Length": "Pkt Len Max",
    "Packet Length Mean": "Pkt Len Mean", "Packet Length Std": "Pkt Len Std", "Packet Length Variance": "Pkt Len Var",
    "FIN Flag Count": "FIN Flag Cnt", "SYN Flag Count": "SYN Flag Cnt", "RST Flag Count": "RST Flag Cnt", "PSH Flag Count": "PSH Flag Cnt",
    "ACK Flag Count": "ACK Flag Cnt", "URG Flag Count": "URG Flag Cnt", "CWE Flag Count": "CWE Flag Count", "ECE Flag Count": "ECE Flag Cnt",
    "Down/Up Ratio": "Down/Up Ratio", "Average Packet Size": "Pkt Size Avg",
    "Avg Fwd Segment Size": "Fwd Seg Size Avg", "Avg Bwd Segment Size": "Bwd Seg Size Avg",
    "Fwd Avg Bytes/Bulk": "Fwd Byts/b Avg", "Fwd Avg Packets/Bulk": "Fwd Pkts/b Avg", "Fwd Avg Bulk Rate": "Fwd Blk Rate Avg",
    "Bwd Avg Bytes/Bulk": "Bwd Byts/b Avg", "Bwd Avg Packets/Bulk": "Bwd Pkts/b Avg", "Bwd Avg Bulk Rate": "Bwd Blk Rate Avg",
    "Subflow Fwd Packets": "Subflow Fwd Pkts", "Subflow Fwd Bytes": "Subflow Fwd Byts",
    "Subflow Bwd Packets": "Subflow Bwd Pkts", "Subflow Bwd Bytes": "Subflow Bwd Byts",
    "Init_Win_bytes_forward": "Init Fwd Win Byts", "Init_Win_bytes_backward": "Init Bwd Win Byts",
    "act_data_pkt_fwd": "Fwd Act Data Pkts", "min_seg_size_forward": "Fwd Seg Size Min",
    "Active Mean": "Active Mean", "Active Std": "Active Std", "Active Max": "Active Max", "Active Min": "Active Min",
    "Idle Mean": "Idle Mean", "Idle Std": "Idle Std", "Idle Max": "Idle Max", "Idle Min": "Idle Min",
}


def load_by_name(path, columns_2018):
    raw = pd.read_csv(path, low_memory=False)
    raw.columns = [c.strip() for c in raw.columns]
    raw = raw[raw["Label"].notna()]
    label = raw.pop("Label").astype(str).str.strip()
    dup = {}
    if "Fwd Header Length.1" in raw:
        a = pd.to_numeric(raw["Fwd Header Length"], errors="coerce").to_numpy()
        b = pd.to_numeric(raw["Fwd Header Length.1"], errors="coerce").to_numpy()
        dup = {"present": True, "identical": bool(np.array_equal(a, b, equal_nan=True)), "rows_differing": int((a != b).sum())}
    unmapped_2017 = [c for c in raw.columns if c not in NAME_MAP and not c.endswith(".1")]
    target = set(NAME_MAP.values())
    missing_2018 = [c for c in columns_2018 if c not in target]
    if unmapped_2017 or missing_2018 != ["Protocol"]:
        raise ValueError(f"name map incomplete: unmapped 2017 {unmapped_2017}, missing 2018 {missing_2018}")
    frame = raw[list(NAME_MAP)].rename(columns=NAME_MAP)
    port = pd.to_numeric(frame["Dst Port"], errors="coerce")
    frame.insert(1, "Protocol", np.where(port.isin(C.UDP_PORTS), 17, 6))
    frame = frame[columns_2018]
    return frame, label, dup


def numeric(frame):
    return frame.apply(pd.to_numeric, errors="coerce").astype(np.float32).replace([np.inf, -np.inf], np.nan).fillna(0)


def benign_2018(columns, per_day, seed=2026):
    rng = np.random.default_rng(seed)
    out = {}
    for f in sorted(RAW18.glob("*.csv")):
        df = pd.read_csv(f, low_memory=False)
        df.columns = df.columns.str.strip()
        df = df[df["Label"].astype(str).str.strip() == "Benign"]
        if len(df) > per_day:
            df = df.iloc[np.sort(rng.choice(len(df), per_day, replace=False))]
        out[f.stem] = numeric(df[columns])
        print(f"2018 benign {f.stem}: {len(out[f.stem])}", flush=True)
    return out


def rescore(frame, label, family):
    attack = (label != "BENIGN").to_numpy()
    out = {}
    for name in ("esnn", "esnn_t4", "xgb"):
        pred = Detector(name).predict(frame)
        alarm = pred["alarm"].to_numpy()
        rng = np.random.default_rng(2017)
        benign_idx = np.flatnonzero(~attack)
        fit = np.zeros(len(frame), bool)
        fit[rng.choice(benign_idx, len(benign_idx) // 2, replace=False)] = True
        score = pred["attack_log_odds"].to_numpy()
        local = float(np.quantile(score[fit], 0.95))
        la = score > local
        out[name] = {"false_alarm_rate": float(alarm[~attack].mean()), "detection_rate_all_attacks": float(alarm[attack].mean()),
                     "recal_false_alarm_rate": float(la[~attack & ~fit].mean()), "recal_detection_rate": float(la[attack].mean())}
        print(name, out[name], flush=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv")
    ap.add_argument("--per-day", type=int, default=200000, help="2018 benign rows per local day")
    ap.add_argument("--skip-rescore", action="store_true")
    args = ap.parse_args()
    cols = Detector("esnn").input_columns
    model_cols = Detector("esnn").preprocessor.columns_

    by_name, label, dup = load_by_name(args.csv, cols)
    positional, label_p, family = C.load(args.csv, cols)
    A, B = numeric(by_name), numeric(positional[cols])
    identical = bool(A.shape == B.shape and np.array_equal(A.to_numpy(), B.to_numpy()) and (label.to_numpy() == label_p.to_numpy()).all())
    result = {"name_map": NAME_MAP, "protocol": "not in the 2017 export; imputed from Dst Port as in cross_dataset_cic2017.py",
              "duplicate_fwd_header_length": dup, "positional_vs_name_frames_identical": identical, "rows": len(A)}
    print("frames identical:", identical, "dup:", dup, flush=True)

    if not args.skip_rescore:
        old = json.loads((ROOT / "results/cross_dataset/cic2017.json").read_text())["models"]
        new = rescore(by_name, label, family)
        cmp = {}
        for m, v in new.items():
            o = old[m]
            ref = {"false_alarm_rate": o["false_alarm_rate"], "detection_rate_all_attacks": o["detection_rate_all_attacks"],
                   "recal_false_alarm_rate": o["site_recalibrated_5pct"]["false_alarm_rate"], "recal_detection_rate": o["site_recalibrated_5pct"]["detection_rate_all_attacks"]}
            cmp[m] = {"name_mapped": v, "published": ref, "max_abs_diff": max(abs(v[k] - ref[k]) for k in ref)}
        result["rescore_vs_published"] = cmp

    # ---------------- KS shift
    b17 = A[(label == "BENIGN").to_numpy()]
    days = benign_2018(cols, args.per_day)
    b18 = pd.concat(days.values(), ignore_index=True)
    ks = {}
    for c in cols:
        r = ks_2samp(b18[c].to_numpy(), b17[c].to_numpy())
        ks[c] = {"ks": float(r.statistic), "median_2018": float(b18[c].median()), "median_2017": float(b17[c].median()),
                 "zero_frac_2018": float((b18[c] == 0).mean()), "zero_frac_2017": float((b17[c] == 0).mean()), "model_input": c in model_cols}
    within = {}
    names = list(days)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            within[f"{names[i]} vs {names[j]}"] = {c: float(ks_2samp(days[names[i]][c].to_numpy(), days[names[j]][c].to_numpy()).statistic) for c in model_cols}
    within_max = {c: max(v[c] for v in within.values()) for c in model_cols}
    ranked = sorted(((c, v) for c, v in ks.items() if v["model_input"]), key=lambda kv: -kv[1]["ks"])
    ks_vals = np.array([v["ks"] for _, v in ranked])
    result["ks"] = {"reference_2018": {"days": names, "rows": len(b18), "per_day_cap": args.per_day,
                                       "note": "benign flows from the locally available raw 2018 days; approximates, does not equal, the calibration partition"},
                    "benign_2017_rows": len(b17), "per_feature": ks, "within_2018_day_pairs_max": within_max,
                    "top10": [{"feature": c, **v, "within_2018_max": within_max[c]} for c, v in ranked[:10]],
                    "summary": {"model_inputs": len(ranked), "median_ks": float(np.median(ks_vals)), "n_ks_above_0.3": int((ks_vals > 0.3).sum()),
                                "n_ks_above_within_2018_max": int(sum(v["ks"] > within_max[c] for c, v in ranked)),
                                "median_within_2018_max": float(np.median(list(within_max.values())))}}
    write("transfer_hygiene.json", result)

    L = ["# Transfer hygiene (item 6)", "", "Script `scripts/analysis/transfer_hygiene.py`; JSON `results/analysis/transfer_hygiene.json`.", "",
         f"- Name-mapped and positional feature frames identical: **{identical}** ({len(A):,} rows x {A.shape[1]} columns).",
         f"- 2017 duplicate 'Fwd Header Length' columns identical: {dup.get('identical')} (rows differing: {dup.get('rows_differing')}).", ""]
    if "rescore_vs_published" in result:
        L += ["| Model | FAR (2018 thr.) | DR | Recal. FAR | Recal. DR | max abs diff vs cic2017.json |", "|---|---|---|---|---|---|"]
        for m, v in result["rescore_vs_published"].items():
            n = v["name_mapped"]
            L.append(f"| {m} | {n['false_alarm_rate']:.4f} | {n['detection_rate_all_attacks']:.4f} | {n['recal_false_alarm_rate']:.4f} | {n['recal_detection_rate']:.4f} | {v['max_abs_diff']:.2e} |")
    s = result["ks"]["summary"]
    L += ["", f"## KS shift, 2018 benign ({len(b18):,} rows from {', '.join(names)}) vs 2017 benign ({len(b17):,} rows)", "",
          f"Median KS over the {s['model_inputs']} model inputs: {s['median_ks']:.3f}; {s['n_ks_above_0.3']} features above 0.3; "
          f"{s['n_ks_above_within_2018_max']} features shift more than the largest shift between any two 2018 days (median of that day-to-day maximum: {s['median_within_2018_max']:.3f}).", "",
          "| Rank | Feature | KS 2018 vs 2017 | max KS between 2018 days | median 2018 | median 2017 | zero share 2018 | zero share 2017 |", "|---|---|---|---|---|---|---|---|"]
    for i, t in enumerate(result["ks"]["top10"], 1):
        L.append(f"| {i} | {t['feature']} | {t['ks']:.3f} | {t['within_2018_max']:.3f} | {t['median_2018']:.4g} | {t['median_2017']:.4g} | {t['zero_frac_2018']:.3f} | {t['zero_frac_2017']:.3f} |")
    L += ["", "## Explicit column map (2017 -> 2018)", "", "| CIC-IDS2017 | CSE-CIC-IDS2018 |", "|---|---|"]
    L += [f"| {a} | {b} |" for a, b in NAME_MAP.items()]
    L.append("| (absent; imputed from Dst Port) | Protocol |")
    (OUT / "transfer_hygiene_table.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:40]))


if __name__ == "__main__":
    main()
