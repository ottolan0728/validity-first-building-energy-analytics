"""Run gap-safe seasonal-naive and Ridge baselines on rolling monthly folds."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_buildings.folds import monthly_rolling_folds  # noqa: E402
from energy_buildings.metrics import regression_metrics  # noqa: E402


FEATURES = [
    "consumption_lag_1h",
    "consumption_lag_2h",
    "consumption_lag_3h",
    "consumption_lag_6h",
    "consumption_lag_24h",
    "consumption_lag_168h",
    "consumption_roll_mean_24h",
    "consumption_roll_std_24h",
    "indoor_temperature_c",
    "hvac_on_count",
    "mean_setpoint_c",
    "mode_off",
    "mode_heating",
    "mode_cooling",
    "outdoor_temperature_c",
    "outdoor_humidity_pct",
    "solar_radiation",
    "wind_speed",
    "precipitation",
    "sin_hour",
    "cos_hour",
    "sin_day_of_week",
    "cos_day_of_week",
    "is_weekend",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
    except ImportError as error:
        raise SystemExit("scikit-learn is required; install requirements.txt") from error

    frame = pd.read_csv(args.dataset, parse_dates=["timestamp", "target_timestamp"])
    folds = monthly_rolling_folds(frame["target_timestamp"])
    results: list[dict[str, object]] = []

    numeric = FEATURES
    categorical = ["block"]
    transformer = ColumnTransformer(
        [
            ("numeric", Pipeline([("impute", SimpleImputer()), ("scale", StandardScaler())]), numeric),
            ("block", OneHotEncoder(handle_unknown="ignore"), categorical),
        ]
    )

    for fold in folds:
        train_end = pd.Timestamp(fold.train_end)
        test_start = pd.Timestamp(fold.test_start)
        test_end = pd.Timestamp(fold.test_end)
        target_time = frame["target_timestamp"]
        train = frame[target_time.lt(train_end)]
        test = frame[target_time.ge(test_start) & target_time.lt(test_end)]

        for name, column in [("seasonal_naive_24h", "consumption_lag_24h"), ("seasonal_naive_168h", "consumption_lag_168h")]:
            metrics = regression_metrics(test["target"].to_numpy(), test[column].to_numpy())
            results.append({"fold": fold.name, "model": name, "n_train": len(train), "n_test": len(test), **metrics})

        model = Pipeline([("transform", transformer), ("model", Ridge(alpha=1.0))])
        model.fit(train[numeric + categorical], train["target"])
        prediction = model.predict(test[numeric + categorical])
        metrics = regression_metrics(test["target"].to_numpy(), prediction)
        results.append({"fold": fold.name, "model": "ridge", "n_train": len(train), "n_test": len(test), **metrics})

    result_frame = pd.DataFrame(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result_frame.to_csv(args.output, index=False)
    summary = result_frame.groupby("model")[["mae", "rmse", "r2"]].agg(["mean", "std"])
    summary.columns = [f"{metric}_{statistic}" for metric, statistic in summary.columns]
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summary.reset_index().to_dict(orient="records"), indent=2) + "\n",
        encoding="utf-8",
    )
    print(result_frame.to_string(index=False))
    print("\nMean by model\n", result_frame.groupby("model")[["mae", "rmse", "r2"]].mean())


if __name__ == "__main__":
    main()
