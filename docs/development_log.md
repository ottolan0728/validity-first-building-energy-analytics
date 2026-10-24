# Development Log

## 2026-07-12 - Milestone 1

- Verified and extracted PLEIAData archive.
- Audited source notebook aggregation logic.
- Identified unbounded forward fills, fixed energy cutoffs, target smoothing, and Block A
  selection as methods that must not be inherited silently.
- Implemented component-table joins instead of using the author's merged modeling tables.
- Implemented gap segmentation and gap-safe lag/rolling/target construction.
- Added three automated tests for segment and target leakage boundaries; all passed.
- Created the first one-hour-ahead processed dataset (19,678 rows).
- Ran five expanding-window monthly folds.
- Fixed JSON summary serialization after a successful training run exposed MultiIndex keys.
- Completed seasonal-naive and Ridge baselines.

Next milestone: sensitivity datasets, per-block predictions, ablations, and tree baselines.

## 2026-07-12 - Milestone 2

- Added a 24-hour-history primary cohort and retained 168 hours as sensitivity only.
- Increased usable rows from 19,678 to 22,813 and Block C rows from 4,217 to 6,458.
- Exported timestamp-level predictions for five Ridge ablations, Random Forest, Histogram
  Gradient Boosting, and seasonal naive across five rolling folds.
- Added day-cluster bootstrap comparisons.
- Found robust RF gains over naive and Ridge, but no reliable incremental forecasting gain from
  HVAC or setpoint features.
- Completed per-block evaluation; Block C was consistently hardest.
- First leave-one-block-out run exceeded the compute timeout before writing outputs. Reduced the
  screening configuration to 80 RF trees and 150 boosting iterations and reran successfully.
- Leave-one-block-out rejected reliable zero-shot transfer: naive retained slightly lower mean MAE,
  while RF retained lower RMSE.
- Kept December 2021 frozen as the untouched final holdout.

Next milestone: uncertainty calibration, explanation stability, and thermal response modeling.

