# WINDOWS_WSL2_STRATEGY_HYPOTHESIS_EXPANSION_BATCH_R18_20260707 Spec

## Objective

Find more strategy hypotheses aggressively while keeping all outputs research-only.

Do not loop into controller architecture or gate redesign. Do not activate market_data routes. Do not produce recommendation, ticket, eligibility candidate, strategy candidate promotion, readiness, product route, or trading path.

## Baseline

- R17 external audit verdict: `VERIFIED_ACCEPT_WITH_WARNINGS`.
- R17 closeout: `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`.
- R17 `strategy_candidate_available=false`.
- R17 wide3068 result: `NO_R17_WIDE_PROBE_ELIGIBLE_STRATEGY`.
- R17 positive diagnostic factor: `medium_overlap_198_not_pass / low_vol_20`, overlap-only and failed same-universe pass-only gate.
- R16 factor labels: `WEAK=5`, `UNSTABLE=8`, `POSITIVE=1`.
- East Money split: `77 CROSSCHECK_PASS`, `121 CROSSCHECK_DATE_GAP`, `2870 CROSSCHECK_MISSING_EAST_MONEY`.
- market_data product-route prep remains inactive and separately gated.

## A_Share_Monitor Tasks

| Task | Name | Deliverables |
|---|---|---|
| `A-WIN-R18-1` | R17 failure freeze and search-budget allocation | `reports/workspace_dispatch/windows_wsl2_r18_failure_freeze_and_search_budget_20260707.md`; `.json` |
| `A-WIN-R18-2` | Broad factor-pair interaction search | `reports/workspace_dispatch/windows_wsl2_r18_factor_pair_interaction_search_20260707.md`; `.csv` |
| `A-WIN-R18-3` | Triple-factor constrained interaction search | `reports/workspace_dispatch/windows_wsl2_r18_triple_factor_constrained_search_20260707.md`; `.csv` |
| `A-WIN-R18-4` | Regime-gated strategy discovery | `reports/workspace_dispatch/windows_wsl2_r18_regime_gated_strategy_discovery_20260707.md`; `.csv` |
| `A-WIN-R18-5` | Holding-period and rebalance-frequency search | `reports/workspace_dispatch/windows_wsl2_r18_holding_rebalance_frequency_search_20260707.md`; `.csv` |
| `A-WIN-R18-6` | Trade-count recovery strategy search | `reports/workspace_dispatch/windows_wsl2_r18_trade_count_recovery_search_20260707.md`; `.csv` |
| `A-WIN-R18-7` | Cost-aware low-turnover strategy search | `reports/workspace_dispatch/windows_wsl2_r18_cost_aware_low_turnover_search_20260707.md`; `.csv` |
| `A-WIN-R18-8` | Drawdown-control strategy search | `reports/workspace_dispatch/windows_wsl2_r18_drawdown_control_strategy_search_20260707.md`; `.csv` |
| `A-WIN-R18-9` | Mean-reversion and rebound family expansion | `reports/workspace_dispatch/windows_wsl2_r18_mean_reversion_rebound_expansion_20260707.md`; `.csv` |
| `A-WIN-R18-10` | Momentum family expansion with risk filters | `reports/workspace_dispatch/windows_wsl2_r18_momentum_family_expansion_20260707.md`; `.csv` |
| `A-WIN-R18-11` | Sector-neutral and board-aware strategy search | `reports/workspace_dispatch/windows_wsl2_r18_sector_neutral_board_aware_search_20260707.md`; `.csv` |
| `A-WIN-R18-12` | ML-score as filter, not standalone signal | `reports/workspace_dispatch/windows_wsl2_r18_ml_score_filter_search_20260707.md`; `.csv` |
| `A-WIN-R18-13` | Meta-label prototype for entry suppression | `reports/workspace_dispatch/windows_wsl2_r18_meta_label_entry_suppression_20260707.md`; `.csv` |
| `A-WIN-R18-14` | Portfolio construction diagnostic variants | `reports/workspace_dispatch/windows_wsl2_r18_portfolio_construction_diagnostics_20260707.md`; `.csv` |
| `A-WIN-R18-15` | Bootstrap and permutation significance for promising diagnostics | `reports/workspace_dispatch/windows_wsl2_r18_bootstrap_permutation_significance_20260707.md`; `.csv` |
| `A-WIN-R18-16` | Walk-forward stress for top diagnostic families | `reports/workspace_dispatch/windows_wsl2_r18_walk_forward_stress_top_families_20260707.md`; `.csv` |
| `A-WIN-R18-17` | Wide prequalification board | `reports/workspace_dispatch/windows_wsl2_r18_wide_prequalification_board_20260707.md`; `.csv` |
| `A-WIN-R18-18` | Conditional wide3068 chunked research probe | `reports/workspace_dispatch/windows_wsl2_r18_wide3068_chunked_research_probe_or_skip_20260707.md`; `.csv` |
| `A-WIN-R18-19` | Strategy failure casebook | `reports/workspace_dispatch/windows_wsl2_r18_strategy_failure_casebook_20260707.md` |
| `A-WIN-R18-20` | Research-only strategy shadow leaderboard v2 | `reports/workspace_dispatch/windows_wsl2_r18_shadow_leaderboard_v2_20260707.csv`; `reports/workspace_dispatch/windows_wsl2_r18_shadow_leaderboard_v2_notes_20260707.md` |

