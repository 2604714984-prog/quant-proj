# Handoff: strategy_work R16

Send to WSL2 downstream thread `019f3881-5293-74a1-8535-814bd83c8681`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/strategy_work.

Task batch: WINDOWS_WSL2_STRATEGY_DISCOVERY_BATCH_R16_20260707

Controller: /home/rongyu/workspace/quant-proj
Task packet: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-strategy-discovery-batch-r16-20260707/spec.md

Assigned tasks:
1. SW-WIN-R16-1 / R16 strategy discovery memo.
2. SW-WIN-R16-2 / Strategy research map by blocker.
3. SW-WIN-R16-3 / Final sync after A-share and market_data acceptances.

Required artifacts:
- reports/planning/windows_wsl2_strategy_discovery_batch_r16_20260707_strategy_memo.md
- reports/planning/windows_wsl2_r16_strategy_research_map_by_blocker_20260707.md
- reports/planning/windows_wsl2_strategy_discovery_batch_r16_final_sync_20260707.md

Required memo facts:
- R15 baseline remains rejected.
- East Money split remains 77 CROSSCHECK_PASS, 121 CROSSCHECK_DATE_GAP, 2870 CROSSCHECK_MISSING_EAST_MONEY.
- 198 common symbols are overlap evidence only.
- survivor-bias evidence improved but did not eliminate all scope limits.
- wide3068 is chunked-only.
- strategy_candidate_available=false unless source evidence changes.
- market_data contract remains research staging only.

Important dependency:
- SW-WIN-R16-3 is final sync only after accepted A_Share_Monitor and market_data R16 callbacks are available. Do not create placeholder final sync.

Expected validation:
- git diff --check PASS.
- forbidden action-word scan PASS.
- no candidate promotion.
- no recommendation/advice.
- no placeholder final sync.

Completion callback required:
After finishing, send a prompt-only callback to Quant-Dispatcher thread 019f3830-4b44-7a83-944d-247a0d4dc169 with the unified callback envelope from the task packet. If thread messaging is unavailable, include the callback envelope in your final answer.

Boundary:
Research-only. No recommendation/advice, PENDING_HUMAN_REVIEW, ticket, eligibility candidate, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, .env access, key output, secret handling, DB writes, network ingest, schema migration, readiness changes, or registry activation.
```
