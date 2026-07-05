# Reasonix-DB Review / Draft

## Status
WARNING — findings are bounded to evidence obtainable from static file review only; no active DB or network check performed. The inspection plan is valid, but physical verification depends on later Codex-Dev execution after human-gate.

## Scope
- **TASK-US-R6-002** Metadata Enrichment Implementation Plan — review the planned bootstrap design for CSV/JSON metadata around the R5 44-symbol queue split.
- **TASK-MD-R6-001** Research Route Consistency Regression — affirm that A-share, US-300A, and US-300B routes remain research/enrichment-only with no production or broker readiness.

Both tasks are read-only, dry-run. No DB write, no network, no schema migration, no registry/readiness change.

## Findings

### 1. TASK-US-R6-002 — Metadata Enrichment Plan

- The plan proposes **CSV/JSON metadata bootstrap** for four conceptual groups: ETF‑related, historical data, merged composites, and provider‑specific metadata (likely Tiingo, Yahoo Finance, etc.).
- The current **R5 44-symbol queue split** is referenced as the source universe.
- From a database-maintenance perspective, this plan must resolve how metadata will be **stored**, **versioned**, and **traced** back to a provenance source. Likely touchpoints:
  - **Symbol‑Queue registry** (likely a YAML/JSON file in `data/symbols/` or a `symbol_queue` table inside a DuckDB/SQLite file). Without inspection, we cannot confirm the current schema.
  - **Metadata tables** — if they exist, they may be in a `metadata` schema inside the US_Stock_Monitor DuckDB (e.g., `metadata.tiingo_instruments`, `metadata.etf_list`, `metadata.splits`, etc.) or in separate CSVs. The plan should define the target schema before the bootstrap.
  - **Manifest files** — any enrichment ingest must update the manifest (e.g., `manifests/metadata_ingest.yaml`) so that readiness and lineage remain auditable.

- The plan as described lacks:
  - A **target DDL** (even as a draft) for metadata tables.
  - A **provenance field** (e.g., `source_provider`, `fetched_at`, `etag`) per row to avoid data‑drift.
  - A **reconciliation strategy** against the symbol queue: how to handle missing/extra symbols between metadata and the queue.
  - A **dry‑run validation step** that would compare expected coverage without actually writing.

- **Risk**: without a clear schema and provenance design, subsequent strategy work (e.g., factor calculations) may inherit silent gaps. This is a **WARNING**, not a blocker, because the stage is still design.

### 2. TASK-MD-R6-001 — Research Route Consistency Regression

- The verification involves three route identifiers:
  - A‑share research route (likely tied to Chinese A‑share data via e.g., AkShare or similar).
  - US‑300A and US‑300B (likely two partitioned subsets of the US stock universe, possibly used for backtest expansion).
- These routes are supposed to remain at `PASS_LEVEL_2_FOR_RESEARCH` with `product_read_allowed=false`, `production_recommendation_data_ready=false`, and all broker/live/auto flags false.
- From a database/registry standpoint, these flags are typically stored in:
  - `registry/projects.yaml` under each project/sub‑project’s `data_route` entry.
  - Possibly a per‑route `readiness_report.md` (e.g., `docs/readiness_reports/`).
  - The `US_Stock_Monitor` manifest may also carry a `route_readiness` section.

- **Finding**: I cannot physically confirm the current values. A stale registry snapshot could show incorrect flags. The instruction says to “verify” they remain correct. Therefore, the proper procedure is to inspect the registry and any auto‑generated readiness files **as they exist now** (post‑R5 closeout) against the expected constraints. If any deviation is found, it must be flagged but **not corrected** in this draft (readiness changes require human‑gate).

## Draft Plan

### For TASK-US-R6-002

1. **Inventory existing metadata artifacts**:
   - Locate DuckDB databases under `US_Stock_Monitor/local_databases/` or similar.
   - List tables: `SELECT table_name FROM information_schema.tables WHERE table_schema='metadata'` (if DuckDB).
   - Examine `symbol_queue` file (likely `data/symbol_queue_R5.yaml` or CSV).

