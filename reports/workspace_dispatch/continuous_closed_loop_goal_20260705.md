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
   Downstream Codex-Dev threads must send completion callbacks to the active dispatcher thread. On the Windows WSL2 host, the active dispatcher thread is `019f3830-4b44-7a83-944d-247a0d4dc169`. If direct thread messaging is unavailable, downstream threads must include the callback envelope in their final answer.
6. Record controller-layer evidence in quant-proj, including dispatch summaries, result summaries, acceptance records, and board updates.
7. Commit and push controller records after each meaningful dispatch/result/closeout step.
8. Updated 2026-07-07: GPT Pro / ChatGPT external-audit operation is user-operated. Quant-Dispatcher must not drive Chrome/GPT Pro itself. When there is no active user task list or downstream result to process, prepare current controller status if useful and ask the user for the next pasted task list, verdict, or external-audit result.
9. Use controller external-audit classification immediately when:
   - the user explicitly brings an external-audit verdict or asks for packet preparation,
   - a real external-audit trigger opens, including ticket, product route, production readiness, broker/order/paper/live/auto, raw-data migration, secret handling, or Human-Gate model change, or
   - the dispatcher has no active task and needs the next user-provided task batch to continue the closed loop.
10. When external audit is requested or needed for loop continuation, Quant-Dispatcher may prepare controller records or packet paths when asked, but the user performs GPT Pro submission. Quant-Dispatcher records the pasted verdict and next-task instructions in quant-proj, commit/pushes, then continues the loop with the next task batch.
11. When waiting for downstream agents or user-provided GPT Pro results, wait in coarse intervals rather than polling tightly.

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
- Future data-source work must source provider candidates from `https://github.com/simonlin1212` unless the user explicitly changes this policy. This source restriction does not authorize network ingest, DB writes, data-clear promotion, readiness changes, product routes, tickets, recommendations, or broker/order/paper/live/auto behavior.
- Downstream Codex-Dev completion callbacks are required for future dispatches. Callback protocol record: `reports/workspace_dispatch/downstream_completion_callback_protocol_20260706.md`.

## Mutable Current Task

Current task batch: WINDOWS_WSL2_DISPATCHER_RUNTIME_CLARIFICATION_20260707 completed; awaiting next user-provided task list / downstream callback / GPT Pro verdict

Objective:

Continue as Quant-Dispatcher only. The user clarified Windows WSL2 operating rules on 2026-07-07:

- GPT Pro / ChatGPT external-audit UI operation is user-operated; Quant-Dispatcher receives pasted task lists, verdicts, and downstream acceptances.
- For normal scoped controller work, execute and record instead of asking repeatedly.
- Old Mac-side downstream Codex thread ids are not visible on the current local host; current dispatcher thread is `019f3830-4b44-7a83-944d-247a0d4dc169`.
- New Windows WSL2 downstream Codex-Dev threads were created and acknowledged on 2026-07-07.
- Use DS v4 pro max through Claude Code CLI for advisory project review when requested.

Do not create a controller/gate loop unless a real boundary trigger opens. Do not authorize recommendation, ticket, product route, production readiness, broker/order/paper/live/auto, raw-data migration, or secrets.

Current intake and controller records:

- R13 interim GPT Pro result: `reports/agent_handoff/data_strategy_batch_r13_interim_external_audit_result_20260706.md`
- R13C intake: `reports/workspace_dispatch/data_strategy_batch_r13c_20260706_intake.md`
- R13C task packet: `tasks/in_progress/data-strategy-batch-r13c-20260706/spec.md`
- R13C dispatch summary: `reports/workspace_dispatch/data_strategy_batch_r13c_20260706_dispatch_summary.md`
- Windows WSL2 dispatcher role acceptance: `reports/workspace_dispatch/windows_wsl2_dispatcher_role_acceptance_20260707.md`
- Windows WSL2 registry refresh: `reports/workspace_status/windows_wsl2_registry_refresh_20260707.md`
- Runtime clarification and DS review: `reports/workspace_dispatch/dispatcher_runtime_clarification_and_ds_review_20260707.md`
- Refreshed registry: `registry/projects.yaml`
- GPT Pro audit operation after 2026-07-07 is user-operated; Quant-Dispatcher receives pasted verdicts/task lists and does not operate Chrome/GPT Pro directly.
- Current classification: controller runtime clarification, registry refresh, and DS advisory review
- External-audit trigger opened by this clarification: `no`

Current dispatch plan:

- `A_Share_Monitor`: `019f387b-617e-7273-b539-161216ae3002`, acknowledged `A_SHARE_MONITOR_WSL2_DOWNSTREAM_THREAD_READY`.
- `US_Stock_Monitor`: `019f387b-a161-7ad0-8678-f03a099612ba`, acknowledged `US_STOCK_MONITOR_WSL2_DOWNSTREAM_THREAD_READY`.
- `market_data`: `019f387b-e763-7c01-ae3d-6be552cdb6dc`, acknowledged `MARKET_DATA_WSL2_DOWNSTREAM_THREAD_READY`.
- `strategy_work`: `019f3881-5293-74a1-8535-814bd83c8681`, acknowledged `STRATEGY_WORK_WSL2_DOWNSTREAM_THREAD_READY`.
- Future downstream handoffs must use these WSL2-visible threads and the active dispatcher callback target, or final-answer callback envelopes if thread sending is unavailable.

R13C / WSL2 hard execution rule:

- Do not run 3068-symbol full-frame pandas strategy search.
- Add fail-closed guard for unsafe full-frame `StrategySearch.run()`.
- Implement chunked feature reading and chunked backtest state handling.
- Prove full-frame vs chunked equivalence on small cache before wide3068 dry run.

Next dispatcher actions:

1. Commit and push the Windows WSL2 runtime clarification, callback update, registry refresh, and DS review records.
2. Use the new WSL2-visible downstream Codex-Dev threads for future source-project handoffs and include the updated callback instruction.
3. When the user pastes a GPT Pro verdict or new task list, write intake / task packet / dispatch summary and classify boundary triggers.
4. Keep `market_data` old thread state as historical/stale unless the user reopens that thread or a new downstream thread is established.
5. Track DS review follow-ups: downstream hardcoded path fixes, downstream `CLAUDE.md`/policy propagation, cross-project consistency check, and A-share 3068-symbol full-frame guard unit test.
