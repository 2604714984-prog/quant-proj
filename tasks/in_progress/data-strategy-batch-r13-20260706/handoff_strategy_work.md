# Handoff: strategy_work R13

Send to `strategy_work` Codex-Dev thread `019f30c3-247e-7f43-af60-96164539a183`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /Users/rongyuxu/Desktop/strategy_work.

Task batch: DATA_STRATEGY_BATCH_R13_20260706

Objective:
Prepare research-only wide-cache configs for A-share 3068-symbol data/cache, then archive A-share run artifacts and sync final R13 memos after source acceptances are available.

Tasks:

1. SW-R13-1 / prepare wide-cache research configs
   - Create or update:
     - configs/bare_minimum_r13_wide3068.yaml
     - configs/lowvol_quality_focused_r13_wide3068.yaml
   - Both configs must use store_root: data/cache.
   - synthetic_data_when_missing: false.
   - Mark as research_only in a config field or clear YAML comment.
   - Do not weaken code-level strict defaults.
   - If survivor-bias or cost-stress is explicitly disabled in config, document why it is research-only diagnostic and not candidate promotion.
   - Do not add recommendation/ticket/product/readiness fields.

2. SW-R13-2 / archive wide-cache run artifacts
   - Start only after A_Share_Monitor provides R13 run artifacts.
   - Archive:
     - reports/a_share/r13_wide3068_bare_minimum_<run_id>/leaderboard.csv
     - reports/a_share/r13_wide3068_bare_minimum_<run_id>/candidate_registry.json
   - If focused run executes, also archive:
     - reports/a_share/r13_wide3068_lowvol_quality_<run_id>/leaderboard.csv
     - reports/a_share/r13_wide3068_lowvol_quality_<run_id>/candidate_registry.json
   - Update reports/SUMMARY.md and an R13 planning memo.

3. SW-R13-3 / final R13 memo sync after source acceptances only
   - Only final-sync after A_Share_Monitor and market_data R13 source acceptances are available.
   - Sync 3068-symbol cache preflight, features_daily build result, coverage/leakage validation, bare_minimum wide result, conditional focused result, archived artifacts, remaining blockers, and boundary statement.
   - If A-share results are incomplete, write draft only, not final acceptance.

Required final output:
CODEX_ACCEPTANCE / STRATEGY_REPORT with commit, changed files, validation, artifacts, and boundary statement.

Boundary:
Research-only. No recommendation/advice, ticket, PENDING_HUMAN_REVIEW, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, .env access, key output, or secret handling.
```
