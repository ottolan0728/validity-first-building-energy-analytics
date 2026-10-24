# One-hour-ahead Baseline Results

Run date：2026-07-12  
Status：`PRELIMINARY`  
Dataset SHA-256：`6b2a23e0df805754212c45a4671a90715d7ac9033c53bda730a7e3ab35039205`

## 1. Experimental frame

- Unit：block-hour pooled across PLEIA blocks A/B/C.
- Horizon：one hour ahead.
- Feature history requirement：168 contiguous hours.
- Evaluation：expanding-window rolling origin.
- Test folds：July, August, September, October, and November 2021.
- Models：24-hour seasonal naive, 168-hour seasonal naive, Ridge regression.
- Preprocessing：fit within each training fold only.

These are feasibility baselines, not final paper results.

## 2. Fold-level results

| Fold | Model | N test | MAE | RMSE | R2 |
|---|---|---:|---:|---:|---:|
| 2021-07 | Naive 24h | 1,317 | 1.612 | 2.620 | 0.591 |
| 2021-07 | Naive 168h | 1,317 | 1.843 | 2.813 | 0.529 |
| 2021-07 | Ridge | 1,317 | **1.083** | **1.753** | **0.817** |
| 2021-08 | Naive 24h | 1,176 | 0.827 | 1.170 | 0.721 |
| 2021-08 | Naive 168h | 1,176 | 1.229 | 1.826 | 0.321 |
| 2021-08 | Ridge | 1,176 | **0.675** | **0.938** | **0.821** |
| 2021-09 | Naive 24h | 1,485 | 1.461 | 2.298 | 0.596 |
| 2021-09 | Naive 168h | 1,485 | 1.578 | 2.284 | 0.601 |
| 2021-09 | Ridge | 1,485 | **0.978** | **1.571** | **0.811** |
| 2021-10 | Naive 24h | 1,778 | 0.729 | 1.318 | 0.776 |
| 2021-10 | Naive 168h | 1,778 | 1.212 | 2.126 | 0.418 |
| 2021-10 | Ridge | 1,778 | **0.615** | **0.953** | **0.883** |
| 2021-11 | Naive 24h | 2,160 | 0.833 | 1.736 | 0.209 |
| 2021-11 | Naive 168h | 2,160 | 0.984 | 1.739 | 0.207 |
| 2021-11 | Ridge | 2,160 | **0.605** | **1.098** | **0.684** |

## 3. Mean across folds

| Model | MAE mean | RMSE mean | R2 mean |
|---|---:|---:|---:|
| Ridge | **0.791** | **1.262** | **0.803** |
| Seasonal naive 24h | 1.092 | 1.828 | 0.579 |
| Seasonal naive 168h | 1.369 | 2.158 | 0.415 |

Relative to the mean 24-hour naive metrics, Ridge reduced MAE by approximately 27.6% and
RMSE by approximately 31.0%. Ridge was better in all five folds.

## 4. Interpretation boundary

This result establishes that the real PLEIAData signal is predictable and that a simple
regularized model adds value beyond seasonal persistence. It does not yet establish:

- that HVAC/setpoint variables cause the gain;
- that the model transfers across blocks or buildings;
- that a decision policy saves energy;
- that Ridge is superior to tree ensembles;
- statistical significance at timestamp level;
- robustness to the 168-hour complete-history selection rule.

## 5. Required next analyses

1. 24-hour-history sensitivity dataset so Block C is not disproportionately removed.
2. Per-block metrics and leave-one-block-out evaluation.
3. Feature-group ablations: history, weather, indoor state, HVAC, and setpoint.
4. Timestamp-level prediction export and paired error analysis with confidence intervals.
5. Tree ensemble benchmark after the linear baseline is frozen.
6. A dedicated untouched final test period after model selection.

