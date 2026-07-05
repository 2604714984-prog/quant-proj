# DATA_STRATEGY_BATCH_R13_20260706 Interim External-Audit Packet

Project: quant-proj
Prepared: 2026-07-06
Role: Quant-Dispatcher
Packet type: user-requested interim external audit

## Controller Repo

- `https://github.com/2604714984-prog/quant-proj`
- branch: `main`
- packet file: `reports/agent_handoff/data_strategy_batch_r13_interim_external_audit_packet_20260706.md`
- result summary: `reports/workspace_dispatch/data_strategy_batch_r13_20260706_interim_result_summary.md`

## Source Anchors

| Repository | Branch | Relevant ref |
|---|---|---:|
| `A_Share_Monitor` | `codex/harden-a-share-research-pipeline` | `b5928fb` |
| `strategy_work` | `main` | R13 config-prep commit `9424c1b`; current pushed head observed `451812b` |
| `market_data` | `main` / fixed worktree pending | no R13 acceptance yet |

## Review Request

Please review this interim R13 state and return:

1. `VERDICT`
2. `EXTERNAL_AUDIT_TRIGGER_OPEN`: yes/no
3. `FIXES_REQUIRED`
4. `NEXT_DATA_STRATEGY_BATCH`
5. `MEMORY_ASSESSMENT`

## What Happened

R13 objective was to build `features_daily` safely for the cleaned 3068-symbol A-share `data/cache`, then rerun `low_vol_quality` on the wider cross-section.

Completed:

- A-share built `features_daily` safely via chunked store path.
- A-share validated row/key coverage.
- strategy_work prepared R13 wide-cache research configs.

Blocked:

- A-share did not run `bare_minimum_r13_wide3068`.
- A-share did not run `lowvol_quality_focused_r13_wide3068`.
- Blocker: current `StrategySearch.run()` still loads full `daily` and `features_daily` into pandas DataFrames before backtest/evaluation.

## Important Evidence

From A-share R13 acceptance:

- `features_daily` rows: `6,262,517`
- symbols: `3068`
- columns: `183`
- chunks: `35`
- duplicate feature keys: `0`
- feature rows match daily rows: true
- build max RSS: `5,156,962,304` bytes
- build peak memory footprint: `8,448,727,680` bytes
- current machine physical memory: `8 GB`

The build succeeded only because it used chunked `FeatureStore.build_to_store()` / `python -m qta features build --max-output-dates-per-chunk 60`.

The strategy run was intentionally not executed because it would require all features to be resident in memory.

## Current Interpretation

R13 should be treated as:

```text
ACCEPTED_FEATURE_BUILD_VALIDATION_WITH_STRATEGY_BLOCKED
```

The practical blocker is no longer missing `features_daily`; it is the in-memory strategy-search/backtest architecture.

Estimated memory if current full-pandas strategy path is kept:

- 8 GB: unsafe for wide strategy run.
- 16 GB: likely still swaps.
- 32 GB: plausible minimum for bare-minimum wide run.
- 64 GB: more realistic for focused run with walk-forward/robustness/candidate variants.

Preferred next work should be implementing chunked strategy search/backtest rather than forcing the current path on larger hardware.

## Suggested Next Batch Shape

Please confirm or revise this proposed next batch:

```text
DATA_STRATEGY_BATCH_R14_20260706

Primary objective:
Implement and validate chunked strategy search/backtest for 3068-symbol A-share wide-cache diagnostics.

Tasks:

1. A_Share_Monitor:
   Implement bounded feature loading in StrategySearch.
   Read by split/date window and candidate-required columns instead of full features_daily.
   Ensure missing features_daily never triggers full in-memory FeatureStore.build().

2. A_Share_Monitor:
   Implement or adapt DailyBacktestEngine flow so each candidate/split can run with bounded feature frames and persisted intermediate outputs.
   Preserve exact metrics semantics where possible.

3. A_Share_Monitor:
   Add tests proving wide configs do not call full FeatureStore.build() and do not load all features_daily at once.

4. A_Share_Monitor:
   Run bare_minimum_r13_wide3068 only after bounded-search validation.
   If test Sharpe > 0 and data quality does not fail, run focused lowvol_quality wide config.

5. strategy_work:
   Archive R13/R14 run artifacts only after A-share source acceptance exists.

6. market_data:
   Add/finish derived-feature evidence boundary note as lightweight non-blocking evidence note if still needed.
```

## Boundary

No recommendation/advice, ticket, `PENDING_HUMAN_REVIEW`, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, `.env` access, key output, or secret handling is authorized.

DB writes, network ingest, schema migration, bulk ingest, readiness changes, and registry activation remain gated by separate task-level HG-EXEC evidence and transcript.

## Ready-To-Send Prompt

```text
Project: quant-proj
Controller repo: https://github.com/2604714984-prog/quant-proj
Packet entry: reports/agent_handoff/data_strategy_batch_r13_interim_external_audit_packet_20260706.md
Result summary: reports/workspace_dispatch/data_strategy_batch_r13_20260706_interim_result_summary.md

Please review DATA_STRATEGY_BATCH_R13_20260706 interim state and return:
1. VERDICT
2. EXTERNAL_AUDIT_TRIGGER_OPEN yes/no
3. FIXES_REQUIRED
4. NEXT_DATA_STRATEGY_BATCH
5. MEMORY_ASSESSMENT

Key state:
A-share built and validated 3068-symbol features_daily safely through chunked path: 6,262,517 rows, 3068 symbols, 183 columns, 35 chunks, duplicate keys 0. Build max RSS was about 5.16 GB and peak footprint about 8.45 GB on an 8 GB machine.

Strategy diagnostics were intentionally not run because current StrategySearch.run() still reads full daily and full features_daily into pandas DataFrames. R13 status is ACCEPTED_FEATURE_BUILD_VALIDATION_WITH_STRATEGY_BLOCKED / BLOCKED_STRATEGY_SEARCH_REQUIRES_FULL_FEATURES_IN_MEMORY.

Please focus on whether the next batch should implement chunked strategy search/backtest before any 3068-symbol research discover run. Do not turn this into controller/gate architecture review.

Boundary:
No recommendation/advice, ticket/PENDING_HUMAN_REVIEW, eligibility candidate, data-clear promotion, product route, production readiness, broker/order/paper/live/auto, raw-data migration, or secret handling is authorized.
```
