# WINDOWS_WSL2_LIQUIDITY_REVERSAL_LOCAL_PROBE_VALIDATION_R31_20260709 Intake

Classification: ordinary research-only local-probe validation batch.

## Trigger

R30 reached `LOCAL_RESEARCH_PROBE_ELIGIBLE` for `liquidity_constrained_reversal`, but external audit identified that R30 prequalification included test spread and test IC in the eligibility rule. R31 is required before any local probe execution.

## Baseline

- R30 eligible line: `liquidity_constrained_reversal`.
- R30 train spread: 0.006455.
- R30 validation spread: 0.037909.
- R30 test spread: 0.012947.
- R30 validation IC: 0.079738.
- R30 test IC: 0.05352.
- strategy_candidate_available=false.

## Required reads

- `tasks/in_progress/windows-wsl2-liquidity-reversal-local-probe-validation-r31-20260709/spec.md`
- `reports/agent_handoff/windows_wsl2_liquidity_reversal_local_probe_validation_r31_dispatcher_prompt_20260709.md`
- R30 source artifacts.

## Boundary

Research-only. No actionable output, no candidate promotion, no readiness/product-route activation, no daily signal, no raw-data migration into controller, no active schema/registry activation, and no credential output.
