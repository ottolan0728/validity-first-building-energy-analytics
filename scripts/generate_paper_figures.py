"""Generate publication-ready tables and figures for manuscript revision round 2."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "tmp" / "matplotlib"))

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd


OUTPUT = ROOT / "paper" / "phase8_visuals"
FIGURES = OUTPUT / "figures"
TABLES = OUTPUT / "tables"

OKABE_ITO = {
    "orange": "#E69F00",
    "sky": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "black": "#000000",
    "grey": "#7A7A7A",
}


def configure_style() -> None:
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.bbox": "tight",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def save(fig: plt.Figure, stem: str) -> list[str]:
    paths = []
    for suffix, kwargs in (("pdf", {}), ("svg", {}), ("png", {"dpi": 600})):
        path = FIGURES / f"{stem}.{suffix}"
        fig.savefig(path, facecolor="white", **kwargs)
        paths.append(str(path.relative_to(ROOT)))
    plt.close(fig)
    return paths


def label_panels(axes) -> None:
    for label, ax in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", np.ravel(axes)):
        ax.text(-0.12, 1.07, label, transform=ax.transAxes, fontweight="bold",
                fontsize=10, va="top")


def block_characteristics() -> pd.DataFrame:
    frame = pd.read_csv(ROOT / "data/processed/pleiadata_h1_history24.csv",
                        parse_dates=["timestamp", "target_timestamp"])
    thermal_gate = json.loads((ROOT / "outputs/revision_round1/thermal_specific/decision_gate.json")
                              .read_text(encoding="utf-8"))
    thermal_counts = thermal_gate["development_rows_by_block"]
    rows = []
    for block, group in frame.groupby("block"):
        expected = int((group["timestamp"].max() - group["timestamp"].min()) /
                       pd.Timedelta(hours=1)) + 1
        rows.append({
            "Block": block,
            "Forecast rows": len(group),
            "Thermal development rows": thermal_counts[block],
            "Forecast start (UTC)": group["timestamp"].min().strftime("%Y-%m-%d"),
            "Forecast end (UTC)": group["timestamp"].max().strftime("%Y-%m-%d"),
            "Coverage within block span (%)": round(100 * len(group) / expected, 1),
            "Mean HVAC consumption (kWh)": round(group["consumption_kwh"].mean(), 2),
            "Mean active HVAC count": round(group["hvac_on_count"].mean(), 2),
            "Mean indoor temperature (°C)": round(group["indoor_temperature_c"].mean(), 2),
        })
    table = pd.DataFrame(rows)
    table.to_csv(TABLES / "table1_block_characteristics.csv", index=False)
    (TABLES / "table1_block_characteristics.md").write_text(
        table.to_markdown(index=False) + "\n", encoding="utf-8"
    )
    return table


def figure_framework() -> list[str]:
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.8)
    ax.axis("off")
    gates = [
        ("Data validity", "Provenance and gaps"),
        ("Point forecast", "MAE vs persistence"),
        ("Uncertainty", "Coverage and width"),
        ("Explanation", "Exact-model stability"),
        ("Transfer", "Leave-one-block-out"),
        ("Thermal", "MAE vs persistence"),
        ("Action screen", "Observed proximity"),
    ]
    colors = [OKABE_ITO["blue"], OKABE_ITO["green"], OKABE_ITO["orange"],
              OKABE_ITO["sky"], OKABE_ITO["purple"], OKABE_ITO["yellow"],
              OKABE_ITO["vermillion"]]
    positions = [(1.2, 4.25), (3.7, 4.25), (6.2, 4.25), (8.7, 4.25),
                 (2.4, 2.85), (5.0, 2.85), (7.6, 2.85)]
    for i, ((title, subtitle), (x, y), color) in enumerate(zip(gates, positions, colors)):
        box = FancyBboxPatch((x - 0.88, y - 0.43), 1.76, 0.86,
                             boxstyle="round,pad=0.08", facecolor=color,
                             edgecolor="black", linewidth=0.7, alpha=0.88)
        ax.add_patch(box)
        ax.text(x, y + 0.16, title, ha="center", va="center", fontweight="bold", fontsize=7.0)
        ax.text(x, y - 0.16, subtitle, ha="center", va="center", fontsize=6.0)
        if i in (0, 1, 2, 4, 5):
            nx, ny = positions[i + 1]
            ax.add_patch(FancyArrowPatch((x + 0.90, y), (nx - 0.90, ny),
                                         arrowstyle="-|>", mutation_scale=8, linewidth=0.8))
    ax.plot([9.60, 9.82, 9.82, 3.42], [4.25, 4.25, 2.85, 2.85],
            color="black", linewidth=0.8)
    ax.add_patch(FancyArrowPatch((3.42, 2.85), (3.30, 2.85),
                                 arrowstyle="-|>", mutation_scale=8, linewidth=0.8))
    state_text = [
        ("Baseline-only", "Point gate fails", OKABE_ITO["grey"]),
        ("Forecast-enabled advisory", "Point gate passes", OKABE_ITO["green"]),
        ("Warning / recalibration", "Uncertainty or transfer fails", OKABE_ITO["orange"]),
        ("Action-disabled", "Thermal or support gate fails", OKABE_ITO["vermillion"]),
    ]
    for (title, subtitle, color), x in zip(state_text, [1.25, 3.75, 6.25, 8.75]):
        box = FancyBboxPatch((x - 1.03, 0.78), 2.06, 0.72, boxstyle="round,pad=0.06",
                             facecolor="white", edgecolor=color, linewidth=1.5)
        ax.add_patch(box)
        ax.text(x, 1.25, title, ha="center", va="center", fontweight="bold", color=color, fontsize=6.8)
        ax.text(x, 0.99, subtitle, ha="center", va="center", fontsize=5.8)
    ax.text(5, 5.42, "Evidence gates: validity does not propagate automatically",
            ha="center", fontweight="bold", fontsize=10)
    ax.text(5, 0.28,
            "Failure suppresses the affected output and requires prospective revalidation; it does not erase supported upstream forecasts.",
            ha="center", fontsize=7.4)
    return save(fig, "figure1_evidence_gating_framework")


def figure_data_and_performance(block_table: pd.DataFrame) -> list[str]:
    metrics = pd.read_csv(ROOT / "outputs/milestone2/metrics.csv")
    final = pd.read_csv(ROOT / "outputs/milestone4/final_holdout/point_metrics.csv")
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.0), constrained_layout=True)
    ax = axes[0, 0]
    for _, row in block_table.iterrows():
        start = pd.Timestamp(row["Forecast start (UTC)"])
        end = pd.Timestamp(row["Forecast end (UTC)"])
        ax.plot([start, end], [row["Block"], row["Block"]], linewidth=6,
                solid_capstyle="butt", label=f"Block {row['Block']}")
    ax.axvspan(pd.Timestamp("2021-12-01"), pd.Timestamp("2021-12-18"),
               color=OKABE_ITO["orange"], alpha=0.25, label="Available final period")
    ax.set_xlabel("Calendar date (2021)")
    ax.set_ylabel("Block")
    ax.set_title("Eligible forecast coverage")
    ax.legend(frameon=False, loc="lower left")

    ax = axes[0, 1]
    dev = metrics[(metrics["scope"] == "all") & metrics["model"].isin(
        ["seasonal_naive_24h", "ridge_history_calendar", "random_forest_full",
         "hist_gradient_boosting_full"])]
    styles = {
        "seasonal_naive_24h": ("24-h persistence", OKABE_ITO["black"], "--", "o"),
        "ridge_history_calendar": ("Ridge", OKABE_ITO["sky"], "-.", "s"),
        "random_forest_full": ("Random Forest", OKABE_ITO["green"], "-", "^"),
        "hist_gradient_boosting_full": ("HGB", OKABE_ITO["orange"], ":", "D"),
    }
    for model, (label, color, ls, marker) in styles.items():
        group = dev[dev["model"] == model].sort_values("fold")
        ax.plot(group["fold"], group["mae"], label=label, color=color,
                linestyle=ls, marker=marker, linewidth=1.3, markersize=4)
    ax.set_xlabel("Development test month")
    ax.set_ylabel("MAE (kWh)")
    ax.set_title("Rolling-origin development performance")
    ax.tick_params(axis="x", rotation=30)
    ax.legend(frameon=False, ncol=2)

    ax = axes[1, 0]
    selected = final[(final["scope"] == "all")].copy()
    order = ["seasonal_naive_24h", "ridge_full", "random_forest_full",
             "hist_gradient_boosting_full"]
    labels = ["24-h\npersistence", "Ridge", "Random\nForest", "HGB"]
    colors = [OKABE_ITO["black"], OKABE_ITO["sky"], OKABE_ITO["green"], OKABE_ITO["orange"]]
    vals = [float(selected.loc[selected["model"] == m, "mae"].iloc[0]) for m in order]
    ax.bar(labels, vals, color=colors, edgecolor="black", linewidth=0.5)
    for i, value in enumerate(vals):
        ax.text(i, value + 0.035, f"{value:.3f}", ha="center", fontsize=7)
    ax.set_ylim(0, max(vals) * 1.18)
    ax.set_ylabel("MAE (kWh)")
    ax.set_title("Available-December holdout (n = 930)")

    ax = axes[1, 1]
    rf = final[final["model"] == "random_forest_full"].set_index("scope")
    hgb = final[final["model"] == "hist_gradient_boosting_full"].set_index("scope")
    blocks = ["block_A", "block_B", "block_C"]
    x = np.arange(3)
    width = 0.36
    ax.bar(x - width / 2, rf.loc[blocks, "mae"], width, label="Random Forest",
           color=OKABE_ITO["green"], edgecolor="black", linewidth=0.5)
    ax.bar(x + width / 2, hgb.loc[blocks, "mae"], width, label="HGB",
           color=OKABE_ITO["orange"], edgecolor="black", linewidth=0.5)
    ax.set_xticks(x, ["A", "B", "C"])
    ax.set_xlabel("Block")
    ax.set_ylabel("MAE (kWh)")
    ax.set_title("Final performance heterogeneity")
    ax.legend(frameon=False)
    label_panels(axes)
    return save(fig, "figure2_data_and_forecast_performance")


def figure_uncertainty_and_explanation() -> list[str]:
    dev = pd.read_csv(ROOT / "outputs/milestone3/uncertainty/summary.csv")
    final = pd.read_csv(ROOT / "outputs/milestone4/final_holdout/interval_metrics.csv")
    stability = pd.read_csv(ROOT / "outputs/revision_round1/explanations_exact_rf/rank_stability.csv")
    perm = pd.read_csv(ROOT / "outputs/revision_round1/explanations_exact_rf/permutation_importance.csv")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.8), constrained_layout=True)

    ax = axes[0]
    dev_all = dev[dev["scope"] == "all"].sort_values("nominal_coverage")
    final_all = final[final["scope"] == "all"].sort_values("nominal_coverage")
    x = np.arange(2)
    width = 0.35
    ax.bar(x - width / 2, dev_all["coverage"], width, label="Development",
           color=OKABE_ITO["sky"], edgecolor="black", linewidth=0.5)
    ax.bar(x + width / 2, final_all["coverage"], width, label="Final",
           color=OKABE_ITO["vermillion"], edgecolor="black", linewidth=0.5)
    for i, nominal in enumerate([0.8, 0.9]):
        ax.hlines(nominal, i - 0.43, i + 0.43, color="black", linestyle="--", linewidth=0.9)
    ax.set_xticks(x, ["80%", "90%"])
    ax.set_ylim(0.5, 1.0)
    ax.set_ylabel("Empirical coverage")
    ax.set_xlabel("Nominal interval")
    ax.set_title("Static conformal calibration")
    ax.legend(frameon=False)

    ax = axes[1]
    ax.scatter(stability["spearman_rho"], stability["top10_jaccard"],
               color=OKABE_ITO["blue"], edgecolor="black", linewidth=0.4, s=24)
    ax.axvline(stability["spearman_rho"].mean(), color=OKABE_ITO["blue"], linestyle="--")
    ax.axhline(stability["top10_jaccard"].mean(), color=OKABE_ITO["orange"], linestyle=":")
    ax.set_xlim(0.25, 0.9)
    ax.set_ylim(0.35, 0.9)
    ax.set_xlabel("Spearman rank correlation")
    ax.set_ylabel("Top-10 Jaccard similarity")
    ax.set_title("Cross-month explanation stability")
    ax.text(0.28, 0.86, f"Mean ρ = {stability['spearman_rho'].mean():.3f}\nMean J = {stability['top10_jaccard'].mean():.3f}",
            va="top", fontsize=7)

    ax = axes[2]
    overall = perm[perm["scope"] == "all"].groupby("feature")["importance"].mean().nlargest(8).sort_values()
    ax.barh(overall.index.str.replace("consumption_", "cons. ").str.replace("_", " "),
            overall.values, color=OKABE_ITO["green"], edgecolor="black", linewidth=0.4)
    ax.set_xlabel("Permutation ΔMAE (kWh)")
    ax.set_title("Exact-model feature importance")
    label_panels(axes)
    return save(fig, "figure3_uncertainty_and_explanation")


def figure_thermal_and_support() -> list[str]:
    thermal = pd.read_csv(ROOT / "outputs/revision_round1/thermal_specific/summary.csv")
    support = pd.read_csv(ROOT / "outputs/revision_round1/thermal_specific/setpoint_common_support.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), constrained_layout=True)

    ax = axes[0]
    order = ["persistence", "ridge", "hist_gradient_boosting"]
    labels = ["Persistence", "Ridge", "HGB"]
    colors = [OKABE_ITO["black"], OKABE_ITO["green"], OKABE_ITO["orange"]]
    vals = [float(thermal.loc[thermal["model"] == m, "mae"].iloc[0]) for m in order]
    ax.bar(labels, vals, color=colors, edgecolor="black", linewidth=0.5)
    for i, value in enumerate(vals):
        ax.text(i, value + 0.004, f"{value:.3f}", ha="center", fontsize=7)
    ax.axhline(vals[0] * 0.95, color=OKABE_ITO["vermillion"], linestyle="--", linewidth=1,
               label="5% improvement gate")
    ax.set_ylim(0, max(vals) * 1.22)
    ax.set_ylabel("Mean development MAE (°C)")
    ax.set_title("Thermal-specific cohort")
    ax.legend(frameon=False)

    ax = axes[1]
    support["row"] = support["block"] + "–" + support["mode"]
    matrix = support.pivot(index="row", columns="delta_c", values="support_rate")
    matrix = matrix.reindex(["A–cooling", "A–heating", "B–cooling", "B–heating",
                             "C–cooling", "C–heating"])
    image = ax.imshow(matrix.values, cmap="cividis", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks([0, 1], ["−1°C", "+1°C"])
    ax.set_yticks(np.arange(len(matrix)), matrix.index)
    ax.set_xlabel("Candidate change to block-mean setpoint")
    ax.set_title("Empirical action-support screen")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix.iloc[i, j]
            ax.text(j, i, f"{value:.2f}", ha="center", va="center",
                    color="white" if value < 0.45 else "black", fontsize=7)
    ax.axvline(-0.5, color="none")
    cbar = fig.colorbar(image, ax=ax, shrink=0.8)
    cbar.set_label("Supported-row proportion")
    ax.text(0.5, -0.27, "Required in every cell: ≥0.80 (not achieved)",
            transform=ax.transAxes, ha="center", color=OKABE_ITO["vermillion"], fontsize=7)
    label_panels(axes)
    return save(fig, "figure4_thermal_and_action_support")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    configure_style()
    table = block_characteristics()
    generated = []
    generated.extend(figure_framework())
    generated.extend(figure_data_and_performance(table))
    generated.extend(figure_uncertainty_and_explanation())
    generated.extend(figure_thermal_and_support())
    generated.extend([
        str((TABLES / "table1_block_characteristics.csv").relative_to(ROOT)),
        str((TABLES / "table1_block_characteristics.md").relative_to(ROOT)),
    ])
    sources = [
        "data/processed/pleiadata_h1_history24.csv",
        "outputs/milestone2/metrics.csv",
        "outputs/milestone3/uncertainty/summary.csv",
        "outputs/milestone4/final_holdout/point_metrics.csv",
        "outputs/milestone4/final_holdout/interval_metrics.csv",
        "outputs/revision_round1/explanations_exact_rf/rank_stability.csv",
        "outputs/revision_round1/explanations_exact_rf/permutation_importance.csv",
        "outputs/revision_round1/thermal_specific/summary.csv",
        "outputs/revision_round1/thermal_specific/setpoint_common_support.csv",
    ]
    provenance = {
        "generator": "scripts/generate_paper_figures.py",
        "design": "double-column 7.2-inch figures, Okabe-Ito categorical palette, cividis heatmap",
        "source_sha256": {p: sha256(ROOT / p) for p in sources},
        "generated_sha256": {p: sha256(ROOT / p) for p in generated},
    }
    (OUTPUT / "figure_provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({"generated": generated, "table_rows": len(table)}, indent=2))


if __name__ == "__main__":
    main()
