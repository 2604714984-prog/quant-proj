# DATA_STRATEGY_BATCH_R5_20260705 Intake

Date: 2026-07-05
Source: ChatGPT external audit result for `DATA_STRATEGY_BATCH_R4_20260705`
Result file: `reports/agent_handoff/data_strategy_batch_r4_chatgpt_external_audit_result_20260705.md`

## Dispatcher Classification

R5 is an ordinary research-only Data + Strategy batch.

Do not create:

- ChatGPT external-audit packet
- Codex-Audit task
- gate-only task
- ticket task
- product-route activation task

Allowed outputs:

- `DATA_REPORT`
- `STRATEGY_REPORT`
- `CODEX_ACCEPTANCE`
- `REASONIX_DRAFT`

Forbidden outputs:

- external audit packet
- recommendation
- ticket
- product-route activation
- production readiness
- broker/order/paper/live

## Dispatch Queue

### A_Share_Monitor

- `TASK-A-R5-001` Conservative Momentum Strategy Rework
- `TASK-A-R5-002` Low-vol Strategy Downgrade or Rebuild
- `TASK-A-R5-003` A11 Candidate Quality Dataset Freeze
- `TASK-A-R5-004` A-share Data Gap Repair Design

### US_Stock_Monitor

- `TASK-US-R5-001` US-239 Candidate Quality Breakdown
- `TASK-US-R5-002` 44 Metadata Enrichment Queue Split
- `TASK-US-R5-003` US Sector Metadata Repair Plan
- `TASK-US-R5-004` Feedback Bootstrap First Usable Loop
- `TASK-US-R5-005` US-239 Strategy Weakness Report

### market_data

- `TASK-MD-R5-001` A-share Research Route Metadata Consistency Check
- `TASK-MD-R5-002` US-300A / US-300B Access-Gate Tests

### strategy_work

- `TASK-SW-R5-001` Merge / Reconcile R4 Strategy Work Branch
- `TASK-SW-R5-002` A-share 203 Candidate Research Memo
- `TASK-SW-R5-003` US 239/44 Dual-track Research Memo

### Reasonix-DB

- `TASK-A-R5-004`
- `TASK-US-R5-002`
- `TASK-US-R5-003`

Mode: draft/advisory only unless Codex-Dev implements; no DB write, no network, no readiness promotion.

### Reasonix-Strategy

- `TASK-A-R5-001`
- `TASK-A-R5-002`
- `TASK-US-R5-001`
- `TASK-US-R5-005`
- `TASK-SW-R5-*`

Mode: research-only; no advice, no ticket, no product promotion.

## Next Dispatcher Action

Create fixed downstream dispatch prompts for the listed R5 source-project tasks, preserving the boundaries above.
