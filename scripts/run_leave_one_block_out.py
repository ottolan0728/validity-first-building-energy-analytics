"""Rolling leave-one-block-out evaluation for spatial transferability."""

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    frame = pd.read_csv(args.dataset, parse_dates=["timestamp", "target_timestamp"])
    development = frame[frame["target_timestamp"].lt(pd.Timestamp("2021-12-01", tz="UTC"))]
    folds = monthly_rolling_folds(development["target_timestamp"])
    features = FEATURE_GROUPS["plus_setpoint"]
    columns = features + ["block"]
    rows = []

    for held_block in sorted(development["block"].unique()):
        for fold in folds:
            train_end = pd.Timestamp(fold.train_end)
            test_start = pd.Timestamp(fold.test_start)
            test_end = pd.Timestamp(fold.test_end)
            train = development[
                development["block"].ne(held_block)
                & development["target_timestamp"].lt(train_end)
            ]
            test = development[
                development["block"].eq(held_block)
                & development["target_timestamp"].ge(test_start)
                & development["target_timestamp"].lt(test_end)
            ]
            if train.empty or test.empty:
                continue

            specs = [
                ("ridge_full", Ridge(alpha=1.0)),
                (
                    "random_forest_full",
                    RandomForestRegressor(
                        n_estimators=80,
                        max_depth=14,
                        min_samples_leaf=3,
                        n_jobs=1,
                        random_state=42,
                    ),
                ),
                (
                    "hist_gradient_boosting_full",
                    HistGradientBoostingRegressor(
                        learning_rate=0.05,
                        max_iter=150,
                        max_leaf_nodes=31,
                        l2_regularization=1.0,
                        random_state=42,
                    ),
                ),
            ]
            naive_metrics = regression_metrics(
                test["target"].to_numpy(), test["consumption_lag_24h"].to_numpy()
            )
            rows.append(
                {
                    "held_block": held_block,
                    "fold": fold.name,
                    "model": "seasonal_naive_24h",
                    "n_train": len(train),
                    "n_test": len(test),
                    **naive_metrics,
                }
            )
            for name, estimator in specs:
                model = Pipeline(
                    [("transform", make_transformer(features)), ("model", estimator)]
                )
                model.fit(train[columns], train["target"])
                prediction = model.predict(test[columns])
                rows.append(
                    {
                        "held_block": held_block,
                        "fold": fold.name,
                        "model": name,
                        "n_train": len(train),
                        "n_test": len(test),
                        **regression_metrics(test["target"].to_numpy(), prediction),
                    }
                )

    results = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output, index=False)
    print("Mean MAE by held block")
    print(results.pivot_table(index="model", columns="held_block", values="mae").to_string())
    print("\nOverall mean")
    print(results.groupby("model")[["mae", "rmse", "r2"]].mean().sort_values("mae"))


if __name__ == "__main__":
    main()
