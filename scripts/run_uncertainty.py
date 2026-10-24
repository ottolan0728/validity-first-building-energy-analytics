"""Milestone 3: chronological split-conformal prediction intervals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_buildings.folds import monthly_rolling_folds  # noqa: E402
from energy_buildings.modeling import FEATURE_GROUPS, make_transformer  # noqa: E402
from energy_buildings.uncertainty import conformal_quantile, interval_metrics  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--calibration-days", type=int, default=30)
    args = parser.parse_args()

    frame = pd.read_csv(args.dataset, parse_dates=["timestamp", "target_timestamp"])
    development = frame[frame["target_timestamp"].lt(pd.Timestamp("2021-12-01", tz="UTC"))]
    folds = monthly_rolling_folds(development["target_timestamp"])
    features = FEATURE_GROUPS["plus_setpoint"]
    columns = features + ["block"]
    prediction_rows: list[pd.DataFrame] = []
    calibration_rows = []

    for fold in folds:
        train_end = pd.Timestamp(fold.train_end)
        calibration_start = train_end - pd.Timedelta(days=args.calibration_days)
        proper_train = development[development["target_timestamp"].lt(calibration_start)]
        calibration = development[
            development["target_timestamp"].ge(calibration_start)
            & development["target_timestamp"].lt(train_end)
        ]
        test = development[
            development["target_timestamp"].ge(pd.Timestamp(fold.test_start))
            & development["target_timestamp"].lt(pd.Timestamp(fold.test_end))
        ]
        if proper_train.empty or calibration.empty or test.empty:
            continue

        model = Pipeline(
            [
                ("transform", make_transformer(features)),
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
        )
        model.fit(proper_train[columns], proper_train["target"])
        calibration_prediction = model.predict(calibration[columns])
        residuals = np.abs(calibration["target"].to_numpy() - calibration_prediction)
        test_prediction = model.predict(test[columns])
        result = test[["block", "timestamp", "target_timestamp", "target"]].copy()
        result = result.rename(columns={"target": "actual"})
        result["fold"] = fold.name
        result["prediction"] = test_prediction
        for nominal, alpha in ((80, 0.20), (90, 0.10)):
            radius = conformal_quantile(residuals, alpha)
            result[f"lower_{nominal}"] = test_prediction - radius
            result[f"upper_{nominal}"] = test_prediction + radius
            calibration_rows.append(
                {
                    "fold": fold.name,
                    "nominal_coverage": nominal / 100,
                    "n_proper_train": len(proper_train),
                    "n_calibration": len(calibration),
                    "radius": radius,
                }
            )
        prediction_rows.append(result)

    predictions = pd.concat(prediction_rows, ignore_index=True)
    metrics = []
    for fold, fold_group in predictions.groupby("fold"):
        scopes = [("all", fold_group)] + [
            (f"block_{block}", group) for block, group in fold_group.groupby("block")
        ]
        for scope, group in scopes:
            for nominal in (80, 90):
                metrics.append(
                    {
                        "fold": fold,
                        "scope": scope,
                        "nominal_coverage": nominal / 100,
                        "n": len(group),
                        **interval_metrics(
                            group["actual"].to_numpy(),
                            group[f"lower_{nominal}"].to_numpy(),
                            group[f"upper_{nominal}"].to_numpy(),
                        ),
                    }
                )

    metrics_frame = pd.DataFrame(metrics)
    calibration_frame = pd.DataFrame(calibration_rows)
    summary = (
        metrics_frame.groupby(["scope", "nominal_coverage"])[["coverage", "mean_width"]]
        .mean()
        .reset_index()
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(args.output_dir / "predictions_with_intervals.csv", index=False)
    calibration_frame.to_csv(args.output_dir / "calibration.csv", index=False)
    metrics_frame.to_csv(args.output_dir / "interval_metrics.csv", index=False)
    summary.to_csv(args.output_dir / "summary.csv", index=False)
    manifest = {
        "final_holdout_opened": False,
        "development_cutoff": "2021-12-01T00:00:00+00:00",
        "calibration_days": args.calibration_days,
        "interval_method": "symmetric split conformal with finite-sample correction",
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
