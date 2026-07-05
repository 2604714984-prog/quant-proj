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

Current task batch: DATA_STRATEGY_BATCH_R12_20260705 execution and result collection

Objective:

Continue R12 as Quant-Dispatcher only. R11 GPT Pro external review accepted the prior batch, confirmed no external-audit trigger, and issued R12. R12 remains an ordinary research-only data/strategy batch focused on data quality, strategy experiments, and candidate quality. Do not create a controller external-audit package for ordinary R12 work. Collect downstream results, record controller evidence, commit/push, dispatch `strategy_work` only after source acceptances are available, close out R12, then use the fresh GPT Pro audit conversation for the next batch only when no active task remains.

Current intake and controller records:

- R12 intake: `reports/workspace_dispatch/data_strategy_batch_r12_20260705_intake.md`
- R11 GPT Pro result: `reports/agent_handoff/data_strategy_batch_r11_gpt_pro_external_audit_result_20260705.md`
- R12 dispatch summary: `reports/workspace_dispatch/data_strategy_batch_r12_20260705_dispatch_summary.md`
- R12 registry refresh: `reports/workspace_status/registry_refresh_snapshot_20260705_r12_dispatch.md`
- Fresh GPT Pro audit conversation: `https://chatgpt.com/c/6a4a510b-c9ac-83ea-bf15-af2c9f157f88`
- Classification: ordinary research-only data/strategy batch
- External-audit trigger opened by R12 intake: `no`

Current result state:

- Controller dispatch/Reasonix records have been committed and pushed through controller commit `666a5a1`.
- US R12 returned `CODEX_ACCEPTANCE_DATA_STRATEGY_BATCH_R12_US` at commit `017c1e25b4b05d088121b618f8951ec898145b23`; controller partial result summary now records the result.
- market_data R12 source work was validated and manually committed/pushed at commit `97f1360762e663894ea84af7a6356b89d8cd4f2d`; controller partial result summary now records the result.
- A-share R12 remains active in Codex thread `019f32bd-082d-73e2-b902-3d48b8d198ba`; wait in coarse intervals and do not duplicate-dispatch.
- A-share R12 memory incident was handled by stopping a runaway full-cache `FeatureStore(store).build()` Python process and recording `reports/workspace_dispatch/data_strategy_batch_r12_memory_incident_20260705.md`; the A-share R12 thread was instructed to avoid full-cache builds and return `BLOCKED` with a chunking plan if required.
- FeatureStore root fix is now implemented and pushed in A_Share_Monitor commit `18c19016809210780272512b99b6dd07be074425`; it guards all major FeatureStore source tables and adds chunked `build_to_store()` output. Controller coordination record: `reports/workspace_dispatch/data_source_coordination_20260705.md`.
- DeepSeek/Reasonix A-share data pull completed as local data-source evidence only. Treat it as not data-clear, not product-ready, and not recommendation-ready. Next data-source priority is provider/evidence contracts for `simonlin1212/a-stock-data` and `simonlin1212/global-stock-data`.
- `strategy_work` R12 final memo sync remains dependency-gated until A-share, US, and market_data acceptances are all available.
- Reasonix-DB and Reasonix-Strategy R12 sidecar drafts have been captured with `deepseek-v4-pro` / high effort and committed in controller.
- Partial result summary: `reports/workspace_dispatch/data_strategy_batch_r12_20260705_result_summary.md`

Next dispatcher actions:

1. Wait in coarse intervals for A-share R12 to return `CODEX_ACCEPTANCE` or a blocker.
2. Keep US, market_data, and memory-incident R12 results recorded in controller artifacts without staging unrelated dirty files.
3. After A-share returns, dispatch `SW-R12-1` to the fixed `strategy_work` Codex-Dev thread.
4. Record `strategy_work` output, write R12 closeout, update board and this mutable task section, validate controller checks, commit/push.
5. When no active task remains, submit the R12 closeout to the fresh GPT Pro audit conversation and continue with the next batch it issues.
