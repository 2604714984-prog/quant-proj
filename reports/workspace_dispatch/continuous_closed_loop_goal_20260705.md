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

Current task batch: DATA_STRATEGY_BATCH_R11_20260705 closeout / GPT Pro submission

Objective:

R11 ordinary research-only Data/Strategy source work is complete. Record and push the R11 controller closeout, then submit the R11 closeout to the fresh GPT Pro audit conversation to request a verdict, external-trigger check, fixes if any, and next concrete `DATA_STRATEGY_BATCH_R12_20260705` tasks. The submission must keep the project focused on data quality, strategy experiments, and candidate quality, and must avoid drifting into controller/gate architecture loops unless a real boundary change opens.

Latest completed batch:

- DATA_STRATEGY_BATCH_R11_20260705
- closeout: `reports/workspace_dispatch/data_strategy_batch_r11_20260705_closeout.md`
- controller classification: ordinary research-only data/strategy batch
- source acceptances: A-share `05b79ddabb05003067e1ae86e10411604271ff26`; US `c9dce3782df1e250987129c7ce5350c786e1821d`; market_data `96a325423d00af02c8829d85d770b7d73e30c6f6`; strategy_work `ad33605ec3ae001bc7c17b132f7333f76f60ae74`
- Reasonix sidecars: `reports/workspace_dispatch/reasonix_data_strategy_batch_r11_sidecar_summary_20260705.md`

Current intake:

- R11 intake: `reports/workspace_dispatch/data_strategy_batch_r11_20260705_intake.md`
- R10 GPT Pro result: `reports/agent_handoff/data_strategy_batch_r10_gpt_pro_external_audit_result_20260705.md`
- R11 dispatch summary: `reports/workspace_dispatch/data_strategy_batch_r11_20260705_dispatch_summary.md`
- R11 result summary: `reports/workspace_dispatch/data_strategy_batch_r11_20260705_result_summary.md`
- R11 closeout: `reports/workspace_dispatch/data_strategy_batch_r11_20260705_closeout.md`
- registry refresh: `reports/workspace_status/registry_refresh_snapshot_20260705_r11_dispatch.md`
- classification: ordinary research-only data/strategy batch
- external-audit trigger opened by R11: `no`

Current dispatch/result state:

- Fresh GPT Pro audit conversation: `https://chatgpt.com/c/6a4a510b-c9ac-83ea-bf15-af2c9f157f88`
- R11 controller intake, dispatch summary, registry refresh, result summary, and closeout are prepared.
- A-share R11 source result is accepted with warnings at commit `05b79ddabb05003067e1ae86e10411604271ff26`.
- US R11 source result is accepted at commit `c9dce3782df1e250987129c7ce5350c786e1821d`.
- market_data R11 source result is accepted with warnings at commit `96a325423d00af02c8829d85d770b7d73e30c6f6`.
- strategy_work R11 final memo sync is accepted at commit `ad33605ec3ae001bc7c17b132f7333f76f60ae74`.
- R11 Reasonix-DB and Reasonix-Strategy sidecar drafts have been captured; persistent sessions were resumed and left open.
- R11 remains research-only and non-actionable.

Next dispatcher actions:

1. Validate, commit, and push the R11 controller closeout records.
2. Submit the R11 closeout to the fresh GPT Pro audit conversation.
3. Capture the verdict and next R12 task instructions in `reports/agent_handoff/`.
4. Commit/push the GPT Pro result and dispatch R12 if provided.
