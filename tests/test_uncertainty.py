from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_buildings.uncertainty import conformal_quantile, interval_metrics


def test_conformal_quantile_uses_finite_sample_correction() -> None:
    residuals = np.arange(1.0, 11.0)
    assert conformal_quantile(residuals, alpha=0.2) == 9.0


def test_interval_metrics() -> None:
    result = interval_metrics(
        np.array([1.0, 2.0]), np.array([0.0, 2.5]), np.array([2.0, 3.0])
    )
    assert result == {"coverage": 0.5, "mean_width": 1.25}
