"""Paired day-cluster bootstrap comparisons for Milestone 2 predictions."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


COMPARISONS = [
    ("random_forest_full", "seasonal_naive_24h"),
    ("hist_gradient_boosting_full", "seasonal_naive_24h"),
    ("ridge_history_calendar", "seasonal_naive_24h"),
    ("random_forest_full", "ridge_history_calendar"),
    ("ridge_plus_hvac", "ridge_history_calendar"),
    ("ridge_plus_setpoint", "ridge_plus_hvac"),
]


def clustered_bootstrap(
    differences: pd.DataFrame, repetitions: int = 5000, seed: int = 42
) -> tuple[float, float, float]:
    """Bootstrap block-days while preserving their observation counts."""
    clusters = (
        differences.groupby(["block", "date"], as_index=False)["difference"]
        .agg(["sum", "count"])
        .reset_index()
    )
    sums = clusters["sum"].to_numpy()
    counts = clusters["count"].to_numpy()
    rng = np.random.default_rng(seed)
    estimates = np.empty(repetitions)
    for index in range(repetitions):
        sample = rng.integers(0, len(clusters), size=len(clusters))
        estimates[index] = sums[sample].sum() / counts[sample].sum()
    estimate = differences["difference"].mean()
    low, high = np.quantile(estimates, [0.025, 0.975])
    return float(estimate), float(low), float(high)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    raw = pd.read_csv(args.predictions, parse_dates=["target_timestamp"])
    wide = raw.pivot(
        index=["fold", "block", "target_timestamp", "actual"],
        columns="model",
        values="prediction",
    ).reset_index()
    wide["date"] = wide["target_timestamp"].dt.date

    results = []
    for candidate, comparator in COMPARISONS:
        paired = wide[["fold", "block", "date", "actual", candidate, comparator]].dropna().copy()
        paired["candidate_error"] = (paired["actual"] - paired[candidate]).abs()
        paired["comparator_error"] = (paired["actual"] - paired[comparator]).abs()
        # Positive values mean the candidate has lower absolute error.
        paired["difference"] = paired["comparator_error"] - paired["candidate_error"]
        estimate, low, high = clustered_bootstrap(paired)
        comparator_mae = paired["comparator_error"].mean()
        results.append(
            {
                "candidate": candidate,
                "comparator": comparator,
                "n": len(paired),
                "candidate_mae": paired["candidate_error"].mean(),
                "comparator_mae": comparator_mae,
                "mae_improvement": estimate,
                "relative_improvement_pct": 100 * estimate / comparator_mae,
                "cluster_bootstrap_ci_low": low,
                "cluster_bootstrap_ci_high": high,
                "row_win_rate": (paired["difference"] > 0).mean(),
            }
        )

    output = pd.DataFrame(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False)
    print(output.to_string(index=False))


if __name__ == "__main__":
    main()

