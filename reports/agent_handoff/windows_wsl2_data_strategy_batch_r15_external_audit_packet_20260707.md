# WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R15_20260706 External-Audit Packet

Project: quant-proj
Prepared: 2026-07-07 Asia/Shanghai
Role: Quant-Dispatcher
Packet type: user-requested GPT Pro / ChatGPT external-audit packet

## Why This Packet Exists

R15 itself did not open a required controller external-audit trigger. The user explicitly requested an external-audit packet after R15 closeout, and GPT Pro / ChatGPT submission is user-operated.

This packet is for external review of the closed R15 research-only data/strategy/data-base batch and for requesting the next concrete ordinary data/strategy task batch.

## Publication Repositories

Controller repo:

- `https://github.com/2604714984-prog/quant-proj`
- branch: `main`
- packet file: `reports/agent_handoff/windows_wsl2_data_strategy_batch_r15_external_audit_packet_20260707.md`
- closeout commit before packet prep: `3be90d0c0241f49a6820a7863f3b6b3b1557edf7`

Source refs verified before packet prep:

| Repository | Branch | Pushed ref | Tree | Ahead/behind |
|---|---|---:|---:|---:|
| `A_Share_Monitor` | `codex/harden-a-share-research-pipeline` | `518081d0e110a0518f5c31adc19722e42a6b94a7` | `da538824ce3dff3dfefc21b157aade12794dd739` | `0/0` |
| `market_data` | `main` | `fa014470b39b07ae342996d629f1b2356138111f` | `cef617fa6b975d69edfe1eaa4935da8c809125ef` | `0/0` |
| `strategy_work` | `main` | `bc70517bb5740105989f404510e7b815644d3bf6` | `0c4799330c699bb3aa1232d32d1977f688b5b390` | `0/0` |
| `US_Stock_Monitor` | `main` | `831ef21eda20ecf971bef9ab2f3487b8e96e1001` | `fe5442c0846a8fb5b432ed4a0fe28d143f8c234f` | `0/0` |

## Primary Controller Entry Points

- `reports/workspace_dispatch/windows_wsl2_data_strategy_batch_r15_20260706_closeout.md`
- `reports/workspace_dispatch/windows_wsl2_data_strategy_batch_r15_20260706_result_summary.md`
- `reports/workspace_dispatch/windows_wsl2_data_strategy_batch_r15_20260706_dispatch_summary.md`
- `reports/workspace_dispatch/windows_wsl2_data_strategy_batch_r15_20260706_intake.md`
- `tasks/in_progress/windows-wsl2-data-strategy-and-base-batch-r15-20260706/spec.md`
- `tasks/in_progress/windows-wsl2-data-strategy-and-base-batch-r15-20260706/human_gate.md`
- `tasks/board.md`
- `reports/workspace_dispatch/continuous_closed_loop_goal_20260705.md`

## Source Artifact Entry Points

`A_Share_Monitor`:

- `reports/workspace_dispatch/windows_wsl2_r15_data_strategy_20260707_report.json`
- `reports/workspace_dispatch/windows_wsl2_r15_data_strategy_20260707_report.md`
- `reports/workspace_dispatch/windows_wsl2_r15_data_strategy_20260707_east_money_priority_queue.csv`
- `reports/workspace_dispatch/windows_wsl2_r15_data_strategy_20260707_east_money_date_gap_diagnostics.csv`
- `reports/workspace_dispatch/windows_wsl2_r15_data_strategy_20260707_metadata_only_table_profile.csv`
- `scripts/generate_windows_wsl2_r15_evidence.py`
- `tests/test_windows_wsl2_r15_evidence.py`
- `qta/research/chunked_features.py`
- `qta/research/strategy_search.py`

`market_data`:

- `reports/codex_dev/windows_wsl2_data_strategy_and_base_batch_r15_market_data_report.md`
- `reports/codex_dev/windows_wsl2_data_strategy_and_base_batch_r15_evidence_bridge.json`
- `reports/codex_dev/windows_wsl2_data_strategy_and_base_batch_r15_research_data_base_manifest_schema.json`
- `tests/test_windows_wsl2_data_strategy_and_base_batch_r15.py`

`strategy_work`:

- `reports/planning/data_strategy_batch_r15_20260706_strategy_report.md`
- `reports/planning/strategy_quality_blocker_roadmap_r15_20260706.md`
- `reports/planning/windows_wsl2_data_strategy_batch_r15_final_sync_20260706.md`
- `reports/SUMMARY.md`

