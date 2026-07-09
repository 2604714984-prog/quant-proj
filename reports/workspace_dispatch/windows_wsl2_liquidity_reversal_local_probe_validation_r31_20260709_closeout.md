# R31 Liquidity Reversal Validation Closeout

Batch: `WINDOWS_WSL2_LIQUIDITY_REVERSAL_LOCAL_PROBE_VALIDATION_R31_20260709`

Closeout status: `CLOSED_ACCEPTED_RESEARCH_ONLY_REJECTED_BY_LOCAL_PROBE_DIAGNOSTICS`

R31 is closed. The R30 `LOCAL_RESEARCH_PROBE_ELIGIBLE` label is superseded by R31 validation.

Final decision:

`REJECTED_BY_LOCAL_PROBE_DIAGNOSTICS`

Carry-forward facts:

- Validation-only prequalification passed.
- Test split was diagnostic-only and not used for selection.
- Local-probe diagnostics failed on validation long-short diagnostic portfolio.
- `local_research_probe_eligible_count=0`.
- `strategy_candidate_available=false`.

Next source action: do not proceed to local probe for `liquidity_constrained_reversal` under current evidence. Revisit only with a new validation-only design or new holdout evidence.

Boundary result: `PASS_RESEARCH_ONLY`.
