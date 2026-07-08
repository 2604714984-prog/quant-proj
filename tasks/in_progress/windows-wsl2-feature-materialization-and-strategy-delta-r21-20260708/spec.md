# WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708 Spec

## Objective

Run an ordinary research-only feature materialization and strategy-delta batch after R20_V2 closeout.

R21 must convert R20 source-review / manifest-only work into validated local research feature rows where public/no-secret sources pass source health. R21 must not run broad strategy searches unless new materialized feature rows or materially improved ETF fields justify a limited delta diagnostic.

## R20 Baseline

- R20_V2 closeout: `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`.
- `STRATEGY_CANDIDATE_AVAILABLE=false`.
- `WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT=0`.
- Conditional wide output: `NO_R20_WIDE_RESEARCH_PROBE_ELIGIBLE`.
- No wide probe and no full-frame wide3068.
- ETF dataset: `etf_rotation_e1_20260707`, 30 symbols, 55,726 qfq OHLCV rows.
- ETF timing: close T signal, T+1 open execution, same-day close-to-close false.
- R20 ETF delta rows: `UNSTABLE=24`, `COST_LIMITED=20`.
- ETF amount/NAV/premium unavailable in local Tencent qfq source.
- A-share new-feature lane: source-review only; `features_daily_v2_research` is `MANIFEST_ONLY_NO_LOCAL_ROWS_GENERATED`.
- News/macro: context-only attribution.
- TradingAgents: role-template only.
- market_data product-route prep remains inactive and separately gated.

## Lane 0 - R20 Freeze And Preconditions

| Task | Name | Deliverables |
|---|---|---|
| `R21-0-1` | R20 evidence freeze | `reports/workspace_dispatch/r21_r20_evidence_freeze_20260708.md`; `.json` |
| `R21-0-2` | R20 limitation carry-forward | `reports/workspace_dispatch/r21_r20_limitation_carry_forward_20260708.md`; `.json` |
| `R21-0-3` | Experiment-store and failure-memory import | `reports/workspace_dispatch/r21_experiment_store_failure_memory_import_20260708.md`; `.json` |
| `R21-0-4` | Source-health before fetch-heavy work | `reports/workspace_dispatch/r21_source_health_before_materialization_20260708.md`; `.json` |

Mandatory rule: no new strategy diagnostic may run until these preconditions are complete.

## Lane 1 - ETF Data Field Materialization

| Task | Name | Deliverables |
|---|---|---|
| `ETF-R21-1` | ETF amount/NAV/premium field search and source-health | `reports/workspace_dispatch/etf_r21_amount_nav_premium_source_health_20260708.md`; `.json` |
| `ETF-R21-2` | ETF field materialization or limitation preservation | `reports/workspace_dispatch/etf_r21_amount_nav_premium_materialization_20260708.md`; `.csv`; `.json` |
| `ETF-R21-3` | ETF liquidity and premium limitation matrix | `reports/workspace_dispatch/etf_r21_liquidity_premium_limitation_matrix_20260708.md`; `.csv` |
| `ETF-R21-4` | ETF delta diagnostics only if fields improve | `reports/workspace_dispatch/etf_r21_delta_diagnostics_or_skip_20260708.md`; `.csv` |

Rules:

- If real amount/NAV/premium fields cannot be materialized, preserve explicit limitation labels.
- Do not rerun R19 grid v2 or R20 delta search without new field evidence.
- No daily signal push, candidate, ticket, readiness, or product route.

## Lane 2 - A-share New-Feature Materialization

| Task | Name | Deliverables |
|---|---|---|
| `A-R21-1` | PEG valuation local feature rows | `reports/workspace_dispatch/a_share_r21_peg_feature_materialization_20260708.md`; `.csv`; `.json` |
| `A-R21-2` | Event/funds/hot-money local feature rows | `reports/workspace_dispatch/a_share_r21_event_funds_hotmoney_materialization_20260708.md`; `.csv`; `.json` |
| `A-R21-3` | `features_daily_v2_research` local row manifest | `reports/workspace_dispatch/a_share_r21_features_daily_v2_research_manifest_20260708.md`; `.json` |
| `A-R21-4` | New-feature data-quality audit | `reports/workspace_dispatch/a_share_r21_new_feature_data_quality_audit_20260708.md`; `.csv` |
| `A-R21-5` | New-feature-only delta diagnostic or skip | `reports/workspace_dispatch/a_share_r21_new_feature_delta_diagnostic_or_skip_20260708.md`; `.csv` |

Rules:

