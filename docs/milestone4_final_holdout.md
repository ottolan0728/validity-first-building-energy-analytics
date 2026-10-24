# Milestone 4 — one-shot final holdout

## Integrity record

- Holdout: 2021-12-01 00:00 UTC through the available endpoint, 2021-12-17 23:00 UTC.
- Forecast observations: 930 block-hours (A: 319, B: 319, C: 292).
- Dataset SHA-256: `324abec7b3e0b6fb46a4792622060717646ea9c8ba47ba8e403ecc9cdf5bdfed`.
- Opened once: 2026-07-13 01:35:33 UTC.
- Completed: 2026-07-13 01:36:05 UTC.
- The runner refuses a second opening while `HOLDOUT_OPENED.json` exists.

The source does not cover a complete calendar month. Results are therefore described as the
available December holdout, not as full-month performance.

## Point forecasts

| Model | MAE (kWh) | RMSE (kWh) | R² |
|---|---:|---:|---:|
| Histogram Gradient Boosting | **0.856** | **1.940** | **0.513** |
| Random Forest | 0.859 | 2.020 | 0.472 |
| Ridge | 1.012 | 2.184 | 0.383 |
| 24-hour persistence | 1.713 | 3.674 | -0.747 |

Random Forest improved MAE over persistence by 0.854 kWh. A 5,000-repetition block-day cluster
bootstrap gave a 95% interval of 0.460-1.321 kWh (42 clusters). Point-forecast performance therefore
passed the final gate, although Block C remained hardest (RF MAE 1.400 kWh).

## Prediction intervals

| Scope | 80% coverage | 90% coverage |
|---|---:|---:|
| All blocks | 0.662 | 0.787 |
| Block A | 0.574 | 0.765 |
| Block B | 0.774 | 0.871 |
| Block C | 0.637 | 0.719 |

The corresponding pooled widths were 1.634 and 2.545 kWh. Both intervals under-covered, especially
in Blocks A and C. The uncertainty gate therefore **failed** under temporal shift. Static
November-calibrated residual intervals must not be presented as deployment-ready guarantees.

## Thermal response and decision status

| Model | MAE (°C) | RMSE (°C) | R² |
|---|---:|---:|---:|
| Histogram Gradient Boosting | **0.118** | **0.170** | **0.941** |
| Ridge | 0.124 | 0.179 | 0.935 |
| Persistence | 0.133 | 0.185 | 0.930 |

The final thermal prediction remained better than persistence. The development common-support gate
had already failed, so no setpoint savings or comfort counterfactual was estimated after opening the
holdout. Decision status remains **downgraded**.

## Final evidence-gate outcome

| Module | Status |
|---|---|
| Data validity | Pass for operational PLEIAData; synthetic source restricted to stress testing |
| Calibrated point forecasting | Pass |
| Static split-conformal uncertainty | Fail on final temporal holdout |
| Descriptive explanation stability | Pass with causal-language restriction |
| Zero-shot block transfer | Fail |
| Thermal prediction | Pass |
| ±1°C action common support | Fail |
| Savings/control effectiveness | Not estimated |

The final contribution is a validity-first, fail-safe decision-support architecture. It identifies
where evidence is sufficient and refuses unsupported uncertainty and control claims.
