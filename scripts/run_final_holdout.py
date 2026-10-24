"""One-shot December 2021 final-holdout evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_buildings.metrics import regression_metrics  # noqa: E402
from energy_buildings.modeling import FEATURE_GROUPS, make_transformer  # noqa: E402
from energy_buildings.uncertainty import conformal_quantile, interval_metrics  # noqa: E402


FINAL_START = pd.Timestamp("2021-12-01", tz="UTC")
FINAL_END = pd.Timestamp("2022-01-01", tz="UTC")
THERMAL_FEATURES = [
    "indoor_temperature_c", "outdoor_temperature_c", "outdoor_humidity_pct",
    "solar_radiation", "wind_speed", "precipitation", "hvac_on_count",
    "mode_off", "mode_heating", "mode_cooling", "mean_setpoint_c",
    "consumption_kwh", "sin_hour", "cos_hour", "sin_day_of_week",
    "cos_day_of_week", "is_weekend",
]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metric_rows(predictions: pd.DataFrame, actual: str = "actual") -> pd.DataFrame:
    rows = []
    for model, group in predictions.groupby("model"):
        scopes = [("all", group)] + [(f"block_{b}", g) for b, g in group.groupby("block")]
        for scope, scoped in scopes:
            rows.append({"model": model, "scope": scope, "n": len(scoped),
                **regression_metrics(scoped[actual].to_numpy(), scoped["prediction"].to_numpy())})
    return pd.DataFrame(rows)


def clustered_bootstrap_improvement(predictions: pd.DataFrame, repetitions: int = 5000) -> dict[str, float]:
    wide = predictions.pivot(index=["block", "target_timestamp"], columns="model", values=["actual", "prediction"])
    actual = wide[("actual", "random_forest_full")]
    comparison = pd.DataFrame({
        "block": wide.index.get_level_values("block"),
        "day": wide.index.get_level_values("target_timestamp").floor("D"),
        "rf_error": np.abs(actual - wide[("prediction", "random_forest_full")]),
        "naive_error": np.abs(actual - wide[("prediction", "seasonal_naive_24h")]),
    }).reset_index(drop=True)
    clusters = [group for _, group in comparison.groupby(["block", "day"])]
    rng = np.random.default_rng(42)
    estimates = np.empty(repetitions)
    for index in range(repetitions):
        sampled = rng.integers(0, len(clusters), size=len(clusters))
        draw = pd.concat([clusters[item] for item in sampled], ignore_index=True)
        estimates[index] = (draw["naive_error"] - draw["rf_error"]).mean()
    observed = float((comparison["naive_error"] - comparison["rf_error"]).mean())
    return {"mae_improvement_kwh": observed, "ci_low": float(np.quantile(estimates, 0.025)),
        "ci_high": float(np.quantile(estimates, 0.975)), "clusters": len(clusters),
        "bootstrap_repetitions": repetitions}


def thermal_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.sort_values(["block", "segment_id", "timestamp"]).copy()
    grouped = result.groupby(["block", "segment_id"])
    result["thermal_target"] = grouped["indoor_temperature_c"].shift(-1)
    result["thermal_target_timestamp"] = grouped["timestamp"].shift(-1)
    valid = result["thermal_target_timestamp"].sub(result["timestamp"]).eq(pd.Timedelta(hours=1))
    return result[valid & result["thermal_target"].notna()].copy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    marker = args.output_dir / "HOLDOUT_OPENED.json"
    if marker.exists():
        raise SystemExit(f"Refusing to re-open final holdout; marker exists: {marker}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    opening = {"opened_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(args.dataset.resolve()), "dataset_sha256": file_sha256(args.dataset),
        "holdout_start": FINAL_START.isoformat(), "holdout_end": FINAL_END.isoformat(),
        "status": "started", "one_shot": True}
    marker.write_text(json.dumps(opening, indent=2) + "\n", encoding="utf-8")

    frame = pd.read_csv(args.dataset, parse_dates=["timestamp", "target_timestamp"])
    train = frame[frame["target_timestamp"].lt(FINAL_START)]
    test = frame[frame["target_timestamp"].ge(FINAL_START) & frame["target_timestamp"].lt(FINAL_END)]
    features = FEATURE_GROUPS["plus_setpoint"]
    columns = features + ["block"]
    predictions = []
    base = test[["block", "timestamp", "target_timestamp", "target"]].rename(columns={"target": "actual"})
    base["model"] = "seasonal_naive_24h"
    base["prediction"] = test["consumption_lag_24h"].to_numpy()
    predictions.append(base)
    specs = [
        ("ridge_full", Ridge(alpha=1.0)),
        ("random_forest_full", RandomForestRegressor(n_estimators=300, max_depth=18,
            min_samples_leaf=3, n_jobs=-1, random_state=42)),
        ("hist_gradient_boosting_full", HistGradientBoostingRegressor(learning_rate=0.05,
            max_iter=300, max_leaf_nodes=31, l2_regularization=1.0, random_state=42)),
    ]
    fitted = {}
    for name, estimator in specs:
        model = Pipeline([("transform", make_transformer(features)), ("model", estimator)])
        model.fit(train[columns], train["target"])
        result = test[["block", "timestamp", "target_timestamp", "target"]].rename(columns={"target": "actual"})
        result["model"], result["prediction"] = name, model.predict(test[columns])
        predictions.append(result)
        fitted[name] = model
    point_predictions = pd.concat(predictions, ignore_index=True)
    point_metrics = metric_rows(point_predictions)

    calibration_start = FINAL_START - pd.Timedelta(days=30)
    proper_train = frame[frame["target_timestamp"].lt(calibration_start)]
    calibration = frame[frame["target_timestamp"].ge(calibration_start) & frame["target_timestamp"].lt(FINAL_START)]
    interval_model = Pipeline([("transform", make_transformer(features)),
        ("model", RandomForestRegressor(n_estimators=300, max_depth=18, min_samples_leaf=3,
            n_jobs=-1, random_state=42))])
    interval_model.fit(proper_train[columns], proper_train["target"])
    calibration_residual = np.abs(calibration["target"] - interval_model.predict(calibration[columns]))
    interval_prediction = interval_model.predict(test[columns])
    interval_rows = []
    for nominal, alpha in ((80, 0.20), (90, 0.10)):
        radius = conformal_quantile(calibration_residual.to_numpy(), alpha)
        for scope, scoped in [("all", test)] + [(f"block_{b}", g) for b, g in test.groupby("block")]:
            indices = scoped.index
            positions = test.index.get_indexer(indices)
            values = interval_prediction[positions]
            interval_rows.append({"scope": scope, "nominal_coverage": nominal / 100,
                "n": len(scoped), "radius": radius,
                **interval_metrics(scoped["target"].to_numpy(), values - radius, values + radius)})

    thermal = thermal_frame(frame)
    thermal_train = thermal[thermal["thermal_target_timestamp"].lt(FINAL_START)]
    thermal_test = thermal[thermal["thermal_target_timestamp"].ge(FINAL_START) & thermal["thermal_target_timestamp"].lt(FINAL_END)]
    thermal_predictions = []
    persistence = thermal_test[["block", "timestamp", "thermal_target_timestamp", "thermal_target"]].copy()
    persistence["model"], persistence["prediction"] = "persistence", thermal_test["indoor_temperature_c"].to_numpy()
    thermal_predictions.append(persistence.rename(columns={"thermal_target": "actual"}))
    for name, estimator in [("ridge", Ridge(alpha=1.0)), ("hist_gradient_boosting",
        HistGradientBoostingRegressor(learning_rate=0.05, max_iter=200, max_leaf_nodes=31,
            l2_regularization=1.0, random_state=42))]:
        model = Pipeline([("transform", make_transformer(THERMAL_FEATURES)), ("model", estimator)])
        model.fit(thermal_train[THERMAL_FEATURES + ["block"]], thermal_train["thermal_target"])
        result = thermal_test[["block", "timestamp", "thermal_target_timestamp", "thermal_target"]].copy()
        result["model"] = name
        result["prediction"] = model.predict(thermal_test[THERMAL_FEATURES + ["block"]])
        thermal_predictions.append(result.rename(columns={"thermal_target": "actual"}))
    thermal_prediction_frame = pd.concat(thermal_predictions, ignore_index=True)
    thermal_metrics = metric_rows(thermal_prediction_frame)

    point_predictions.to_csv(args.output_dir / "point_predictions.csv", index=False)
    point_metrics.to_csv(args.output_dir / "point_metrics.csv", index=False)
    pd.DataFrame(interval_rows).to_csv(args.output_dir / "interval_metrics.csv", index=False)
    thermal_prediction_frame.to_csv(args.output_dir / "thermal_predictions.csv", index=False)
    thermal_metrics.to_csv(args.output_dir / "thermal_metrics.csv", index=False)
    bootstrap = clustered_bootstrap_improvement(point_predictions)
    summary = {"point_overall": point_metrics[point_metrics["scope"].eq("all")].set_index("model")[["mae", "rmse", "r2"]].to_dict("index"),
        "intervals": pd.DataFrame(interval_rows).to_dict("records"),
        "thermal_overall": thermal_metrics[thermal_metrics["scope"].eq("all")].set_index("model")[["mae", "rmse", "r2"]].to_dict("index"),
        "rf_vs_naive_cluster_bootstrap": bootstrap, "decision_module_status": "downgraded",
        "offline_savings_estimated": False, "final_holdout_rows": len(test)}
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    opening["status"] = "completed"
    opening["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    marker.write_text(json.dumps(opening, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
