"""Stream flow records to the running service in small batches, like a live sensor.

    python app/replay.py app/samples/demo_flows.csv --url http://localhost:8000 --model esnn
"""
import argparse
import json
import time
import urllib.request

import pandas as pd


def post(url, payload):
    request = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--model", default="esnn")
    parser.add_argument("--batch", type=int, default=50)
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()
    frame = pd.read_csv(args.csv, low_memory=False)
    for start in range(0, len(frame), args.batch):
        batch = frame.iloc[start:start+args.batch].drop(columns=["Label"], errors="ignore")
        flows = json.loads(batch.to_json(orient="records"))
        rows = post(f"{args.url}/api/flows", {"model": args.model, "flows": flows})["rows"]
        for i, row in enumerate(rows):
            if row["alarm"]:
                truth = frame["Label"].iloc[start+i] if "Label" in frame else "?"
                print(f"ALARM flow {start+i:>6}  {row['prediction']:<18} log-odds {row['attack_log_odds']:>8}  (label: {truth})")
        time.sleep(args.delay)


if __name__ == "__main__":
    main()
