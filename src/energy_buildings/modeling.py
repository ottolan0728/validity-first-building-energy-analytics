"""Shared model feature groups and fold-local preprocessing."""

from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


HISTORY_24 = [
    "consumption_lag_1h",
    "consumption_lag_2h",
    "consumption_lag_3h",
    "consumption_lag_6h",
    "consumption_lag_24h",
    "consumption_roll_mean_24h",
    "consumption_roll_std_24h",
]
CALENDAR = [
    "sin_hour",
    "cos_hour",
    "sin_day_of_week",
    "cos_day_of_week",
    "is_weekend",
]
WEATHER = [
    "outdoor_temperature_c",
    "outdoor_humidity_pct",
    "solar_radiation",
    "wind_speed",
    "precipitation",
]
INDOOR = ["indoor_temperature_c"]
HVAC = ["hvac_on_count", "mode_off", "mode_heating", "mode_cooling"]
SETPOINT = ["mean_setpoint_c"]

FEATURE_GROUPS = {
    "history_calendar": HISTORY_24 + CALENDAR,
    "plus_weather": HISTORY_24 + CALENDAR + WEATHER,
    "plus_indoor": HISTORY_24 + CALENDAR + WEATHER + INDOOR,
    "plus_hvac": HISTORY_24 + CALENDAR + WEATHER + INDOOR + HVAC,
    "plus_setpoint": HISTORY_24 + CALENDAR + WEATHER + INDOOR + HVAC + SETPOINT,
}


def make_transformer(numeric: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        [
            (
                "numeric",
                Pipeline([("impute", SimpleImputer()), ("scale", StandardScaler())]),
                numeric,
            ),
            ("block", OneHotEncoder(handle_unknown="ignore"), ["block"]),
        ]
    )