## Review Request

Please review `WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R15_20260706` and return:

1. `VERDICT`
2. `EXTERNAL_AUDIT_TRIGGER_OPEN`: yes/no
3. `FIXES_REQUIRED`
4. `NEXT_DATA_STRATEGY_BATCH`
5. `BOUNDARY_FINDINGS`

The next batch should be ordinary research/data/strategy work unless a true boundary trigger is identified.

## Current Progress

R15 is closed as:

```text
CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS
```

All required downstream tasks completed and were pushed:

- `A-WIN-R15-1` through `A-WIN-R15-15` completed in A_Share_Monitor.
- `MD-WIN-R15-1` through `MD-WIN-R15-4` completed in market_data.
- `SW-WIN-R15-1` through `SW-WIN-R15-3` completed in strategy_work after the final-sync gate was released.
- `QP-WIN-R15-1` and `QP-WIN-R15-2` completed in quant-proj.

No downstream task remains active for R15.

## What Was Done

Controller:

- imported the verified GitHub file-level external-audit conclusion and R15 task list;
- classified the batch as ordinary research-only work with `EXTERNAL_AUDIT_TRIGGER_OPEN: no`;
- created intake, task packet, Human-Gate classification, and dispatch records;
- dispatched prompt-only tasks to fixed WSL2 Codex-Dev threads for A_Share_Monitor, market_data, and strategy_work;
- collected downstream callbacks;
- pushed accepted source commits;
- released strategy_work final sync only after A_Share_Monitor and market_data callbacks were available;
- recorded the result summary and closeout.

A_Share_Monitor:

- preserved the East Money split as `77 CROSSCHECK_PASS`, `121 CROSSCHECK_DATE_GAP`, and `2870 CROSSCHECK_MISSING_EAST_MONEY`;
- treated 198 common symbols as overlap evidence only, not 198 pass;
- created a plan-only East Money expansion queue requiring future task-level HG-EXEC;
- hardened survivor-bias evidence while preserving remaining scope limits;
- recorded `features_daily` lineage and staging assumptions;
- added tradability evidence base;
- finalized the wide3068 full-frame unsafe guard;
- normalized memory telemetry units;
- added metadata-only table profiling;
- hardened chunked feature reading and chunked backtest checks;
- preserved all strategy reruns as rejected.

market_data:

- created a research-only A-share wide feature data-base contract;
- created a cross-repo evidence bridge;
- added negative overclaim regression tests;
- drafted a research data-base manifest schema;
- kept active catalog and registry routes unchanged.

strategy_work:

- created the broad R15 strategy memo;
- created the strategy-quality blocker roadmap;
- completed final sync after accepted A_Share_Monitor and market_data callbacks;
- recorded `strategy_candidate_available=false`.

## Key Evidence

- East Money coverage remains partial: `77/121/2870`.
- Survivor-bias evidence improved, but scope limits remain.
- All strategy reruns remain rejected.
- Full-frame wide3068 StrategySearch remains `BLOCKED_FULL_FRAME_STRATEGY_SEARCH_UNSAFE`.
- wide3068 work is chunked-only.
- `features_daily`, lineage, tradability, and research data-base contract remain staging/local-only research evidence.
- No active data-clear, readiness, or product route changed.

## Validation Summary

- A_Share_Monitor: `py_compile` passed; focused pytest passed with 13 tests; `agent_safety_check.py` passed; JSON parse passed; `git diff --check` passed; forbidden overclaim scan passed.
- market_data: focused pytest passed with 5 tests; JSON parse passed; `git diff HEAD~1..HEAD --check` passed; forbidden overclaim scan passed; working tree clean.
- strategy_work: initial memo and final sync passed `git diff --check`; restricted action/trading-word scans passed; forbidden overclaim/enabling scans passed; final sync pushed to `origin/main`.
- quant-proj: R15 result summary and closeout committed and pushed; controller `main` aligned with `origin/main`.

## Residual Warnings

- East Money coverage remains partial.
- Survivor-bias scope limits remain.
- Strategy quality and robustness remain unresolved.
- Full-frame wide3068 execution remains blocked.
- Staging/local-only assumptions remain for identity `adj_factor`, board-level limit prices, inferred suspensions, partial East Money OHLCV crosscheck, `features_daily`, lineage, tradability, and the research data-base contract.
- Future East Money coverage expansion, provider/network fetch, DB writes, schema/readiness/registry changes, and activation require a separate task-level HG-EXEC packet.

