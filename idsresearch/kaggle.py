"""Kaggle helpers: locate the attached dataset and fix its timestamp format."""
from pathlib import Path
import subprocess
import sys
import pandas as pd
from .provenance import write_json

EXPECTED = ("02-14-2018.csv", "02-15-2018.csv", "02-16-2018.csv",
            "02-20-2018.csv", "02-21-2018.csv", "02-22-2018.csv",
            "02-23-2018.csv", "02-28-2018.csv", "03-01-2018.csv", "03-02-2018.csv")


def find_data(input_root="/kaggle/input"):
    root = Path(input_root)
    preferred = [root/"datasets/solarmainframe/ids-intrusion-csv", root/"ids-intrusion-csv"]
    def complete(folder):
        files = sorted(folder.rglob("*.csv")) if folder.exists() else []
        return len(files) == len(EXPECTED) and {p.name.casefold() for p in files} == set(EXPECTED)
    for p in preferred:
        if complete(p):
            return p
    matches = []
    for first in root.rglob(EXPECTED[0]):
        for parent in first.parents:
            if parent == root:
                break
            if complete(parent):
                matches.append(parent)
                break
    matches = sorted(set(matches))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one complete 10-CSV copy of CSE-CIC-IDS2018, found {matches}. Attach solarmainframe/ids-intrusion-csv once.")
    return matches[0]


def detect_time_format(data, destination):
    """Pick the one timestamp format that parses every sampled row.

    Only the syntax is inferred. An AM/PM or clock offset is never guessed or
    repaired, so the result stays marked as unverified.
    """
    samples, inspected = [], []
    for file in sorted(Path(data).rglob("*.csv")):
        frame = pd.read_csv(file, nrows=2048, low_memory=False)
        columns = {str(c).strip().casefold(): c for c in frame.columns}
        if "timestamp" not in columns or "label" not in columns:
            raise ValueError(f"Label and Timestamp are required: {file.name}")
        values = frame[columns["timestamp"]].astype(str).str.strip()
        labels = frame[columns["label"]].astype(str).str.strip()
        values = values[labels.str.casefold() != "label"]
        samples.extend(values.tolist())
        inspected.append({"file": file.name, "rows_inspected": len(frame), "timestamp_examples": values.head(5).tolist()})
    series = pd.Series(samples)
    candidates = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S.%f",
                  "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f",
                  "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %I:%M:%S %p",
                  "%m/%d/%Y %I:%M:%S %p")
    valid = []
    details = []
    for fmt in candidates:
        parsed = pd.to_datetime(series, format=fmt, errors="coerce")
        mask = parsed.notna() & (parsed >= "2018-02-14") & (parsed < "2018-03-03")
        details.append({"format": fmt, "valid_samples": int(mask.sum()), "samples": len(series)})
        if len(series) and mask.all():
            valid.append((fmt, parsed))
    report = {"source": str(data), "files": inspected, "candidates": details,
              "timestamp_status": "unverified", "note": "Format validation is not capture-clock validation; no 12-hour correction."}
    write_json(destination, report)
    if not valid:
        raise ValueError(f"No single timestamp format parses every sample; see {destination}")
    chosen, parsed = valid[0]
    if any(not parsed.equals(other) for _, other in valid[1:]):
        raise ValueError(f"Ambiguous day/month order. Inspect {destination}.")
    report["selected_format"] = chosen
    write_json(destination, report)
    return chosen


def run_command(repo, *arguments):
    subprocess.run([sys.executable, "-u", "-B", "-m", "idsresearch", *map(str, arguments)], cwd=repo, check=True)


