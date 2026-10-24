from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_buildings.data import add_features, add_gap_segments


def fixture() -> pd.DataFrame:
    first = pd.date_range("2021-01-01", periods=200, freq="h", tz="UTC")
    second = pd.date_range("2021-01-10", periods=200, freq="h", tz="UTC")
    times = first.append(second)
    return pd.DataFrame(
        {
            "block": "A",
            "timestamp": times,
            "consumption_kwh": range(len(times)),
        }
    )


def test_gap_creates_new_segment() -> None:
    result = add_gap_segments(fixture())
    assert result["segment_id"].nunique() == 2


def test_lag_does_not_cross_gap() -> None:
    result = add_features(fixture(), horizon=1)
    first_row_second_segment = result[result["segment_id"] == 2].iloc[0]
    assert pd.isna(first_row_second_segment["consumption_lag_1h"])


def test_target_does_not_cross_gap() -> None:
    result = add_features(fixture(), horizon=1)
    last_row_first_segment = result[result["segment_id"] == 1].iloc[-1]
    assert pd.isna(last_row_first_segment["target"])


def test_rolling_history_is_strictly_past() -> None:
    result = add_features(fixture(), horizon=1)
    row = result[result["segment_id"] == 1].iloc[24]
    assert row["consumption_roll_mean_24h"] == sum(range(24)) / 24
