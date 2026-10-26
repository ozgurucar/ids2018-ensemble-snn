"""No learned preprocessing before partitioning. Timestamp grouping is a proxy."""
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import QuantileTransformer, RobustScaler
from .provenance import digest, file_hash

CLASSES = ("Benign", "Bot", "DDoS-HOIC", "DDoS-LOIC-UDP", "DDoS-LOIC-HTTP",
           "DoS-GoldenEye", "DoS-Hulk", "DoS-SlowHTTPTest", "DoS-Slowloris",
           "FTP-BruteForce", "Infiltration", "SSH-Bruteforce", "Web Attacks")
ALIASES = {x.casefold(): i for i, x in enumerate(CLASSES)}
ALIASES.update({"ddos attack-hoic": 2, "ddos attack-loic-udp": 3,
                "ddos attacks-loic-http": 4, "dos attacks-goldeneye": 5,
                "dos attacks-hulk": 6, "dos attacks-slowhttptest": 7,
                "dos attacks-slowloris": 8, "infilteration": 10,
                "brute force -web": 12, "brute force -xss": 12, "sql injection": 12})
DROP = {"label", "timestamp", "flow id", "src ip", "source ip", "dst ip",
        "destination ip", "src port", "source port"}
PARTS = ("train", "tune", "calibration", "test")


@dataclass
class Raw:
    X: pd.DataFrame
    y: np.ndarray
    time: np.ndarray
    ids: np.ndarray
    report: dict


def discover(path, max_files=None):
    files = sorted(Path(path).rglob("*.csv"))
    if not files:
        raise ValueError(f"No CSV files found in {path}")
    return files[:max_files] if max_files else files


def load(path, timestamp_format, max_files=None):
    """Read all rows, numeric float32 chunks, with file:physical-row identity.

    Explicit timestamp format is mandatory. No guessed AM/PM correction.
    Only repeated headers and unknown dates are removed; all counts are logged.
    """
    frames, targets, times, identities, reports = [], [], [], [], []
    schema = None
    nonfinite = {}
    dropped_time = repeated_headers = 0
    for number, file in enumerate(discover(path, max_files)):
        offset, kept = 0, 0
        for frame in pd.read_csv(file, chunksize=100000, low_memory=False):
            frame.columns = frame.columns.str.strip()
            if frame.columns.duplicated().any():
                raise ValueError(f"Duplicate columns: {file}")
            columns = {c.casefold(): c for c in frame.columns}
            if "label" not in columns or "timestamp" not in columns:
                raise ValueError(f"Label and Timestamp required: {file}")
            ids = (np.uint64(number) << np.uint64(48)) + np.arange(offset, offset + len(frame), dtype=np.uint64)
            offset += len(frame)
            labels = frame[columns["label"]].astype(str).str.strip().str.casefold()
            header = labels == "label"
            repeated_headers += int(header.sum())
            unknown = sorted(set(labels[~header]) - set(ALIASES))
            if unknown:
                raise ValueError(f"Unknown labels in {file}: {unknown[:10]}")
            ts = pd.to_datetime(frame[columns["timestamp"]].astype(str).str.strip(), format=timestamp_format, errors="coerce")
            valid = ~header & ts.notna() & (ts >= "2018-02-14") & (ts < "2018-03-03")
            dropped_time += int((~header & ~valid).sum())
            feature_cols = [c for c in frame if c.casefold() not in DROP]
            if schema is None:
                schema = feature_cols
            if set(feature_cols) != set(schema):
                raise ValueError(f"Feature schema differs across CSVs: {file}")
            numeric = frame.loc[valid, schema].apply(pd.to_numeric, errors="coerce").astype(np.float32)
            for col in numeric:
                nonfinite[col] = nonfinite.get(col, 0) + int((~np.isfinite(numeric[col].to_numpy())).sum())
            numeric = numeric.replace([np.inf, -np.inf], np.nan).fillna(0)
            frames.append(numeric)
            targets.append(labels[valid].map(ALIASES).to_numpy(dtype=np.int64))
            times.append(ts[valid].to_numpy(dtype="datetime64[ns]"))
            identities.append(ids[valid.to_numpy()])
            kept += int(valid.sum())
        reports.append({"file": str(file.relative_to(path)), "sha256": file_hash(file), "rows": offset, "kept": kept})
    X = pd.concat(frames, ignore_index=True)
    if len(X) == 0:
        raise ValueError("No valid rows; check the timestamp format")
    report = {"files": reports, "timestamp_format": timestamp_format,
              "dropped_timestamp": dropped_time, "repeated_headers": repeated_headers,
              "retained": len(X), "sampling": "all rows before split", "nonfinite_replaced_with_zero": nonfinite, "cleaning_note": "Float32 and zero imputation retained for continuity; missing/true-zero equivalence is explicitly audited, not assumed harmless."}
    report["dataset_id"] = digest(report)
    return Raw(X, np.concatenate(targets), np.concatenate(times), np.concatenate(identities), report)


