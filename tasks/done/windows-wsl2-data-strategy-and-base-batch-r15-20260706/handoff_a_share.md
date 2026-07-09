# Handoff: A_Share_Monitor R15

Send to WSL2 downstream thread `019f387b-617e-7273-b539-161216ae3002`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/A_Share_Monitor.

Task batch: WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R15_20260706

Controller: /home/rongyu/workspace/quant-proj
Task packet: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-data-strategy-and-base-batch-r15-20260706/spec.md
Human-Gate classification: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-data-strategy-and-base-batch-r15-20260706/human_gate.md

Verified R14 facts:
- R14 evidence commit: dd3089e2a9c1693ea0571db37c185d6584f1bc14.
- Repair package commit: 735ac8f18266a3720d1b0e729ed6b203539d758e.
- East Money split: 77 CROSSCHECK_PASS, 121 CROSSCHECK_DATE_GAP, 2870 CROSSCHECK_MISSING_EAST_MONEY.
- Survivor-bias active rejection disappeared from candidate rejection reasons, but survivor-bias risk is not fully eliminated.
- All strategy reruns remain rejected.
- wide3068 full-frame remains blocked; chunked mode is required.
- R14 memory telemetry unit naming must be normalized.

Assigned tasks:
1. A-WIN-R15-1 / East Money coverage expansion priority queue.
2. A-WIN-R15-2 / East Money date-gap diagnostics.
3. A-WIN-R15-3 / Controlled East Money HG-EXEC plan only.
4. A-WIN-R15-4 / Survivor-bias evidence hardening v2.
5. A-WIN-R15-5 / features_daily lineage and staging assumptions manifest.
6. A-WIN-R15-6 / Tradability evidence base.
7. A-WIN-R15-7 / Full-frame guard finalization.
8. A-WIN-R15-8 / Memory telemetry unit normalization.
9. A-WIN-R15-9 / Metadata-only table profiling.
10. A-WIN-R15-10 / Chunked feature reader hardening.
11. A-WIN-R15-11 / Chunked backtest equivalence expansion.
12. A-WIN-R15-12 / Strategy rejection research agenda.
13. A-WIN-R15-13 / Cost-stress decomposition.
14. A-WIN-R15-14 / Parameter instability surface.
15. A-WIN-R15-15 / Pre-registered broad strategy family diagnostics.

Hard requirements:
- Do not execute network/provider fetch.
- Do not perform DB/cache rebuild, schema migration, readiness change, registry activation, or raw-data migration.
- A-WIN-R15-3 is plan-only and must output HG_EXEC_REQUIRED_FOR_EAST_MONEY_COVERAGE_EXPANSION if execution would be needed.
- Do not write 198 overlap as 198 pass. Use 77 pass + 121 date-gap + 2870 missing.
- Do not write survivor-bias risk as fully eliminated. Use SURVIVOR_BIAS_ACTIVE_REJECTION_REMOVED_WITH_REMAINING_SCOPE_LIMITS.
- Do not run full-frame wide3068 StrategySearch. wide3068 must be chunked-only.
- Do not tune parameters to find a pass; produce diagnostics and pre-registration.

Expected validation:
- py_compile PASS for changed Python files.
- focused pytest PASS.
- agent_safety_check.py PASS if present.
- JSON parse PASS where applicable.
- git diff --check PASS.
- forbidden overclaim scan PASS.

Completion callback required:
After finishing, send a prompt-only callback to Quant-Dispatcher thread 019f3830-4b44-7a83-944d-247a0d4dc169 with the unified callback envelope from the task packet. If thread messaging is unavailable, include the callback envelope in your final answer.

Boundary:
Research-only. No recommendation/advice, PENDING_HUMAN_REVIEW, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, .env access, key output, or secret handling.
```
