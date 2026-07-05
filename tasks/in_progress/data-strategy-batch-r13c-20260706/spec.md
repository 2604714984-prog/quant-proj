# DATA_STRATEGY_BATCH_R13_CHUNKED_SEARCH_20260706 Spec

## Objective

Implement and validate chunked strategy search/backtest for 3068-symbol A-share wide-cache diagnostics.

## Tasks

| ID | Owner | Task | Dependency |
|---|---|---|---|
| `A-R13C-1` | `A_Share_Monitor` | Confirm/quantify full-frame memory blocker and add unsafe full-frame guard. | none |
| `A-R13C-2` | `A_Share_Monitor` | Implement chunked feature reader for strategy search. | `A-R13C-1` |
| `A-R13C-3` | `A_Share_Monitor` | Implement/adapt chunked backtest state model. | `A-R13C-2` |
| `A-R13C-4` | `A_Share_Monitor` | Full-frame vs chunked equivalence test on small cache. | `A-R13C-3` |
| `A-R13C-5` | `A_Share_Monitor` | Run wide3068 `bare_minimum` chunked dry run. | `A-R13C-4` PASS |
| `A-R13C-6` | `A_Share_Monitor` | Conditional wide3068 `low_vol_quality` chunked rerun. | `A-R13C-5` positive test Sharpe and data quality not FAIL |
| `SW-R13C-1` | `strategy_work` | Chunked wide-run configs and archive plan. | can start now |
| `MD-R13C-1` | `market_data` | Derived-feature evidence boundary contract. | can start now |
| `SW-R13C-2` | `strategy_work` | Final interim-to-closeout memo sync. | after A-share and market_data acceptances |

## Required A-Share Outputs

- `chunk_plan.json`
- `chunk_inventory.csv`
- `chunk_reader_validation.md`
- `chunked_backtest_design.md`
- `chunked_state_schema.json`
- `chunked_equivalence_report.md`
- `chunked_vs_full_metrics_diff.csv`
- focused unit tests
- wide run leaderboard/candidate registry if preconditions pass

## Boundary

Research-only. Do not emit recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, `.env` access, key output, or secret handling.
