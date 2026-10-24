# Reproducibility and evidence boundaries

The original project used PLEIAData (https://doi.org/10.5281/zenodo.7096790). The source archive and processed cohorts are **not** redistributed.

The accepted one-hour-ahead target is consumption at feature time t+1. The frozen `seasonal_naive_24h` comparator uses consumption at feature time t-24, so its effective separation is 25 hours. The accepted results are archived as produced, not silently corrected.

The upstream consumption components were prefiltered at `0 < dif_cons < 25` kWh. This selection affects the observed cohort.

The original December holdout was opened once and is archival-only. Do not rerun it as a new untouched test. Any future corrected final-period analysis must be separately preregistered and labelled as post-acceptance.

The initial public repository is a limited code release. Row-level predictions, complete final figures and original data are not yet included. See README and DATA_SOURCES.
