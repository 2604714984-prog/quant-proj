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

Current task batch: DATA_STRATEGY_BATCH_R10_20260705_DISPATCH

Objective:

R9 was accepted by the fixed GPT Pro `外审对话` with `VERDICT: ACCEPT`, `EXTERNAL_AUDIT_TRIGGER_OPEN: no`, and `FIXES_REQUIRED: none`. R10 has been imported as an ordinary research-only Data/Strategy batch. Record and push the R9 GPT Pro result and R10 intake, dispatch R10 to fixed downstream agents and persistent Reasonix sidecar sessions, collect CODEX_ACCEPTANCE / REASONIX_DRAFT outputs, close out R10, then continue the permanent closed loop.

Latest completed batch:

- DATA_STRATEGY_BATCH_R9_20260705
- closeout: `reports/workspace_dispatch/data_strategy_batch_r9_20260705_closeout.md`
- controller classification: ordinary research-only data/strategy batch
- source acceptances: A-share `77dec660ffb3a3a18c8e98b8e6dae53bbe238f27`; US `9dd4f468b4d26092a29e3cb30d3e4ced0b8ad5c7`; market_data `21ce90be2533e14389e253c5d94b3ca18a106850`; strategy_work `9b74db4fa535156cfa0c310b4a5818454e643a64`
- Reasonix sidecars: `reports/workspace_dispatch/reasonix_data_strategy_batch_r9_sidecar_summary_20260705.md`

Current intake:

- R10 intake: `reports/workspace_dispatch/data_strategy_batch_r10_20260705_intake.md`
- R9 GPT Pro result: `reports/agent_handoff/data_strategy_batch_r9_gpt_pro_external_audit_result_20260705.md`
- R9 intake: `reports/workspace_dispatch/data_strategy_batch_r9_20260705_intake.md`
- result summary: `reports/workspace_dispatch/data_strategy_batch_r9_20260705_result_summary.md`
- closeout: `reports/workspace_dispatch/data_strategy_batch_r9_20260705_closeout.md`
- classification: ordinary research-only data/strategy batch
- external-audit trigger opened by R9: `no`

Current dispatch/result state:

- R9 downstream dispatch completed for A_Share_Monitor, US_Stock_Monitor, market_data, strategy_work, Reasonix-DB, and Reasonix-Strategy.
- R9 result summary and closeout are recorded in controller workspace.
- GPT Pro accepted R9 and issued `DATA_STRATEGY_BATCH_R10_20260705`.
- R10 downstream Codex dispatch completed for A_Share_Monitor, US_Stock_Monitor, market_data, and strategy_work.
- R10 Reasonix-DB and Reasonix-Strategy sidecar prompts were submitted in the existing persistent CLI-like sessions; sessions were not closed, restarted, or recreated.
- Reasonix-Strategy runaway file-reading attempt was stopped with `Esc` without closing the session; a compact pasted evidence packet completed the R9 strategy draft.

Next dispatcher actions:

1. Record and push R10 dispatch evidence.
2. Wait in coarse intervals for downstream CODEX_ACCEPTANCE and REASONIX_DRAFT outputs.
3. Collect downstream outputs and close out R10.
4. When R10 is complete, continue the permanent closed loop by packaging the latest state and asking the fixed GPT Pro `外审对话` for verdict plus R11 instructions.
