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

Current task batch: DATA_STRATEGY_BATCH_R13_20260706 active dispatch

Objective:

Continue as Quant-Dispatcher only. GPT Pro reviewed the R12 external-audit packet and returned `ACCEPT_WITH_WARNINGS`, `EXTERNAL_AUDIT_TRIGGER_OPEN: no`, and `FIXES_REQUIRED: none before dispatching R13`. R13 is an ordinary research-only data/strategy batch focused on safe 3068-symbol A-share `features_daily` construction, coverage/leakage validation, and wider `low_vol_quality` research diagnostics. Do not create a controller architecture/gate loop. Do not authorize recommendation, ticket, product route, production readiness, broker/order/paper/live/auto, raw-data migration, or secrets.

Current intake and controller records:

- R12 GPT Pro result: `reports/agent_handoff/data_strategy_batch_r12_gpt_pro_external_audit_result_20260706.md`
- R13 intake: `reports/workspace_dispatch/data_strategy_batch_r13_20260706_intake.md`
- R13 task packet: `tasks/in_progress/data-strategy-batch-r13-20260706/spec.md`
- R13 dispatch summary: `reports/workspace_dispatch/data_strategy_batch_r13_20260706_dispatch_summary.md`
- Fresh GPT Pro audit conversation for later loop continuation: `https://chatgpt.com/c/6a4a510b-c9ac-83ea-bf15-af2c9f157f88`
- Classification: ordinary research-only data/strategy batch
- External-audit trigger opened by R13 intake: `no`

Current dispatch plan:

- `A_Share_Monitor` fixed thread `019f32bd-082d-73e2-b902-3d48b8d198ba`: `A-R13-1` through `A-R13-5`.
- `strategy_work` fixed thread `019f30c3-247e-7f43-af60-96164539a183`: `SW-R13-1`, `SW-R13-2`, `SW-R13-3`.
- `market_data` fixed thread `019f3283-a821-7002-961b-6f533d3518c2`: `MD-R13-1`.

R13 hard execution rule:

- `StrategySearch.run()` must not auto-fallback to full in-memory `FeatureStore.build()` over 3068-symbol `data/cache` when `features_daily` is missing or empty.
- A-share must first run read-only preflight, then `python -m qta features build` or equivalent `FeatureStore.build_to_store()`, then coverage/leakage validation, and only then `research discover`.

Next dispatcher actions:

1. Send R13 prompt-only handoffs to the fixed A-share, strategy_work, and market_data Codex-Dev threads without model/thinking overrides.
2. Commit and push the R13 controller intake/dispatch records.
3. Poll downstream threads in coarse intervals.
4. Record source acceptances as they arrive, then trigger strategy_work final sync only after A-share and market_data acceptances are available.
5. Close out R13, push controller records, and request the next GPT Pro batch only when no active task remains or a true external-audit trigger opens.
