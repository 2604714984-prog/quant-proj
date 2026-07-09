# Handoff: strategy_work R13C

Send to `strategy_work` Codex-Dev thread `019f30c3-247e-7f43-af60-96164539a183`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/strategy_work.

Task batch: DATA_STRATEGY_BATCH_R13_CHUNKED_SEARCH_20260706

Objective:
Prepare chunked wide-run config notes and archive/final memo plan; final sync only after A-share and market_data R13C acceptances.

Tasks:

1. SW-R13C-1 / Chunked wide-run configs and archive plan
   - Confirm or update existing configs:
     - configs/bare_minimum_r13_wide3068.yaml
     - configs/lowvol_quality_focused_r13_wide3068.yaml
   - Add chunked execution notes: store_root, expected feature table, no synthetic fallback, research-only, no recommendation/ticket/product route.
   - Record that the old 50-symbol clean cache is gate/debug sample only, not wide-sample evidence.
   - Prepare archive plan for leaderboard, candidate_registry, metrics diff, chunked equivalence report, memory telemetry, and R13C strategy memo.

2. SW-R13C-2 / Final interim-to-closeout memo sync
   - Only after A_Share_Monitor and market_data R13C source acceptances are available.
   - Sync features_daily build/validation, full-frame blocker, chunked implementation, equivalence result, wide bare_minimum result, conditional low_vol_quality result or skip reason, remaining blockers, memory constraints, and boundary.
   - If chunked wide run is incomplete, mark R13_REMAINS_INTERIM_CHUNKED_BACKTEST_NOT_COMPLETE.

Required final output:
CODEX_ACCEPTANCE / STRATEGY_REPORT with commit, changed files, validation, artifacts, and boundary statement.

Boundary:
Research-only. No recommendation/advice, PENDING_HUMAN_REVIEW, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, .env access, key output, or secret handling.
```