## Boundary

R15 remained research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, `.env` access, key output, secret handling, DB write, network ingest, schema migration, readiness change, or registry activation occurred.

Reasonix / DeepSeek / DS-style output, if any, must remain advisory only and cannot replace Codex-Dev validation.

## Candidate Next-Batch Shape For Auditor To Confirm Or Revise

Please confirm or revise a next ordinary research batch focused on unresolved research blockers, not controller architecture:

```text
WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R16

Primary objective:
Continue research-only data quality and strategy-quality diagnostics after R15. Do not create recommendations, tickets, eligibility candidates, readiness, product routes, or trading flows.

Suggested tasks:
1. A_Share_Monitor:
   Deepen East Money date-gap diagnostics for the 121 date-gap group without network/provider fetch unless a separate HG-EXEC is issued.

2. A_Share_Monitor:
   Expand rejection taxonomy across all R15 strategy reruns, including cost stress, parameter instability, drawdown, trade count, and tradability causes.

3. A_Share_Monitor:
   Add stricter tests that wide3068 paths cannot enter full-frame pandas StrategySearch and must use chunked readers.

4. market_data:
   Add read-only regression checks that the research data-base contract cannot be treated as data-clear, readiness, product route, or registry activation.

5. strategy_work:
   Archive the R15 rejection taxonomy and produce a next-experiment memo that preserves `strategy_candidate_available=false` unless source evidence changes.

6. Optional US branch only if explicitly requested:
   Keep US_Stock_Monitor ready but do not dispatch optional US tasks unless the user or auditor makes them concrete.
```

## Ready-To-Send Prompt

```text
Project: quant-proj
Controller repo: https://github.com/2604714984-prog/quant-proj
Controller branch: main
Packet entry: reports/agent_handoff/windows_wsl2_data_strategy_batch_r15_external_audit_packet_20260707.md

Please review WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R15_20260706 and return:
1. VERDICT
2. EXTERNAL_AUDIT_TRIGGER_OPEN yes/no
3. FIXES_REQUIRED
4. NEXT_DATA_STRATEGY_BATCH
5. BOUNDARY_FINDINGS

Primary controller files:
- reports/workspace_dispatch/windows_wsl2_data_strategy_batch_r15_20260706_closeout.md
- reports/workspace_dispatch/windows_wsl2_data_strategy_batch_r15_20260706_result_summary.md
- reports/workspace_dispatch/windows_wsl2_data_strategy_batch_r15_20260706_dispatch_summary.md
- tasks/in_progress/windows-wsl2-data-strategy-and-base-batch-r15-20260706/spec.md
- tasks/in_progress/windows-wsl2-data-strategy-and-base-batch-r15-20260706/human_gate.md

Current pushed source refs:
- A_Share_Monitor codex/harden-a-share-research-pipeline: 518081d0e110a0518f5c31adc19722e42a6b94a7
- market_data main: fa014470b39b07ae342996d629f1b2356138111f
- strategy_work main: bc70517bb5740105989f404510e7b815644d3bf6
- US_Stock_Monitor main: 831ef21eda20ecf971bef9ab2f3487b8e96e1001

Current outcome:
R15 is CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS. All assigned A-share, market_data, strategy_work, and controller tasks are complete and pushed. East Money coverage remains partial at 77 CROSSCHECK_PASS, 121 CROSSCHECK_DATE_GAP, and 2870 CROSSCHECK_MISSING_EAST_MONEY; 198 common symbols are overlap only. Survivor-bias evidence improved but did not eliminate scope limits. Full-frame wide3068 StrategySearch remains blocked as unsafe; chunked-only execution is required. All strategy reruns remain rejected and strategy_candidate_available=false.

Review focus:
Confirm whether R15 closeout is acceptable with warnings, whether any real external-audit trigger opened, whether fixes are required before the next ordinary data/strategy batch, and what the next concrete R16 data/strategy research batch should be.

Boundary:
No recommendation/advice, PENDING_HUMAN_REVIEW, ticket, eligibility candidate, data-clear promotion, product route, production readiness, broker/order/paper/live/auto, raw-data migration, secret handling, DB write, network ingest, schema migration, readiness change, or registry activation is authorized.
```
