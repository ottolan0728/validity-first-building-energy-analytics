"""Deterministic Stage 4.5 checks for manuscript/result/figure alignment."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, label: str, failures: list[str]) -> None:
    if not condition:
        failures.append(label)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manuscript", nargs="?", type=Path,
                        default=ROOT / "paper/phase12_minor_revision/manuscript_v3.md")
    args = parser.parse_args()
    manuscript = args.manuscript.resolve()
    text = manuscript.read_text(encoding="utf-8")
    body, references = text.split("## References", 1)
    failures: list[str] = []

    citations = set(map(int, re.findall(r"\[(\d+)\](?=<!--ref:)", body)))
    reference_numbers = set(map(int, re.findall(r"(?m)^(\d+)\. ", references)))
    require(citations == reference_numbers == set(range(1, 22)), "citation_reference_set", failures)

    summary = pd.read_csv(ROOT / "outputs/milestone2/summary.csv").set_index("model")
    final = pd.read_csv(ROOT / "outputs/milestone4/final_holdout/point_metrics.csv")
    final_all = final[final["scope"].eq("all")].set_index("model")
    intervals = pd.read_csv(ROOT / "outputs/milestone4/final_holdout/interval_metrics.csv")
    interval_all = intervals[intervals["scope"].eq("all")].set_index("nominal_coverage")
    xai = json.loads((ROOT / "outputs/revision_round1/explanations_exact_rf/summary.json")
                     .read_text(encoding="utf-8"))
    thermal = json.loads((ROOT / "outputs/revision_round1/thermal_specific/decision_gate.json")
                         .read_text(encoding="utf-8"))

    expected_strings = {
        f"{summary.loc['random_forest_full', 'mae']:.3f}": "development_rf_mae",
        f"{final_all.loc['hist_gradient_boosting_full', 'mae']:.3f}": "final_hgb_mae",
        f"{final_all.loc['random_forest_full', 'mae']:.3f}": "final_rf_mae",
        f"{final_all.loc['seasonal_naive_24h', 'mae']:.3f}": "final_persistence_mae",
        f"{interval_all.loc[0.8, 'coverage']:.3f}": "final_80_coverage",
        f"{interval_all.loc[0.9, 'coverage']:.3f}": "final_90_coverage",
        f"{xai['mean_spearman_rho']:.3f}": "xai_spearman",
        f"{xai['mean_top10_jaccard']:.3f}": "xai_jaccard",
        f"{thermal['best_mae_c']:.3f}": "thermal_ridge_mae",
        f"{thermal['persistence_mae_c']:.3f}": "thermal_persistence_mae",
        f"{100 * thermal['relative_mae_improvement']:.1f}%": "thermal_improvement",
    }
    for token, label in expected_strings.items():
        require(token in body, f"missing_or_misaligned:{label}:{token}", failures)

    require(xai["model_identity_status"] == "exact_match_to_frozen_forecast_rf",
            "xai_model_identity", failures)
    require(xai["seed_stability_evaluated"] is False and "no seed-stability claim" in body,
            "seed_stability_boundary", failures)
    require(thermal["common_support_pass"] is False and
            "no setpoint counterfactual" in body.lower(), "action_refusal_boundary", failures)
    require("conducted after peer review" in body and
            "not represented as part of the original one-shot holdout protocol" in body,
            "corrective_analysis_timing", failures)

    provenance = json.loads((ROOT / "paper/phase8_visuals/figure_provenance.json")
                            .read_text(encoding="utf-8"))
    for relative, expected in provenance["source_sha256"].items():
        require(sha256(ROOT / relative) == expected, f"source_hash:{relative}", failures)
    for relative, expected in provenance["generated_sha256"].items():
        require(sha256(ROOT / relative) == expected, f"generated_hash:{relative}", failures)

    links = re.findall(r"!\[[^]]*\]\(([^)]+)\)", text)
    for link in links:
        require((manuscript.parent / link).resolve().exists(), f"figure_link:{link}", failures)

    result = {
        "verdict": "PASS" if not failures else "FAIL",
        "citation_count": len(citations),
        "empirical_tokens_checked": len(expected_strings),
        "figure_links_checked": len(links),
        "source_hashes_checked": len(provenance["source_sha256"]),
        "generated_hashes_checked": len(provenance["generated_sha256"]),
        "failures": failures,
    }
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
