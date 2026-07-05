# DATA_STRATEGY_BATCH_R4_20260705 ChatGPT External Audit Result

Date: 2026-07-05
Project: `quant-proj`
Fixed external-audit conversation: `外审对话`
Submitted packet: `reports/agent_handoff/data_strategy_batch_r4_chatgpt_external_audit_packet_20260705.md`
Publication tag: `quant-workspace-data-strategy-r4-chatgpt-packet-20260705`

## Verdict

`ACCEPT_DATA_STRATEGY_R4_PACKET`

R4 is accepted as an ordinary research-only Data + Strategy batch closeout.

The external reviewer accepted that R4 did not promote research candidates into recommendations, HITL tickets, or product routes, and did not treat the US metadata-valid scan as HITL-ready or product-ready.

## Findings

- Blocking: none
- High: none
- Medium: none
- Low:
  - R4 did not have a neighboring Codex-Audit PASS, but this is accepted because R4 was an ordinary research-only batch and not a product-route, ticket, readiness, or execution-boundary change.
  - Final publication metadata should continue to include tag object, commit, tree, packet path, and manifest path.
  - A-share conservative momentum can be misread as strong candidates; it remains `BEAR_MARKET_FRAGILE`.
  - US-239 scan candidate counts are high, but the universe remains biased while 44 metadata gaps, sector metadata, and second-source crosschecks are unresolved.

## Required Fixes Before Acceptance

None.

## Boundary Statement

This acceptance does not authorize:

- recommendations or buy/sell/hold/reduce/exit advice
- `PENDING_HUMAN_REVIEW` ticket emission
- HITL ticket readiness
- market_data product-route activation
- production recommendation readiness
- broker API, order routing, order submission, or auto execution
- paper trading or live trading
- manual-fill generation, system-generated orders, or system-generated fills
- trade plans, entry prices, target weights, position sizing, or allocation
- new DB writes, schema migration, bulk ingest, registry activation, or readiness promotion
- raw DuckDB, SQLite, parquet, payload, output, or log migration into `quant-proj`
- `.env` reads, token/key printing, or committing secrets

Accepted scope only:

- A-share research-candidate quality research
- US metadata-valid scan and metadata-gap classification
- market_data research-route expression
- strategy_work research roadmap sync

## External Reviewer Direction For Next Batch

Next batch: `DATA_STRATEGY_BATCH_R5_20260705`

Dispatcher rules:

- Do not create a ChatGPT external-audit packet for R5.
- Do not create a Codex-Audit task for R5.
- Do not create a gate-only task.
- Do not create a ticket task.
- Do not create a product-route activation task.
- Allowed outputs: `DATA_REPORT`, `STRATEGY_REPORT`, `CODEX_ACCEPTANCE`, `REASONIX_DRAFT`.
- Forbidden outputs: external audit packet, recommendation, ticket, product-route activation, production readiness, broker/order/paper/live.

## R5 Task Assignments

### A_Share_Monitor

- `TASK-A-R5-001`: Conservative Momentum Strategy Rework. Owner: Codex-Dev + Reasonix-Strategy. Priority: P0.
- `TASK-A-R5-002`: Low-vol Strategy Downgrade or Rebuild. Owner: Reasonix-Strategy first, Codex-Dev if code changes are needed. Priority: P0.
- `TASK-A-R5-003`: A11 Candidate Quality Dataset Freeze. Owner: Codex-Dev. Priority: P0.
- `TASK-A-R5-004`: A-share Data Gap Repair Design. Owner: Reasonix-DB + Codex-Dev. Priority: P1.

### US_Stock_Monitor

- `TASK-US-R5-001`: US-239 Candidate Quality Breakdown. Owner: Codex-Dev + Reasonix-Strategy. Priority: P0.
- `TASK-US-R5-002`: 44 Metadata Enrichment Queue Split. Owner: Codex-Dev + Reasonix-DB. Priority: P0.
- `TASK-US-R5-003`: US Sector Metadata Repair Plan. Owner: Reasonix-DB + Codex-Dev. Priority: P0.
- `TASK-US-R5-004`: Feedback Bootstrap First Usable Loop. Owner: Codex-Dev. Priority: P0.
- `TASK-US-R5-005`: US-239 Strategy Weakness Report. Owner: Reasonix-Strategy. Priority: P1.

### market_data

- `TASK-MD-R5-001`: A-share Research Route Metadata Consistency Check. Owner: Codex-Dev. Priority: P0.
- `TASK-MD-R5-002`: US-300A / US-300B Access-Gate Tests. Owner: Codex-Dev. Priority: P0.

### strategy_work

- `TASK-SW-R5-001`: Merge / Reconcile R4 Strategy Work Branch. Owner: Reasonix-Strategy + Codex-Dev. Priority: P0.
- `TASK-SW-R5-002`: A-share 203 Candidate Research Memo. Owner: Reasonix-Strategy. Priority: P1.
- `TASK-SW-R5-003`: US 239/44 Dual-track Research Memo. Owner: Reasonix-Strategy. Priority: P1.

### Reasonix Sidecars

Reasonix-DB:

- `TASK-A-R5-004`
- `TASK-US-R5-002`
- `TASK-US-R5-003`

Mode: draft/advisory only unless Codex-Dev implements; no DB write, no network, no readiness promotion.

Reasonix-Strategy:

- `TASK-A-R5-001`
- `TASK-A-R5-002`
- `TASK-US-R5-001`
- `TASK-US-R5-005`
- `TASK-SW-R5-*`

Mode: research-only; no advice, no ticket, no product promotion.

## R5 Completion Questions

A-share:

1. Is conservative momentum worth continuing?
2. Should low-vol be downgraded into a risk filter?
3. Is there a small subset of the 203 candidates that is genuinely stable for research?

US:

1. Do the US-239 candidates show quality rather than broad filter pass-through?
2. Are the 44 metadata gaps cleanly split?
3. Can sector metadata be repaired?

market_data:

1. Is the research route clearly expressed?
2. Does the product route remain false?

strategy_work:

1. Is research status synchronized with the source projects?

## One-Line External Direction

R4 is accepted. R5 should continue data and strategy only: deepen A-share conservative momentum research, analyze US-239 candidate quality and 44-symbol metadata enrichment, preserve market_data route boundaries, and synchronize strategy_work research status.
