# WINDOWS_WSL2_STRATEGY_DISCOVERY_BATCH_R16_20260707 Spec

## Objective

Use the R15 research-only data and chunked execution base to systematically search for strategy hypotheses worth continued research.

This is strategy discovery, strategy diagnosis, and strategy rescue. It is not recommendation generation, ticket creation, data-clear promotion, readiness, product-route activation, or trading-path work.

## Classification

Ordinary research-only strategy discovery batch.

External-audit trigger opened: `no`.

## Verified Inputs

- R15 closeout: `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`.
- R15 external-audit verdict: `VERIFIED_ACCEPT_WITH_WARNINGS`.
- East Money split: `77 CROSSCHECK_PASS`, `121 CROSSCHECK_DATE_GAP`, `2870 CROSSCHECK_MISSING_EAST_MONEY`.
- 198 common symbols are overlap evidence only.
- Survivor-bias evidence improved but did not eliminate all scope limits.
- wide3068 full-frame StrategySearch remains `BLOCKED_FULL_FRAME_STRATEGY_SEARCH_UNSAFE`.
- wide3068 work is chunked-only.
- All strategy reruns remain rejected.
- `strategy_candidate_available=false`.
- market_data contract remains `RESEARCH_STAGING_ONLY_NOT_DATA_CLEAR`.
- No registry/readiness/product route changed.

## Tasks

| ID | Owner | Task | Dependency |
|---|---|---|---|
| `A-WIN-R16-1` | `A_Share_Monitor` | Strategy evidence freeze before new search. | R15 accepted source state |
| `A-WIN-R16-2` | `A_Share_Monitor` | Factor predictive diagnostics before strategy construction. | `A-WIN-R16-1` |
| `A-WIN-R16-3` | `A_Share_Monitor` | Pre-registered strategy hypothesis catalog. | `A-WIN-R16-1`; can incorporate `A-WIN-R16-2` diagnostics |
| `A-WIN-R16-4` | `A_Share_Monitor` | Strategy scout run on small and medium caches. | `A-WIN-R16-1` through `A-WIN-R16-3` |
| `A-WIN-R16-5` | `A_Share_Monitor` | Wide3068 chunked diagnostic run for eligible families. | `A-WIN-R16-1` through `A-WIN-R16-4`; chunked-only guard active |
| `A-WIN-R16-6` | `A_Share_Monitor` | Trade-count rescue diagnostics. | R15/R16 strategy outputs |
| `A-WIN-R16-7` | `A_Share_Monitor` | Cost-aware strategy redesign diagnostics. | R15/R16 strategy outputs |
| `A-WIN-R16-8` | `A_Share_Monitor` | Parameter stability and cluster selection map. | pre-registered parameter grids |
| `A-WIN-R16-9` | `A_Share_Monitor` | Regime and period attribution. | R15/R16 strategy outputs |
| `A-WIN-R16-10` | `A_Share_Monitor` | Strategy-family rejection taxonomy v2. | R15/R16 strategy outputs |
| `A-WIN-R16-11` | `A_Share_Monitor` | Research-only shadow leaderboard. | R16 strategy outputs |
| `MD-WIN-R16-1` | `market_data` | Strategy-search evidence manifest extension. | R15 research data-base schema |
| `MD-WIN-R16-2` | `market_data` | Negative tests for strategy-search overclaim. | none |
| `MD-WIN-R16-3` | `market_data` | Feature/factor evidence bridge. | A-share R16 factor diagnostics paths; reference only |
| `SW-WIN-R16-1` | `strategy_work` | R16 strategy discovery memo. | can start after dispatch; final facts require source callbacks |
| `SW-WIN-R16-2` | `strategy_work` | Strategy research map by blocker. | can start after dispatch |
| `SW-WIN-R16-3` | `strategy_work` | Final sync after A-share and market_data acceptances. | A-share + market_data callbacks |
| `QP-WIN-R16-1` | `quant-proj` | R16 intake. | done by dispatcher |
| `QP-WIN-R16-2` | `quant-proj` | R16 result summary and closeout. | downstream callbacks |

## Required A_Share_Monitor Deliverables

- `reports/workspace_dispatch/windows_wsl2_r16_strategy_evidence_freeze_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r16_strategy_evidence_freeze_20260707.json`
- `reports/workspace_dispatch/windows_wsl2_r16_factor_predictive_diagnostics_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r16_factor_predictive_diagnostics_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_r16_pre_registered_strategy_hypothesis_catalog_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r16_pre_registered_strategy_hypothesis_catalog_20260707.json`
- `reports/workspace_dispatch/windows_wsl2_r16_strategy_scout_small_medium_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r16_strategy_scout_small_medium_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_r16_wide3068_chunked_strategy_diagnostics_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r16_wide3068_chunked_strategy_diagnostics.csv`
- `reports/workspace_dispatch/windows_wsl2_r16_trade_count_rescue_diagnostics_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r16_trade_count_rescue_diagnostics.csv`
- `reports/workspace_dispatch/windows_wsl2_r16_cost_aware_strategy_diagnostics_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r16_cost_aware_strategy_diagnostics.csv`
- `reports/workspace_dispatch/windows_wsl2_r16_parameter_stability_cluster_map_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r16_parameter_stability_cluster_map.csv`
- `reports/workspace_dispatch/windows_wsl2_r16_regime_period_attribution_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r16_regime_period_attribution.csv`
- `reports/workspace_dispatch/windows_wsl2_r16_strategy_family_rejection_taxonomy_v2_20260707.md`
- `reports/workspace_dispatch/windows_wsl2_r16_strategy_family_rejection_taxonomy_v2.csv`
- `reports/workspace_dispatch/windows_wsl2_r16_research_only_shadow_leaderboard_20260707.csv`
- `reports/workspace_dispatch/windows_wsl2_r16_research_only_shadow_leaderboard_notes_20260707.md`

