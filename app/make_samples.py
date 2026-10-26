"""Build the small bundled demo file from raw CSE-CIC-IDS2018 day CSVs.

These rows come from the public dataset and may overlap the v3 test split,
so demo numbers illustrate the service; they are not an evaluation.

    python app/make_samples.py RAW_DIR app/samples/demo_flows.csv
"""
import sys
from pathlib import Path

import pandas as pd

PER_CLASS = 400


def main(raw_dir, out):
    parts = []
    for file in sorted(Path(raw_dir).glob("*.csv")):
        frame = pd.read_csv(file, low_memory=False)
        frame.columns = frame.columns.str.strip()
        frame = frame[frame["Label"].astype(str).str.casefold() != "label"]
        for _, group in frame.groupby("Label"):
            parts.append(group.sample(min(len(group), PER_CLASS), random_state=7))
    sample = pd.concat(parts).sample(frac=1, random_state=7)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(out, index=False)
    print(sample["Label"].value_counts().to_string())


if __name__ == "__main__":
    main(*sys.argv[1:3])
