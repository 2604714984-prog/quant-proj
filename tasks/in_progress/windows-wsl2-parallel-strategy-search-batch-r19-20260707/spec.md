# WINDOWS_WSL2_PARALLEL_STRATEGY_SEARCH_BATCH_R19_20260707 Spec

## Objective

Continue strategy development aggressively on two parallel research-only lanes:

1. ETF rotation lane using the newly available 30-symbol ETF dataset and E1 results.
2. A-share equity signal lane continuing from R18 failure modes.

Do not revisit controller/gate architecture. Do not activate market_data routes. Do not create recommendation, ticket, eligibility candidate, strategy candidate promotion, readiness, product route, daily signal push, or trading path.

## Baseline

- Fastpath external audit: `FASTPATH_BATCH: VERIFIED_ACCEPT_WITH_WARNINGS`.
- R18 external audit: `PRELIMINARY_VERIFIED_ACCEPT_WITH_WARNINGS`.
- Fastpath catchup closeout: `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`.
- R18 closeout: `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS` in controller records.
- ETF snapshot: `etf_rotation_e1_20260707`, 30 ETF symbols, 55,726 qfq OHLCV rows.
- ETF timing rule: close `T` signal and `T+1` open execution.
- ETF screenshot reproduction remains research-only and non-actionable.
- East Money split remains `77 CROSSCHECK_PASS / 121 CROSSCHECK_DATE_GAP / 2870 CROSSCHECK_MISSING_EAST_MONEY`.
- East Money broad reconciliation remains provider-blocked with zero accepted new rows.
- R18 `WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT=0`.
- R18 `strategy_candidate_available=false`.
- market_data product-route prep remains inactive and separately gated.

## A. ETF Rotation Lane

| Task | Name | Deliverables |
|---|---|---|
| `ETF-R19-1` | ETF E1 evidence freeze and reproducibility check | `reports/workspace_dispatch/etf_rotation_r19_e1_evidence_freeze_20260707.md`; `.json` |
| `ETF-R19-2` | ETF expanded universe grouping audit | `reports/workspace_dispatch/etf_rotation_r19_universe_grouping_audit_20260707.md`; `.csv` |
| `ETF-R19-3` | ETF robust rotation grid v2 | `reports/workspace_dispatch/etf_rotation_r19_robust_grid_v2_20260707.md`; `.csv` |
| `ETF-R19-4` | ETF walk-forward and period robustness | `reports/workspace_dispatch/etf_rotation_r19_walk_forward_robustness_20260707.md`; `.csv` |
| `ETF-R19-5` | ETF cost, slippage, liquidity, and missing amount stress | `reports/workspace_dispatch/etf_rotation_r19_cost_liquidity_stress_20260707.md`; `.csv` |
| `ETF-R19-6` | ETF permutation and bootstrap robustness | `reports/workspace_dispatch/etf_rotation_r19_permutation_bootstrap_20260707.md`; `.csv` |
| `ETF-R19-7` | ETF route-to-strategy hypothesis board | `reports/workspace_dispatch/etf_rotation_r19_hypothesis_board_20260707.md`; `.csv` |

## ETF Rotation Rules

- Freeze ETF dataset `etf_rotation_e1_20260707`, 30 symbols, 55,726 rows.
- Preserve timing rule: close `T` signal and `T+1` open execution.
- Classify all 30 ETFs into width/index, style, sector/theme, overseas, bond, gold/commodity, and cash-like/defensive groups.
- Robust grid v2 must be pre-registered before evaluation:
  - `momentum_window`: `5`, `10`, `20`, `40`, `60`, `120`
  - `rebalance_days`: `3`, `5`, `10`, `20`
  - `top_n`: `1`, `2`, `3`, `4`, `5`
  - `weights`: `equal`, `50/25/25`, `40/30/30`, `60/20/20`, `60/15/15/10`
  - `skip_negative`: `true`, `false`
  - `domestic_only`: `true`, `false`
  - `defensive_fallback`: `true`, `false`
  - `group_max_1_constraint`: `true`, `false`
- No post-hoc parameter tuning.
- Since Tencent qfq source lacks amount/NAV, use proxy liquidity only and explicitly label the limitation.
- Stress 1/3/5/10/20 bps slippage.
- Use random ETF selection, random group assignment, random rebalance dates, random momentum labels, and false-discovery controls.

Allowed ETF hypothesis labels:

- `ETF_RESEARCH_HYPOTHESIS_INTERESTING`
- `ETF_RESEARCH_HYPOTHESIS_WEAK`
- `ETF_RESEARCH_HYPOTHESIS_UNSTABLE`
- `ETF_RESEARCH_HYPOTHESIS_COST_LIMITED`
- `ETF_RESEARCH_HYPOTHESIS_DATA_LIMITED`

No candidate, recommendation, readiness, daily signal push, or product-route label may be emitted.

## B. A-share Equity Signal Lane

