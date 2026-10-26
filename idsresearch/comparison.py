"""Paired seed differences are descriptive, not independent-flow significance."""
from .pipeline import summarize, validated
from .provenance import write_json
from .metrics import aggregate


def compare(left, right, destination):
    lm, lc = validated(left)
    rm, rc = validated(right)
    a, b = summarize(left), summarize(right)
    if lm["dataset"]["dataset_id"] != rm["dataset"]["dataset_id"]:
        raise ValueError("Protocol comparison requires the same cleaned row universe")
    if a["missing_runs"] or b["missing_runs"]:
        raise ValueError("Complete both declared matrices before comparing protocols")
    if list(lc.seeds) != list(rc.seeds) or list(lc.models) != list(rc.models):
        raise ValueError("Model and seed sets must match")
    c1, c2 = lc.dictionary(), rc.dictionary()
    for key in ("split", "selection_note"):
        c1.pop(key)
        c2.pop(key)
    if c1 != c2:
        raise ValueError("Configurations differ beyond the split protocol")
    result = {"left_experiment": lm["experiment_id"], "right_experiment": rm["experiment_id"],
              "direction": "right minus left", "interpretation": "Combined protocol effect; support, covariate shift and overlap can all change. Not an isolated leakage estimate.", "models": {}}
    for name in lc.models:
        left_by_seed = {r["seed"]: r for r in a["per_seed"][name]}
        differences = []
        for r in b["per_seed"][name]:
            p = left_by_seed[r["seed"]]["operating_points"][str(lc.primary_tau)]["test"]
            q = r["operating_points"][str(rc.primary_tau)]["test"]
            differences.append({k: q[k]-p[k] if q[k] is not None and p[k] is not None else None for k in ("macro_f1", "weighted_f1", "accuracy", "adr", "fpr")})
        result["models"][name] = {"seed_order": list(rc.seeds), "paired_differences": differences, "summary": aggregate(differences)}
    result["supports"] = {"left": lm["split"]["counts"], "right": rm["split"]["counts"]}
    write_json(destination, result)
    return result
