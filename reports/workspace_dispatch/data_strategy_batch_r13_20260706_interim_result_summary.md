# DATA_STRATEGY_BATCH_R13_20260706 Interim Result Summary

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-06 05:22 CST
Classification: ordinary research-only data/strategy batch
Packet type: interim external-audit request, user requested

## Current Source Results

| Target | Status | Commit | Notes |
|---|---|---:|---|
| `A_Share_Monitor` | `ACCEPTED_FEATURE_BUILD_VALIDATION_WITH_STRATEGY_BLOCKED` | `b5928fb` | `features_daily` was built/validated safely; wide strategy run blocked by current full-pandas memory path. |
| `strategy_work` | `CODEX_ACCEPTANCE_SW_R13_CONFIG_PREP_DEPENDENCY_GATED` | `9424c1b` | R13 wide-cache configs prepared; archive/final sync wait for A-share run artifacts and market_data acceptance. |
| `market_data` | not available for R13 | n/a | R13 handoff was sent, but fixed thread is still waiting on older git approval state; no R13 market_data acceptance yet. |

## A-Share R13 Result

Source acceptance:

- `/Users/rongyuxu/Desktop/A_Share_Monitor/reports/codex_dev/data_strategy_batch_r13_20260706_codex_acceptance.md`
- `/Users/rongyuxu/Desktop/A_Share_Monitor/reports/codex_dev/data_strategy_batch_r13_20260706_data_report.md`
- `/Users/rongyuxu/Desktop/A_Share_Monitor/reports/codex_dev/data_strategy_batch_r13_20260706_strategy_report.md`

Key facts:

- `features_daily` exists at `data/cache/features_daily.parquet`.
- Final feature dataset: `6,262,517` rows, `3068` symbols, `183` columns, `35` chunks.
- Feature rows match daily rows; duplicate feature keys: `0`.
- Daily-minus-feature keys: `0`; feature-minus-daily keys: `0`.
- All-null factor rows: `0`.
- Usable post-2024-07-01 symbols for key low-vol/liquidity fields: `3037`.
- Fundamental lag fields remain `MISSING_INPUT_TABLE_NO_IMPUTATION`.

Memory evidence:

- Final build command: `env -u TUSHARE_TOKEN -u TUSHARE_HTTP_URL /usr/bin/time -l python -m qta features build --max-output-dates-per-chunk 60`
- Build result: PASS.
- Final build max resident set size: `5,156,962,304` bytes.
- Final build peak memory footprint: `8,448,727,680` bytes.
- Current machine physical memory: `8 GB`.
- Current full `features_daily` stored data size: about `6.0 GB` on disk.

Strategy status:

- `A-R13-4` wide `bare_minimum` command was not run.
- `A-R13-5` focused wide run was not run.
- Block reason: current `StrategySearch.run()` reads full `daily` and full `features_daily` into pandas DataFrames before evaluation.
- A-share returned `BLOCKED_STRATEGY_SEARCH_REQUIRES_FULL_FEATURES_IN_MEMORY`.
- Required next design: chunked search by split/date window and candidate-required columns, with persisted chunk-level metrics/trades before aggregation.

## Strategy Work R13 Result

Source acceptance:

- `/Users/rongyuxu/Desktop/strategy_work/reports/planning/data_strategy_batch_r13_20260706_strategy_report.md`

Key facts:

- `configs/bare_minimum_r13_wide3068.yaml` prepared.
- `configs/lowvol_quality_focused_r13_wide3068.yaml` prepared.
- Both point to `store_root: data/cache`.
- Both set `synthetic_data_when_missing: false`.
- Both are marked research-only.
- `SW-R13-2` artifact archive is blocked until A-share run artifacts exist.
- `SW-R13-3` final memo sync is blocked until A-share and market_data source acceptances are available.

## Current Memory Assessment

The feature build can run on the current 8 GB machine, but only at the edge of available memory and only through chunked build.

The current wide backtest path should not run on this 8 GB machine because it loads the full feature table into pandas. Practical estimate:

- 8 GB: unsafe for wide `research discover`; feature build only barely fits.
- 16 GB: still likely to swap for current wide pandas strategy path.
- 32 GB: plausible minimum for bare-minimum wide run if the current full-pandas implementation is kept.
- 64 GB: more realistic for focused run with walk-forward, robustness, and several candidates.

Preferred next step is not to buy more memory first. The safer project path is to implement chunked strategy search/backtest.

## Boundary Review

R13 remains research-only and non-actionable.

- Recommendation/advice: not present
- `PENDING_HUMAN_REVIEW`: not emitted
- Ticket: not emitted
- Eligibility candidate: not emitted
- Data-clear promotion: not performed
- Product-route activation: not performed
- Production readiness: not claimed
- Broker/order/paper/live/auto: not present
- Raw/local_market DB write: not performed
- Network ingest: not performed
- Schema migration/readiness/registry activation: not performed
- `.env` or secret access: not performed

## Open Question For External Audit

Should R13 now pivot to a new implementation batch for chunked strategy search/backtest before any wide 3068-symbol `research discover` run, and should market_data `MD-R13-1` be treated as a lightweight fallback controller/source note rather than blocking the chunked-search work?