| Task | Name | Deliverables |
|---|---|---|
| `A-WIN-R19-1` | R18 failure-mode clustering | `reports/workspace_dispatch/windows_wsl2_r19_r18_failure_mode_clustering_20260707.md`; `.csv` |
| `A-WIN-R19-2` | Targeted rescue of R18 top blocked-by-instability families | `reports/workspace_dispatch/windows_wsl2_r19_instability_rescue_diagnostics_20260707.md`; `.csv` |
| `A-WIN-R19-3` | Targeted rescue of blocked-by-validation families | `reports/workspace_dispatch/windows_wsl2_r19_validation_failure_rescue_20260707.md`; `.csv` |
| `A-WIN-R19-4` | ETF-informed A-share factor transfer test | `reports/workspace_dispatch/windows_wsl2_r19_etf_informed_equity_regime_transfer_20260707.md`; `.csv` |
| `A-WIN-R19-5` | Conditional equity wide prequalification | `reports/workspace_dispatch/windows_wsl2_r19_equity_wide_prequalification_or_skip_20260707.md`; `.csv` |

## Equity Signal Rules

- Cluster the 130 R18 validation-only search rows into failure modes: validation failure, instability, trade count, cost, drawdown, ML-filter weakness, portfolio-construction weakness, and universe limitation.
- Use only validation-safe transformations for rescue diagnostics.
- Do not select parameters from test results.
- Use ETF regime classifications only as research diagnostics; do not create ETF/equity combined trading instructions.
- Full-frame wide strategy search remains blocked.
- Only update wide prequalification if validation-safe rescue produces eligible rows; otherwise output `NO_R19_EQUITY_WIDE_RESEARCH_PROBE_ELIGIBLE`.

## C. market_data Support

| Task | Name | Deliverables |
|---|---|---|
| `MD-R19-1` | ETF research manifest schema | `reports/codex_dev/etf_rotation_r19_research_manifest_schema.md`; `.json` |
| `MD-R19-2` | No-overclaim tests for ETF research outputs | `tests/test_etf_rotation_r19_overclaim.py` |

market_data must encode ETF research dataset, universe grouping, timing rule, cost/liquidity limitation, walk-forward, bootstrap/permutation, and no-action boundary. Negative tests must ensure ETF leaderboard, screenshot reproduction, ETF hypothesis labels, and ETF/equity regime transfer are not recommendation, ticket, readiness, candidate, product route, or daily signal push.

## D. strategy_work

| Task | Name | Deliverables |
|---|---|---|
| `SW-R19-1` | ETF + A-share parallel strategy memo | `reports/planning/windows_wsl2_parallel_strategy_search_batch_r19_strategy_memo_20260707.md` |
| `SW-R19-2` | Final sync after source callbacks | `reports/planning/windows_wsl2_parallel_strategy_search_batch_r19_final_sync_20260707.md` |

strategy_work may create the initial memo from accepted baseline evidence, but must not create final sync until accepted A_Share_Monitor and market_data callback envelopes are available.

## E. quant-proj

| Task | Name | Deliverables |
|---|---|---|
| `QP-R19-1` | Intake and dispatch | `reports/workspace_dispatch/windows_wsl2_parallel_strategy_search_batch_r19_20260707_intake.md`; this task packet; dispatch summary |
| `QP-R19-2` | Result summary and closeout | `reports/workspace_dispatch/windows_wsl2_parallel_strategy_search_batch_r19_20260707_result_summary.md`; `reports/workspace_dispatch/windows_wsl2_parallel_strategy_search_batch_r19_20260707_closeout.md` |

## Stop Conditions

- `ETF_DAILY_SIGNAL_PUSH_ATTEMPTED`
- `ETF_RESEARCH_HYPOTHESIS_WRITTEN_AS_RECOMMENDATION`
- `SHADOW_LEADERBOARD_USED_AS_ACTIONABLE_RANKING`
- `MARKET_DATA_PRODUCT_ROUTE_ACTIVATION_ATTEMPTED`
- `STRATEGY_CANDIDATE_PROMOTION_ATTEMPTED`
- `TEST_RESULT_USED_TO_SELECT_PARAMETERS`
- `FULL_FRAME_WIDE_STRATEGY_SEARCH_ATTEMPTED`
- `NETWORK_OR_DB_WRITE_REQUIRED_OUTSIDE_FASTPATH_SCOPE`
- `SECRET_OR_ENV_ACCESS_REQUIRED`

## Validation

Required where applicable:

- `py_compile` for changed Python.
- focused pytest for changed tests.
- `agent_safety_check.py`.
- JSON parse for JSON artifacts.
- `git diff --check`.
- forbidden overclaim scan.
- no same-day close-to-close ETF timing.
- no daily signal push.
- no full-frame wide strategy search.
- no market_data product-route activation.
- no unapproved DB/cache write/rebuild outside research fastpath scope.

## Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_PARALLEL_STRATEGY_SEARCH_BATCH_R19_20260707
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
ETF_KEY_RESULTS:
EQUITY_KEY_RESULTS:
STRATEGY_CANDIDATE_AVAILABLE:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
