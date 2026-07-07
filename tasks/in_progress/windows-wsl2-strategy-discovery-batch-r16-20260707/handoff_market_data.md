# Handoff: market_data R16

Send to WSL2 downstream thread `019f387b-e763-7c01-ae3d-6be552cdb6dc`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/market_data.

Task batch: WINDOWS_WSL2_STRATEGY_DISCOVERY_BATCH_R16_20260707

Controller: /home/rongyu/workspace/quant-proj
Task packet: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-strategy-discovery-batch-r16-20260707/spec.md
Human-Gate classification: /home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-strategy-discovery-batch-r16-20260707/human_gate.md

Assigned tasks:
1. MD-WIN-R16-1 / Strategy-search evidence manifest extension.
2. MD-WIN-R16-2 / Negative tests for strategy-search overclaim.
3. MD-WIN-R16-3 / Feature/factor evidence bridge.

Required artifacts:
- reports/codex_dev/windows_wsl2_r16_strategy_search_evidence_manifest_schema.md
- reports/codex_dev/windows_wsl2_r16_strategy_search_evidence_manifest_schema.json
- tests/test_windows_wsl2_r16_strategy_search_overclaim.py
- reports/codex_dev/windows_wsl2_r16_feature_factor_evidence_bridge.md
- reports/codex_dev/windows_wsl2_r16_feature_factor_evidence_bridge.json

Required negative controls:
- shadow leaderboard is not recommendation.
- WIDE_DIAGNOSTIC_ELIGIBLE is not candidate.
- positive validation metric is not ticket.
- stable parameter region is not readiness.
- research evidence tier is not product readiness.
- chunked execution success is not data-clear.
- no product_read_allowed=true.
- no production_recommendation_data_ready=true.
- no registry_activation_allowed=true.
- no readiness_change_allowed=true.

Expected validation:
- focused pytest PASS.
- JSON parse PASS where applicable.
- git diff --check PASS.
- no product/readiness/registry flags.
- no raw data import.

Completion callback required:
After finishing, send a prompt-only callback to Quant-Dispatcher thread 019f3830-4b44-7a83-944d-247a0d4dc169 with the unified callback envelope from the task packet. If thread messaging is unavailable, include the callback envelope in your final answer.

Boundary:
Research-only. No recommendation/advice, PENDING_HUMAN_REVIEW, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, .env access, key output, secret handling, DB writes, network ingest, schema migration, readiness changes, or registry activation.
```

