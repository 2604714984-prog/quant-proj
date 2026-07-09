# WINDOWS_WSL2_TARGETED_STRATEGY_REPAIR_AND_PROBE_R25_20260708

Recorded: 2026-07-09 Asia/Shanghai

## Purpose

Run a short, targeted, research-only strategy repair sprint after R24. R25 continues strategy research itself; it must not reopen controller/gate cleanup, expand process work, create process-only reports, rerun broad grids, introduce new strategy families, or repeat R19/R20/R24 grids.

## Accepted baseline

R24 compressed the current active strategy work into two live research lines and one final decision board:

- A-share pass77: one `CONTINUE_RESEARCH` line and four `REPAIR_FEATURE` lines.
- ETF amount/turnover rotation: five `REGIME_DEPENDENT_ONLY` lines.
- Final state: `LOCAL_PROBE_ELIGIBLE=0`, `WIDE_PROBE_ELIGIBLE=0`, `STRATEGY_CANDIDATE_AVAILABLE=false`.

R25 must use accepted R24 evidence only as its immediate starting point. It may use accepted C1/R21/R22 materialized rows as R24 input lineage, but it must not use unaccepted R23 output as evidence.

## Goal

Repair or retire the R24 surviving strategy lines:

1. A-share pass77 fixed features.
2. ETF amount/turnover regime-dependent rotation.
3. Final strategy decision board with hard keep / benchmark / retire outcomes.

## A-share pass77 scope

Use only these five features:

- `peg_proxy`
- `funds_flow_proxy_score`
- `hot_money_proxy_score`
- `amount_z20`
- `turnover_z20`

R24 status:

- `peg_proxy`: `CONTINUE_RESEARCH`
- `funds_flow_proxy_score`: `REPAIR_FEATURE`
- `hot_money_proxy_score`: `REPAIR_FEATURE`
- `amount_z20`: `REPAIR_FEATURE`
- `turnover_z20`: `REPAIR_FEATURE`

Required fixed repair experiments:

- source proxy repair
- date-neutralized repair
- low-turnover filter
- rank residualized repair
- regime-guarded repair
- reverse-signal research for `peg_proxy` only as failure analysis

Allowed A-share output labels:

- `REPAIRED_RESEARCH_SIGNAL`
- `STILL_DIVERGENT`
- `REVERSE_ONLY`
- `RETIRE_FEATURE`

Required A-share artifacts:

- `reports/workspace_dispatch/a_share_r25_repair_feature_experiment_results.csv`
- `reports/workspace_dispatch/a_share_r25_pass77_repair_decision_board.csv`
- `reports/workspace_dispatch/a_share_r25_probe_or_retire_memo.md`

## ETF scope

Use only R24 ETF amount/turnover evidence and accepted C1/R21/R22 materialized ETF row lineage. Treat ETF rotation as regime-dependent research only, not as an always-on rotation strategy.

Do not rerun R19/R20/R24 broad grids.

Test only these fixed ETF strategies:

- `turnover_throttled_regime_on`
- `defensive_fallback_regime_on`
- `slower_rebalance_regime_on`

Allowed predefined regime filters:

- `ETF_CONTEXT_NEUTRAL`
- `ETF_CONTEXT_RISK_ON`
- `ETF_CONTEXT_RISK_OFF`
- drawdown-safe period
- liquidity-high bucket

Required ETF diagnostics:

- walk-forward by regime
- cost stress
- drawdown stress
- turnover stress

Allowed ETF output labels:

- `REGIME_RESEARCH_CONTINUE`
- `BENCHMARK_ONLY`
- `RETIRE_ETF_ROTATION`

Required ETF artifacts:

- `reports/workspace_dispatch/etf_r25_regime_dependent_rotation_results.csv`
- `reports/workspace_dispatch/etf_r25_regime_walkforward_stress.csv`
- `reports/workspace_dispatch/etf_r25_keep_benchmark_retire_board.csv`

## Final decision board

Produce one final R25 strategy decision board with these columns:

- `strategy_line`
- `input_evidence`
- `r25_result`
- `local_probe_eligible`
- `wide_probe_eligible`
- `candidate_available`
- `next_action`

Allowed final labels:

- `LOCAL_RESEARCH_PROBE_ELIGIBLE`
- `WIDE_RESEARCH_PROBE_ELIGIBLE`
- `CONTINUE_RESEARCH`
- `BENCHMARK_ONLY`
- `REPAIR_AGAIN_ON_NEW_DATA_ONLY`
- `RETIRE`
- `DO_NOT_RETRY`

Required final artifacts:

- `reports/workspace_dispatch/r25_final_strategy_decision_board.csv`
- `reports/workspace_dispatch/r25_final_strategy_research_memo.md`

## Probe semantics

`LOCAL_RESEARCH_PROBE_ELIGIBLE` and `WIDE_RESEARCH_PROBE_ELIGIBLE` are research labels only. They are not recommendation, ticket, candidate, readiness, product-route, daily-signal, or trading evidence.

`STRATEGY_CANDIDATE_AVAILABLE` remains false unless a separate candidate protocol is explicitly authorized later.

## Hard boundaries

Research-only. Hard stops remain:

- secret / credential / key / token / auth / `.env` access or output
- broker / order / paper / live / auto execution or daily signal push
- product route / readiness / active registry / production adapter activation
- actionable investment advice, ticket claim, or candidate promotion
- test-result parameter selection
- non-public, paywalled, auth-required, or anti-abuse-bypassing provider access
- full-frame wide3068 strategy search

## Validation expected

- JSON parse PASS for JSON artifacts if generated.
- CSV parse PASS for required CSV artifacts.
- `git diff --check` PASS.
- Existing safety/overclaim scan PASS.
- Boundary assertion PASS.
- Focused tests / `py_compile` if code changes.

## Callback envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_TARGETED_STRATEGY_REPAIR_AND_PROBE_R25_20260708
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
A_SHARE_RESULTS:
ETF_RESULTS:
FINAL_DECISION_BOARD_COUNTS:
LOCAL_RESEARCH_PROBE_ELIGIBLE_COUNT:
WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT:
STRATEGY_CANDIDATE_AVAILABLE:
BOUNDARY_RESULT:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
