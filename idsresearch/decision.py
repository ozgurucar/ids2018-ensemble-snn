"""Training-prior correction, disjoint probability calibration and alarm rules.

Everything is fitted on training counts or on named calibration rows. None of
it corrects label noise, and the FPR control is not guaranteed under
distribution shift.
"""
import numpy as np
from scipy.special import logsumexp
from scipy.optimize import minimize_scalar
from scipy.stats import binom


def prior_offset(full_counts, sampled_counts, class_weights, enabled=True):
    full = np.asarray(full_counts, dtype=float)
    sampled = np.asarray(sampled_counts, dtype=float)
    weight = np.asarray(class_weights, dtype=float)
    if full.shape != sampled.shape or full.shape != weight.shape:
        raise ValueError("Prior vectors must have the same shape")
    if np.any(full < 0) or np.any(sampled < 0) or not full.sum() or not sampled.sum():
        raise ValueError("Invalid training counts")
    seen = sampled > 0
    if np.any((full > 0) & ~seen) or np.any(weight[seen] <= 0):
        raise ValueError("A represented training class cannot be discarded or have zero weight")
    # An absent training class has no fitted posterior. It is never predicted.
    result = np.full(len(full), -1e9, dtype=float)
    result[seen] = 0.
    if enabled:
        result[seen] = (np.log(full[seen]/full.sum())
                        - np.log(sampled[seen]/sampled.sum()) - np.log(weight[seen]))
    return result


def log_probabilities(logits):
    z = np.asarray(logits, dtype=np.float64)
    if z.ndim != 2 or not np.isfinite(z).all():
        raise ValueError("Finite two-dimensional logits required")
    return z - logsumexp(z, axis=1, keepdims=True)


def alarm_score(logits):
    """Log odds retains distinctions lost by float32 (1 - P(benign))."""
    z = np.asarray(logits, dtype=np.float64)
    return logsumexp(z[:, 1:], axis=1) - z[:, 0]


def temperature_fit(logits, y):
    z, y = np.asarray(logits, dtype=np.float64), np.asarray(y, dtype=int)
    if len(z) != len(y) or not len(y):
        raise ValueError("Nonempty aligned probability-calibration data required")
    def nll(log_t):
        lp = log_probabilities(z/np.exp(log_t))
        return float(-lp[np.arange(len(y)), y].mean())
    fit = minimize_scalar(nll, bounds=(np.log(.05), np.log(20.)), method="bounded")
    if not fit.success or not np.isfinite(fit.fun):
        raise ValueError("Temperature fit failed")
    return {"temperature": float(np.exp(fit.x)), "nll_before": nll(0.),
            "nll_after": float(fit.fun), "n": len(y),
            "fit_partition": "probability_calibration", "bounds": [.05, 20.]}


def threshold_fit(scores, tau, min_benign=1, method="empirical", delta=.05):
    s = np.sort(np.asarray(scores, dtype=float))
    n = len(s)
    if n < min_benign or not np.isfinite(s).all() or not 0 < tau < 1:
        raise ValueError("Insufficient benign support or invalid scores/budget")
    if method == "empirical":
        k = n-int(np.floor(tau*n))  # one-based order statistic
    elif method == "np_reference":
        if not 0 < delta < 1:
            raise ValueError("delta must be in (0,1)")
        # P{Binomial(n,1-tau) >= k} is the conditional violation bound.
        if binom.sf(n-1, n, 1-tau) > delta:
            raise ValueError("Insufficient independent benign calibration units for NP reference")
        lo, hi = 1, n
        while lo < hi:
            mid = (lo+hi)//2
            if binom.sf(mid-1, n, 1-tau) <= delta:
                hi = mid
            else:
                lo = mid+1
        k = lo
    else:
        raise ValueError("Unknown threshold method")
    t = float(s[k-1])
    return {"threshold": t, "tau": tau, "benign_support": n, "method": method,
            "order_statistic": k, "empirical_calibration_fpr": float((s > t).mean()),
            "iid_violation_bound_reference": float(binom.sf(k-1, n, 1-tau)),
            "delta": delta if method == "np_reference" else None,
            "fit_partition": "alarm_calibration", "decision": "log_odds > threshold",
            "guarantee": "No unconditional guarantee: IID independent calibration units from the deployment benign distribution are required for the NP bound. Fingerprint groups and temporal data do not establish these assumptions."}


def predict_logits(logits, threshold):
    return np.where(alarm_score(logits) > threshold, np.asarray(logits)[:, 1:].argmax(1)+1, 0)