def counts(y):
    return {name: int((y == i).sum()) for i, name in enumerate(CLASSES)}


def time_groups(time, gap_minutes):
    return np.r_[0, np.cumsum(np.diff(time) > np.timedelta64(gap_minutes, "m"))].astype(int)


def audit(raw):
    classes = {}
    for c, name in enumerate(CLASSES):
        t = np.sort(raw.time[raw.y == c])
        if not len(t):
            classes[name] = {"n": 0}
            continue
        classes[name] = {"n": len(t), "first": str(t[0]), "last": str(t[-1]),
                         "span_minutes": float((t[-1]-t[0])/np.timedelta64(1, "m")),
                         "by_day": {str(d): int((t.astype("datetime64[D]") == d).sum()) for d in np.unique(t.astype("datetime64[D]"))},
                         "groups_by_gap_minutes": {str(g): int(time_groups(t, g)[-1]+1) for g in (5, 15, 30, 60)}}
    return {"dataset": raw.report, "classes": classes,
            "timestamp_status": "unverified", "review_required": [
                "Compare raw timestamps against source capture documentation; inspect missing AM/PM.",
                "Do not add 12 hours globally or use attack labels to silently repair clocks.",
                "Time groups do not establish independently captured attack sessions.",
                "Verify dropped-row counts and minority-class coverage."]}


def partition(raw, config):
    """Split equal timestamps together. Whole-group splitting has no silent fallback."""
    if config.split == "feature_groups":
        from .groups import fingerprint, group_partition
        groups = fingerprint(raw.X)
        chunks = group_partition(groups, config.ratios, config.split_seed)
        result = dict(zip(PARTS, chunks))
        report = {"mode": config.split, "counts": {p: counts(raw.y[i]) for p,i in result.items()},
                  "boundaries": {}, "note": "Label-blind feature-fingerprint grouping; ratios hold in expectation over groups, not rows or classes; not temporal or session generalisation."}
        report["split_id"] = digest({p: digest(raw.ids[i].tolist()) for p,i in result.items()})
        return result, report
    rng = np.random.default_rng(config.split_seed)
    result = {p: [] for p in PARTS}
    details = {}
    class_sets = [(-1, np.arange(len(raw.y)))] if config.split == "global_time" else [(c, np.flatnonzero(raw.y == c)) for c in np.unique(raw.y)]
    targets = np.cumsum(config.ratios)[:-1]
    for c, idx in class_sets:
        if config.split == "random":
            idx = rng.permutation(idx)
            boundaries = np.floor(targets * len(idx)).astype(int)
        else:
            idx = idx[np.argsort(raw.time[idx], kind="stable")]
            t = raw.time[idx]
            if config.split == "time_groups":
                group = time_groups(t, config.session_gap_minutes)
                allowed = np.flatnonzero(np.diff(group)) + 1
            else:
                allowed = np.flatnonzero(np.diff(t) != np.timedelta64(0, "ns")) + 1
            if len(allowed) < 3:
                raise ValueError(f"Class {c}: fewer than four time blocks/groups. Use within_class_time or a separately declared global_time experiment; no session claim is substituted.")
            chosen = []
            for k, target in enumerate(targets):
                feasible = allowed[(allowed > (chosen[-1] if chosen else 0))]
                feasible = feasible[:len(feasible) - (2-k)] if k < 2 else feasible
                boundary = int(feasible[np.argmin(abs(feasible / len(idx) - target))])
                chosen.append(boundary)
            boundaries = np.array(chosen)
        chunks = np.split(idx, boundaries)
        if any(not len(x) for x in chunks):
            raise ValueError(f"Class {c}: too few rows for four nonempty partitions")
        for p, rows in zip(PARTS, chunks):
            result[p].extend(rows.tolist())
        details[str(c)] = {p: len(rows) for p, rows in zip(PARTS, chunks)}
    result = {p: np.array(rows, dtype=np.int64) for p, rows in result.items()}
    report = {"mode": config.split, "counts": {p: counts(raw.y[idx]) for p, idx in result.items()},
              "boundaries": details, "note": "Within-class temporal order is not global future generalisation. Time groups are inactivity proxies."}
    report["split_id"] = digest({p: digest(raw.ids[idx].tolist()) for p, idx in result.items()})
    return result, report


