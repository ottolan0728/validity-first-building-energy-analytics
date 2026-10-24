"""Regression metrics used by all experiment runners."""

from __future__ import annotations

import numpy as np


def regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    error = actual - predicted
    mae = np.mean(np.abs(error))
    rmse = np.sqrt(np.mean(error**2))
    denominator = np.sum((actual - actual.mean()) ** 2)
    r2 = 1 - np.sum(error**2) / denominator if denominator > 0 else float("nan")
    return {"mae": float(mae), "rmse": float(rmse), "r2": float(r2)}

