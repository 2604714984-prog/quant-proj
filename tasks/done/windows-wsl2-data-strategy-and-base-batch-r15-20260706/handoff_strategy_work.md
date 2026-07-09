# Handoff: strategy_work R15

Send to WSL2 downstream thread `019f3881-5293-74a1-8535-814bd83c8681`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/strategy_work.

Task batch: WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R15_20260706

Controller: /home/rongyu/workspace/quant-proj
Task packet: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-data-strategy-and-base-batch-r15-20260706/spec.md

Assigned tasks:
1. SW-WIN-R15-1 / Broad R15 strategy memo.
2. SW-WIN-R15-2 / Strategy-quality blocker roadmap.
3. SW-WIN-R15-3 / Final sync after source acceptances only.

Required memo facts:
- 77 CROSSCHECK_PASS, 121 CROSSCHECK_DATE_GAP, 2870 CROSSCHECK_MISSING_EAST_MONEY.
- Survivor-bias evidence improved, not eliminated.
- All strategies rejected.
- Data-chain blocker reduced.
- Strategy-quality blocker remains.
- Chunked execution is required.
- No recommendation, ticket, readiness, product route, broker/order/paper/live/auto.

Important dependency:
- SW-WIN-R15-3 is final sync only after A_Share_Monitor and market_data callbacks are available. Do not create placeholder final sync.

Expected validation:
- no placeholder final sync.
- no candidate promotion.
- no ranked actionable list.
- no buy/sell/advice wording.
- git diff --check PASS if files changed.

Completion callback required:
After finishing, send a prompt-only callback to Quant-Dispatcher thread 019f3830-4b44-7a83-944d-247a0d4dc169 with the unified callback envelope from the task packet. If thread messaging is unavailable, include the callback envelope in your final answer.

Boundary:
Research-only. No recommendation/advice, PENDING_HUMAN_REVIEW, ticket, eligibility candidate, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, .env access, key output, secret handling, DB writes, network ingest, schema migration, readiness changes, or registry activation.
```
