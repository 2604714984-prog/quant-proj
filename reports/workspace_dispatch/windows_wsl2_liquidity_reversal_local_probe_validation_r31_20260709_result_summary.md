# R31 Liquidity Reversal Validation Result Summary

Batch: `WINDOWS_WSL2_LIQUIDITY_REVERSAL_LOCAL_PROBE_VALIDATION_R31_20260709`

Status: `COMPLETED_RESEARCH_ONLY_REJECTED_BY_LOCAL_PROBE_DIAGNOSTICS`

## Source Preservation

A_Share_Monitor completed and pushed:

- branch: `codex/r31-liquidity-reversal-validation-20260709`
- commit: `5ccc4c93306939df47bd22a1ae8f5d8c450bba7a`
- tree: `06f290fce82466c351a9b368f2c8b2bed53bb7f6`

strategy_work final sync completed and pushed:

- branch: `main`
- commit: `93e3cc00c181c6aded887b152246fdd50527ef7a`
- tree: `d6ad37d4779bd36a5d3e3e2de2e66e4c5562de7e`

## Result

R31 treated R30 as hypothesis-generation evidence and revalidated `liquidity_constrained_reversal` without test outcome selection.

Validation-only prequalification passed:

- train spread: `0.006455`
- validation spread: `0.037909`
- validation IC: `0.079738`
- test result used for selection: `false`

Bounded local-probe diagnostics failed:

- validation top-decile mean 20d: `0.025775`
- validation bottom-decile mean 20d: `0.030387`
- validation long-short mean 20d: `-0.004612`
- validation long-short Sharpe proxy: `-0.131702`

Final label:

`REJECTED_BY_LOCAL_PROBE_DIAGNOSTICS`

## Counts

- `local_research_probe_eligible_count=0`
- `strategy_candidate_available=false`

## Validation

- py_compile PASS
- focused pytest PASS: `8 passed`
- JSON parse PASS
- CSV parse PASS
- agent_safety_check PASS
- git diff --check PASS
- push verification PASS

## Boundary

Research-only boundary passed. No recommendation/advice, ticket, candidate promotion, readiness/product route, daily signal, broker/order/paper/live/auto path, active registry/schema change, secret output, full-frame wide3068, or test-result parameter selection.
