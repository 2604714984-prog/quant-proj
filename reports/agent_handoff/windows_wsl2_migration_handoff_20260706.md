# Windows + WSL2 Migration Handoff

Project: quant-proj
Prepared by: Quant-Dispatcher on old 8GB Mac
Prepared: 2026-07-06
Target machine: Windows + WSL2 Ubuntu, Core Ultra 265K + 48GB

## Project Purpose

This workspace coordinates research-only quant/data systems across A-share, US stock, shared market-data, and strategy research repositories. The current goal is to continue data-quality and strategy-candidate research while preserving strict boundaries: no recommendation/advice, no tickets, no product route, no readiness promotion, and no broker/order/paper/live/auto behavior unless a future audited stage explicitly opens such a boundary.

## Source Repositories

| Local source path | GitHub repo | Branch / HEAD at source inspection |
|---|---|---|
| `/Users/rongyuxu/Desktop/quant proj` | `2604714984-prog/quant-proj` | `main` / `9d17b8eaf1c869395f23e310a1ca887f07e5752f` |
| `/Users/rongyuxu/Desktop/A_Share_Monitor` | `2604714984-prog/A_Share_Monitor` | `codex/harden-a-share-research-pipeline` / `6bfeb816ac8bd6d38b747e30d6f44e81cc8da0bc` |
| `/Users/rongyuxu/Desktop/US_Stock_Monitor` | `2604714984-prog/US_Stock_Monitor` | `main` / `831ef21eda20ecf971bef9ab2f3487b8e96e1001`; pushed/synced with origin/main after cleanup; untracked `logs/` present locally |
| `/Users/rongyuxu/Desktop/market_data` | `2604714984-prog/market_data` | `main` / `ff24166479638b0f35e1cd7a8d0f1d01cdafb495` |
| `/Users/rongyuxu/Desktop/strategy_work` | `2604714984-prog/strategy_work` | `main` / `63c779db89b63ccb65819fe87945cd9e5cbe0c15` |

The US_Stock_Monitor Tencent-source commits are pushed to `origin/main`. Do not copy untracked `logs/` unless explicitly required.

## R13 Interim Anchor

- Tag: `data-strategy-r13-interim-external-audit-20260706`
- Tag object: `262dfc48e44363426113c8a2c1cbc41a6599cfe4`
- R13 interim controller commit: `6a3e509f15cf5b22a9bced561f1a7540df0f4b06`
- Anchor status on source machine: tag exists; commit exists and is reachable from current quant-proj HEAD.

Important controller files:

- `reports/agent_handoff/data_strategy_batch_r13_interim_external_audit_packet_20260706.md`
- `reports/workspace_dispatch/data_strategy_batch_r13_20260706_interim_result_summary.md`
- `reports/workspace_dispatch/data_strategy_batch_r13c_20260706_result_summary.md`
- `reports/workspace_dispatch/downstream_completion_callback_protocol_20260706.md`
- `reports/workspace_dispatch/simonlin1212_data_source_policy_20260706.md`

## Current Technical State

- R13 interim conclusion: `features_daily` has been built and validated.
- Active blocker: `StrategySearch.run()` / related strategy execution paths must not materialize full wide `daily` / `features_daily` pandas frames for 3068 symbols.
- A_Share_Monitor R13C commit `6bfeb816ac8bd6d38b747e30d6f44e81cc8da0bc` implemented chunked strategy search/backtest support and a full-frame fail-closed guard.
- The wide chunked `bare_minimum` run completed with `full_features_daily_loaded=false` and max RSS around `1.32 GB`, but it was rejected by research gates: `parameter_instability_fail`, test Sharpe `-0.5401334785118406`.
- Conditional low-vol-quality wide rerun was skipped: `SKIPPED_LOWVOL_QUALITY_WIDE_RERUN_PRECONDITION_NOT_MET`.

## Target Workspace Rules

- Use WSL2 Ubuntu.
- Work under `~/workspace`, not `/mnt/c`.
- Clone from GitHub first.
- Create compatibility symlinks for old absolute paths only after cloning.
- Rebuild or validate data as a new Windows WSL2 snapshot.
- Do not copy huge local data by default.
- Do not run full-frame wide3068 StrategySearch.
- Use or continue chunked StrategySearch/backtest before any wide rerun.
- Stop before provider/network ingest, DB/schema migration, readiness change, registry activation, raw-data migration, or provider-data persistence unless task-level `HG-EXEC` approval exists.

## Compatibility Symlink Plan

After cloning to `~/workspace`, create compatibility links for code that still references `/Users/rongyuxu/Desktop/...`:

```bash
sudo mkdir -p /Users/rongyuxu/Desktop
ln -sfn "$HOME/workspace/quant-proj" "/Users/rongyuxu/Desktop/quant proj"
ln -sfn "$HOME/workspace/A_Share_Monitor" "/Users/rongyuxu/Desktop/A_Share_Monitor"
ln -sfn "$HOME/workspace/US_Stock_Monitor" "/Users/rongyuxu/Desktop/US_Stock_Monitor"
ln -sfn "$HOME/workspace/market_data" "/Users/rongyuxu/Desktop/market_data"
ln -sfn "$HOME/workspace/strategy_work" "/Users/rongyuxu/Desktop/strategy_work"
```

## Existing DS / Strategy Handoffs

Inspect these after clone:

- `strategy_work/MIGRATION.md`
- `strategy_work/reports/planning/MIGRATION_GUIDE.md`
- `market_data/reports/agent_handoff/database_maintenance_handoff.md`
- `market_data/reports/agent_handoff/deepseek_db_p0_p4_final_handoff.md`
- `market_data/reports/deepseek_db/us_db_2_migration_plan.md`

Treat these as planning/evidence documents. They do not authorize raw-data migration, data-clear promotion, product-read routes, recommendations, tickets, or trading behavior.

## Boundary

This migration handoff does not authorize recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket emission, eligibility candidates, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto behavior, provider/network ingest, DB/schema migration, readiness changes, registry activation, provider-data persistence, raw-data migration into quant-proj, `.env` reads, key output, or secret handling.
