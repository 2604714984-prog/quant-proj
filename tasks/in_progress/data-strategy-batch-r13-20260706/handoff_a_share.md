# Handoff: A_Share_Monitor R13

Send to `A_Share_Monitor` Codex-Dev thread `019f32bd-082d-73e2-b902-3d48b8d198ba`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /Users/rongyuxu/Desktop/A_Share_Monitor.

Task batch: DATA_STRATEGY_BATCH_R13_20260706

Objective:
Build features_daily safely for the cleaned 3068-symbol A-share data/cache, then rerun research-only low_vol_quality diagnostics on the wider cross-section.

Critical hard rule:
Do not run full-cache FeatureStore.build() in a way that returns one full in-memory DataFrame over the 3068-symbol data/cache.
Do not let StrategySearch.run() auto-fallback to full in-memory FeatureStore.build() because features_daily is missing or empty.
Before any research discover run, features_daily must exist and pass coverage/leakage validation.

Tasks:

1. A-R13-1 / 3068-symbol cache preflight inventory
   - Work only read-only.
   - Inspect /Users/rongyuxu/Desktop/A_Share_Monitor/data/cache.
   - Report whether daily, daily_basic, adj_factor, stk_limit, suspend_d, index_daily, and features_daily exist.
   - For each table, report row count, symbol count, date range.
   - Check daily duplicate ts_code/trade_date rows.
   - Check whether features_daily exists, whether it is empty, and whether it covers the main daily date/symbol surface.
   - Compare data/cache with data/cache_expanded and the 50-symbol clean cache at a high level.
   - Return BLOCKED_FEATURES_DAILY_PREFLIGHT if duplicate rows, missing key inputs, path mismatch, or uncontrollable memory risk appears.

2. A-R13-2 / safe features_daily build via chunked path only
   - Run only after A-R13-1 passes.
   - Use:
     cd /Users/rongyuxu/Desktop/A_Share_Monitor
     python -m qta features build
     or an equivalent FeatureStore.build_to_store() path.
   - Do not use full-cache returned-DataFrame FeatureStore.build().
   - Record exact command, start/end parameters if any, output table, row count, chunk count, output path, columns, min/max trade_date, unique symbols, and peak memory or OS-level process observation.
   - If failed, output BLOCKED_FEATURES_DAILY_BUILD_FAILED with failure stage, last successful chunk, exception, and chunk-size recommendation.

3. A-R13-3 / features_daily coverage and leakage validation
   - Do not run strategy yet.
   - Check duplicate ts_code/trade_date count.
   - Compare features_daily row count with daily row count and report coverage ratio.
   - Validate key feature fields by actual project column names: returns, momentum, volatility, liquidity, adjusted price fields, ST/suspend/limit flags, daily_basic-derived fields, fundamental lag fields.
   - Check no-future fundamental usage.
   - Report missingness by date bucket and symbol bucket.
   - Report actual backtest-usable symbol count.
   - Check all-null factor rows and post-split/test leakage risk.
   - Confirm StrategySearch can read features_daily from store and will not auto-trigger FeatureStore.build() fallback.
   - If insufficient, output BLOCKED_FEATURES_DAILY_COVERAGE_INSUFFICIENT.

4. A-R13-4 / run bare_minimum on 3068-symbol cache
   - Only after A-R13-2/A-R13-3 pass and strategy_work R13 config exists.
   - Run:
     cd /Users/rongyuxu/Desktop/A_Share_Monitor
     python -m qta research discover --config /Users/rongyuxu/Desktop/strategy_work/configs/bare_minimum_r13_wide3068.yaml
   - Stop if features_daily is missing or empty. Do not let the strategy runner auto-build it in memory.
   - Output run id, run dir, data snapshot, manifest, leaderboard, candidate registry, train/validation/test metrics, data_quality/survivor_bias/cost_stress/overfit/fill_realism statuses, rejection/research-only reasons, and whether features_daily was read from store.

5. A-R13-5 / conditional lowvol_quality_focused wide rerun
   - Only if A-R13-4 test Sharpe > 0 and data quality does not fail.
   - Run:
     cd /Users/rongyuxu/Desktop/A_Share_Monitor
     python -m qta research discover --config /Users/rongyuxu/Desktop/strategy_work/configs/lowvol_quality_focused_r13_wide3068.yaml
   - Output all candidate rows, leaderboard, candidate registry, trade-count weakness, parameter instability, cost-stress result, survivor-bias status, whether wider sample changes the 50/100/200-symbol conclusion, and whether apparent improvement is caused by gate relaxation rather than genuine strategy improvement.

Required final output:
CODEX_ACCEPTANCE / DATA_REPORT / STRATEGY_REPORT with commit, changed files, validation, artifacts, and boundary statement.

Boundary:
Research-only. No recommendation/advice, ticket, PENDING_HUMAN_REVIEW, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, .env access, key output, or secret handling.
No raw/local_market DB write, network ingest, schema migration, bulk ingest, readiness change, registry activation, provider persistence, or production route change without separate task-level HG-EXEC evidence and transcript.
```
