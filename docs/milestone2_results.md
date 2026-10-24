# Milestone 2 Results: Robustness, Ablation, and Transfer

Run date：2026-07-12  
Status：`DEVELOPMENT RESULTS`  
Final holdout：all targets on or after 2021-12-01 remained unused.

## 1. Data sensitivity decision

| Dataset | Rows | A | B | C | Role |
|---|---:|---:|---:|---:|---|
| 24h history | 22,813 | 8,164 | 8,191 | 6,458 | Primary |
| 168h history | 19,678 | 7,645 | 7,816 | 4,217 | Sensitivity |

Requiring 168 contiguous hours disproportionately removes Block C. The apparently better
168-hour-cohort metrics therefore cannot be interpreted as evidence that longer history improves
the model. On the common evaluation cohort, the model trained with the larger 24-hour-history
population remained competitive or better. The 24-hour dataset is retained as the primary cohort.

## 2. Primary 24-hour-history development results

Mean of five monthly fold metrics:

| Model | MAE | RMSE | R2 |
|---|---:|---:|---:|
| Random Forest full | **0.849** | 1.518 | **0.750** |
| Histogram Gradient Boosting full | 0.862 | **1.517** | 0.741 |
| Ridge + HVAC | 0.896 | 1.518 | 0.745 |
| Ridge + setpoint | 0.896 | 1.522 | 0.744 |
| Ridge history + calendar | 0.897 | 1.531 | 0.743 |
| Ridge + indoor | 0.903 | 1.534 | 0.741 |
| Ridge + weather | 0.903 | 1.534 | 0.741 |
| Seasonal naive 24h | 1.201 | 2.196 | 0.461 |

Random Forest reduced fold MAE versus seasonal naive by 18.8% to 36.5% in every development
month.

## 3. Paired day-cluster bootstrap

Positive improvement means the candidate has lower absolute error. Confidence intervals resample
block-day clusters to avoid treating all hourly errors as independent.

| Candidate vs comparator | MAE improvement | Relative | 95% cluster-bootstrap CI |
|---|---:|---:|---:|
| RF vs seasonal naive | 0.348 kWh | 29.6% | [0.285, 0.413] |
| HGB vs seasonal naive | 0.334 kWh | 28.4% | [0.268, 0.401] |
| Ridge history/calendar vs seasonal naive | 0.294 kWh | 25.0% | [0.235, 0.354] |
| RF vs Ridge history/calendar | 0.054 kWh | 6.1% | [0.024, 0.081] |
| Ridge + HVAC vs Ridge history/calendar | 0.0004 kWh | 0.04% | [-0.0066, 0.0073] |
| Ridge + setpoint vs Ridge + HVAC | -0.0010 kWh | -0.11% | [-0.0034, 0.0015] |

The forecasting evidence supports history/calendar features and nonlinear models. It does not show
a reliable incremental forecasting benefit from HVAC or setpoint variables.

## 4. Per-block error

Mean MAE across development folds:

| Model | Block A | Block B | Block C |
|---|---:|---:|---:|
| Random Forest | **0.893** | 0.626 | **1.109** |
| HGB | 0.915 | **0.621** | 1.140 |
| Ridge history/calendar | 0.925 | 0.659 | 1.223 |
| Seasonal naive | 1.279 | 0.935 | 1.435 |

Block C is consistently hardest. Model rankings are not identical across blocks, so pooled metrics
must never be the only reported results.

## 5. Rolling leave-one-block-out transfer

Each held block is completely excluded from training in every monthly fold.

| Model | Held A MAE | Held B MAE | Held C MAE | Mean MAE | Mean RMSE |
|---|---:|---:|---:|---:|---:|
| Seasonal naive 24h | 1.279 | **0.935** | 1.435 | **1.216** | 2.158 |
| Random Forest | **1.163** | 1.171 | 1.337 | 1.224 | **1.928** |
| HGB | 1.505 | 1.173 | 1.375 | 1.351 | 2.060 |
| Ridge full | 2.111 | 1.096 | **1.247** | 1.485 | 2.025 |

Random Forest improves RMSE and improves MAE for held Blocks A and C, but it is worse than naive
for held Block B. Across the three blocks, naive has slightly lower mean MAE. The evidence therefore
rejects a claim of reliable zero-shot cross-building transfer.

## 6. Research implications

### Supported

- Real building demand is predictably structured.
- Within-building rolling updates provide substantial value beyond seasonal persistence.
- Nonlinear ensembles reduce large errors and provide a modest but robust gain over Ridge.
- Performance heterogeneity across blocks is material and must be reported.

### Not supported

- HVAC and setpoint variables materially improve one-hour load forecasting.
- A model trained on other blocks transfers reliably without calibration.
- Forecast accuracy alone demonstrates energy savings or control value.

## 7. Revised framework architecture

The evidence favors two separately validated modules:

1. **Forecasting module**: building-calibrated history/calendar model with uncertainty.
2. **Decision-support module**: HVAC/setpoint variables used as action/state variables, validated
   through thermal response and constrained offline counterfactual analysis—not justified by their
   incremental load-forecasting importance.

This separation prevents a common conceptual error: assuming that a variable must improve demand
prediction in order to be useful as a decision variable.

## 8. Next gate

Before accessing the frozen December holdout:

- freeze the candidate forecast model and hyperparameters;
- build prediction intervals and calibration diagnostics;
- run SHAP/permutation stability on development folds;
- build a thermal response model for indoor temperature;
- establish setpoint overlap/common-support diagnostics;
- define offline decision constraints and failure conditions.

