# DATA_STRATEGY_BATCH_R10_20260705 Intake

Imported: 2026-07-05
Source: fixed GPT Pro `外审对话`
Source result: `reports/agent_handoff/data_strategy_batch_r9_gpt_pro_external_audit_result_20260705.md`
Classification: ordinary research-only data/strategy batch
External audit trigger open: no
Fixes required before dispatch: none

## Dispatch Targets

- `A_Share_Monitor`: tasks A-R10-1 through A-R10-3
- `US_Stock_Monitor`: tasks US-R10-1 through US-R10-5
- `market_data`: task MD-R10-1
- `strategy_work`: task SW-R10-1
- `Reasonix-DB`: draft/advisory sidecar for data-clear criteria, fixture schemas, crosscheck plans, and route boundary semantics
- `Reasonix-Strategy`: draft/advisory sidecar for candidate-quality interpretation, conservative momentum v2, peer-control, and research memo consistency

## A_Share_Monitor Tasks

### A-R10-1 Conservative Momentum v2 Research Specification

- start from R9 result: 1 KEEP_RESEARCH robust candidate, 1 WATCH_RESEARCH recent-only, 4 fragile/rework candidates
- extract the factors that separated the robust candidate from the five weaker candidates
- define conservative_momentum_v2 thresholds for momentum persistence, drawdown cap, liquidity floor, volatility cap, and data completeness
- run only research diagnostics over the current 203-record / 152-symbol A11 dataset
- output candidate_count before/after, retained symbols, dropped symbols, and fragility reduction
- no recommendation, no ticket, no buy/sell wording

### A-R10-2 Robust Candidate Peer-Control Test

- compare the single robust candidate against same-industry and same-liquidity peers inside the Level2 1000-symbol research universe
- determine whether the robust candidate is genuinely distinctive or just an industry/liquidity artifact
- output peer percentile ranks for return, volatility, drawdown, liquidity, one-lot affordability, and data quality
- no ranking as buy list
- no recommendation or ticket

### A-R10-3 A11 Research Dataset Leakage / Staleness Check

- verify the R5-R9 A11 datasets do not mix old 83-candidate baseline with current 203-candidate dataset
- verify current snapshot id, run id, symbol count, factor row count, and candidate label consistency
- detect stale reports, stale JSON references, duplicate candidate records, and mismatched labels
- output only data-quality report
- no product route change

## US_Stock_Monitor Tasks

### US-R10-1 Data-Clear Criteria Definition for US-239

- define exact conditions for a US research candidate to move from DATA_BLOCKED to DATA_CLEAR_RESEARCH
- fields must include sector, asset_type, metadata provenance, adjusted close availability, row-level crosscheck, price-history completeness, and freshness
- apply criteria to the 60 signal-strong and 61 tightened-survivor sets
- output how many remain blocked by each field
- no eligibility_candidate, no ticket

### US-R10-2 Sector and Asset-Type Fixture Build Plan

- use R9 finding that all 60 signal-strong names are data-blocked by missing sector, asset-type, and row-level crosscheck fields
- produce a dry-run sector/asset-type fixture schema for US-239 and US-300A
- classify which fields can be user-supplied CSV vs provider-derived
- no DB write or network unless separate HG-EXEC is created
- no product readiness claim

### US-R10-3 Row-Level Crosscheck Sample Plan

- design a 20-symbol crosscheck sample drawn from the 60 signal-strong and 61 tightened-survivor sets
- specify source pairing, date range, required columns, tolerance rules, mismatch categories, and failure handling
- plan only unless separate HG-EXEC authorizes data retrieval
- no recommendation, no ticket

### US-R10-4 44-Symbol Metadata Queue Actionability Split

- continue from R9: 44 metadata gap remains separate
- split the queue into actionable-now fixture rows, needs-provider rows, ETF schema rows, historical-only rows, and exclude-from-active-scan rows
- produce a dry-run import manifest but do not write DB
- no product-readiness or HITL-readiness claim

### US-R10-5 Feedback Context to Research Backlog Mapping

- test how non-transactional feedback context maps into research backlog scoring
- must not set actionable_feedback_for_ticket=true
- must not create eligibility_candidate
- must not emit ticket
- output backlog-priority effects only
- forbidden fields: buy_now, sell_now, entry_price, target_weight, position_size, allocation, order, broker

## market_data Task

### MD-R10-1 Data-Clear Boundary Contract

- define research-only data-clear labels for A-share Level2 and US-300A without activating product routes
- A-share Level2 may remain PASS_LEVEL_2_FOR_RESEARCH
- US-300A may receive DATA_CLEAR_RESEARCH only if criteria are met, but product_read_allowed must remain false
- production_recommendation_data_ready=false
- broker/live/auto=false

## strategy_work Task

### SW-R10-1 Research Decision Ledger Update

- update research memos from R9/R10 state
- A-share: conservative_momentum_v2, single robust candidate peer-control result, dataset staleness status
- US: data-clear criteria, sector/asset-type fixture plan, crosscheck sample plan, 44-symbol actionability split
- research-only, not product gate
- no recommendation language

## Boundaries

- No recommendation/advice.
- No PENDING_HUMAN_REVIEW ticket.
- No eligibility candidate.
- No product route or production readiness.
- No broker/order/paper/live/auto.
- No DB write, network ingest, schema migration, bulk ingest, readiness change, or registry activation unless a separate task-level HG-EXEC record is created.
- Reasonix outputs are draft/advisory only until Codex-Dev implements and validates.
