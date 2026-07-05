# Handoff: A_Share_Monitor R13C

Send to `A_Share_Monitor` Codex-Dev thread `019f32bd-082d-73e2-b902-3d48b8d198ba`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /Users/rongyuxu/Desktop/A_Share_Monitor.

Task batch: DATA_STRATEGY_BATCH_R13_CHUNKED_SEARCH_20260706

Objective:
Implement and validate chunked strategy search/backtest so the already-built 3068-symbol features_daily can be consumed safely on the current 8GB machine.

Context:
R13 interim external audit accepted with warnings. features_daily is built and validated: 6,262,517 rows, 3068 symbols, 183 columns, 35 chunks. Strategy run is blocked because current StrategySearch.run() materializes full daily/features_daily into pandas.

Tasks:

1. A-R13C-1 / StrategySearch memory blocker confirmation
   - Confirm whether StrategySearch.run() calls store.read_table("features_daily") and materializes the whole table.
   - Output row count, column count, date range, symbol count, estimated memory footprint.
   - Add a guard: if features_daily exceeds safe threshold and chunked mode is not enabled, return/raise BLOCKED_FULL_FRAME_STRATEGY_SEARCH_UNSAFE before execution.
   - Do not run full-frame wide backtest on the 8GB machine.

2. A-R13C-2 / Chunked feature reader
   - Support reading features_daily by date range and candidate-required columns.
   - Produce chunk_plan.json, chunk_inventory.csv, chunk_reader_validation.md.
   - Include chunk size, date windows, warmup window, train/validation/test coverage, row count, symbol count, date range, missingness summary.
   - Do not read future windows to calculate current-window signals.
   - Preserve synthetic_data=false checks.

3. A-R13C-3 / Chunked backtest state model
   - Add chunked execution mode or wrapper for backtest engine.
   - Preserve state across chunks: cash, positions, last prices, realized/unrealized PnL, transaction costs, portfolio value history, risk/exposure state, pending orders if applicable.
   - Warmup rows are signal-only and must not enter trading results.
   - Split boundaries must not be broken by chunk boundaries.
   - Produce chunked_backtest_design.md and chunked_state_schema.json plus focused tests.

4. A-R13C-4 / Full-frame vs chunked equivalence test on small cache
   - Use 50-symbol clean cache or data/cache_mini_200, not 3068-symbol as first validation.
   - Run same config full-frame and chunked.
   - Compare total return, Sharpe, max drawdown, trade count, orders count, positions count, train/validation/test metrics, cost stress, survivor bias, overfit/parameter instability, final label/rejection reasons.
   - Output chunked_equivalence_report.md, chunked_vs_full_metrics_diff.csv, chunked_equivalence_tests.py or equivalent tests.
   - If differences exist, explain cause and whether research conclusion changes.

5. A-R13C-5 / Wide3068 bare_minimum chunked dry run
   - Preconditions: A-R13C-1 through A-R13C-4 pass; features_daily exists and validation passes; chunked mode enabled; full-frame unsafe guard active.
   - Run: python -m qta research discover --config /Users/rongyuxu/Desktop/strategy_work/configs/bare_minimum_r13_wide3068.yaml --chunked
   - If CLI lacks --chunked, implement an equivalent switch/command first.
   - Output run id, run dir, chunk plan, memory telemetry, leaderboard, candidate registry, metrics by split, rejection reasons, data_quality/survivor_bias/cost_stress/overfit statuses, and confirmation full features_daily was not loaded.
   - If unsafe, return BLOCKED_CHUNKED_BARE_MINIMUM_MEMORY_UNSAFE.

6. A-R13C-6 / Conditional wide3068 low_vol_quality chunked rerun
   - Only if bare_minimum test Sharpe > 0, data quality not FAIL, and chunked equivalence is proven.
   - Run: python -m qta research discover --config /Users/rongyuxu/Desktop/strategy_work/configs/lowvol_quality_focused_r13_wide3068.yaml --chunked
   - If preconditions fail, output SKIPPED_LOWVOL_QUALITY_WIDE_RERUN_PRECONDITION_NOT_MET.

Required final output:
CODEX_ACCEPTANCE / DATA_REPORT / STRATEGY_REPORT with commit, changed files, validation, artifacts, memory telemetry, and boundary statement.

Boundary:
Research-only. No recommendation/advice, PENDING_HUMAN_REVIEW, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, .env access, key output, or secret handling.
No raw/local_market DB write, network ingest, schema migration, bulk ingest, readiness change, registry activation, provider persistence, or production route change.
```
