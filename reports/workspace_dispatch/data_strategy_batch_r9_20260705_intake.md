# DATA_STRATEGY_BATCH_R9_20260705 Intake

Imported: 2026-07-05
Source: fixed GPT Pro `外审对话`
Source result: `reports/agent_handoff/data_strategy_batch_r8_gpt_pro_external_audit_result_20260705.md`
Classification: ordinary research-only data/strategy batch
External audit trigger open: no
Fixes required before dispatch: none

## Dispatch Targets

- `A_Share_Monitor`: tasks A-R9-1 through A-R9-4
- `US_Stock_Monitor`: tasks US-R9-1 through US-R9-5
- `market_data`: task MD-R9-1
- `strategy_work`: task SW-R9-1
- `Reasonix-DB`: draft/advisory sidecar for data, metadata, and route-boundary concerns
- `Reasonix-Strategy`: draft/advisory sidecar for candidate quality, parameter narrowing, and memo consistency

## A_Share_Monitor Tasks

### A-R9-1 Single ROBUST Candidate Evidence Dossier

- focus only on the 1 ROBUST conservative candidate from R8
- build a research-only dossier: factor profile, return windows, volatility, drawdown, liquidity, industry, one-lot cash, qfq/turnover completeness, stale-data checks
- compare against the 1 RECENT_ONLY candidate and 4 BEAR_FRAGILE candidates
- output KEEP_RESEARCH / WATCH_RESEARCH / DROP_RESEARCH only
- no recommendation, no ticket, no buy/sell wording

### A-R9-2 RECENT_ONLY Candidate Regime Validation

- inspect the 1 RECENT_ONLY candidate from R8
- determine whether recent-only behavior is recoverable with a regime filter or should remain WATCH_RESEARCH
- test against 2018-2021 / 2022-2023 / 2024-2026 windows
- no promotion to ticket or recommendation

### A-R9-3 Four BEAR_FRAGILE Candidate Drop/Rework Decision

- inspect the 4 BEAR_FRAGILE candidates
- decide DROP_FOR_NOW / REWORK_LATER / KEEP_AS_STRESS_CASE
- identify exact failure: bear-market drawdown, volatility spike, weak momentum persistence, liquidity, data quality
- no recommendation, no ticket

### A-R9-4 Conservative Momentum Parameter Narrowing

- use R8 evidence to narrow conservative momentum thresholds
- reduce fragile candidates while preserving the single robust candidate if possible
- report before/after candidate count and stability
- research-only; no ticket eligibility claim

## US_Stock_Monitor Tasks

### US-R9-1 Strong Bucket Sector/Crosscheck Gap Overlay

- continue from R8 60 strong bucket
- overlay sector availability, crosscheck status, metadata completeness, and price-history completeness
- separate signal-strong candidates from data-blocked candidates
- no recommendation, no ticket, no eligibility candidate

### US-R9-2 Tightened Filter 61-Candidate Review

- continue from R8 medium+weak reduction: 171 to 61
- inspect the 61 survivors under tightened signal-only dry run
- classify as STRONG_RESEARCH / MEDIUM_RESEARCH / DATA_BLOCKED / DROP_RESEARCH
- explicitly document whether weakness was removed or merely hidden by stricter filters
- no recommendation, no ticket

### US-R9-3 Sector Metadata Repair Dry-run

- design sector metadata repair for US-239 / US-300A only
- produce schema and dry-run validation
- no DB write, no network unless separate HG-EXEC is created
- no product readiness claim

### US-R9-4 44-Symbol Metadata Bootstrap Fixture

- create or validate a dry-run fixture for the 44-symbol metadata gap
- keep ETF / historical / merged-renamed / provider-metadata groups separate
- identify active-equity exclusions
- dry-run only unless separate HG-EXEC is created
- no product route, no HITL readiness

### US-R9-5 Feedback Context Non-Authorization Test

- test that non-transactional feedback creates research context only
- must not set actionable_feedback_for_ticket=true
- must not create eligibility_candidate
- must not emit ticket
- forbidden fields: buy_now, sell_now, entry_price, target_weight, position_size, allocation, order, broker

## market_data Task

### MD-R9-1 Data-Route Boundary Regression

- verify A-share Level2 remains research-only
- verify US-300A remains research-scan only
- verify US-300B remains metadata-enrichment only
- product_read_allowed=false
- production_recommendation_data_ready=false
- broker/live/auto=false

## strategy_work Task

### SW-R9-1 Research Memo Refresh

- update memos from R8/R9 state
- A-share: 1 robust, 1 recent-only, 4 bear-fragile, low-vol archived
- US: 60 strong, 61 tightened survivors, 44 metadata gap, sector/crosscheck blockers
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