- Run source-health before bounded public/no-secret fetch/load.
- If no validated local feature rows exist, emit skip status and do not run strategy diagnostics.
- Do not retry R18/R19/R20 failed combinations without new materialized rows.
- Do not select parameters from test results.

## Lane 3 - Global / News / Macro Regime Materialization

| Task | Name | Deliverables |
|---|---|---|
| `G-R21-1` | Global regime row extension | `reports/workspace_dispatch/global_r21_regime_row_extension_20260708.md`; `.csv`; `.json` |
| `N-R21-1` | News date-indexed attribution rows | `reports/workspace_dispatch/news_r21_date_indexed_attribution_rows_20260708.md`; `.csv`; `.json` |
| `M-R21-1` | Macro date-indexed context rows | `reports/workspace_dispatch/macro_r21_date_indexed_context_rows_20260708.md`; `.csv`; `.json` |
| `GNM-R21-1` | Regime context merge for research only | `reports/workspace_dispatch/r21_global_news_macro_context_merge_20260708.md`; `.csv` |

Rules:

- Global/news/macro rows are context and attribution only.
- No direct signal use, no directional decision output, no recommendation, and no actionable ranking.

## Lane 4 - Tooling And Regression

| Task | Name | Deliverables |
|---|---|---|
| `TOOL-R21-1` | Queryable experiment-store update | `reports/workspace_dispatch/tool_r21_experiment_store_update_20260708.md`; `.json` |
| `TOOL-R21-2` | Duplicate-search blocker update | `reports/workspace_dispatch/tool_r21_duplicate_search_blocker_20260708.md`; `.json` |
| `TOOL-R21-3` | R21 artifact manifest | `reports/workspace_dispatch/r21_unified_artifact_manifest_20260708.json` |
| `TOOL-R21-4` | R21 callback generator | `reports/workspace_dispatch/tool_r21_callback_generator_20260708.md` |
| `TOOL-R21-5` | R21 unified overclaim scan | `reports/workspace_dispatch/tool_r21_unified_overclaim_scan_20260708.md` |

## Lane 5 - market_data Support

| Task | Name | Deliverables |
|---|---|---|
| `MD-R21-1` | Feature materialization research contract | `reports/codex_dev/r21_feature_materialization_research_contract.md`; `.json` |
| `MD-R21-2` | R21 overclaim regression | `tests/test_r21_feature_materialization_overclaim.py` |

No active registry/readiness/product-route change, no market_data activation, no raw-data import into active route, and no production adapter/schema change.

## Lane 6 - strategy_work Support

| Task | Name | Deliverables |
|---|---|---|
| `SW-R21-1` | R21 strategy memo | `reports/planning/windows_wsl2_feature_materialization_and_strategy_delta_r21_strategy_memo_20260708.md` |
| `SW-R21-2` | R21 final sync after source callbacks | `reports/planning/windows_wsl2_feature_materialization_and_strategy_delta_r21_final_sync_20260708.md` |

Final sync must not be created before accepted source callbacks.

## quant-proj

| Task | Name | Deliverables |
|---|---|---|
| `QP-R21-1` | Intake and dispatch | `reports/workspace_dispatch/windows_wsl2_feature_materialization_and_strategy_delta_r21_20260708_intake.md`; this task packet; dispatch summary |
| `QP-R21-2` | Result summary and closeout | `reports/workspace_dispatch/windows_wsl2_feature_materialization_and_strategy_delta_r21_20260708_result_summary.md`; `reports/workspace_dispatch/windows_wsl2_feature_materialization_and_strategy_delta_r21_20260708_closeout.md` |

## Validation

Required where applicable:

- JSON parse PASS.
- `git diff --check` PASS.
- Focused pytest PASS if code/tests changed.
- `agent_safety_check.py` PASS where applicable.
- Forbidden overclaim scan PASS.
- Source health generated before fetch-heavy work.
- Manifest/count/hash evidence for fetched/written artifacts.
- Experiment store and failure memory import PASS before new diagnostics.
- No broad strategy search without new materialized evidence.
- Callback envelope generated.

## Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
SOURCE_HEALTH:
EXPERIMENT_STORE_STATUS:
FAILURE_MEMORY_STATUS:
R20_EVIDENCE_FREEZE_STATUS:
ETF_FIELD_STATUS:
A_SHARE_FEATURE_STATUS:
GLOBAL_NEWS_MACRO_STATUS:
DATA_STATUS:
STRATEGY_RESULTS:
WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT:
STRATEGY_CANDIDATE_AVAILABLE:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
