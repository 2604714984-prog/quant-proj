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

Current task batch: DATA_STRATEGY_BATCH_R10_20260705_NEW_GPT_PRO_AUDIT_CONVERSATION

Objective:

R10 ordinary research-only Data/Strategy work is complete and controller closeout has been pushed. The prior fixed GPT Pro `外审对话` is too long and unstable, so start a fresh GPT Pro audit conversation using `reports/external_audit/new_gpt_pro_audit_conversation_handoff_20260705.md`. The new conversation must be handed the final project goal and the rule that ordinary batches should focus on data and strategy/candidate-quality development, not architecture/gate/controller loops. Request R10 verdict, external-audit-trigger confirmation, fixes if any, and next concrete `DATA_STRATEGY_BATCH_R11_20260705` tasks.

Latest completed batch:

- DATA_STRATEGY_BATCH_R10_20260705
- closeout: `reports/workspace_dispatch/data_strategy_batch_r10_20260705_closeout.md`
- controller classification: ordinary research-only data/strategy batch
- source acceptances: A-share `a908179a7c8c0a3dcb9013ffe7214fd3e4704600`; US `9f89b03b9c2dcab9dc82a86d705c69e4dfb11862`; market_data `b977e9682f078f359286b50be15fe34a6b03a83c`; strategy_work `570944f8839bfa28fa27cd9f59d24cc0f74c9850`
- Reasonix sidecars: `reports/workspace_dispatch/reasonix_data_strategy_batch_r10_sidecar_summary_20260705.md`

Current intake:

- R10 intake: `reports/workspace_dispatch/data_strategy_batch_r10_20260705_intake.md`
- R9 GPT Pro result: `reports/agent_handoff/data_strategy_batch_r9_gpt_pro_external_audit_result_20260705.md`
- R10 dispatch summary: `reports/workspace_dispatch/data_strategy_batch_r10_20260705_dispatch_summary.md`
- result summary: `reports/workspace_dispatch/data_strategy_batch_r10_20260705_result_summary.md`
- closeout: `reports/workspace_dispatch/data_strategy_batch_r10_20260705_closeout.md`
- GPT Pro request draft: `reports/external_audit/data_strategy_batch_r10_gpt_pro_external_audit_request_20260705.md`
- new GPT Pro handoff: `reports/external_audit/new_gpt_pro_audit_conversation_handoff_20260705.md`
- rollover record: `reports/workspace_dispatch/new_external_audit_conversation_rollover_20260705.md`
- classification: ordinary research-only data/strategy batch
- external-audit trigger opened by R10: `no`

Current dispatch/result state:

- R10 downstream Codex work completed for A_Share_Monitor, US_Stock_Monitor, market_data, and strategy_work.
- A_Share_Monitor completed R10 after a systemError recovery follow-up and pushed commit `a908179a7c8c0a3dcb9013ffe7214fd3e4704600`.
- strategy_work completed a final R10 memo sync after source results became available and pushed commit `570944f8839bfa28fa27cd9f59d24cc0f74c9850`.
- R10 Reasonix-DB and Reasonix-Strategy sidecars completed as advisory drafts in existing persistent CLI-like sessions; sessions were not closed, restarted, or recreated.
- R10 result summary, closeout, and GPT Pro request draft are prepared in controller workspace.
- Prior fixed GPT Pro `外审对话` became unstable during R10 submission; a fresh GPT Pro audit-conversation handoff is now prepared to avoid long-thread UI/tool failures.

Next dispatcher actions:

1. Validate, commit, and push the new GPT Pro audit-conversation handoff records.
2. Start a fresh GPT Pro audit conversation.
3. Submit `reports/external_audit/new_gpt_pro_audit_conversation_handoff_20260705.md`.
4. Capture GPT Pro verdict and next-task instructions.
5. Record the new conversation URL/result in controller workspace, commit/push, then dispatch `DATA_STRATEGY_BATCH_R11_20260705` if tasks are provided.
