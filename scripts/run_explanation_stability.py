"""Milestone 3: out-of-sample permutation and SHAP stability analysis."""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import shap
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_buildings.folds import monthly_rolling_folds  # noqa: E402
from energy_buildings.modeling import FEATURE_GROUPS, make_transformer  # noqa: E402


RF_SPEC = {
    "n_estimators": 300,
    "max_depth": 18,
    "min_samples_leaf": 3,
    "n_jobs": -1,
    "random_state": 42,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--shap-sample", type=int, default=500)
    parser.add_argument("--permutation-sample", type=int, default=250)
    parser.add_argument("--permutation-repeats", type=int, default=2)
    args = parser.parse_args()

    frame = pd.read_csv(args.dataset, parse_dates=["timestamp", "target_timestamp"])
    development = frame[frame["target_timestamp"].lt(pd.Timestamp("2021-12-01", tz="UTC"))]
    folds = monthly_rolling_folds(development["target_timestamp"])
    features = FEATURE_GROUPS["plus_setpoint"]
    columns = features + ["block"]
    permutation_rows, shap_rows = [], []

    for fold_index, fold in enumerate(folds):
        target_time = development["target_timestamp"]
        train = development[target_time.lt(pd.Timestamp(fold.train_end))]
        test = development[
            target_time.ge(pd.Timestamp(fold.test_start))
            & target_time.lt(pd.Timestamp(fold.test_end))
        ]
        model = Pipeline(
            [
                ("transform", make_transformer(features)),
                ("model", RandomForestRegressor(**RF_SPEC)),
            ]
        )
        model.fit(train[columns], train["target"])
        scopes = [("all", test)] + [(f"block_{b}", g) for b, g in test.groupby("block")]
        for scope, group in scopes:
            evaluation = group.sample(
                min(args.permutation_sample, len(group)), random_state=420 + fold_index
            )
            perm = permutation_importance(
                model, evaluation[columns], evaluation["target"], scoring="neg_mean_absolute_error",
                n_repeats=args.permutation_repeats, random_state=42, n_jobs=-1,
            )
            for feature, mean, std in zip(columns, perm.importances_mean, perm.importances_std):
                permutation_rows.append({"fold": fold.name, "scope": scope, "feature": feature,
                    "importance": mean, "importance_std": std})

        sample = test.sample(min(args.shap_sample, len(test)), random_state=42 + fold_index)
        transformed = model.named_steps["transform"].transform(sample[columns])
        transformed_names = model.named_steps["transform"].get_feature_names_out()
        values = shap.TreeExplainer(model.named_steps["model"]).shap_values(transformed)
        for scope, mask in [("all", np.ones(len(sample), dtype=bool))] + [
            (f"block_{b}", sample["block"].eq(b).to_numpy()) for b in sorted(sample["block"].unique())
        ]:
            for feature, importance in zip(transformed_names, np.abs(values[mask]).mean(axis=0)):
                shap_rows.append({"fold": fold.name, "scope": scope, "feature": feature,
                    "mean_abs_shap": importance, "n": int(mask.sum())})

    permutation_frame = pd.DataFrame(permutation_rows)
    shap_frame = pd.DataFrame(shap_rows)
    stability_rows = []
    overall = permutation_frame[permutation_frame["scope"].eq("all")]
    pivot = overall.pivot(index="feature", columns="fold", values="importance")
    for left, right in itertools.combinations(pivot.columns, 2):
        rho = spearmanr(pivot[left], pivot[right]).statistic
        top_left = set(pivot[left].nlargest(10).index)
        top_right = set(pivot[right].nlargest(10).index)
        stability_rows.append({"fold_left": left, "fold_right": right,
            "spearman_rho": rho, "top10_jaccard": len(top_left & top_right) / len(top_left | top_right)})
    stability = pd.DataFrame(stability_rows)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    permutation_frame.to_csv(args.output_dir / "permutation_importance.csv", index=False)
    shap_frame.to_csv(args.output_dir / "shap_importance.csv", index=False)
    stability.to_csv(args.output_dir / "rank_stability.csv", index=False)
    summary = {
        "final_holdout_opened": False,
        "explained_model": "random_forest_full",
        "model_specification": RF_SPEC,
        "model_identity_status": "exact_match_to_frozen_forecast_rf",
        "stability_dimensions": ["development_month", "block"],
        "seed_stability_evaluated": False,
        "shap_sample_per_fold": args.shap_sample,
        "permutation_sample_per_scope_fold": args.permutation_sample,
        "permutation_repeats": args.permutation_repeats,
        "mean_spearman_rho": float(stability["spearman_rho"].mean()),
        "mean_top10_jaccard": float(stability["top10_jaccard"].mean()),
        "top_permutation_features": overall.groupby("feature")["importance"].mean().nlargest(10).to_dict(),
        "top_shap_features": shap_frame[shap_frame["scope"].eq("all")].groupby("feature")["mean_abs_shap"].mean().nlargest(10).to_dict(),
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
