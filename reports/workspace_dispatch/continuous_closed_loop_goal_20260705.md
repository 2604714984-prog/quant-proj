# Quant-Dispatcher Continuous Closed Loop Goal

Created: 2026-07-05T05:31:00Z
Owner: Quant-Dispatcher
Status: ACTIVE

## Permanent Closed Loop Process

This section is permanent. Do not delete it when updating the current task.

Quant-Dispatcher must continuously run the following loop:

1. Import the latest user task list, ChatGPT external-audit verdict, or downstream acceptance result.
2. Classify whether it is an ordinary research/data/strategy batch or an external-audit-triggering boundary change.
3. Dispatch ordinary implementation/research tasks to fixed downstream agents and projects:
   - A_Share_Monitor fixed Codex-Dev thread
   - US_Stock_Monitor fixed Codex-Dev thread
   - market_data fixed Codex-Dev thread
   - strategy_work fixed Codex-Dev thread when available, creating and recording one if missing
   - Reasonix-DB fixed session for DB/data advisory sidecars
   - Reasonix-Strategy fixed session for strategy/research advisory sidecars
4. Quant-Dispatcher must not directly implement source-project work unless the user explicitly asks or no downstream agent is available.
5. Collect downstream outputs only as appropriate:
   - CODEX_ACCEPTANCE
   - DATA_REPORT
   - STRATEGY_REPORT
   - REASONIX_DRAFT
6. Record controller-layer evidence in quant-proj, including dispatch summaries, result summaries, acceptance records, and board updates.
7. Commit and push controller records after each meaningful dispatch/result/closeout step.
8. Use Chrome with the fixed GPT Pro external-audit conversation only when:
   - the user explicitly asks for an external audit packet, or
   - a real external-audit trigger opens, including ticket, product route, production readiness, broker/order/paper/live/auto, raw-data migration, secret handling, or Human-Gate model change.
9. When external audit is triggered, submit the GitHub/tag/packet through the fixed ChatGPT Pro audit conversation, capture the verdict and next-task instructions, record them in quant-proj, commit/push, then continue the loop with the next task batch.
10. When waiting for downstream agents or GPT Pro, wait in coarse intervals rather than polling tightly.

## Permanent Boundary Rules

These rules are permanent. Do not delete them when updating the current task.

- Ordinary research/data/strategy batches do not get controller external-audit packets.
- No recommendation, ticket emission, product-route activation, production readiness, broker/order path, paper trading, live trading, or auto execution is authorized by this loop.
- DB write, schema migration, bulk ingest, network ingest, readiness change, and registry activation require task-level HG-EXEC evidence and transcript before execution.
- Reasonix outputs remain draft/advisory unless Codex-Dev implements and validates them.
- Preserve blocked and non-actionable states honestly; do not convert blocked research candidates into recommendations.
- For cross-thread Codex sends, send prompt content only. Do not pass model or thinking overrides.
- Reasonix sidecars use fixed sessions with model deepseek-v4-pro and effort high.

## Mutable Current Task

Current task batch: DATA_STRATEGY_BATCH_R5_20260705

Objective:

Run the R5 research-only data/strategy batch from dispatch through downstream result collection and controller closeout. Do not create an external audit packet unless a trigger opens.

Current dispatch queue:

- A_Share_Monitor:
  - TASK-A-R5-001 Conservative Momentum Strategy Rework
  - TASK-A-R5-002 Low-vol Strategy Downgrade or Rebuild
  - TASK-A-R5-003 A11 Candidate Quality Dataset Freeze
  - TASK-A-R5-004 A-share Data Gap Repair Design
- US_Stock_Monitor:
  - TASK-US-R5-001 US-239 Candidate Quality Breakdown
  - TASK-US-R5-002 44 Metadata Enrichment Queue Split
  - TASK-US-R5-003 US Sector Metadata Repair Plan
  - TASK-US-R5-004 Feedback Bootstrap First Usable Loop
  - TASK-US-R5-005 US-239 Strategy Weakness Report
- market_data:
  - TASK-MD-R5-001 A-share Research Route Metadata Consistency Check
  - TASK-MD-R5-002 US-300A / US-300B Access-Gate Tests
- strategy_work:
  - TASK-SW-R5-001 Merge / Reconcile R4 Strategy Work Branch
  - TASK-SW-R5-002 A-share 203 Candidate Research Memo
  - TASK-SW-R5-003 US 239/44 Dual-track Research Memo
- Reasonix-DB:
  - TASK-A-R5-004
  - TASK-US-R5-002
  - TASK-US-R5-003
- Reasonix-Strategy:
  - TASK-A-R5-001
  - TASK-A-R5-002
  - TASK-US-R5-001
  - TASK-US-R5-005
  - TASK-SW-R5-*

Next dispatcher actions:

1. Send R5 prompts to fixed Codex-Dev threads.
2. Create and record a fixed strategy_work Codex-Dev thread if no fixed endpoint exists.
3. Run Reasonix-DB and Reasonix-Strategy sidecars as draft/advisory only.
4. Collect downstream results.
5. Record closeout, commit, and push controller changes.
