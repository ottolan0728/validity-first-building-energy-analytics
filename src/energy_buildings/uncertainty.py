"""Distribution-free split-conformal prediction intervals."""

from __future__ import annotations

import math

import numpy as np


def conformal_quantile(residuals: np.ndarray, alpha: float) -> float:
    """Return the finite-sample split-conformal absolute-residual quantile."""
    values = np.asarray(residuals, dtype=float)
    if values.size == 0:
        raise ValueError("residuals must not be empty")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between zero and one")
    rank = min(values.size, math.ceil((values.size + 1) * (1 - alpha)))
    return float(np.partition(values, rank - 1)[rank - 1])


def interval_metrics(actual: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> dict[str, float]:
    """Compute empirical interval coverage and mean width."""
    actual_values = np.asarray(actual, dtype=float)
    lower_values = np.asarray(lower, dtype=float)
    upper_values = np.asarray(upper, dtype=float)
    if not (actual_values.shape == lower_values.shape == upper_values.shape):
        raise ValueError("actual, lower, and upper must have matching shapes")
    covered = (actual_values >= lower_values) & (actual_values <= upper_values)
    return {
        "coverage": float(np.mean(covered)),
        "mean_width": float(np.mean(upper_values - lower_values)),
    }
