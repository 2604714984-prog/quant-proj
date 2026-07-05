# Data Source Coordination

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-05
Status: ACTIVE_DATA_SOURCE_PRIORITY

## Current Priority

The current data-source priority is to fix the evidence chain before more strategy expansion:

1. Finish the `FeatureStore.build()` memory fix so large local caches cannot be expanded into a returned in-memory DataFrame.
2. Treat the DeepSeek/Reasonix A-share data pull as local provider evidence only, not as data-clear or readiness.
3. Prioritize provider specs and evidence contracts from the attached review:
   - `simonlin1212/a-stock-data` for A-share provider, second-source, corporate-action, peer-control, announcement/news, sector/theme, and amount-scale diagnostics.
   - `simonlin1212/global-stock-data` for US metadata, Yahoo/SEC/EDGAR/XBRL, row-level crosscheck, provenance, freshness, and source-hash contracts.
4. Defer `investment-news`, `astock-peg`, and `TradingAgents-astock` until the data-source evidence chain has specs and negative tests.

## FeatureStore Fix

A_Share_Monitor source fix:

- Branch: `codex/harden-a-share-research-pipeline`
- Commit: `18c19016809210780272512b99b6dd07be074425`
- Tree: `5588665df67b0974fd1a1d0b7c66536e64cd9d55`
- Report: `/Users/rongyuxu/Desktop/A_Share_Monitor/reports/codex_dev/feature_store_memory_guard_20260705.md`

Implemented behavior:

- `FeatureStore.build()` now refuses large returned-DataFrame builds before reading full source tables.
- The guard counts `daily`, `daily_basic`, `adj_factor`, `stk_limit`, `suspend_d`, and `index_daily`.
- `FeatureStore.build_to_store()` writes chunked Parquet dataset output and returns a lightweight result.
- `qta features build` now uses `build_to_store()`.

Validation observed:

- FeatureStore focused suite: PASS, `9 passed`.
- A-share agent safety check: PASS.
- Real local `data/cache` memory-guard smoke: PASS; `FeatureStore(ParquetDataStore('data/cache')).build(max_in_memory_rows=300000)` raised `MemoryError` before full build.

## DeepSeek / Reasonix Data Pull

Observed command:

```text
python3 -u /Users/rongyuxu/Desktop/A_Share_Monitor/scripts/expand_cache_300.py --count 3300 --force
```

Observed parent:

```text
Reasonix node process under persistent session chain
```

Observed result:

- The Python child process exited.
- Reasonix parent sessions remained alive.
- No FeatureStore full-cache Python process remained active after the fix.
- Local cache metadata after pull:
  - `data/cache_expanded/daily`: about `8,861,682` rows, `3,068` symbols, `20180102-20260701`.
  - `data/cache/daily`: about `284,798` rows, `3,068` symbols.
  - `data/cache/daily_basic`: about `8,791,542` rows.
  - `data/cache/adj_factor`: about `8,826,180` rows.
  - `data/cache/stk_limit`: about `5,131,790` rows.

Interpretation:

- This is local data-source evidence only.
- It is not `DATA_CLEAR_RESEARCH`.
- It is not true post-freeze forward holdout.
- It is not product route activation.
- It is not production recommendation readiness.
- It does not authorize recommendation, ticket, broker/order, paper/live, or auto execution.

## Next Data-Source Tasks

`DS-A-1`: A-share provider spec from `simonlin1212/a-stock-data`

- Output a research-only provider contract for K-line, qfq/复权, amount, turnover, market cap, industry/concept, announcements, 龙虎榜, 解禁, and资金流.
- Include provenance fields, source hash, snapshot id, freshness, provider caveats, and crosscheck tolerances.
- No network execution unless separate task-level `HG-EXEC` exists.

`DS-US-1`: US provider spec from `simonlin1212/global-stock-data`

- Output a research-only provider contract for Yahoo chart, Yahoo quoteSummary, SEC CIK/EDGAR/XBRL, market list, sector/industry/asset type, adjusted close, row-level crosscheck, freshness, and source hash.
- No network execution unless separate task-level `HG-EXEC` exists.

`MD-DS-1`: market_data negative contract tests

- External provider code exists does not imply data imported.
- Network can fetch does not imply data-clear.
- LLM summary does not imply evidence.
- Partial provenance/freshness/crosscheck does not imply product-read or readiness.

`SW-DS-1`: strategy_work memo taxonomy parking lot

- Park `investment-news`, `astock-peg`, and `TradingAgents-astock` as future research-only memo/enrichment structures.
- Do not integrate trader/investment-plan language.

## Boundary Statement

This coordination record does not authorize recommendations, `PENDING_HUMAN_REVIEW`, ticket emission, eligibility candidates, product-route activation, production readiness, broker/order/paper/live/auto behavior, raw-data migration into quant-proj, `.env` reads, key output, or secret handling. Provider fetch/import work requires task-level `HG-EXEC`, transcript, source artifacts, Codex-Dev validation, and downstream boundary checks before it can affect research data state.
