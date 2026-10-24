# Result-to-artifact map

| Evidence domain | Primary source | Frozen/corrective outputs | Figure/provenance |
|---|---|---|---|
| Data validity | `src/energy_buildings/data.py`, `scripts/audit_pleiadata.py`, `scripts/prepare_pleiadata.py` | `outputs/audit/pleiadata_manifest_rc1.json` (path-normalized release record carrying the source hash) | Table 1; `paper/phase8_visuals/figure_provenance.json` |
| Point forecasting | `scripts/run_milestone2.py`, `scripts/analyze_milestone2.py` | `outputs/milestone2/{predictions,metrics,summary,paired_comparisons}.csv` | Figure 2; experiment/evidence registries |
| Uncertainty | `src/energy_buildings/uncertainty.py`, `scripts/run_uncertainty.py` | `outputs/milestone3/uncertainty/*`, final interval metrics | Figure 3; evidence registry |
| Explanation | `scripts/run_explanation_stability.py` | `outputs/revision_round1/explanations_exact_rf/*` | Figure 3; evidence registry |
| Transfer | `scripts/run_leave_one_block_out.py` | `outputs/milestone2/leave_one_block_out.csv` | experiment/claim registries |
| Thermal prediction | `scripts/run_thermal_response.py` | `outputs/revision_round1/thermal_specific/{predictions,metrics,summary}.csv` | Figure 4; evidence registry |
| Action screening | `scripts/run_thermal_response.py` | `setpoint_common_support.csv`, `decision_gate.json` | Figure 4; evidence registry |
| Final holdout | `scripts/run_final_holdout.py` | `outputs/milestone4/final_holdout/*` | Figures 2–3; holdout marker and evidence registry |
| Post-acceptance R-01/R-02 | forensic scripts | `forensic/post_acceptance_gate0a/*` | Not accepted evidence; disclosure/support only |