## A_Share_Monitor Search Rules

- Use validation-only prequalification.
- Do not select parameters from test results.
- Do not use the shadow leaderboard as an actionable ranking.
- Keep ML score as a filter or diagnostic, not a standalone recommendation or candidate generator.
- Full-frame wide3068 remains blocked.
- Only run wide3068 chunked research probe if `A-WIN-R18-17` emits at least one `R18_WIDE_RESEARCH_PROBE_ELIGIBLE`.
- If none qualify, output `NO_R18_WIDE_RESEARCH_PROBE_ELIGIBLE`.
- Any positive wide result remains research-only and not a candidate.

Allowed wide-prequalification labels:

- `R18_WIDE_RESEARCH_PROBE_ELIGIBLE`
- `NO_R18_WIDE_RESEARCH_PROBE_ELIGIBLE`
- `BLOCKED_BY_VALIDATION`
- `BLOCKED_BY_COST`
- `BLOCKED_BY_TRADE_COUNT`
- `BLOCKED_BY_INSTABILITY`

## market_data Tasks

| Task | Name | Deliverables |
|---|---|---|
| `MD-WIN-R18-1` | Keep product-route prep inactive | `reports/codex_dev/windows_wsl2_r18_product_route_prep_inactive_boundary_20260707.md` |
| `MD-WIN-R18-2` | R18 strategy research manifest schema | `reports/codex_dev/windows_wsl2_r18_strategy_research_manifest_schema.md`; `.json` |
| `MD-WIN-R18-3` | Overclaim tests for R18 strategy outputs | `tests/test_windows_wsl2_r18_strategy_overclaim.py` |

market_data must encode candidate/readiness/product flags as false and must reject overclaims that treat R18 wide eligibility, shadow leaderboard, positive validation, bootstrap pass, wide probe, ML score, or meta-label output as recommendation, ticket, readiness, product route, candidate, or investment advice.

## strategy_work Tasks

| Task | Name | Deliverables |
|---|---|---|
| `SW-WIN-R18-1` | Strategy hypothesis expansion memo | `reports/planning/windows_wsl2_strategy_hypothesis_expansion_batch_r18_strategy_memo_20260707.md` |
| `SW-WIN-R18-2` | Strategy search map by family | `reports/planning/windows_wsl2_r18_strategy_search_map_by_family_20260707.md` |
| `SW-WIN-R18-3` | Final sync after source callbacks | `reports/planning/windows_wsl2_strategy_hypothesis_expansion_batch_r18_final_sync_20260707.md` |

strategy_work must not create final sync until A_Share_Monitor and market_data callbacks are accepted.

## quant-proj Tasks

| Task | Name | Deliverables |
|---|---|---|
| `QP-WIN-R18-1` | Intake and dispatch | `reports/workspace_dispatch/windows_wsl2_strategy_hypothesis_expansion_batch_r18_20260707_intake.md`; this task packet; dispatch summary |
| `QP-WIN-R18-2` | Result summary and closeout | `reports/workspace_dispatch/windows_wsl2_strategy_hypothesis_expansion_batch_r18_20260707_result_summary.md`; `reports/workspace_dispatch/windows_wsl2_strategy_hypothesis_expansion_batch_r18_20260707_closeout.md` |

## Stop Conditions

- `FULL_FRAME_WIDE_STRATEGY_SEARCH_ATTEMPTED`
- `MARKET_DATA_PRODUCT_ROUTE_ACTIVATION_ATTEMPTED`
- `R18_WIDE_RESEARCH_PROBE_ELIGIBLE_WRITTEN_AS_CANDIDATE`
- `TEST_RESULT_USED_TO_SELECT_PARAMETERS`
- `RECOMMENDATION_OR_TICKET_LANGUAGE_APPEARS`
- `SECRET_OR_ENV_ACCESS_REQUIRED`
- `NETWORK_OR_DB_WRITE_REQUIRED_WITHOUT_HG_EXEC`
- `SHADOW_LEADERBOARD_USED_AS_ACTIONABLE_RANKING`
- `ML_SCORE_USED_AS_RECOMMENDATION`

## Validation

Required where applicable:

- `py_compile` for changed Python.
- focused pytest for changed tests.
- `agent_safety_check.py`.
- JSON parse for JSON artifacts.
- `git diff --check`.
- forbidden overclaim scan.
- full-frame wide3068 guard.
- no market_data product-route activation.
- no unapproved network/provider fetch.
- no unapproved DB/cache write/rebuild.

## Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_STRATEGY_HYPOTHESIS_EXPANSION_BATCH_R18_20260707
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
KEY_RESULTS:
WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT:
STRATEGY_CANDIDATE_AVAILABLE:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
