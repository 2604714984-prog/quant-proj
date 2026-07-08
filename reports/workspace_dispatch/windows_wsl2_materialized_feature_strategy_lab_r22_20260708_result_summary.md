# WINDOWS_WSL2_MATERIALIZED_FEATURE_STRATEGY_LAB_R22_20260708 result summary

Recorded: 2026-07-08 Asia/Shanghai

## Verdict

Status: `ACCEPTED_RESEARCH_ONLY_WITH_NO_PROBE_ELIGIBLE`

R22 completed as an ordinary research-only materialized-feature strategy diagnostics batch. It used C1/R21 row evidence for ETF, pass77 A-share, and global/news/macro context diagnostics. The batch improved failure memory and validation/test divergence evidence, but no local or wide research probe became eligible.

## Accepted source state

| repo | branch | commit | tree | status |
| --- | --- | --- | --- | --- |
| A_Share_Monitor | `codex/task-packet-r20-v2-20260708` | `9a450019a07f55534bb2eddedd401b56825f6683` | `a92c65a551a40b844eeeafd8e0cd95884f7e72e5` | `COMPLETED_RESEARCH_ONLY_WITH_NO_PROBE_ELIGIBLE` |
| market_data | `main` | `9e097fe959bed433fae5dfae75493dba7b08f10e` | `5797f1c6d3956c17692e336b53636342229173c3` | `ACCEPTED_RESEARCH_ONLY_WITH_VALIDATION_PASS` |
| strategy_work | `main` | `bb6a0d953e1aa5dfeb80f7303cf54c80ee2cd00e` | `cf6edf4e69ee923e110dd6f6695f15ecb802c540` | `CODEX_ACCEPTANCE_SW_R22_FINAL_SYNC_RESEARCH_ONLY_NO_PROBE_ELIGIBLE` |

## Materialized data status

| lane | evidence |
| --- | --- |
| ETF amount/turnover | 32,482 rows |
| ETF NAV | 340 rows |
| ETF premium | 340 rows |
| pass77 A-share feature rows | 136,767 rows |
| global/news/macro context | 100 rows |
| evidence freeze/import/failure memory | PASS |

## Diagnostics status

- ETF amount/turnover quality audit completed.
- R19/R20 ETF 44 rows were reinterpreted with materialized amount/turnover context.
- ETF liquidity-aware, turnover-throttled, and defensive drawdown diagnostics were executed.
- pass77 feature quality audit completed.
- pass77 IC/decile/stability diagnostics produced 15 rows.
- validation/test divergence attribution produced 5 rows.
- opposite/neutralized, regime-conditioned, fixed pair/triple, walk-forward, and bootstrap diagnostics were executed.
- global/news/macro context was used only for context and divergence attribution; direct signal use remained false.
- strategy prequalification board produced no eligible local or wide probe.

## Probe and strategy state

`local_research_probe_eligible_count=0`

`wide_research_probe_eligible_count=0`

`WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT=0`

`STRATEGY_CANDIDATE_AVAILABLE=false`

R22 did not open a local or wide research probe and did not create strategy candidate availability.

## Validation

- A_Share_Monitor: `py_compile` PASS; focused pytest PASS with 4 passed; JSON parse PASS; `agent_safety_check.py` PASS; `git diff --check` PASS; boundary scans PASS.
- market_data: focused pytest PASS with 6 passed; JSON parse PASS; `git diff --check` PASS; overclaim regression PASS.
- strategy_work: final sync `git diff --check` PASS; restricted wording and promotion scans PASS; push verification PASS.
- Controller dispatch branch was preserved and downstream source commits were pushed.

## Boundary result

Research-only boundary preserved. No actionable output, recommendation/advice, ticket, candidate promotion, readiness/product-route/registry activation, daily signal, broker/order/paper/live/auto path, raw-data migration into controller, active schema change, full-frame wide3068, direct news/macro signal use, test-result parameter selection, non-public/auth-required provider access, or secret output occurred.

## Fixes required

`none`

Source note: A_Share_Monitor reported an unrelated unstaged `qta/backtest/engine.py` modification outside the R22 commit.

## Next source action

Update failure memory with the R22 no-probe result. A follow-up research batch should target why materialized liquidity and pass77 features still fail prequalification, with emphasis on validation/test divergence, scope limits, partial NAV/premium coverage, and non-promotional feature transformations.
