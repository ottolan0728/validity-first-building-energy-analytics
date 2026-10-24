# Validity-First Building Energy Analytics

Research code and selected aggregate results associated with **A Validity-First Evidence-Gating Framework for Explainable Building Energy Management**, *Energy & Buildings* (2026). Article DOI: https://doi.org/10.1016/j.enbuild.2026.118420.

## Archived software release

The initial limited public-code archive (GitHub release `v1.0.1`) is preserved at Zenodo: https://doi.org/10.5281/zenodo.23609759. This is the **software archive DOI**, distinct from the journal article DOI. The archive does not include the complete timestamp-level prediction exports or final production figures.

## Important post-acceptance disclosures

### Revision 1 — Persistence Comparator Timing

The forecasting target is consumption at `t+1`, but the frozen comparator `seasonal_naive_24h` uses consumption at feature-time `t-24`. Its effective observation-to-target separation is therefore **25 hours**, although the accepted paper describes it as “24-hour persistence.”

The accepted development comparator MAE (1.201 kWh) and final-period comparator MAE (1.713 kWh) are results of the **implemented 25-hour-separation comparator**. A separate post-acceptance development-only sensitivity with a genuine target-minus-24-hour comparator retained the Random Forest advantage (paired MAE improvement 0.269 kWh, 24.5%, 95% block-day bootstrap CI [0.208, 0.333] kWh). The genuine-24-hour December holdout and held-block transfer comparisons have **not** been quantified.

### Revision 2 — Upstream Data Filtering

The PLEIAData source notebook generated hourly consumption component tables after applying `0 < dif_cons < 25` kWh. This project's reconstruction did not apply a second cutoff, but inherited the source filter. For Block C, 305 candidate high-consumption hours were excluded and 155 additional hours lacked raw meter observations. The impact of restoring these observations on predictive performance remains **unquantified**.

These disclosures do not constitute a publisher-issued correction. The frozen original code and accepted numerical outputs have not been silently changed.

## Scope

This initial repository release contains original analysis scripts, unit tests, historical dependency specifications, selected aggregate statistical results, method documentation, and source attribution.

It intentionally excludes:
- Original or processed PLEIAData, available separately at https://doi.org/10.5281/zenodo.7096790
- Row-level prediction and forensic exports pending redistribution review
- Historical pre-proof figure PDFs that do not match the final six published figure slots
- Final production Figure 1–6 files, not available in the archived Codex workspace
- Internal audit dossiers, manuscript and proof files, and author correspondence

**This is a limited public-code release, not a complete timestamp-level replication archive.** It should not be cited as containing all final figures or full timestamp-level predictions.

## Reproduction

See `REPRODUCIBILITY.md`. Obtain the PLEIAData archive independently, work in a disposable copy, and do not treat the already-opened one-shot December holdout as a fresh untouched validation set.

## License and citation

MIT covers original author-owned code only. PLEIAData is CC BY 4.0 and must be attributed separately. See `LICENSE`, `THIRD_PARTY_NOTICES.md`, `DATA_SOURCES.md`, and `CITATION.cff`.

## Publication status

The journal article is available online. The authors have separately requested editorial consideration of the two post-acceptance methodological clarifications. Public code disclosure does not itself amend the journal article.
