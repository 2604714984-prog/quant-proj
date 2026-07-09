# Dispatcher Prompt - R31 Liquidity Reversal Local Probe Validation

Batch: `WINDOWS_WSL2_LIQUIDITY_REVERSAL_LOCAL_PROBE_VALIDATION_R31_20260709`

Read:

- `tasks/in_progress/windows-wsl2-liquidity-reversal-local-probe-validation-r31-20260709/spec.md`
- R30 result summary and closeout.
- A_Share_Monitor R30 diagnostics and final board.
- strategy_work R30 final sync.

## Execute

Run R31 as a research-only local-probe validation batch for `liquidity_constrained_reversal` only.

## Audit caveat from R30

R30 found `LOCAL_RESEARCH_PROBE_ELIGIBLE`, but its prequalification rule included test spread and test IC. R31 must not treat R30 as sufficient for immediate probe execution. Treat R30 as hypothesis-generation evidence and revalidate without using test outcomes for selection.

## Objective

Freeze the R30 formula and universe, then revalidate using validation-only prequalification. Test split is diagnostic-only. If validation-only passes, run bounded local research probe diagnostics with T+1/conservative fill assumptions.

## Boundary

Research-only. No actionable output, candidate promotion, readiness/product route, daily signal, broker/order/paper/live/auto path, active registry/schema change, credential output, full-frame wide3068, or test-result parameter selection.

## Callback

Return validation-only prequalification result, local probe diagnostics result, final decision label, local research probe eligible count, strategy_candidate_available, boundary result, fixes required, and next source action.
