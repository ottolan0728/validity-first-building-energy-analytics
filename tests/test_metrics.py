from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_buildings.metrics import regression_metrics


def test_regression_metrics_exact_prediction() -> None:
    result = regression_metrics(np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0]))
    assert result == {"mae": 0.0, "rmse": 0.0, "r2": 1.0}
