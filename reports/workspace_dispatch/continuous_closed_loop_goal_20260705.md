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

Current task batch: DATA_STRATEGY_BATCH_R13_20260706 interim external audit requested

Objective:

Continue as Quant-Dispatcher only. R13 ordinary research-only work reached an interim blocked state: A_Share_Monitor safely built and validated the 3068-symbol `features_daily`, but intentionally did not run wide `research discover` because current `StrategySearch.run()` requires full `daily` and `features_daily` DataFrames in memory. The user requested external audit before continuing.

Current intake and controller records:

- R12 GPT Pro result: `reports/agent_handoff/data_strategy_batch_r12_gpt_pro_external_audit_result_20260706.md`
- R13 intake: `reports/workspace_dispatch/data_strategy_batch_r13_20260706_intake.md`
- R13 task packet: `tasks/in_progress/data-strategy-batch-r13-20260706/spec.md`
- R13 dispatch summary: `reports/workspace_dispatch/data_strategy_batch_r13_20260706_dispatch_summary.md`
- R13 interim result summary: `reports/workspace_dispatch/data_strategy_batch_r13_20260706_interim_result_summary.md`
- R13 interim external-audit packet: `reports/agent_handoff/data_strategy_batch_r13_interim_external_audit_packet_20260706.md`
- Fresh GPT Pro audit conversation for later loop continuation: `https://chatgpt.com/c/6a4a510b-c9ac-83ea-bf15-af2c9f157f88`
- Classification: ordinary research-only data/strategy batch, interim external audit user-requested
- External-audit trigger opened by R13 itself: `no`

Current result state:

- A_Share_Monitor R13 source commit `b5928fb`: `ACCEPTED_FEATURE_BUILD_VALIDATION_WITH_STRATEGY_BLOCKED`.
- `features_daily` built safely: `6,262,517` rows, `3068` symbols, `183` columns, `35` chunks, duplicate keys `0`.
- Final build max RSS: about `5.16 GB`; peak memory footprint: about `8.45 GB` on an 8 GB machine.
- Wide strategy runs were not executed because current strategy search still loads full feature data into pandas.
- strategy_work R13 config-prep commit `9424c1b`: `CODEX_ACCEPTANCE_SW_R13_CONFIG_PREP_DEPENDENCY_GATED`.
- market_data R13 acceptance is not available; fixed thread remains tied up on older approval state.

Next dispatcher actions:

1. Commit/push the R13 interim external-audit packet and result summary.
2. Submit or provide the packet to GPT Pro external audit if user wants active submission.
3. Capture GPT Pro verdict and next task batch.
4. Likely next batch: implement chunked strategy search/backtest before any 3068-symbol wide research discover run.
5. Keep all boundaries closed: no recommendation, ticket, product route, production readiness, broker/order/paper/live/auto, raw-data migration, or secrets.
