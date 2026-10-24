# Methodology and claim boundaries

- The target is monitored-HVAC consumption at `t+1`, not whole-building energy.
- The three blocks belong to one building complex and are not independent buildings.
- The accepted cohort inherits upstream consumption filtering and excludes missing
  or ineligible timestamps; results do not generalize to removed hours.
- The frozen `seasonal_naive_24h` implementation is 25 hours behind the target.
- Fold-mean metrics and pooled paired metrics are different estimands.
- SHAP and permutation importance are descriptive model diagnostics, not causal effects.
- Split-conformal outputs are empirical static intervals under dependent data, not
  unconditional deployment guarantees.
- Leave-one-block-out evaluation is an operational domain-shift stress test, not
  proof of cross-building transfer.
- Thermal prediction accuracy does not establish setpoint intervention effects.
- Empirical action proximity is not causal positivity, exchangeability, or
  intervention consistency.
- The failed support gate prohibits savings, comfort, control-effect, optimization,
  and deployment claims.
- Post-acceptance true-24 development sensitivity does not repair or replace the
  frozen final-holdout and transfer comparisons.
