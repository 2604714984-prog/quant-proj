# Windows WSL2 Migration Source Data Inventory

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-06
Source machine: old 8GB Mac

## Scope

This is a shell-level source-machine inventory for migration planning. No large Parquet/DuckDB files were loaded into pandas. No database rebuild, provider/network ingest, raw-data migration, readiness change, registry activation, or wide strategy run was performed.

## A_Share_Monitor Data Paths

| Path | Exists | Size | features_daily present | local DB present | Notes |
|---|---:|---:|---:|---:|---|
| `/Users/rongyuxu/Desktop/A_Share_Monitor/data/cache` | yes | `6.5G` | yes: `features_daily.metadata.json`, `features_daily.parquet` | no DuckDB/SQLite found at maxdepth 2 | primary wide cache; do not copy by default |
| `/Users/rongyuxu/Desktop/A_Share_Monitor/data/cache_mini_200` | yes | `626M` | yes: `features_daily.metadata.json`, `features_daily.parquet` | no DuckDB/SQLite found at maxdepth 2 | smaller validation cache |
| `/Users/rongyuxu/Desktop/A_Share_Monitor/data/phase3_real_small_cache_20260630_50` | yes | `92M` | yes: `features_daily.metadata.json`, `features_daily_smoke.metadata.json`, `features_daily.parquet`, `features_daily_smoke.parquet` | no DuckDB/SQLite found at maxdepth 2 | 50-symbol small cache |
| `/Users/rongyuxu/Desktop/A_Share_Monitor/data/local_market` | yes | `2.6G` | no features_daily found | yes: `a_share_market.duckdb` | source local-market DB; do not migrate raw DB by default |
| `/Users/rongyuxu/Desktop/A_Share_Monitor/data/cache_expanded` | yes | `557M` | no features_daily found at maxdepth 2 | no DuckDB/SQLite found at maxdepth 2 | expanded cache evidence only |

## Migration Interpretation

- The new Windows + WSL2 machine should clone repos from GitHub first.
- Large local data should not be packaged or copied unless the user explicitly opens a later audited raw-data migration stage.
- Data should be rebuilt or validated as a fresh WSL2 snapshot on the new machine.
- The existing source-machine `features_daily` is useful evidence that the R13 feature build succeeded, but it is not a product-read route, data-clear promotion, ticket eligibility, or production readiness.
- The active blocker is strategy execution memory/model behavior: current or legacy full-frame `StrategySearch.run()` paths must not be used for wide3068. Chunked StrategySearch/backtest must be used or implemented before wide reruns.

## DS / Strategy Handoff Files Already Present

The following local handoff files were observed and should be inspected after clone/rebuild planning:

- `/Users/rongyuxu/Desktop/strategy_work/MIGRATION.md`
- `/Users/rongyuxu/Desktop/strategy_work/reports/planning/MIGRATION_GUIDE.md`
- `/Users/rongyuxu/Desktop/market_data/reports/agent_handoff/database_maintenance_handoff.md`
- `/Users/rongyuxu/Desktop/market_data/reports/agent_handoff/deepseek_db_p0_p4_final_handoff.md`
- `/Users/rongyuxu/Desktop/market_data/reports/deepseek_db/us_db_2_migration_plan.md`

## Boundary

This inventory does not authorize recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket emission, eligibility candidates, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto behavior, provider/network ingest, DB/schema migration, readiness change, registry activation, provider-data persistence, raw-data migration, `.env` reads, key output, or secret handling.
