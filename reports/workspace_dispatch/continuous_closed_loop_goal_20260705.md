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

## Mutable Current Task

Current task batch: DATA_STRATEGY_BATCH_R6_20260705_CLOSEOUT_AND_NEXT_GPT_PRO_REQUEST

Objective:

R6 downstream execution is complete. Record the R6 controller closeout, commit/push the controller records, submit the R6 closeout to the fixed GPT Pro external-audit conversation for a short verdict and next concrete Data/Strategy task batch, record the returned verdict/tasks, then continue the permanent closed loop. Preserve the permanent closed-loop process above. On the next batch, replace only this mutable current-task section.

Latest completed batch:

- DATA_STRATEGY_BATCH_R6_20260705
- closeout: `reports/workspace_dispatch/data_strategy_batch_r6_20260705_closeout.md`
- controller classification: ordinary research-only data/strategy batch
- source acceptances: A-share `8beac22d0ed2f9dea72392df5456b4441b2a9180`; US `4e1304cbac0984c11ccc0c66d39d6685db289866`; market_data `9439dc094ad7ebe9e5ddcc46601c707bf013a090`; strategy_work `1775637dd42cbc858c144da7c4aa60cfaa90a81d`
- next GPT Pro request draft: `reports/external_audit/data_strategy_batch_r6_gpt_pro_external_audit_request_20260705.md`

Current intake:

- pending GPT Pro closed-loop verdict and next task batch for R7

Next dispatcher actions:

1. Commit and push R6 closeout/controller records.
2. Submit `reports/external_audit/data_strategy_batch_r6_gpt_pro_external_audit_request_20260705.md` to the fixed GPT Pro external-audit conversation.
3. Capture GPT Pro verdict and next task batch.
4. Record the verdict/tasks in quant-proj, commit/push, dispatch the next batch, and continue the loop.
