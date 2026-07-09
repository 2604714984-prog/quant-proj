# R33 Qlib Vectorized Validation Strategy Design Result Summary

Batch: `WINDOWS_WSL2_QLIB_VECTORBT_VALIDATION_STRATEGY_DESIGN_R33_20260709`

Status: `COMPLETED_RESEARCH_ONLY_NO_PROBE_ELIGIBLE`

## Source Preservation

A_Share_Monitor completed and pushed:

- branch: `codex/r33-qlib-vectorbt-validation-strategy-design-20260709`
- commit: `a271f4d07928969c48805829d2aae314c752158c`
- tree: `529d3510244e7906687d0d22985d461974cdf5b0`

strategy_work final sync completed and pushed:

- branch: `main`
- commit: `78da95b837b1d72a8a316ea7bd0f1d1b42372abd`
- tree: `dcc6798cdeffc0117985b9ec0971138f9361447f`

## Research Outcome

R33 continued from R32 by using the qlib-ready pass77 export and R32 validation-interesting vectorized scanner rows as hypotheses only.

- input rows: `136,767`
- R32 validation-interesting hypothesis rows: `6`
- pre-registered transformation rows: `36`
- diagnostic rows: `36`

Decision label counts:

- `REJECTED_BY_BOTTOM_DECILE_DOMINANCE`: `25`
- `REJECTED_BY_VALIDATION_WEAKNESS`: `11`

No transformation reached local or wide research probe eligibility.

## Final Counts

- `local_research_probe_eligible_count=0`
- `wide_research_probe_eligible_count=0`
- `strategy_candidate_available=false`
- `test_result_used_for_selection=false`

## Validation

- py_compile PASS
- focused pytest PASS: `8 passed`
- JSON parse PASS
- agent_safety_check PASS
- git diff --check PASS
- restricted overclaim scan PASS
- push verification PASS

## Boundary

Research-only boundary passed. No recommendation/advice, ticket, candidate promotion, readiness/product route, daily signal, broker/order/paper/live/auto path, active registry/schema change, secret output, or test-result parameter selection.