def training_subset(y, cap, preserve, seed):
    """Keep every member of a rare class; distribute remaining capacity by class size."""
    if len(y) <= cap:
        return np.arange(len(y))
    classes, sizes = np.unique(y, return_counts=True)
    base = np.minimum(sizes, preserve)
    if base.sum() > cap:
        raise ValueError("Training cap cannot preserve requested minority support; increase cap")
    remaining = sizes-base
    allocation = base + np.floor((cap-base.sum()) * remaining / remaining.sum()).astype(int)
    for j in np.argsort(-(remaining - (allocation-base))):
        if allocation.sum() == cap:
            break
        if allocation[j] < sizes[j]:
            allocation[j] += 1
    rng = np.random.default_rng(seed)
    selected = np.concatenate([rng.choice(np.flatnonzero(y == c), n, replace=False) for c, n in zip(classes, allocation)])
    return np.sort(selected)


class Preprocessor:
    def __init__(self, config):
        self.config = config

    def fit(self, X):
        # X is the final real training subset only, never tuning/calibration/test.
        self.input_columns_ = X.columns.tolist()
        cols = [c for c in X if X[c].nunique() > 1 and (self.config.feature_selection == "nonconstant" or X[c].value_counts(normalize=True).iloc[0] <= self.config.dominant_fraction)]
        if not cols:
            raise ValueError("No features survived training-only selection")
        sample = X[cols].sample(min(len(X), 50000), random_state=self.config.split_seed)
        corr = sample.corr().abs().to_numpy()
        keep = []
        for j, c in enumerate(cols):
            if self.config.feature_selection == "nonconstant" or not any(corr[j, k] > self.config.correlation_threshold for k in keep):
                keep.append(j)
        self.columns_ = [cols[k] for k in keep]
        self.log_columns_ = X[self.columns_].skew().abs().loc[lambda s: s > 5].index.tolist()
        prepared = self._values(X)
        self.scaler_ = QuantileTransformer(n_quantiles=min(1000, len(X)), output_distribution="uniform", subsample=200000, random_state=self.config.split_seed) if self.config.scaler == "quantile" else RobustScaler()
        self.scaler_.fit(prepared)
        self.fit_rows_ = len(X)
        return self

    def _values(self, X):
        values = X[self.columns_].to_numpy(dtype=np.float32, copy=True)
        for c in self.log_columns_:
            j = self.columns_.index(c)
            values[:, j] = np.sign(values[:, j]) * np.log1p(abs(values[:, j]))
        return values

    def transform(self, X):
        return self.scaler_.transform(self._values(X)).astype(np.float32)

    def report(self):
        return {"fit_rows": self.fit_rows_, "input_columns": self.input_columns_, "selected_columns": self.columns_, "log_columns": self.log_columns_, "scaler": self.config.scaler, "fit_partition": "train"}