2. **Produce a target metadata schema draft** as a SQL file (not executed). Suggested minimal tables:
   - `metadata.tiingo_instruments` (ticker, exchange, assetType, priceCurrency, startDate, endDate, fetched_at, source_provenance)
   - `metadata.etf_basics` (ticker, fund_name, asset_class, inception_date, fetched_at, source_provenance)
   - `metadata.historical_calendar` (ticker, market, trading_date, is_trading_day, fetched_at)
   - `metadata.merged_index` (ticker, constituent_of_index, effective_date, source_provenance)

3. **Draft a coverage diagnostic query** (dry‑run) that joins the symbol queue against the metadata tables to report missing/extra symbols, without writing.

4. **Define the bootstrap flow** as a YAML manifest entry (`manifests/metadata_bootstrap.yaml`) that references source files (CSV/JSON paths), target tables, and a validation script.

5. **Recommend Codex-Dev** to implement the above artifacts as non‑executable drafts, then request a human‑gate for a DB‑write execution pass.

### For TASK-MD-R6-001

1. **Read `registry/projects.yaml`** for the market‑data project and confirm the `route_readiness` sections for A‑share, US‑300A, US‑300B have the correct flags.
2. **Read any auto‑generated readiness report** linked from the registry (e.g., `docs/readiness_reports/us300_route_readiness.md`). Verify the fields match.
3. **Cross‑check the `US_Stock_Monitor` manifest** if it contains `route_registry` entries.
4. If any mismatch is found, **document it as a finding**, but do not alter flags. A separate human‑gate ticket would be required to reconcile.
5. **Validate that no broker, live, or paper‑trading configuration appears** in the workspace for these routes. This is a code‑review task for Codex-Dev, but from a DB perspective, we can check if any trade‑related tables or configs exist under these routes.

## Required Human-Gate Decisions
*No human-gate required for this draft.*  
Future human‑gate triggers that would be needed:

| Trigger Event | Required HG? |
|---------------|--------------|
| Execution of SQL DDL or DML (CREATE / INSERT / UPDATE) for metadata tables | YES |
| Physical CSV/JSON ingest (network or local copy) into database | YES |
| Schema migration of existing metadata tables | YES |
| Changing any readiness status, `product_read_allowed`, or `route_readiness` flag in registry or manifest | YES |
| Bulk deletion or re‑ingest of metadata | YES |
| Enabling broker, order routing, paper/live trading flags | YES (permanently forbidden here) |

## Required Codex-Dev Work
- For TASK-US-R6-002: Implement **non‑executing artifacts** (SQL schema draft, manifest draft, coverage script) and stage them in a feature branch (e.g., `feature/r6-metadata-bootstrap`).
- For TASK-MD-R6-001: Write a checklist test script (pytest) that reads `registry/projects.yaml` and asserts the research‑route constraints. Run it **read‑only** against the workspace at commit `e5416a36`. Report any failures.

## Validation Suggested
- **Metadata**: Run the draft coverage script against a copy of the current DuckDB (if a Dev‑copy exists) to preview gaps without touching production data.
- **Route consistency**: Execute the assertion script. If passes, mark TASK-MD-R6-001 as `VERIFIED_PASS`. If fails, emit a warning and open a separate HG ticket.

## Explicit Non-Authorization
This draft does **not** authorize:
- Any database write, schema migration, or data ingest.
- Any change to registry or readiness flags.
- Any recommendation, broker integration, order routing, paper trading, or live trading.
- Emission of `PENDING_HUMAN_REVIEW` tickets, product‑route activation, or production readiness claims.

All actions beyond static review require a separate, explicitly approved Human‑Gate execution pass.

— turns:1 cache:73.6% cost:$0.002501 save-vs-claude:94.5%

transcript: reports/workspace_dispatch/reasonix_db_data_strategy_batch_r6_20260705.jsonl
  → npx reasonix replay reports/workspace_dispatch/reasonix_db_data_strategy_batch_r6_20260705.jsonl
