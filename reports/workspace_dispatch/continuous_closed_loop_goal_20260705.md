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

Current task batch: DATA_STRATEGY_BATCH_R7_20260705_CLOSEOUT_PACKAGING

Objective:

GPT Pro accepted the R6 closeout and returned R7 as the next ordinary research-only Data/Strategy task batch. R7 has been imported, dispatched, completed by downstream Codex threads, completed by Reasonix sidecars, and packaged into closeout/request artifacts. Commit and push the R7 closeout package, then submit it to the fixed GPT Pro external-audit conversation for verdict and the next concrete Data/Strategy task batch. Preserve the permanent closed-loop process above. On the next batch, replace only this mutable current-task section.

Latest completed batch:

- DATA_STRATEGY_BATCH_R6_20260705
- closeout: `reports/workspace_dispatch/data_strategy_batch_r6_20260705_closeout.md`
- controller classification: ordinary research-only data/strategy batch
- source acceptances: A-share `8beac22d0ed2f9dea72392df5456b4441b2a9180`; US `4e1304cbac0984c11ccc0c66d39d6685db289866`; market_data `9439dc094ad7ebe9e5ddcc46601c707bf013a090`; strategy_work `1775637dd42cbc858c144da7c4aa60cfaa90a81d`
- GPT Pro result: `reports/agent_handoff/data_strategy_batch_r6_gpt_pro_external_audit_result_20260705.md`

Current intake:

- R7 intake: `reports/workspace_dispatch/data_strategy_batch_r7_20260705_intake.md`
- verdict: `ACCEPT`
- external-audit trigger open: `no`
- fixes required: `none`
- classification: ordinary research-only data/strategy batch

Current dispatch/result state:

- Controller R6 GPT result and R7 intake were committed and pushed at `269346b`.
- A-share R7 tasks 1-4 were dispatched to fixed Codex-Dev thread `019f2a5a-8b4b-76b3-b838-abc6b54e4992`.
- US R7 tasks 5-9 were dispatched to fixed Codex-Dev thread `019f2a5a-8f92-7672-bbff-db71694e8676`.
- market_data R7 task 10 was dispatched to fixed Codex-Dev thread `019f2957-de0a-7721-ade9-1abfef298127`.
- strategy_work R7 task 11 was dispatched to fixed Codex-Dev thread `019f30c3-247e-7f43-af60-96164539a183`.
- Reasonix-DB R7 sidecar completed as dry-run/advisory; artifact `reports/workspace_dispatch/reasonix_db_data_strategy_batch_r7_result_20260705.md`.
- Reasonix-Strategy fixed session `quant-reasonix-strategy` remains open; after correcting from path-based file reading to pasted no-file-read context, it completed `RESEARCH_DRAFT`; artifact `reports/workspace_dispatch/reasonix_strategy_data_strategy_batch_r7_result_20260705.md`.
- Reasonix persistent-session handling is documented in `runbooks/reasonix_sessions.md` and `reports/workspace_dispatch/reasonix_data_strategy_batch_r7_sidecar_summary_20260705.md`.
- A-share R7 accepted with warnings at commit `c10dfd1f2e7d2178bcf4fd7e334bb54cb34eedab`.
- US R7 completed and was pushed after follow-up at commit `45c722410eca56556a6b37c82b770565236e6041`.
- market_data R7 accepted with warnings at commit `9606e5838f312d765964dfda4dc5caec079bccd3`.
- strategy_work R7 accepted at commit `9324943c12160b51a8a0e206f4a2f3fb50476d46`.
- R7 closeout artifact: `reports/workspace_dispatch/data_strategy_batch_r7_20260705_closeout.md`.
- R7 GPT Pro request artifact: `reports/external_audit/data_strategy_batch_r7_gpt_pro_external_audit_request_20260705.md`.

Next dispatcher actions:

1. Commit and push the R7 closeout package.
2. Use Chrome with the fixed GPT Pro `外审对话` conversation to submit the R7 short external-audit request.
3. Capture GPT Pro verdict and next task batch.
4. Record the result, commit/push, then dispatch the next batch.
