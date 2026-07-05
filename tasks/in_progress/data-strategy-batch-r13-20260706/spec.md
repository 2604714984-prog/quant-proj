# DATA_STRATEGY_BATCH_R13_20260706 Spec

## Objective

Build `features_daily` safely for the cleaned 3068-symbol A-share `data/cache`, then rerun research-only strategy diagnostics on the wider cross-section.

## Assigned Tasks

| ID | Owner | Task | Dependency |
|---|---|---|---|
| `A-R13-1` | `A_Share_Monitor` | 3068-symbol cache preflight inventory | none |
| `A-R13-2` | `A_Share_Monitor` | safe `features_daily` build via chunked path only | `A-R13-1` PASS |
| `A-R13-3` | `A_Share_Monitor` | `features_daily` coverage/leakage validation | `A-R13-2` PASS |
| `SW-R13-1` | `strategy_work` | prepare R13 wide-cache configs | can start now |
| `A-R13-4` | `A_Share_Monitor` | run wide `bare_minimum` | `A-R13-3` PASS and `SW-R13-1` available |
| `A-R13-5` | `A_Share_Monitor` | conditional wide `lowvol_quality_focused` rerun | `A-R13-4` positive test Sharpe and data quality not FAIL |
| `SW-R13-2` | `strategy_work` | archive run artifacts | after A-share run artifacts exist |
| `MD-R13-1` | `market_data` | derived-feature evidence boundary note | can start now |
| `SW-R13-3` | `strategy_work` | final memo sync | after A-share and market_data source acceptances |

## Boundary

R13 is research-only. It does not authorize recommendation/advice, ticket, `PENDING_HUMAN_REVIEW`, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, `.env` access, key output, or secret handling.

No raw/local_market DB write, network ingest, schema migration, bulk ingest, readiness change, registry activation, provider persistence, or production route change is allowed without separate task-level HG-EXEC evidence and transcript.
