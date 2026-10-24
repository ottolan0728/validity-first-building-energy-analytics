# Milestone 3 — uncertainty, explanation, and decision-safety gates

## Scope and holdout status

- Dataset: `pleiadata_h1_history24.csv`.
- Development folds: July-November 2021 expanding-window evaluation.
- December 2021 final holdout: **not opened**.
- All claims below are development-stage evidence.

## Split-conformal uncertainty

Each fold used the last 30 days before its test month as a chronological calibration set. Symmetric
absolute-residual intervals used the finite-sample split-conformal quantile.

| Scope | Nominal | Mean coverage | Mean width (kWh) |
|---|---:|---:|---:|
| All blocks | 80% | 0.810 | 2.587 |
| All blocks | 90% | 0.898 | 4.166 |
| Block A | 80% | 0.778 | 2.587 |
| Block A | 90% | 0.895 | 4.166 |
| Block B | 80% | 0.847 | 2.587 |
| Block B | 90% | 0.916 | 4.166 |
| Block C | 80% | 0.820 | 2.587 |
| Block C | 90% | 0.891 | 4.166 |

Pooled calibration is close to nominal, but the Block A 80% interval under-covers. The framework
therefore requires block-level monitoring.

## Explanation stability

The computationally bounded stability screen used a 60-tree Random Forest, 250 fixed-seed test
observations per fold and scope with two permutation repeats, and up to 500 observations for SHAP.

- Mean pairwise Spearman correlation of overall permutation ranks: **0.745**.
- Mean pairwise Top-10 Jaccard similarity: **0.824**.
- Both permutation and SHAP ranked the 1-hour consumption lag first.
- Calendar phase, rolling/lagged consumption, HVAC on-count, solar radiation, and indoor/outdoor
  temperature formed the secondary group.

This supports moderate-to-high temporal stability of the descriptive explanation, not causality.

## One-hour thermal response

| Model | Mean MAE (°C) | Mean RMSE (°C) | Mean R² |
|---|---:|---:|---:|
| Ridge | **0.0790** | **0.1169** | **0.9887** |
| Persistence | 0.0907 | 0.1253 | 0.9869 |
| Histogram Gradient Boosting | 0.1876 | 0.2919 | 0.8719 |

Ridge improved MAE over persistence by **12.9%**, exceeding the pre-specified 5% prediction gate.

## Setpoint common-support gate

Candidate actions were the observed mean setpoint plus or minus 1°C. An action was supported only
when it fell within the block-mode 1st-99th percentile range and had at least 20 observed actions
within ±0.25°C. The pre-specified gate required at least 80% support for every combination.

The gate **failed**. Support ranged from 0 to 0.870, and most combinations were far below 0.80;
both directions in Block C had near-zero support. Consequently:

- thermal prediction gate: **pass**;
- common-support gate: **fail**;
- decision module: **downgraded**;
- offline savings, comfort improvement, and causal setpoint-effect claims: **not authorized**.

The publishable contribution becomes a gated evidence architecture that refuses unsupported
actions, rather than an unvalidated optimization claim.

## Reproducibility

```powershell
.\.venv\Scripts\python.exe scripts\run_uncertainty.py data\processed\pleiadata_h1_history24.csv outputs\milestone3\uncertainty
.\.venv\Scripts\python.exe scripts\run_explanation_stability.py data\processed\pleiadata_h1_history24.csv outputs\milestone3\explanations
.\.venv\Scripts\python.exe scripts\run_thermal_response.py data\processed\pleiadata_h1_history24.csv outputs\milestone3\thermal
```

Machine-readable outputs are under `outputs/milestone3/` and are intentionally ignored by Git.
