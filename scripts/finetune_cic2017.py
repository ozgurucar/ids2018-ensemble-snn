"""Local adaptation on CIC-IDS2017: how many labelled local flows recover detection?

Starting point: the frozen CSE-CIC-IDS2018 detectors transfer badly to
CIC-IDS2017 (scripts/cross_dataset_cic2017.py). Here an operator is assumed to
label a small stratified sample of local traffic. We compare

  frozen_recal     frozen 2018 model, only the 5% alarm threshold refitted on
                   2017 benign calibration flows (no attack labels; budget 0)
  esnn_t4_finetune E-SNN T=4 fine-tuned from the 2018 checkpoint (all layers,
                   fixed schedule, small lr, frozen 2018 preprocessor)
  xgb_scratch      XGBoost trained from scratch on the budget only (same
                   preprocessed features, same 2018 hyperparameters)
  xgb_continue     2018 XGBoost continued with extra boosting rounds on the
                   budget (13-class space, so PortScan rows are not usable)

Leakage control. The 2017 rows are split by feature-vector fingerprint groups
(idsresearch.groups) into adaptation pool / calibration / test (50/10/40),
label-blind, fixed seed. Budgets are class-stratified samples of the pool only.
The calibration partition is split by groups into a probability half
(temperature) and an alarm half (5% benign threshold), as in
idsresearch/evaluation_v3.py. No hyperparameter, epoch count or threshold is
chosen with test rows; all training schedules are fixed in advance.

Label space: the 13 CSE-CIC-IDS2018 classes plus PortScan (index 13).
Heartbleed (11 rows) has no class: it is never trained on, it is excluded from
macro-F1, and it counts as an attack in the binary alarm metrics.

    python scripts/finetune_cic2017.py ~/.cache/ids-x17/combine.csv \
        results/cross_dataset/finetune_cic2017.json --seeds 42 43 44
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "app"), str(ROOT / "scripts")]
from detector import Detector  # noqa: E402
from cross_dataset_cic2017 import load  # noqa: E402
from idsresearch.data import CLASSES  # noqa: E402
from idsresearch.decision import alarm_score, log_probabilities, prior_offset, temperature_fit, threshold_fit  # noqa: E402
from idsresearch.groups import fingerprint, group_audit, group_partition  # noqa: E402
from idsresearch.models import build  # noqa: E402
from idsresearch.training import neural_logits, seed_all  # noqa: E402
from sklearn.metrics import f1_score  # noqa: E402

LABELS = tuple(CLASSES) + ("PortScan",)
K = len(LABELS)
PORTSCAN = K - 1
TAU = 0.05
MASK = -1e9


def to_index(family):
    lookup = {name: i for i, name in enumerate(LABELS)}
    return family.map(lambda s: lookup.get(s, -1)).to_numpy(np.int64)


def stratified_budget(y, pool, fraction, rng):
    """Proportional class-stratified sample of the pool; every class present in
    the pool keeps at least one row. Rows without a class (-1) are never drawn."""
    yp = y[pool]
    n = int(round(fraction * len(pool)))
    classes, sizes = np.unique(yp[yp >= 0], return_counts=True)
    alloc = np.maximum(1, np.floor(n * sizes / sizes.sum()).astype(int))
    alloc = np.minimum(alloc, sizes)
    chosen = np.concatenate([rng.choice(pool[yp == c], a, replace=False) for c, a in zip(classes, alloc)])
    return np.sort(chosen)


def counts(y):
    return {LABELS[i] if i >= 0 else "Heartbleed(unclassed)": int((y == i).sum()) for i in range(-1, K) if (y == i).any()}


# ---------------------------------------------------------------- models
def esnn_14(detector, config):
    """2018 E-SNN with one extra output (PortScan); old weights copied exactly."""
    old = detector.model.state_dict()
    model = build("esnn", len(detector.preprocessor.columns_), K, config)
    new = model.state_dict()
    for key, value in old.items():
        if new[key].shape == value.shape:
            new[key] = value.clone()
        elif key.endswith("readout.weight") or key == "meta.2.weight":
            new[key].zero_(); new[key][:K - 1] = value
        elif key.endswith("readout.bias") or key == "meta.2.bias":
            new[key].zero_(); new[key][:K - 1] = value
        elif key == "meta.0.weight":
            # input = concat of branch logits, (K-1) per branch -> K per branch
            new[key].zero_()
            branches = value.shape[1] // (K - 1)
            for b in range(branches):
                new[key][:, b * K:b * K + K - 1] = value[:, b * (K - 1):(b + 1) * (K - 1)]
        else:
            raise ValueError(f"Unexpected shape change: {key}")
    model.load_state_dict(new)
    return model


def finetune_esnn(detector, config, X, y, seed, lr, batch, min_steps, min_epochs):
    seed_all(seed)
    model = esnn_14(detector, config)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=config.weight_decay)
    Xt, yt = torch.tensor(X), torch.tensor(y)
    per_epoch = int(np.ceil(len(y) / batch))
    epochs = max(min_epochs, int(np.ceil(min_steps / per_epoch)))
    gen = torch.Generator().manual_seed(seed)
    history = []
    model.train()
    for epoch in range(epochs):
        order = torch.randperm(len(y), generator=gen)
        total = 0.
        for s in range(0, len(y), batch):
            idx = order[s:s + batch]
            opt.zero_grad(set_to_none=True)
            loss = nn.functional.cross_entropy(model(Xt[idx]), yt[idx])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            opt.step()
            total += float(loss.detach()) * len(idx)
        history.append(round(total / len(y), 5))
    model.eval()
    return model, {"epochs": epochs, "steps": epochs * per_epoch, "lr": lr, "batch": batch,
                   "train_loss_per_epoch": history}


def esnn_logits(model, X):
    with torch.no_grad():
        return neural_logits(model, X, 4096, "cpu").astype(float)


def xgb_scratch(X, y, seed, trees, threads):
    from xgboost import XGBClassifier
    classes, enc = np.unique(y, return_inverse=True)
    model = XGBClassifier(n_estimators=trees, max_depth=8, learning_rate=0.1, subsample=0.8,
                          colsample_bytree=0.8, tree_method="hist", n_jobs=threads, random_state=seed)
    if len(classes) == 1:
        raise ValueError("Budget has a single class")
    model.fit(X, enc)

    def logits(Z):
        p = np.zeros((len(Z), K))
        p[:, classes] = model.predict_proba(Z)
        return np.log(np.maximum(p, 1e-12))
    return logits, {"trees": trees, "classes": [LABELS[c] for c in classes]}


def xgb_continue(booster, X, y, seed, rounds, threads):
    import xgboost as xgb
    keep = y < PORTSCAN
    params = {"objective": "multi:softprob", "num_class": K - 1, "max_depth": 8, "eta": 0.1,
              "subsample": 0.8, "colsample_bytree": 0.8, "tree_method": "hist", "nthread": threads, "seed": seed}
    model = xgb.train(params, xgb.DMatrix(X[keep], label=y[keep]), num_boost_round=rounds, xgb_model=booster.copy())

    def logits(Z):
        p = np.zeros((len(Z), K))
        p[:, :K - 1] = model.predict(xgb.DMatrix(Z))
        return np.log(np.maximum(p, 1e-12))
    return logits, {"extra_rounds": rounds, "dropped_portscan_rows": int((~keep).sum())}


# ---------------------------------------------------------------- decision + metrics
def calibrate(cal_logits, cal_y, prob_idx, alarm_idx, offset, fit_temperature=True, temperature=None):
    if fit_temperature:
        usable = prob_idx[(cal_y[prob_idx] >= 0) & (offset[np.maximum(cal_y[prob_idx], 0)] > MASK / 2)]
        temp = temperature_fit(cal_logits[usable] + offset, cal_y[usable])
    else:
        temp = {"temperature": temperature, "fit_partition": "2018 (frozen)"}
    z = (cal_logits + offset) / temp["temperature"]
    benign = alarm_idx[cal_y[alarm_idx] == 0]
    rule = threshold_fit(alarm_score(z[benign]), TAU, 1000)
    return temp, rule


def evaluate(logits, offset, temperature, threshold, y, raw_label, families_present):
    z = (logits + offset) / temperature
    score = alarm_score(z)
    alarm = score > threshold
    pred = np.where(alarm, z[:, 1:].argmax(1) + 1, 0)
    attack = raw_label != "BENIGN"
    classed = y >= 0
    per = {}
    for value in sorted(np.unique(raw_label)):
        rows = raw_label == value
        per[value] = {"n": int(rows.sum()), "alarm_rate": float(alarm[rows].mean()),
                      "correct_family": float((pred[rows] == y[rows]).mean()) if value != "BENIGN" and classed[rows].all() else None}
    seen18 = [c for c in families_present if c != PORTSCAN]
    return {"far": float(alarm[~attack].mean()),
            "detection_rate": float(alarm[attack].mean()),
            "detection_rate_excl_portscan": float(alarm[attack & (y != PORTSCAN)].mean()),
            "macro_f1": float(f1_score(y[classed], pred[classed], labels=families_present, average="macro", zero_division=0)),
            "macro_f1_2018_families": float(f1_score(y[classed], pred[classed], labels=seen18, average="macro", zero_division=0)),
            "per_label": per}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv")
    ap.add_argument("out")
    ap.add_argument("--budgets", type=float, nargs="+", default=[0.001, 0.01, 0.05])
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    ap.add_argument("--split-seed", type=int, default=2017)
    ap.add_argument("--ratios", type=float, nargs=3, default=[0.5, 0.1, 0.4])
    ap.add_argument("--test-benign-cap", type=int, default=0, help="0 = use every benign test row")
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--min-steps", type=int, default=300)
    ap.add_argument("--min-epochs", type=int, default=5)
    ap.add_argument("--xgb-trees", type=int, default=400)
    ap.add_argument("--xgb-extra-rounds", type=int, default=100)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--methods", nargs="+", default=["esnn_t4_finetune", "xgb_scratch", "xgb_continue"])
    args = ap.parse_args()
    torch.set_num_threads(args.threads)
    t0 = time.perf_counter()

    esnn, xgbd = Detector("esnn_t4"), Detector("xgb")
    frame, raw_label, family = load(args.csv, esnn.input_columns)
    raw_label = raw_label.to_numpy()
    y = to_index(family)
    X = frame[esnn.input_columns].apply(pd.to_numeric, errors="coerce").astype(np.float32)
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    del frame
    groups = fingerprint(X)
    audit = group_audit(groups, np.where(y < 0, K, y), LABELS + ("Heartbleed",))
    Z = np.concatenate([esnn.preprocessor.transform(X.iloc[s:s + 200000]) for s in range(0, len(X), 200000)])
    del X
    print(f"loaded {len(y)} rows, {audit['groups']} groups in {time.perf_counter()-t0:.0f}s", flush=True)

    pool, cal, test = group_partition(groups, tuple(args.ratios), args.split_seed)
    prob_local, alarm_local = group_partition(groups[cal], (.5, .5), args.split_seed + 177)
    rng = np.random.default_rng(args.split_seed + 178)
    prob_local = np.sort(rng.choice(prob_local, min(len(prob_local), 100000), replace=False))
    test_note = "all test rows"
    if args.test_benign_cap:
        b = test[raw_label[test] == "BENIGN"]
        if len(b) > args.test_benign_cap:
            keep_b = np.random.default_rng(args.split_seed + 179).choice(b, args.test_benign_cap, replace=False)
            test = np.sort(np.concatenate([test[raw_label[test] != "BENIGN"], keep_b]))
            test_note = f"benign test rows subsampled to {args.test_benign_cap}"
    Zc, yc = Z[cal], y[cal]
    Zt, yt, lt = Z[test], y[test], raw_label[test]
    present = sorted(int(c) for c in np.unique(yt[yt >= 0]))

    report = {"protocol": {
        "data": f"{args.csv} (CIC-IDS2017 MachineLearningCVE, {len(y)} rows); Protocol imputed from port",
        "split": f"feature-fingerprint groups (idsresearch.groups), label-blind, ratios pool/calibration/test={args.ratios}, seed {args.split_seed}",
        "calibration": "calibration partition split by groups 50/50: probability half (temperature, <=100k rows, classes represented in the model's training data only) and alarm half (threshold at 5% benign FPR, empirical order statistic, idsresearch.decision.threshold_fit)",
        "prior_offset": "adapted models: idsresearch.decision.prior_offset(budget, budget) -> 0 for classes in the budget, masked (-1e9) for classes absent from it; budget is a proportional stratified sample so no prior shift. frozen_recal keeps the 2018 offset and temperature.",
        "label_space": "13 CSE-CIC-IDS2018 classes + PortScan; Heartbleed unclassed (attack in binary metrics, excluded from macro-F1)",
        "budget_sampling": "proportional class-stratified sample of the pool, >=1 row per class present in the pool, seed-dependent",
        "esnn_t4_finetune": f"from app/models/esnn_t4.pt, all layers, extra PortScan output (zero-initialised), AdamW lr={args.lr}, wd=1e-3, batch={args.batch}, max({args.min_epochs} epochs, {args.min_steps} steps), unweighted CE, no early stopping or selection",
        "xgb_scratch": f"XGBClassifier {args.xgb_trees} trees, depth 8, lr 0.1, subsample/colsample 0.8 (2018 settings), on 2018-preprocessed features",
        "xgb_continue": f"2018 booster + {args.xgb_extra_rounds} rounds on the budget (PortScan rows dropped: 13-class model)",
        "test": test_note, "macro_f1": "over classes present in the test partition (14-class space incl. PortScan); prediction = argmax attack class if alarm else Benign",
        "no_test_use": "no choice (epochs, lr, rounds, thresholds) uses test rows"},
        "group_audit": {k: audit[k] for k in ("rows", "groups", "rows_in_repeated_groups", "conflicting_groups", "rows_in_conflicting_groups", "empirical_representation_error_floor")},
        "partitions": {"pool": counts(y[pool]), "calibration": counts(yc), "calibration_probability_rows": len(prob_local),
                       "calibration_alarm_rows": len(alarm_local), "test": counts(yt)},
        "summary": [], "runs": []}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    def save():
        report["seconds_total"] = time.perf_counter() - t0
        out.write_text(json.dumps(report, indent=1))

    def record(method, budget, seed, logits_fn, offset, info, fit_temperature=True, temperature=None, budget_counts=None, train_seconds=None):
        s = time.perf_counter()
        temp, rule = calibrate(logits_fn(Zc), yc, prob_local, alarm_local, offset, fit_temperature, temperature)
        res = evaluate(logits_fn(Zt), offset, temp["temperature"], rule["threshold"], yt, lt, present)
        run = {"method": method, "budget": budget, "seed": seed, "budget_counts": budget_counts, "info": info,
               "temperature": temp["temperature"], "threshold": rule["threshold"],
               "calibration_fpr": rule["empirical_calibration_fpr"], "train_seconds": train_seconds,
               "score_seconds": time.perf_counter() - s, **res}
        report["runs"].append(run)
        report["summary"].append({k: run[k] for k in ("method", "budget", "seed", "far", "detection_rate", "detection_rate_excl_portscan", "macro_f1")})
        print(f"{method:17s} budget={budget:<6} seed={seed} FAR={res['far']:.4f} DR={res['detection_rate']:.4f} "
              f"DR-PS={res['detection_rate_excl_portscan']:.4f} mF1={res['macro_f1']:.4f}", flush=True)
        save()

    def pad(fn):
        return lambda Z_: np.concatenate([fn(Z_), np.full((len(Z_), 1), np.log(1e-12))], 1)

    # Budget 0: frozen 2018 models, threshold refitted on 2017 benign calibration flows only.
    for name, det in (("esnn_t4", esnn), ("xgb", xgbd)):
        record(f"frozen_recal_{name}", 0.0, None, pad(det.logits), np.r_[det.offset, MASK], {"note": "2018 offset/temperature, 2017 threshold"},
               fit_temperature=False, temperature=det.temperature)

    booster = xgbd.model["estimator"].get_booster()
    for budget in args.budgets:
        for seed in args.seeds:
            idx = stratified_budget(y, pool, budget, np.random.default_rng(seed * 1000 + int(budget * 1e5)))
            Xb, yb = Z[idx], y[idx]
            bc = np.bincount(yb, minlength=K)
            offset = prior_offset(bc, bc, np.ones(K))
            bcounts = counts(yb)
            if "esnn_t4_finetune" in args.methods:
                s = time.perf_counter()
                model, info = finetune_esnn(esnn, esnn.config, Xb, yb, seed, args.lr, args.batch, args.min_steps, args.min_epochs)
                record("esnn_t4_finetune", budget, seed, lambda Z_: esnn_logits(model, Z_), offset, info,
                       budget_counts=bcounts, train_seconds=time.perf_counter() - s)
            if "xgb_scratch" in args.methods:
                s = time.perf_counter()
                fn, info = xgb_scratch(Xb, yb, seed, args.xgb_trees, args.threads)
                record("xgb_scratch", budget, seed, fn, offset, info, budget_counts=bcounts, train_seconds=time.perf_counter() - s)
            if "xgb_continue" in args.methods:
                s = time.perf_counter()
                fn, info = xgb_continue(booster, Xb, yb, seed, args.xgb_extra_rounds, args.threads)
                off = offset.copy(); off[PORTSCAN] = MASK
                record("xgb_continue", budget, seed, fn, off, info, budget_counts=bcounts, train_seconds=time.perf_counter() - s)
    save()
    print(f"done in {time.perf_counter()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
