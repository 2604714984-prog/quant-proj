# Handoff: market_data R15

Send to WSL2 downstream thread `019f387b-e763-7c01-ae3d-6be552cdb6dc`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/market_data.

Task batch: WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R15_20260706

Controller: /home/rongyu/workspace/quant-proj
Task packet: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-data-strategy-and-base-batch-r15-20260706/spec.md
Human-Gate classification: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-data-strategy-and-base-batch-r15-20260706/human_gate.md

Assigned tasks:
1. MD-WIN-R15-1 / A-share wide feature research data-base contract.
2. MD-WIN-R15-2 / Cross-repo evidence bridge.
3. MD-WIN-R15-3 / Negative overclaim regression tests.
4. MD-WIN-R15-4 / Research data-base manifest schema draft.

Required facts:
- East Money crosscheck is partial: 77 CROSSCHECK_PASS, 121 CROSSCHECK_DATE_GAP, 2870 CROSSCHECK_MISSING_EAST_MONEY.
- Survivor-bias evidence improved; risk is not fully eliminated.
- features_daily exists as research staging evidence, not product readiness.
- All strategies remain rejected.
- chunked execution success is not readiness.

Required negative controls:
- no product_read_allowed=true.
- no production_recommendation_data_ready=true.
- no broker/live/auto=true.
- no registry activation.
- no readiness change.
- no partial East Money coverage as full coverage.
- no 198 overlap as 198 pass.
- no all rejected as candidate available.

Expected validation:
- focused pytest PASS.
- JSON parse PASS where applicable.
- git diff --check PASS.
- forbidden overclaim scan PASS.

Completion callback required:
After finishing, send a prompt-only callback to Quant-Dispatcher thread 019f3830-4b44-7a83-944d-247a0d4dc169 with the unified callback envelope from the task packet. If thread messaging is unavailable, include the callback envelope in your final answer.

Boundary:
Research-only. No recommendation/advice, PENDING_HUMAN_REVIEW, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, .env access, key output, secret handling, DB writes, network ingest, schema migration, readiness changes, or registry activation.
```
