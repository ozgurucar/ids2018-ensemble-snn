"""Summarise results/analysis/adapt_label_budget.json into a markdown table.

    python scripts/analysis/adapt_summary.py
"""
import json
from collections import defaultdict

import numpy as np

from records import OUT, write

KEYS = ("labelled_flows", "benign_only_flows", "temperature", "far", "detection_rate", "dr_at_test_far_5pct", "dr_at_test_far_1pct", "macro_f1")


def main():
    d = json.loads((OUT / "adapt_label_budget.json").read_text())
    groups = defaultdict(list)
    for r in d["runs"]:
        for v, res in r["variants"].items():
            groups[(r["method"], r["budget"], v)].append({**res, "budget_size": r["budget_size"]})
    agg = {}
    for (m, b, v), rows in groups.items():
        agg[f"{m}|{b}|{v}"] = {"method": m, "budget": b, "variant": v, "n": len(rows), "budget_size": float(np.mean([x["budget_size"] for x in rows])),
                               **{k: {"mean": float(np.mean([x[k] for x in rows])), "sd": float(np.std([x[k] for x in rows], ddof=1)) if len(rows) > 1 else None,
                                      "values": [x[k] for x in rows]} for k in KEYS}}
        agg[f"{m}|{b}|{v}"]["bot_alarm_rate"] = float(np.mean([x["alarm_rate_per_label"].get("Bot", np.nan) for x in rows]))
    write("adapt_label_budget_summary.json", agg)
    L = ["# CIC-IDS2017 adaptation with label accounting and matched FAR (item 5)", "",
         "Source: `results/analysis/adapt_label_budget.json` (script `scripts/analysis/adapt_label_budget.py`). Means over seeds 42, 43, 44 (s.d. in the JSON).",
         "Labelled = flows with a class label (budget + temperature rows). Benign-only = flows that must be known benign for the alarm threshold (no attack labels).",
         "DR@FAR is read off the test ROC at exactly that test FAR (oracle comparison view).", "",
         "| Method | Budget | Variant | Labelled | Benign-only | T | FAR | DR | DR@FAR 5% | DR@FAR 1% | Macro-F1 | Bot alarm |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    order = {"frozen_recal_esnn_t4": 0, "frozen_recal_xgb": 1, "esnn_t4_finetune": 2, "xgb_scratch": 3, "xgb_continue": 4}
    vorder = {"orig": 0, "budget_T": 1, "no_T": 2, "strict": 3}
    for key in sorted(agg, key=lambda k: (agg[k]["budget"], order[agg[k]["method"]], vorder[agg[k]["variant"]])):
        a = agg[key]
        L.append(f"| {a['method']} | {a['budget']:.1%} | {a['variant']} | {a['labelled_flows']['mean']:,.0f} | {a['benign_only_flows']['mean']:,.0f} | {a['temperature']['mean']:.2f} | "
                 f"{a['far']['mean']:.3f} | {a['detection_rate']['mean']:.3f} | {a['dr_at_test_far_5pct']['mean']:.3f} | {a['dr_at_test_far_1pct']['mean']:.3f} | {a['macro_f1']['mean']:.3f} | {a['bot_alarm_rate']:.3f} |")
    (OUT / "adapt_label_budget_table.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
