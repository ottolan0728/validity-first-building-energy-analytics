"""PLEIAData preprocessing with explicit gap and leakage controls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


BLOCKS = ("A", "B", "C")
TARGET = "consumption_kwh"
ONE_HOUR = pd.Timedelta(hours=1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_semicolon(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";")


def _parse_timestamp(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result.pop("Date"), utc=True, errors="raise")
    if result["timestamp"].duplicated().any():
        raise ValueError("Duplicate timestamps detected")
    return result.sort_values("timestamp").reset_index(drop=True)


def load_block_hourly(data_dir: Path, block: str) -> pd.DataFrame:
    """Join author-provided component tables without using the merged/smoothed table."""
    if block not in BLOCKS:
        raise ValueError(f"Unknown block: {block}")

    consumption = _parse_timestamp(_read_semicolon(data_dir / f"cons{block}-60T.csv"))
    consumption = consumption.rename(columns={"dif_cons_real": TARGET})
    consumption = consumption[["timestamp", TARGET, "cons_total"]]

    temperature = _parse_timestamp(_read_semicolon(data_dir / f"temp-sensor{block}-60T.csv"))
    temperature = temperature.rename(columns={"V2": "indoor_temperature_c"})

    hvac = _parse_timestamp(_read_semicolon(data_dir / f"hvac-agg{block}-60T.csv"))
    hvac = hvac.rename(
        columns={
            "V4": "hvac_on_count",
            "V12": "mean_setpoint_c",
            "V26": "mean_active_device_type",
            "V5_0": "mode_off",
            "V5_1": "mode_heating",
            "V5_2": "mode_cooling",
        }
    )
    hvac = hvac[
        [
            "timestamp",
            "hvac_on_count",
            "mean_setpoint_c",
            "mean_active_device_type",
            "mode_off",
            "mode_heating",
            "mode_cooling",
        ]
    ]

    weather = _parse_timestamp(_read_semicolon(data_dir / "data-weather-60T.csv"))
    weather = weather.rename(
        columns={
            "tmed": "outdoor_temperature_c",
            "hrmed": "outdoor_humidity_pct",
            "radmed": "solar_radiation",
            "vvmed": "wind_speed",
            "dvmed": "wind_direction",
            "prec": "precipitation",
            "dewpt": "dew_point_c",
            "dpv": "vapor_pressure_deficit",
        }
    )

    result = consumption.merge(temperature, on="timestamp", how="inner", validate="one_to_one")
    result = result.merge(hvac, on="timestamp", how="inner", validate="one_to_one")
    result = result.merge(weather, on="timestamp", how="inner", validate="one_to_one")
    result.insert(0, "block", block)
    return result.sort_values("timestamp").reset_index(drop=True)


def add_gap_segments(frame: pd.DataFrame) -> pd.DataFrame:
    """Assign a new segment whenever consecutive observations are not one hour apart."""
    result = frame.sort_values(["block", "timestamp"]).copy()
    delta = result.groupby("block")["timestamp"].diff()
    boundary = delta.isna() | delta.ne(ONE_HOUR)
    result["segment_id"] = boundary.groupby(result["block"]).cumsum().astype(int)
    return result.reset_index(drop=True)


def add_features(frame: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
    """Create causal, gap-safe features and a future target within each segment."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    result = add_gap_segments(frame)
    group = result.groupby(["block", "segment_id"], sort=False)

    for lag in (1, 2, 3, 6, 24, 168):
        result[f"consumption_lag_{lag}h"] = group[TARGET].shift(lag)
    result["consumption_roll_mean_24h"] = group[TARGET].transform(
        lambda values: values.shift(1).rolling(24, min_periods=24).mean()
    )
    result["consumption_roll_std_24h"] = group[TARGET].transform(
        lambda values: values.shift(1).rolling(24, min_periods=24).std()
    )
    result["target"] = group[TARGET].shift(-horizon)
    result["target_timestamp"] = group["timestamp"].shift(-horizon)

    hour = result["timestamp"].dt.hour
    day_of_week = result["timestamp"].dt.dayofweek
    result["sin_hour"] = np.sin(2 * np.pi * hour / 24)
    result["cos_hour"] = np.cos(2 * np.pi * hour / 24)
    result["sin_day_of_week"] = np.sin(2 * np.pi * day_of_week / 7)
    result["cos_day_of_week"] = np.cos(2 * np.pi * day_of_week / 7)
    result["is_weekend"] = day_of_week.ge(5).astype(int)
    result["month"] = result["timestamp"].dt.month
    result["horizon_hours"] = horizon
    return result


def prepare_dataset(data_dir: Path, horizon: int = 1, history: int = 168) -> pd.DataFrame:
    if history not in {24, 168}:
        raise ValueError("history must be 24 or 168 hours")
    combined = pd.concat(
        [load_block_hourly(data_dir, block) for block in BLOCKS], ignore_index=True
    )
    featured = add_features(combined, horizon=horizon)
    required_lag = f"consumption_lag_{history}h"
    required = [required_lag, "consumption_roll_std_24h", "target"]
    result = featured.dropna(subset=required).reset_index(drop=True)
    result["history_requirement_hours"] = history
    return result


def write_dataset(frame: pd.DataFrame, output: Path, source_dir: Path) -> dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "dataset": str(output.resolve()),
        "sha256": sha256(output),
        "rows": len(frame),
        "columns": list(frame.columns),
        "blocks": frame.groupby("block").size().to_dict(),
        "time_start": frame["timestamp"].min().isoformat(),
        "time_end": frame["timestamp"].max().isoformat(),
        "source_dir": str(source_dir.resolve()),
        "horizon_hours": int(frame["horizon_hours"].iloc[0]),
        "history_requirement_hours": int(frame["history_requirement_hours"].iloc[0]),
    }
    manifest_path = output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
