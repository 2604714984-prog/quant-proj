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

Current task batch: DATA_STRATEGY_BATCH_R12_20260705 closed; GPT Pro next-batch request pending

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
- A-share R12 returned `CODEX_ACCEPTANCE DATA_STRATEGY_BATCH_R12_20260705` at commit `30910a1e46b729f0e50efb81150b15a7c91f5083`; controller result summary now records the result.
- A-share R12 memory incident was handled by stopping a runaway full-cache `FeatureStore(store).build()` Python process and recording `reports/workspace_dispatch/data_strategy_batch_r12_memory_incident_20260705.md`; the A-share R12 thread was instructed to avoid full-cache builds and return `BLOCKED` with a chunking plan if required.
- FeatureStore root fix is now implemented and pushed in A_Share_Monitor commit `18c19016809210780272512b99b6dd07be074425`; it guards all major FeatureStore source tables and adds chunked `build_to_store()` output. Controller coordination record: `reports/workspace_dispatch/data_source_coordination_20260705.md`.
- DeepSeek/Reasonix A-share data pull completed as local data-source evidence only. Treat it as not data-clear, not product-ready, and not recommendation-ready. Next data-source priority is provider/evidence contracts for `simonlin1212/a-stock-data` and `simonlin1212/global-stock-data`.
- A subsequent old-style full-cache `fs.build()` command was observed and killed; downstream guidance now requires `build_to_store()`, bounded windows, or metadata inspection only.
- Data-source priority tasks have been dispatched in `reports/workspace_dispatch/data_source_priority_20260705_dispatch_summary.md`: `DS-US-1`, `MD-DS-1`, `DS-A-1` after A-share R12, and `SW-DS-1`.
- Direct user-requested strategy clean-cache rerun completed and pushed in `strategy_work` commit `b0d7d823f956067c6e58fef013dfc5e2e721c1ea`; controller record `reports/workspace_dispatch/data_source_priority_strategy_clean_cache_rerun_20260705.md`. The selected 50-symbol clean cache removed the `fina_indicator`/data-quality mis-kill path, but all candidates remained rejected on validation, parameter stability, cost stress, or trade-count blockers. Next data-source priority remains safe `features_daily` construction for the cleaned 3068-symbol `data/cache`.
- User requested rolling back the strict `FeatureStore.build()` guard because ordinary research runs became unusable. A_Share_Monitor commit `89373e8f133b946e7d8c3048e704b8c6c5a6f9e2` restores legacy `build()` DataFrame behavior while keeping explicit `build_to_store()` available; controller record `reports/workspace_dispatch/feature_store_build_rollback_20260705.md`.
- `strategy_work` R12 final memo sync `SW-R12-1` returned `ACCEPTED_WITH_WARNINGS` at commit `0c7583dc6bce19d2c4ff58eb256e225a3b03603e`; controller result summary now records the result.
- Reasonix-DB and Reasonix-Strategy R12 sidecar drafts have been captured with `deepseek-v4-pro` / high effort and committed in controller.
- Result summary: `reports/workspace_dispatch/data_strategy_batch_r12_20260705_result_summary.md`
- Closeout: `reports/workspace_dispatch/data_strategy_batch_r12_20260705_closeout.md`

Next dispatcher actions:

1. Validate controller closeout files and commit/push the R12 controller records without staging unrelated older Reasonix transcript edits.
2. Submit the R12 closeout to the fresh GPT Pro audit conversation and request verdict plus the next concrete data/strategy task batch.
3. Record the GPT Pro result in quant-proj, commit/push, then dispatch the next batch if accepted.
4. Keep data-source-priority follow-up results recorded separately from the R12 closeout so DS-US/DS-A/SW-DS work does not blur the R12 acceptance commits.
