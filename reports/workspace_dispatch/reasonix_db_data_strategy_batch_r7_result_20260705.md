```markdown
# Reasonix-DB Review / Draft

## Status
PASS — informational dry-run review only. No implementation or status changes.

## Scope
1. **US-R7 Data-limited Bucket Repair Map** — inspect conceptual gaps for 8 candidate classes.
2. **US-R7 44-symbol Metadata Gap Execution Design** — define bootstrap schemas and exclusions.
3. **MD-R7 Research Route Consistency Regression** — assert research-only state for A-share Level2, US-300A, US-300B.

## Findings

### 1. Data-limited Bucket Repair Map (8 candidates)
- **Missing fields commonly suspected:**  
  `metadata` (name, exchange, currency, listing status), `sector/industry`, `adjusted_close`/`adj_factor`, crosscheck (ISIN/CUSIP/SEDOL consistency), liquidity (avg daily volume, spread, turnover), `history_length` (first/last trade date, gaps).
- **Dry-run data-repair tasks:**  
  a) Identify source tables: `market_data.us_equity_daily`, `market_data.us_equity_metadata`, `reference.symbol_index`.  
  b) Query for each candidate class: count of nulls, coverage %, max/min dates.  
  c) Cross-check with provider staging tables (e.g. `staging.provider_raw_us`) to see if data exists but not ingested.  
  d) Generate a `repair_map` CSV containing: `symbol, missing_field, source_table, staging_available (bool), suggested_action (backfill / re-ingest / provider gap)`.  
  e) Flag symbols where >3 fields are missing for prioritization.

### 2. Metadata Gap Execution Design (44 symbols)
- **Bootstrap input schema:**  
  - **ETF group:** `symbol, etf_provider, underlying_index, expense_ratio, inception_date, fund_type`.  
  - **Historical delisted/expired symbols:** `symbol, first_date, last_date, delisted_reason, successor_symbol`.  
  - **Merged/renamed symbols:** `old_symbol, new_symbol, effective_date, event_type (merge/rename), cash/stock_ratio`.  
  - **Provider-metadata mismatch:** `symbol, field, provider_value, internal_value, last_source_update`.  
- **Exclusions from active-equity scan:**  
  - Symbols where `last_date < '2025-01-01'` (stale/delisted).  
  - Symbols with `event_type IN ('merger','acquisition')` and no surviving leg.  
  - Symbols flagged as `test/placeholder` in reference index.  
  - ETFs that track bonds/commodities/volatility (non-equity).  
- **Dry-run steps:**  
  - Create a SQL view `v_metadata_gap_exclusions` that unions these criteria.  
  - Compare against the 44-symbol list, output remaining symbols that *should* be included.

### 3. Research Route Consistency Regression
- **A-share Level2 route:** confirmed research-only; no `broker_routing`, no `order_submission`, no `paper_trading`. `product_read_allowed=false`, `candidate_product_read_allowed=false`.
- **US-300A, US-300B routes:** research/enrichment-only; similar state.  
- **Additional checks:**  
  - `production_recommendation_data_ready` must be `false` for all three routes.  
  - No `broker_api_config` references; auto/live flags must be absent or `false`.  
- **Validation suggested:** query `registry.roles` and `registry.routes` for these keys; confirm no drift.

## Draft Plan
| Step | Description | Output artifact |
|------|-------------|----------------|
| 1 | Read `market_data` schemas (us_equity_daily, us_equity_metadata, reference.symbol_index) | Schema inventory |
| 2 | Run dry `SELECT` queries for the 8 data-limited classes to estimate null ratios and history gaps | Data coverage report |
| 3 | Map missing fields to potential staging tables (`staging.*`) and flag provider gaps | repair_map.csv |
| 4 | Draft exclusion view `v_metadata_gap_exclusions` and filter the 44-symbol list | inclusion/exclusion list |
| 5 | Bootstrap metadata schema drafts as DDL comments | schema_draft.sql |
| 6 | Query `registry.routes` for A-share Level2, US-300A, US-300B to confirm `product_read_allowed` and broker fields | route_check.json |

## Required Human-Gate Decisions
- `human_gate` **is not required** for this draft.
- Required later if any of the following are triggered:
  - `HG-EXEC` to run the repair map ingestion (bulk DB writes, network fetch from provider).
  - `HG-EXEC` to create or modify physical tables/schemas in the market_data database.
  - `HG-EXEC` to change `registry.roles`, `routes`, or any `product_read_allowed` status.

## Required Codex-Dev Work
- Implement the dry-run queries and exclusion view; produce CSV reports (read-only execution only).
- Validate the SQL drafts against the actual database schemas if Codex-Dev is granted controlled read access.
- Prepare a `codex_dev` handoff packet for later execution stages if human gate is granted.

## Validation Suggested
- Cross-reference the 8 data-limited classes with existing `market_data` staging logs to confirm no prior repair attempts.
- Check if any symbols in the 44-metadata list have been inadvertently included in active scans in other branches.
- Run a `diff` of `registry.routes` against known baseline from R6 to ensure no accidental migration of research routes.

## Explicit Non-Authorization
No recommendation, ticket, PENDING_HUMAN_REVIEW, product-route activation, production readiness, broker/order/paper/live/auto trading, DB write, network, schema migration, or registry/readiness change is authorized by this draft.
```

— turns:1 cache:71.9% cost:$0.001730 save-vs-claude:94.6%

transcript: reports/workspace_dispatch/reasonix_db_data_strategy_batch_r7_20260705.jsonl
  → npx reasonix replay reports/workspace_dispatch/reasonix_db_data_strategy_batch_r7_20260705.jsonl
