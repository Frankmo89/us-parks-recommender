"""How sure are we about a metric that rests on a handful of profiles?

Two tools, both over per-profile scores:

- ``bootstrap_ci``: resample profiles with replacement and take the 2.5th and
  97.5th percentiles of the mean. This is the range the mean could land in
  with a different draw of profiles like these.
- ``paired_test``: compare two methods on the same profiles. The bootstrap
  gives a range for the mean difference; an exact sign-flip test gives a
  p-value for "no real difference". Under that null, each profile's
  difference is as likely to be positive as negative, so we try every sign
  pattern (2^n; n is small) and count how often the mean is at least as far
  from zero as the one we saw.

Both are deterministic (fixed seed) so `python -m src.evaluate` output does
not change from run to run.
"""

from __future__ import annotations

import numpy as np

N_RESAMPLES = 10_000
SEED = 0
ALPHA = 0.05
# Above this, 2^n sign patterns get slow; fall back to random sign flips.
EXACT_MAX_N = 20
TOLERANCE = 1e-12


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _percentile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolated percentile, q in [0, 1]."""
    if not sorted_values:
        return 0.0
    pos = q * (len(sorted_values) - 1)
    low = int(pos)
    high = min(low + 1, len(sorted_values) - 1)
    frac = pos - low
    return sorted_values[low] * (1 - frac) + sorted_values[high] * frac


def bootstrap_means(values: list[float], n_resamples: int = N_RESAMPLES, seed: int = SEED) -> list[float]:
    if not values:
        return []
    rng = np.random.default_rng(seed)
    data = np.asarray(values, dtype=float)
    picks = rng.integers(0, len(data), size=(n_resamples, len(data)))
    return np.sort(data[picks].mean(axis=1)).tolist()


def bootstrap_ci(
    values: list[float], n_resamples: int = N_RESAMPLES, seed: int = SEED, alpha: float = ALPHA
) -> tuple[float, float]:
    means = bootstrap_means(values, n_resamples, seed)
    return _percentile(means, alpha / 2), _percentile(means, 1 - alpha / 2)


def sign_flip_p_value(diffs: list[float], n_random: int = N_RESAMPLES, seed: int = SEED) -> float:
    """Two-sided p-value for mean(diffs) == 0 under random sign flips."""
    active = [d for d in diffs if abs(d) > TOLERANCE]
    if not active:
        return 1.0
    data = np.asarray(active, dtype=float)
    observed = abs(data.sum())
    n = len(data)
    if n <= EXACT_MAX_N:
        # Row i's bits give the sign pattern: bit set -> flip that profile.
        bits = (np.arange(2**n, dtype=np.uint32)[:, None] >> np.arange(n, dtype=np.uint32)) & 1
        sums = (1 - 2 * bits.astype(np.int8)) @ data
        return float(np.mean(np.abs(sums) >= observed - TOLERANCE))
    rng = np.random.default_rng(seed)
    signs = rng.choice((-1.0, 1.0), size=(n_random, n))
    extreme = int(np.sum(np.abs(signs @ data) >= observed - TOLERANCE))
    return (extreme + 1) / (n_random + 1)


def paired_test(a: list[float], b: list[float]) -> dict:
    """Compare method A with method B on the same profiles (A - B)."""
    if len(a) != len(b):
        raise ValueError("paired_test needs one score per profile for both methods")
    diffs = [x - y for x, y in zip(a, b)]
    low, high = bootstrap_ci(diffs)
    return {
        "n": len(diffs),
        "mean_diff": _mean(diffs),
        "ci_low": low,
        "ci_high": high,
        "p_value": sign_flip_p_value(diffs),
        "wins": sum(d > TOLERANCE for d in diffs),
        "ties": sum(abs(d) <= TOLERANCE for d in diffs),
        "losses": sum(d < -TOLERANCE for d in diffs),
    }


def metric_summary(values: list[float]) -> dict:
    low, high = bootstrap_ci(values)
    return {"n": len(values), "mean": _mean(values), "ci_low": low, "ci_high": high}
