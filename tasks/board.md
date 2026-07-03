# Quant Workspace Task Board

## Inbox

- `20260704-chatgpt-external-audit-fixes`: imported ChatGPT external audit fix list; classified by Quant-Dispatcher.
- `20260704-controller-workspace-p0-dispatch-list`: imported controller workspace P0 dispatch list; converted into task packets.
- `20260704-updated-night-batch-recorded-execution-mode`: imported recorded execution mode update and night batch task list.
- `20260704-night-batch-external-audit-accepted-followups`: imported ChatGPT external audit acceptance and next task list.

## Backlog

- `a-strat-1-gap-reacceptance-followup-20260704`: assigned dry-run packet for `Reasonix-Strategy`; source-project execution not started.
- `TASK-025 market_data Access-Gate Regression`: queued P1 after P0 evidence or independent regression need.
- `TASK-027 A11 Candidate Safety Advisory Review`: queued P1 after `TASK-021`.
- `TASK-028 US Strategy Safety Advisory Review`: queued P1 after `TASK-024`.

## In Progress

- `post_acceptance_followup_20260704`: P0 complete; P1 dispatch/implementation in progress.
- `TASK-025 market_data Access-Gate Regression`: ready to dispatch to fixed market_data Codex-Dev thread `019f2957-de0a-7721-ade9-1abfef298127`.
- `TASK-027 A11 Candidate Safety Advisory Review`: ready for fixed `Reasonix-Advisory` session after `TASK-021`.
- `TASK-028 US Strategy Safety Advisory Review`: ready for fixed `Reasonix-Advisory` session after `TASK-024`.

## Blocked / Hold

- `HOLD-001 A-share PENDING_HUMAN_REVIEW ticket emission from A11`: 0 eligible ticket candidates; upstream data/readiness gaps.
- `HOLD-002 US PENDING_HUMAN_REVIEW refresh`: no eligibility candidate; evidence/feedback gaps persist.
- `HOLD-003 US 300-symbol network ingest`: preflight blockers first; requires new `HG-EXEC-TASK-*`.
- `HOLD-004 A-share network ingest for suspension/limit repair`: repair plan first; requires new `HG-EXEC-TASK-*` if network/write.
- `HOLD-005 active product route replacement`: requires separate source-project packet and likely external audit.

## Done

- `recorded-execution-mode-v1-policy-update-20260704`: controller policy updated; Human-Gate batch record added; follow-up task packets created; no L1-L4 execution performed.
- `dispatcher-dry-run-a-strat-1-gap-reacceptance-20260704`: task packet created, handoff prepared, no source-project execution.
- `TASK-001 CODEX_ACCEPTANCE_A11_RESEARCH_RUNNER`: accepted with warnings by Codex-Dev; A-share source commit `012006c40897f999f2a2ba5c69e2630b9d50a552`.
- `TASK-002 CODEX_ACCEPTANCE_US_STRATEGY_EXPERIMENTS`: accepted with warnings by Codex-Dev; US source commit `2d779f5837f309de45d43f2d9c60d7f4e3eeae21`.
- `TASK-003 US_DB_OPS_2_CONTROLLED_EXPANSION_HELPER`: accepted with warnings by Codex-Dev; US source commit `c046c0ce56e5ea501aa2600df410b80b58d412fb`; Human-Gate execution record still required before real network or DB writes.
- `TASK-004 A_DB_OPS_SCRIPTS_FINAL_CLASSIFICATION`: completed by Reasonix-DB; primary summary `reports/workspace_dispatch/reasonix_db_task_004_result_20260704.md`.
- `TASK-005 STRATEGY_WORK_NEXT_TASK_PROMPTS`: completed by Reasonix-Strategy; primary summary `reports/workspace_dispatch/reasonix_strategy_task_005_result_20260704.md`.
- `TASK-006 US-DB-OPS-2 controlled US 300-symbol expansion`: accepted with warnings by Codex-Dev; US source commit `f3b3b10b6cb70babe47e1e44fad490e9f9366b17`; no network fetch or DuckDB write occurred because preflight blocked on duplicate rows and missing metadata.
- `TASK-007 A-DB-OPS controlled A-share expansion`: accepted with warnings by Codex-Dev; A-share source commit `7c168999b6a583ca20a325098cc2111de311a1a1`; local L1 snapshot `a_expand_20260704_l1_local1000_0317` produced 1000 symbols and 2,059,000 canonical rows with readiness `WARNING` / `Level 1`.
- `TASK-008 market_data registry/readiness controlled update`: accepted with warnings by Codex-Dev; market_data branch `codex/task-008-market-data-registry-readiness`, commit `413829f0179c5142e26f57594d52e1b6de9c338f`; A-share 1000-symbol evidence recorded as `WARNING` / `Level 1` candidate only, US remained blocked.
- `TASK-009 A11 research-to-HITL gated ticket attempt`: accepted with warnings by Codex-Dev; A-share source commit `a2c8b825942a59d7c03429f41336ca1b9145a875`; gate result `NO_RECOMMENDATION_AVAILABLE`, `ticket_emitted=false`, no recommendation or trade fields produced.
- `TASK-010 US strategy experiment to ticket refresh attempt`: accepted with warnings by Codex-Dev; US source commit `8b537ae214fa805d177fa067af879e3fbb83b035`; gate result `NO_RECOMMENDATION_AVAILABLE`, `ticket_emitted=false`, blockers remain evidence, feedback, and eligibility.
- `night_batch_recorded_execution_chatgpt_external_audit`: verdict `ACCEPT_RECORDED_EXECUTION_PACKET`; controller-workspace recorded-execution process accepted with future `HG-EXEC-TASK-*` pre-execution requirement.
- `TASK-022 A-share L1 Snapshot Capability Repair Plan`: completed by Reasonix-DB as L0 read-only plan; outputs `reports/deepseek_db/task_022_a_share_l1_capability_repair_plan.md` and `.json`; next DB ops task should be read-only diagnosis first.
- `TASK-021 A11 Research Candidate Root-Cause Drilldown`: accepted with warnings by Codex-Dev; A-share source commit `025f773d42fa16916e31da8d153382d67c02ebe1`; 83 candidates remain exposed to run-level blockers and data-readiness-only repair still yields 0 eligible.
- `TASK-023 US DB Preflight Blocker Repair`: accepted with warnings by Codex-Dev; US source commit `356f56ab5b7452e342c05d44087d867853e3fea0`; historical overlaps are warning-only, target snapshot collision clear, remaining blocker is 44 missing metadata symbols.
- `TASK-024 US Eligibility Candidate Blocker Drilldown`: accepted by Codex-Dev; US source commit `04e7e6742a7fa87d04ea9a65ebc5cf6f0f55a3a7`; feedback is not actionable, evidence re-entry incomplete, eligibility candidate absent by design.
- `TASK-026 Human-Gate Pre-Execution Template Enforcement`: accepted in controller workspace; `HG-EXEC-TASK-*` template, HOLD example, dispatcher checklist, and task-packet validation rule added.