## Required market_data Deliverables

- `reports/codex_dev/windows_wsl2_r16_strategy_search_evidence_manifest_schema.md`
- `reports/codex_dev/windows_wsl2_r16_strategy_search_evidence_manifest_schema.json`
- `tests/test_windows_wsl2_r16_strategy_search_overclaim.py`
- `reports/codex_dev/windows_wsl2_r16_feature_factor_evidence_bridge.md`
- `reports/codex_dev/windows_wsl2_r16_feature_factor_evidence_bridge.json`

## Required strategy_work Deliverables

- `reports/planning/windows_wsl2_strategy_discovery_batch_r16_20260707_strategy_memo.md`
- `reports/planning/windows_wsl2_r16_strategy_research_map_by_blocker_20260707.md`
- `reports/planning/windows_wsl2_strategy_discovery_batch_r16_final_sync_20260707.md`

## R16 Strategy Hypothesis Families

Pre-register and audit strategy hypotheses before execution. Suggested families:

- `low_vol_quality_v2`
- `low_turnover_quality`
- `defensive_momentum`
- `drawdown_controlled_momentum`
- `liquidity_quality`
- `sector_neutral_low_vol`
- `tradability_filtered_quality`
- `cost_aware_low_turnover`
- `benchmark_relative_defensive`
- `volatility_regime_filtered`
- `mean_reversion_quality`
- `post_drawdown_rebound`
- `low_beta_quality`

Each hypothesis must include signal definition, required features, economic rationale, universe filter, holding period, expected turnover, failure mode, train/validation/test split, cost model, allowed parameter grid, and forbidden post-hoc changes.

## Required Factor Diagnostic Labels

Factor diagnostics may only classify factors as:

- `FACTOR_DIAGNOSTIC_POSITIVE`
- `FACTOR_DIAGNOSTIC_WEAK`
- `FACTOR_DIAGNOSTIC_UNSTABLE`
- `FACTOR_DIAGNOSTIC_INSUFFICIENT_DATA`

## Wide Diagnostic Rule

Only families marked `WIDE_DIAGNOSTIC_ELIGIBLE` after pre-registered small/medium scout work may enter wide3068 diagnostics.

If no family qualifies, output `NO_WIDE_DIAGNOSTIC_ELIGIBLE_STRATEGY`.

`WIDE_DIAGNOSTIC_ELIGIBLE` is not a candidate, recommendation, ticket input, readiness signal, or product signal.

## Required Validation

A_Share_Monitor:

- `py_compile` PASS for changed Python files.
- focused pytest PASS.
- `agent_safety_check.py` PASS if present.
- JSON parse PASS where applicable.
- `git diff --check` PASS.
- forbidden overclaim scan PASS.
- full-frame wide3068 not run.
- wide3068 runs are chunked-only.
- no network/provider fetch.
- no DB/cache rebuild.

market_data:

- focused pytest PASS.
- JSON parse PASS where applicable.
- `git diff --check` PASS.
- no product/readiness/registry flags.
- no raw data import.

strategy_work:

- `git diff --check` PASS.
- forbidden action-word scan PASS.
- no candidate promotion.
- no recommendation/advice.
- no placeholder final sync.

## Stop Conditions

- `FULL_FRAME_WIDE_STRATEGY_SEARCH_ATTEMPTED`
- `NETWORK_PROVIDER_FETCH_REQUIRED_WITHOUT_HG_EXEC`
- `DB_WRITE_OR_CACHE_REBUILD_REQUIRED_WITHOUT_HG_EXEC`
- `STRATEGY_RESULT_PROMOTED_TO_CANDIDATE`
- `SHADOW_LEADERBOARD_USED_AS_RECOMMENDATION`
- `PARAMETERS_CHANGED_AFTER_TEST_RESULT`
- `STABLE_PARAMETER_REGION_WRITTEN_AS_READINESS`
- `POSITIVE_VALIDATION_METRIC_WRITTEN_AS_TICKET`
- `SECRET_OR_ENV_ACCESS_REQUIRED`

## Required Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_STRATEGY_DISCOVERY_BATCH_R16_20260707
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
KEY_RESULTS:
WARNINGS:
BLOCKERS:
STRATEGY_CANDIDATE_AVAILABLE:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```

## Boundary

Research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, `.env` access, key output, secret handling, DB write, network ingest, schema migration, readiness change, or registry activation.

Future provider/network fetch, DB/cache rebuild, schema/readiness/registry changes require separate task-level HG-EXEC.

