import copy
import random
import time
import os
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import f1_score
from .data import CLASSES
from .models import build


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def weights(y, ceiling):
    count = np.bincount(y, minlength=len(CLASSES))
    w = np.zeros(len(CLASSES), dtype=np.float32)
    seen = count > 0
    w[seen] = np.minimum(len(y)/(seen.sum()*count[seen]), ceiling)
    w[seen] /= w[seen].mean()
    return w


@torch.no_grad()
def neural_logits(model, X, batch_size, device):
    model.eval().to(device)
    output = []
    for start in range(0, len(X), batch_size):
        batch = torch.tensor(np.asarray(X[start:start+batch_size]), dtype=torch.float32, device=device)
        output.append(model(batch).cpu().numpy())
    return np.concatenate(output)


def train_neural(name, X, y, tune_X, tune_y, config, seed, device, resume_path=None, full_counts=None):
    seed_all(seed)
    model = build(name, X.shape[1], len(CLASSES), config).to(device)
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(TensorDataset(torch.tensor(np.asarray(X)), torch.tensor(y)), batch_size=config.batch_size, shuffle=True, generator=generator)
    weight = torch.tensor(np.ones(len(CLASSES), np.float32) if config.loss == "ce" else weights(y, config.weight_ceiling), device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.lr, weight_decay=config.weight_decay)
    history, best, best_state, stale = [], -1., None, 0
    from .decision import prior_offset, log_probabilities
    from .provenance import digest, file_hash, write_json, read_json
    full_counts = np.bincount(y, minlength=len(CLASSES)) if full_counts is None else full_counts
    offset = prior_offset(full_counts, np.bincount(y, minlength=len(CLASSES)), weight.cpu().numpy(), config.prior_correction)
    start_epoch, previous_seconds = 0, 0.
    contract = digest({"config": config.dictionary(), "name": name, "seed": seed,
                       "full_counts": list(map(int, full_counts)), "features": X.shape[1]})
    resume_path = Path(resume_path) if resume_path else None
    if resume_path and resume_path.exists():
        stamp = read_json(resume_path.with_suffix(".json"))
        if stamp["contract"] != contract or file_hash(resume_path) != stamp["sha256"]:
            raise ValueError("Resume checkpoint/contract mismatch")
        saved = torch.load(resume_path, map_location="cpu", weights_only=False)
        model.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        history, best, best_state, stale = saved["history"], saved["best"], saved["best_state"], saved["stale"]
        start_epoch, previous_seconds = saved["epoch"], saved["seconds"]
        random.setstate(saved["python_rng"]); np.random.set_state(saved["numpy_rng"])
        torch.set_rng_state(saved["torch_rng"]); generator.set_state(saved["loader_rng"])
        if torch.cuda.is_available() and saved["cuda_rng"] is not None:
            torch.cuda.set_rng_state_all(saved["cuda_rng"])
    start = time.perf_counter()
    for epoch in range(start_epoch, config.epochs):
        if stale >= config.patience:
            break
        model.train()
        total = 0.
        for features, target in loader:
            features, target = features.to(device), target.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(features)
            losses = nn.functional.cross_entropy(logits, target, weight=weight, reduction="none")
            if config.loss == "focal":
                pt = logits.softmax(1).gather(1, target[:, None]).squeeze(1)
                losses = (1-pt).pow(config.focal_gamma)*losses
            loss = losses.mean()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step()
            total += float(loss.detach())*len(target)
        tune_logits = neural_logits(model, tune_X, config.batch_size, device).astype(float)+offset
        predictions = tune_logits.argmax(1)
        score = float(f1_score(tune_y, predictions, labels=np.arange(len(CLASSES)), average="macro", zero_division=0))
        tune_nll = float(-log_probabilities(tune_logits)[np.arange(len(tune_y)), tune_y].mean())
        selection = score if config.selection_metric == "corrected_macro_f1" else -tune_nll
        history.append({"epoch": epoch+1, "train_loss": total/len(y), "tune_macro_f1": score, "tune_nll": tune_nll})
        print(f"{name} seed={seed} epoch={epoch+1} tune_macro_f1={score:.4f}", flush=True)
        if best_state is None or selection > best:
            best, stale = selection, 0
            best_state = copy.deepcopy(model.state_dict())
        else:
            stale += 1
        if resume_path:
            resume_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = resume_path.with_suffix(".tmp")
            torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(),
                        "history": history, "best": best, "best_state": best_state, "stale": stale,
                        "epoch": epoch+1, "seconds": previous_seconds+time.perf_counter()-start,
                        "python_rng": random.getstate(), "numpy_rng": np.random.get_state(),
                        "torch_rng": torch.get_rng_state(), "loader_rng": generator.get_state(),
                        "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None}, temporary)
            os.replace(temporary, resume_path)
            write_json(resume_path.with_suffix(".json"), {"contract": contract, "sha256": file_hash(resume_path)})
    model.load_state_dict(best_state)
    return model.cpu(), {"selection_partition": "tune", "selection_metric": config.selection_metric,
                         "best_selection_value": best, "history": history,
                         "train_seconds": previous_seconds+time.perf_counter()-start,
                         "parameters": sum(p.numel() for p in model.parameters()),
                         "class_weights": weight.cpu().tolist()}


def train_tree(name, X, y, config, seed, tune_X=None, tune_y=None):
    if name == "rf":
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=config.rf_trees, max_depth=25, n_jobs=2, random_state=seed)
    elif name == "catboost":
        from catboost import CatBoostClassifier
        model = CatBoostClassifier(iterations=config.catboost_trees, depth=8, learning_rate=.05,
                                   loss_function="MultiClass", random_seed=seed, thread_count=2,
                                   verbose=False, allow_writing_files=False)
    else:
        from xgboost import XGBClassifier
        model = XGBClassifier(n_estimators=config.xgb_trees, max_depth=8, learning_rate=0.1,
                             subsample=0.8, colsample_bytree=0.8, tree_method="hist", n_jobs=2, random_state=seed)
    classes, encoded = np.unique(y, return_inverse=True)
    start = time.perf_counter()
    weight = np.ones(len(CLASSES), np.float32) if config.loss == "ce" else weights(y, config.weight_ceiling)
    model.fit(X, encoded, sample_weight=weight[y])
    return {"estimator": model, "class_ids": classes}, {"train_seconds": time.perf_counter()-start,
             "selection_partition": "none", "selection_metric": "pre-specified tree hyperparameters", "class_weights": weight.tolist()}


def tree_proba(wrapper, X):
    proba = wrapper["estimator"].predict_proba(X)
    full = np.zeros((len(X), len(CLASSES)), dtype=np.float32)
    full[:, wrapper["class_ids"]] = proba
    return full
