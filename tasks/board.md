# Quant Workspace Task Board

## Inbox

- `20260704-chatgpt-external-audit-fixes`: imported ChatGPT external audit fix list; classified by Quant-Dispatcher.
- `20260704-controller-workspace-p0-dispatch-list`: imported controller workspace P0 dispatch list; converted into task packets.
- `20260704-updated-night-batch-recorded-execution-mode`: imported recorded execution mode update and night batch task list.

## Backlog

- `a-strat-1-gap-reacceptance-followup-20260704`: assigned dry-run packet for `Reasonix-Strategy`; source-project execution not started.
- `TASK-008 market_data registry/readiness controlled update`: packet ready; L3 recorded execution; Human-Gate `HG-NIGHT-BATCH-20260704-L1-L4` available; not executed.
- `TASK-009 A11 research-to-HITL gated ticket attempt`: packet ready; L4 `PENDING_HUMAN_REVIEW` only if all gates pass; not executed.
- `TASK-010 US strategy experiment to ticket refresh attempt`: packet ready; L4 `PENDING_HUMAN_REVIEW` only if all gates pass; not executed.

## In Progress

- `TASK-006 US-DB-OPS-2 controlled US 300-symbol expansion`: sent to fixed `US_Stock_Monitor` Codex-Dev thread `019f2913-0031-7513-af16-017b8f990f83`; L1/L2 recorded execution under `HG-NIGHT-BATCH-20260704-L1-L4`.
- `TASK-007 A-DB-OPS controlled A-share expansion`: sent to fixed `A_Share_Monitor` Codex-Dev thread `019f2911-ef0c-7053-aa77-a3b0bf0b05de`; L1 and conditional L2 recorded execution under `HG-NIGHT-BATCH-20260704-L1-L4`.

## Blocked / Hold

- None yet.

## Done

- `recorded-execution-mode-v1-policy-update-20260704`: controller policy updated; Human-Gate batch record added; follow-up task packets created; no L1-L4 execution performed.
- `dispatcher-dry-run-a-strat-1-gap-reacceptance-20260704`: task packet created, handoff prepared, no source-project execution.
- `TASK-001 CODEX_ACCEPTANCE_A11_RESEARCH_RUNNER`: accepted with warnings by Codex-Dev; A-share source commit `012006c40897f999f2a2ba5c69e2630b9d50a552`.
- `TASK-002 CODEX_ACCEPTANCE_US_STRATEGY_EXPERIMENTS`: accepted with warnings by Codex-Dev; US source commit `2d779f5837f309de45d43f2d9c60d7f4e3eeae21`.
- `TASK-003 US_DB_OPS_2_CONTROLLED_EXPANSION_HELPER`: accepted with warnings by Codex-Dev; US source commit `c046c0ce56e5ea501aa2600df410b80b58d412fb`; Human-Gate execution record still required before real network or DB writes.
- `TASK-004 A_DB_OPS_SCRIPTS_FINAL_CLASSIFICATION`: completed by Reasonix-DB; primary summary `reports/workspace_dispatch/reasonix_db_task_004_result_20260704.md`.
- `TASK-005 STRATEGY_WORK_NEXT_TASK_PROMPTS`: completed by Reasonix-Strategy; primary summary `reports/workspace_dispatch/reasonix_strategy_task_005_result_20260704.md`.
