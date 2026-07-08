# WINDOWS_WSL2_TARGETED_STRATEGY_REPAIR_AND_PROBE_R25_20260708 result summary

Recorded: 2026-07-09 Asia/Shanghai

## Verdict

Status: `ACCEPTED_RESEARCH_ONLY_NO_PROBE_ELIGIBLE`

R25 completed as a targeted research-only repair and probe sprint after R24. It used accepted R24 evidence as the immediate baseline, did not use unaccepted R23 outputs, did not introduce new strategy families, and did not rerun broad grids.

## Accepted source state

| repo | branch | commit | tree | status |
| --- | --- | --- | --- | --- |
| A_Share_Monitor | `codex/task-packet-r25-targeted-strategy-repair-and-probe-20260708` | `fe0b7a8a7ff7c0afcb5b2952cf8cfc123a8e8647` | `a783667aa25c8732eb64926ae6ad325fecb49446` | `COMPLETED_RESEARCH_ONLY_NO_PROBE_ELIGIBLE` |
| strategy_work | `main` | `83192e737ae929eb00ee795f606bec4cc3eef17c` | `5e67f90109f99d1de5e1b6d0220edcf101127e61` | `CODEX_ACCEPTANCE_R25_FINAL_SYNC_RESEARCH_ONLY_NO_PROBE_ELIGIBLE` |

## Evidence basis

R25 used accepted R24 artifacts only. Accepted C1/R21/R22 materialized rows remained lineage evidence behind R24. Unaccepted R23 output was explicitly not used as evidence.

## Completed research

- A-share pass77 repair experiments were run only on the five accepted fixed features: `peg_proxy`, `funds_flow_proxy_score`, `hot_money_proxy_score`, `amount_z20`, and `turnover_z20`.
- ETF diagnostics were run only on the three fixed regime-on variants: `turnover_throttled_regime_on`, `defensive_fallback_regime_on`, and `slower_rebalance_regime_on`.
- Final R25 strategy decision board was produced.

## A-share results

- Repair experiment rows: 26.
- `REPAIRED_RESEARCH_SIGNAL=16`.
- `STILL_DIVERGENT=9`.
- `REVERSE_ONLY=1`.
- Final A-share board: `peg_proxy` remains `CONTINUE_RESEARCH`; the other four pass77 features are `REPAIR_AGAIN_ON_NEW_DATA_ONLY`.

## ETF results

- Fixed regime-on variants tested: 3.
- `RETIRE_ETF_ROTATION=3`.
- Final ETF board: all three ETF regime-on variants are `RETIRE`.

## Decision board counts

| decision status | count |
| --- | ---: |
| `CONTINUE_RESEARCH` | 1 |
| `REPAIR_AGAIN_ON_NEW_DATA_ONLY` | 4 |
| `RETIRE` | 3 |
| `LOCAL_RESEARCH_PROBE_ELIGIBLE` | 0 |
| `WIDE_RESEARCH_PROBE_ELIGIBLE` | 0 |
| `BENCHMARK_ONLY` | 0 |
| `DO_NOT_RETRY` | 0 |

## Probe and strategy state

`LOCAL_RESEARCH_PROBE_ELIGIBLE_COUNT=0`

`WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT=0`

`STRATEGY_CANDIDATE_AVAILABLE=false`

R25 did not create local probe eligibility, wide probe eligibility, or strategy candidate availability.

## Validation

- A_Share_Monitor CSV parse PASS.
- A_Share_Monitor JSON parse PASS.
- Boundary assertion PASS.
- R23 outputs not used PASS.
- A-share scope assertion PASS: exactly five allowed pass77 features used.
- ETF scope assertion PASS: exactly three fixed regime-on variants used.
- `test_result_used_for_parameter_selection=false` verified in A-share and ETF artifacts.
- A_Share_Monitor `git diff --check` PASS.
- A_Share_Monitor `agent_safety_check.py` PASS.
- strategy_work final sync `git diff --check` PASS.
- strategy_work restricted wording and promotion scans PASS.
- strategy_work push verification PASS.

## Boundary result

Research-only boundary preserved. No recommendation/advice, ticket, candidate promotion, readiness/product-route/registry activation, daily signal, broker/order/paper/live/auto path, raw-data migration, active schema change, full-frame wide3068, test-result parameter selection, or secret access/output occurred.

## Fixes required

`none` for R25 acceptance.

Carry-forward warnings:

- A-share direct/proxy source evidence must improve before probe eligibility can reopen.
- ETF amount/turnover rotation remains retired under current fixed regime-on diagnostics unless new accepted evidence changes the instability premise.

## Next source action

Close R25 as research-only no-probe-eligible. Later source work should require changed accepted evidence for A-share proxy quality or ETF amount/turnover instability and keep `STRATEGY_CANDIDATE_AVAILABLE=false` unless a separate accepted protocol changes it.
