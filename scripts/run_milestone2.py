"""Milestone 2: ablations, tree baselines, predictions, and per-block metrics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_buildings.folds import monthly_rolling_folds  # noqa: E402
from energy_buildings.metrics import regression_metrics  # noqa: E402
from energy_buildings.modeling import FEATURE_GROUPS, make_transformer  # noqa: E402


def evaluate_predictions(frame: pd.DataFrame) -> dict[str, float]:
    return regression_metrics(frame["actual"].to_numpy(), frame["prediction"].to_numpy())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    frame = pd.read_csv(args.dataset, parse_dates=["timestamp", "target_timestamp"])
    # December is frozen as the untouched final holdout.
    development = frame[frame["target_timestamp"].lt(pd.Timestamp("2021-12-01", tz="UTC"))]
    folds = monthly_rolling_folds(development["target_timestamp"])
    predictions: list[pd.DataFrame] = []

    model_specs = []
    for group_name, features in FEATURE_GROUPS.items():
        model_specs.append(
            (
                f"ridge_{group_name}",
                features,
                Pipeline([("transform", make_transformer(features)), ("model", Ridge(alpha=1.0))]),
            )
        )
    full_features = FEATURE_GROUPS["plus_setpoint"]
    model_specs.extend(
        [
            (
                "random_forest_full",
                full_features,
                Pipeline(
                    [
                        ("transform", make_transformer(full_features)),
                        (
                            "model",
                            RandomForestRegressor(
                                n_estimators=300,
                                max_depth=18,
                                min_samples_leaf=3,
                                n_jobs=-1,
                                random_state=42,
                            ),
                        ),
                    ]
                ),
            ),
            (
                "hist_gradient_boosting_full",
                full_features,
                Pipeline(
                    [
                        ("transform", make_transformer(full_features)),
                        (
                            "model",
                            HistGradientBoostingRegressor(
                                learning_rate=0.05,
                                max_iter=300,
                                max_leaf_nodes=31,
                                l2_regularization=1.0,
                                random_state=42,
                            ),
                        ),
                    ]
                ),
            ),
        ]
    )

    for fold in folds:
        train_end = pd.Timestamp(fold.train_end)
        test_start = pd.Timestamp(fold.test_start)
        test_end = pd.Timestamp(fold.test_end)
        target_time = development["target_timestamp"]
        train = development[target_time.lt(train_end)]
        test = development[target_time.ge(test_start) & target_time.lt(test_end)]

        naive = test[["block", "timestamp", "target_timestamp", "target"]].copy()
        naive["model"] = "seasonal_naive_24h"
        naive["fold"] = fold.name
        naive["prediction"] = test["consumption_lag_24h"].to_numpy()
        predictions.append(naive.rename(columns={"target": "actual"}))

        for name, features, model in model_specs:
            columns = features + ["block"]
            model.fit(train[columns], train["target"])
            result = test[["block", "timestamp", "target_timestamp", "target"]].copy()
            result["model"] = name
            result["fold"] = fold.name
            result["prediction"] = model.predict(test[columns])
            predictions.append(result.rename(columns={"target": "actual"}))

    prediction_frame = pd.concat(predictions, ignore_index=True)
    metrics = []
    for (fold, model), group in prediction_frame.groupby(["fold", "model"]):
        metrics.append({"fold": fold, "model": model, "scope": "all", **evaluate_predictions(group)})
        for block, block_group in group.groupby("block"):
            metrics.append(
                {"fold": fold, "model": model, "scope": f"block_{block}", **evaluate_predictions(block_group)}
            )
    metrics_frame = pd.DataFrame(metrics)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    prediction_frame.to_csv(args.output_dir / "predictions.csv", index=False)
    metrics_frame.to_csv(args.output_dir / "metrics.csv", index=False)
    summary = (
        metrics_frame[metrics_frame["scope"].eq("all")]
        .groupby("model")[["mae", "rmse", "r2"]]
        .mean()
        .sort_values("mae")
    )
    summary.to_csv(args.output_dir / "summary.csv")
    print(summary.to_string())


if __name__ == "__main__":
    main()
