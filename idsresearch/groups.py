"""Cleaned-feature fingerprint groups, never claimed to be network sessions."""
import numpy as np
import pandas as pd


def fingerprint(X):
    # Canonicalize signed zero, which the classifier treats as the same value.
    # Missing values have already been replaced by zero by the explicit v2
    # cleaning contract. The groups refer to that float32 representation.
    a, b = np.empty(len(X), np.uint64), np.empty(len(X), np.uint64)
    for start in range(0, len(X), 100000):
        values = X.iloc[start:start+100000].astype(np.float32).copy()
        values[values == 0] = 0.
        a[start:start+len(values)] = pd.util.hash_pandas_object(values, index=False).to_numpy(np.uint64)
        b[start:start+len(values)] = pd.util.hash_pandas_object(values.iloc[:, ::-1], index=False).to_numpy(np.uint64)
    return np.rec.fromarrays([a, b], names="a,b")


def group_partition(groups, ratios, seed):
    keys, inverse = np.unique(groups, return_inverse=True)
    rng = np.random.default_rng(seed)
    unit = rng.random(len(keys))
    assignments = np.searchsorted(np.cumsum(ratios), unit, side="right")
    result = [np.flatnonzero(assignments[inverse] == k) for k in range(len(ratios))]
    if any(len(idx) == 0 for idx in result):
        raise ValueError("Too few feature groups for nonempty partitions; no row-wise fallback")
    return result


def group_audit(groups, y, classes):
    _, inv, size = np.unique(groups, return_inverse=True, return_counts=True)
    pair = np.rec.fromarrays([inv, y], names="group,label")
    unique_pair, n = np.unique(pair, return_counts=True)
    n_labels = np.bincount(unique_pair['group'], minlength=len(size))
    conflicting = n_labels > 1
    majority = np.zeros(len(size), dtype=np.int64)
    np.maximum.at(majority, unique_pair['group'], n)
    by_class = {}
    for c, name in enumerate(classes):
        idx = np.flatnonzero(y == c)
        by_class[name] = {"rows": len(idx), "groups": len(np.unique(inv[idx])),
                          "rows_in_conflicting_groups": int(conflicting[inv[idx]].sum())}
    largest = np.argsort(size)[-10:][::-1]
    return {"rows": len(y), "groups": len(size),
            "rows_in_repeated_groups": int(size[size > 1].sum()),
            "conflicting_groups": int(conflicting.sum()),
            "rows_in_conflicting_groups": int(size[conflicting].sum()),
            "empirical_representation_error_floor": float((size-majority).sum()/len(y)),
            "largest_groups": [{"rows": int(size[g]), "label_counts": {
                classes[int(p['label'])]: int(k) for p, k in zip(unique_pair[unique_pair['group']==g], n[unique_pair['group']==g])}}
                for g in largest], "by_class": by_class,
            "definition": "Paired pandas uint64 fingerprints over canonical zero-filled float32 predictors before learned feature selection; excludes label/time/flow identifiers. Hash collisions are not exhaustively ruled out. This is not flow or session identity.",
            "error_floor_scope": "Empirical deterministic-classifier floor on this representation and observed labels, not a population Bayes bound or a macro-F1 bound."}
