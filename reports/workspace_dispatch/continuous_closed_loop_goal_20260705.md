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
8. When there is no active user task list or downstream result to process, do not idle indefinitely. Package the latest completed batch state and use Chrome with the fixed GPT Pro external-audit conversation to request a verdict and the next concrete Data/Strategy task batch.
9. Use Chrome with the fixed GPT Pro external-audit conversation immediately when:
   - the user explicitly asks for an external audit packet,
   - a real external-audit trigger opens, including ticket, product route, production readiness, broker/order/paper/live/auto, raw-data migration, secret handling, or Human-Gate model change, or
   - the dispatcher has no active task and needs the next task batch to continue the closed loop.
10. When external audit is requested or needed for loop continuation, submit the GitHub/commit/report paths through the fixed ChatGPT Pro audit conversation, capture the verdict and next-task instructions, record them in quant-proj, commit/push, then continue the loop with the next task batch.
11. When waiting for downstream agents or GPT Pro, wait in coarse intervals rather than polling tightly.

## Permanent Boundary Rules

These rules are permanent. Do not delete them when updating the current task.

- Ordinary research/data/strategy batches do not get controller external-audit packets.
- No recommendation, ticket emission, product-route activation, production readiness, broker/order path, paper trading, live trading, or auto execution is authorized by this loop.
- DB write, schema migration, bulk ingest, network ingest, readiness change, and registry activation require task-level HG-EXEC evidence and transcript before execution.
- Reasonix outputs remain draft/advisory unless Codex-Dev implements and validates them.
- Preserve blocked and non-actionable states honestly; do not convert blocked research candidates into recommendations.
- For cross-thread Codex sends, send prompt content only. Do not pass model or thinking overrides.
- Reasonix sidecars use fixed sessions with model deepseek-v4-pro and effort high.
- Reasonix fixed sessions are persistent CLI-like conversations. Keep `quant-reasonix-db`, `quant-reasonix-strategy`, and `quant-reasonix-advisory` open and reuse the same live session when possible; do not close or recreate them after each task.

## Mutable Current Task

Current task batch: DATA_STRATEGY_BATCH_R9_20260705_DISPATCH

Objective:

GPT Pro accepted the R8 closeout and returned R9 as the next ordinary research-only Data/Strategy task batch. Record the R8 GPT Pro result, dispatch R9 to fixed downstream Codex-Dev agents and persistent Reasonix sidecars, collect CODEX_ACCEPTANCE / REASONIX_DRAFT outputs, close out R9, push controller records, then continue the permanent closed loop.

Latest completed batch:

- DATA_STRATEGY_BATCH_R8_20260705
- closeout: `reports/workspace_dispatch/data_strategy_batch_r8_20260705_closeout.md`
- controller classification: ordinary research-only data/strategy batch
- source acceptances: A-share `5deaab12a53830528b09159f37678fecbab589a0`; US `c52c3ad5c64e8f624154c1e60f7a1edf67e0b22c`; market_data `92a60d2bd84968db032e71e1e232d94b4cf2ad12`; strategy_work `5f2c0eee84457b5d8f20254a01fbb9a695c8f985`
- GPT Pro result: `reports/agent_handoff/data_strategy_batch_r8_gpt_pro_external_audit_result_20260705.md`

Current intake:

- R9 intake: `reports/workspace_dispatch/data_strategy_batch_r9_20260705_intake.md`
- verdict: `ACCEPT`
- external-audit trigger open: `no`
- fixes required: `none`
- classification: ordinary research-only data/strategy batch

Current dispatch/result state:

- R8 GPT Pro request was submitted through the fixed `外审对话`.
- R8 GPT Pro result was captured at `reports/agent_handoff/data_strategy_batch_r8_gpt_pro_external_audit_result_20260705.md`.
- R9 intake was recorded at `reports/workspace_dispatch/data_strategy_batch_r9_20260705_intake.md`.
- R9 downstream dispatch is pending.
- Reasonix-DB and Reasonix-Strategy must remain open and be reused as persistent CLI-like sessions.

Next dispatcher actions:

1. Update `tasks/board.md`.
2. Commit and push the R8 GPT Pro result plus R9 intake.
3. Dispatch R9 to fixed Codex-Dev downstream agents/projects.
4. Dispatch R9 sidecar prompts to the persistent Reasonix-DB and Reasonix-Strategy sessions without closing or recreating them.
5. Wait in coarse intervals, collect downstream outputs, then close out R9.
