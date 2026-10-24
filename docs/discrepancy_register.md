# RC2 discrepancy register

## Revision 1 — Persistence Comparator Timing

The underlying frozen evidence and program identifiers remain `R-01` and
`seasonal_naive_24h`; RC2 does not rename code, outputs, or accepted artifacts.

**Status:** CONFIRMED; accepted artifacts preserved; publication disposition open.

The frozen target is at `t+1`; `consumption_lag_24h` is observed at feature time
`t-24`. The effective separation is therefore 25 hours. Accepted labels and the
1.201 kWh development / 1.713 kWh final comparator values must not be represented
as verified true target-minus-24-hour results.

Post-acceptance development sensitivity found true-24 pooled persistence MAE
1.097 kWh versus RF 0.827 kWh, with a 0.269 kWh (24.5%) improvement and 95%
block-day bootstrap interval [0.208, 0.333]. RF and HGB still won all five
development months. This sensitivity is not an accepted result. December and
zero-shot transfer were not recomputed and remain unquantified under true-24.

## Revision 2 — Upstream Data Filtering

The underlying frozen evidence identifier remains `R-02`; RC2 does not rename
code, outputs, or accepted artifacts.

**Status:** CONFIRMED; accepted no-fixed-filter wording contradicted.

The upstream notebook applies `0 < dif_cons < 25` before writing the component
consumption tables. The local pipeline avoids reapplying the rule but inherits the
filtered files. Block C has 305 identified high-load removals and 155 hours with
no raw observation. The threshold contributes to segmentation and eligibility
loss, but it is not identifiable as the sole cause of Block C error.

## Required interpretation

- Frozen accepted outputs remain archival; no value was overwritten.
- Point and transfer claims require comparator-specific wording.
- Every numerical module is conditional on the filtered retained cohort.
- Uncertainty and action failures remain failures.
- No causal, savings, comfort, control, deployment, or cross-building claim is
  upgraded by the post-acceptance analysis.
- Publisher/editor guidance remains pending; RC2 is not a correction notice.
