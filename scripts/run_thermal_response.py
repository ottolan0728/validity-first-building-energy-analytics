"""Milestone 3: one-hour thermal response and setpoint common-support gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_buildings.folds import monthly_rolling_folds  # noqa: E402
from energy_buildings.metrics import regression_metrics  # noqa: E402
from energy_buildings.modeling import make_transformer  # noqa: E402
from energy_buildings.data import BLOCKS, add_gap_segments, load_block_hourly  # noqa: E402


THERMAL_FEATURES = [
    "indoor_temperature_c", "outdoor_temperature_c", "outdoor_humidity_pct",
    "solar_radiation", "wind_speed", "precipitation", "hvac_on_count",
    "mode_off", "mode_heating", "mode_cooling", "mean_setpoint_c",
    "consumption_kwh", "sin_hour", "cos_hour", "sin_day_of_week",
    "cos_day_of_week", "is_weekend",
]


def thermal_source_frame(data_dir: Path) -> pd.DataFrame:
    """Build the thermal cohort independently of load-history eligibility."""
    combined = pd.concat(
        [load_block_hourly(data_dir, block) for block in BLOCKS], ignore_index=True
    )
    result = add_gap_segments(combined)
    hour = result["timestamp"].dt.hour
    day_of_week = result["timestamp"].dt.dayofweek
    result["sin_hour"] = np.sin(2 * np.pi * hour / 24)
    result["cos_hour"] = np.cos(2 * np.pi * hour / 24)
    result["sin_day_of_week"] = np.sin(2 * np.pi * day_of_week / 7)
    result["cos_day_of_week"] = np.cos(2 * np.pi * day_of_week / 7)
    result["is_weekend"] = day_of_week.ge(5).astype(int)
    return result


def add_thermal_target(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.sort_values(["block", "segment_id", "timestamp"]).copy()
    result["thermal_target"] = result.groupby(["block", "segment_id"])[
        "indoor_temperature_c"
    ].shift(-1)
    result["thermal_target_timestamp"] = result.groupby(["block", "segment_id"])[
        "timestamp"
    ].shift(-1)
    valid = result["thermal_target_timestamp"].sub(result["timestamp"]).eq(pd.Timedelta(hours=1))
    return result[valid & result["thermal_target"].notna()].copy()


def support_table(development: pd.DataFrame) -> pd.DataFrame:
    active = development[development["hvac_on_count"].gt(0) & development["mean_setpoint_c"].notna()].copy()
    active["dominant_mode"] = np.select(
        [active["mode_heating"].gt(active["mode_cooling"]), active["mode_cooling"].gt(active["mode_heating"])],
        ["heating", "cooling"], default="mixed_or_off",
    )
    rows = []
    for (block, mode), group in active.groupby(["block", "dominant_mode"]):
        observed = group["mean_setpoint_c"].to_numpy()
        low, high = np.quantile(observed, [0.01, 0.99])
        for delta in (-1.0, 1.0):
            candidate = observed + delta
            in_range = (candidate >= low) & (candidate <= high)
            local_count = np.array([np.sum(np.abs(observed - value) <= 0.25) for value in candidate])
            supported = in_range & (local_count >= 20)
            rows.append({"block": block, "mode": mode, "delta_c": delta, "n": len(group),
                "observed_p01": low, "observed_p99": high,
                "support_rate": float(supported.mean()), "median_local_count": float(np.median(local_count)),
                "action_definition": "rowwise block-mean observed setpoint plus delta_c",
                "screening_only": True})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--raw-data-dir", type=Path)
    args = parser.parse_args()

    if args.raw_data_dir is not None:
        frame = thermal_source_frame(args.raw_data_dir)
        cohort_source = "raw_hourly_components_without_load_history_filter"
    else:
        frame = pd.read_csv(args.dataset, parse_dates=["timestamp", "target_timestamp"])
        cohort_source = "provided_processed_dataset"
    thermal = add_thermal_target(frame)
    development = thermal[thermal["thermal_target_timestamp"].lt(pd.Timestamp("2021-12-01", tz="UTC"))]
    folds = monthly_rolling_folds(development["thermal_target_timestamp"])
    columns = THERMAL_FEATURES + ["block"]
    prediction_rows = []
    specs = [
        ("ridge", Ridge(alpha=1.0)),
        ("hist_gradient_boosting", HistGradientBoostingRegressor(
            learning_rate=0.05, max_iter=200, max_leaf_nodes=31,
            l2_regularization=1.0, random_state=42)),
    ]
    for fold in folds:
        times = development["thermal_target_timestamp"]
        train = development[times.lt(pd.Timestamp(fold.train_end))]
        test = development[times.ge(pd.Timestamp(fold.test_start)) & times.lt(pd.Timestamp(fold.test_end))]
        base = test[["block", "timestamp", "thermal_target_timestamp", "thermal_target"]].copy()
        base["fold"], base["model"] = fold.name, "persistence"
        base["prediction"] = test["indoor_temperature_c"].to_numpy()
        prediction_rows.append(base)
        for name, estimator in specs:
            model = Pipeline([("transform", make_transformer(THERMAL_FEATURES)), ("model", estimator)])
            model.fit(train[columns], train["thermal_target"])
            result = test[["block", "timestamp", "thermal_target_timestamp", "thermal_target"]].copy()
            result["fold"], result["model"] = fold.name, name
            result["prediction"] = model.predict(test[columns])
            prediction_rows.append(result)

    predictions = pd.concat(prediction_rows, ignore_index=True)
    metric_rows = []
    for (fold, model), group in predictions.groupby(["fold", "model"]):
        scopes = [("all", group)] + [(f"block_{b}", g) for b, g in group.groupby("block")]
        for scope, scoped in scopes:
            metric_rows.append({"fold": fold, "model": model, "scope": scope, "n": len(scoped),
                **regression_metrics(scoped["thermal_target"].to_numpy(), scoped["prediction"].to_numpy())})
    metrics = pd.DataFrame(metric_rows)
    support = support_table(development)
    overall = metrics[metrics["scope"].eq("all")].groupby("model")[["mae", "rmse", "r2"]].mean()
    best_model = overall["mae"].idxmin()
    persistence_mae = float(overall.loc["persistence", "mae"])
    best_mae = float(overall.loc[best_model, "mae"])
    thermal_pass = best_model != "persistence" and best_mae <= 0.95 * persistence_mae
    support_pass = bool((support["support_rate"] >= 0.80).all()) if not support.empty else False
    gate = {
        "final_holdout_opened": False, "best_model": best_model,
        "analysis_timing": "post_review_corrective_analysis",
        "cohort_source": cohort_source,
        "thermal_rows": len(thermal),
        "development_rows": len(development),
        "development_rows_by_block": development.groupby("block").size().to_dict(),
        "persistence_mae_c": persistence_mae, "best_mae_c": best_mae,
        "relative_mae_improvement": 1 - best_mae / persistence_mae,
        "thermal_prediction_pass": thermal_pass, "common_support_pass": support_pass,
        "decision_module_status": "pass" if thermal_pass and support_pass else "downgraded",
        "rule": "best model >=5% MAE improvement and every block-mode-direction support rate >=0.80",
        "support_interpretation": "empirical proximity screening; not causal positivity or intervention identification",
        "setpoint_action": "plus-or-minus 1 C applied to the rowwise block-mean observed setpoint",
        "dominant_mode_rule": "heating if heating count exceeds cooling count; cooling if converse; otherwise mixed_or_off",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(args.output_dir / "predictions.csv", index=False)
    metrics.to_csv(args.output_dir / "metrics.csv", index=False)
    overall.to_csv(args.output_dir / "summary.csv")
    support.to_csv(args.output_dir / "setpoint_common_support.csv", index=False)
    (args.output_dir / "decision_gate.json").write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    print(overall.to_string())
    print(json.dumps(gate, indent=2))
    print(support.to_string(index=False))


if __name__ == "__main__":
    main()
