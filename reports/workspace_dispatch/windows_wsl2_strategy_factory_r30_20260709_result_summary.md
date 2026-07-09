# R30 Strategy Factory Result Summary

Batch: `WINDOWS_WSL2_STRATEGY_FACTORY_R30_20260709`

Status: `COMPLETED_RESEARCH_ONLY_STRATEGY_FACTORY_LOCAL_PROBE_ELIGIBLE`

## Source Preservation

A_Share_Monitor completed and pushed:

- branch: `codex/r30-strategy-factory-20260709`
- commit: `cd4ee4012f2fb6b6cb99df3aa6f38e6a5ae3d193`
- tree: `119e0317da5b632f4fd2841eae7808fc7c7d3db4`

strategy_work final sync completed and pushed:

- branch: `main`
- commit: `174f1028a819e94f44e6ee2a3b633559445b344e`
- tree: `7a384bf0e0c8fb0e783957ee95e06ccb476d5a4c`

## Factory Outcome

R30 reached one of the required terminal outcomes:

`LOCAL_RESEARCH_PROBE_ELIGIBLE`

Eligible research line:

- `liquidity_constrained_reversal`

This remains a research-only local probe label, not a candidate, recommendation, readiness, product route, daily signal, or trading path.

## Active Surface Status

- SmallCap: `DO_NOT_RETRY_UNTIL_NEW_SOURCE_DIRECT_MARKET_CAP`
- US30W-R22-002: `OBSERVATION_ONLY_LOCAL_PRESERVATION_LIMIT`
- pass77 old repairs: `REPAIR_ON_NEW_EVIDENCE_ONLY`
- ETF rotation: `RETIRED_UNDER_CURRENT_EVIDENCE`

## New Family Diagnostics

R30 pre-registered six new local/pass77 research families before evaluation. Five ended `NO_VERIFIABLE_STRATEGY_UNDER_CURRENT_EVIDENCE`. One line, `liquidity_constrained_reversal`, passed strict local prequalification:

- train spread: `0.006455`
- validation spread: `0.037909`
- test spread: `0.012947`
- validation IC: `0.079738`
- test IC: `0.05352`
- `test_result_used_for_parameter_selection=false`
- `strategy_candidate_available=false`

Final board counts:

- `LOCAL_RESEARCH_PROBE_ELIGIBLE`: `1`
- `NO_VERIFIABLE_STRATEGY_UNDER_CURRENT_EVIDENCE`: `5`
- `DO_NOT_RETRY_UNTIL_NEW_SOURCE`: `1`
- `OBSERVATION_ONLY`: `1`
- `REPAIR_ON_NEW_EVIDENCE_ONLY`: `1`
- `RETIRED_UNDER_CURRENT_EVIDENCE`: `1`

## Validation

- py_compile PASS
- focused pytest PASS: `8 passed`
- JSON parse PASS
- CSV parse PASS
- agent_safety_check PASS
- git diff --check PASS
- push verification PASS

## Boundary

Research-only boundary passed. No actionable output, recommendation/advice, ticket, candidate promotion, readiness/product route, daily signal, broker/order/paper/live/auto path, active registry/schema change, secret output, full-frame wide3068, or test-result parameter selection.
