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

Current task batch: DATA_STRATEGY_BATCH_R12_20260705 dispatch

Objective:

R11 GPT Pro external review is complete in the fresh `New Audit Handoff` conversation. GPT Pro accepted R11, confirmed no external-audit trigger is open, required no fixes before R12 dispatch, and issued `DATA_STRATEGY_BATCH_R12_20260705`. Dispatch R12 to fixed downstream Codex-Dev and Reasonix sidecar sessions, keep `strategy_work` final sync dependency-gated until source acceptances are available, collect results, close out, push, and then continue the closed loop.

Latest completed batch:

- DATA_STRATEGY_BATCH_R11_20260705
- closeout: `reports/workspace_dispatch/data_strategy_batch_r11_20260705_closeout.md`
- controller classification: ordinary research-only data/strategy batch
- source acceptances: A-share `05b79ddabb05003067e1ae86e10411604271ff26`; US `c9dce3782df1e250987129c7ce5350c786e1821d`; market_data `96a325423d00af02c8829d85d770b7d73e30c6f6`; strategy_work `ad33605ec3ae001bc7c17b132f7333f76f60ae74`
- Reasonix sidecars: `reports/workspace_dispatch/reasonix_data_strategy_batch_r11_sidecar_summary_20260705.md`

Current intake:

- R12 intake: `reports/workspace_dispatch/data_strategy_batch_r12_20260705_intake.md`
- R11 GPT Pro result: `reports/agent_handoff/data_strategy_batch_r11_gpt_pro_external_audit_result_20260705.md`
- registry refresh: `reports/workspace_status/registry_refresh_snapshot_20260705_r12_dispatch.md`
- classification: ordinary research-only data/strategy batch
- external-audit trigger opened by R12 intake: `no`

Current dispatch/result state:

- Fresh GPT Pro audit conversation: `https://chatgpt.com/c/6a4a510b-c9ac-83ea-bf15-af2c9f157f88`
- GPT Pro accepted R11 and returned R12 tasks focused on data quality, strategy experiments, and candidate quality.
- R12 controller intake and registry refresh are prepared.
- R12 A-share, US, and market_data Codex-Dev prompts need to be sent to fixed threads/worktrees.
- R12 Reasonix-DB and Reasonix-Strategy sidecar drafts need to be requested with `deepseek-v4-pro` / high effort.
- R12 strategy_work final memo sync remains dependency-gated until source acceptances are available.

Next dispatcher actions:

1. Commit and push the R11 GPT Pro result, R12 intake, registry refresh, board update, and goal update.
2. Send R12 prompts to A-share, US, and market_data fixed Codex-Dev threads/worktrees.
3. Run Reasonix-DB and Reasonix-Strategy R12 advisory sidecars with fixed persistent sessions where possible and durable transcript capture.
4. Record R12 dispatch summary, commit/push, wait in coarse intervals for source acceptances, then dispatch SW-R12-1.
