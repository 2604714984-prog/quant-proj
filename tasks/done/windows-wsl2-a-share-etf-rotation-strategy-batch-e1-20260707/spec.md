# WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_20260707 Spec

## Objective

Add A-share ETF momentum rotation as a separate research-only strategy family and test whether the screenshot idea survives strict data, timing, cost, validation, and robustness checks.

Do not replicate screenshot performance as evidence unless the strategy is reproduced under the controls below. Do not create recommendation, ticket, eligibility candidate, strategy candidate promotion, readiness, product route, broker/order/paper/live/auto, or daily signal push.

## Context

The user supplied a screenshot of an A-share ETF momentum rotation strategy:

- Group4 / Top3 / `50/25/25`.
- 20-day momentum.
- Rebalance every 5 trading days.
- 14 ETFs grouped into broad/style/overseas/defensive.
- Reported 640-day backtest around `+63.84%`.

Treat this as a hypothesis only, not evidence.

## A_Share_Monitor Tasks

| Task | Name | Deliverables |
|---|---|---|
| `ETF-E1-1` | ETF universe freeze | `reports/workspace_dispatch/etf_rotation_e1_universe_freeze_20260707.md`; `reports/workspace_dispatch/etf_rotation_e1_universe_freeze_20260707.csv` |
| `ETF-E1-2` | ETF data audit and no-future timing | `reports/workspace_dispatch/etf_rotation_e1_data_audit_20260707.md`; `reports/workspace_dispatch/etf_rotation_e1_data_audit_20260707.json` |
| `ETF-E1-3` | Screenshot strategy reproduction | `reports/workspace_dispatch/etf_rotation_e1_screenshot_reproduction_20260707.md`; `reports/workspace_dispatch/etf_rotation_e1_screenshot_reproduction_20260707.csv` |
| `ETF-E1-4` | Baseline comparison | `reports/workspace_dispatch/etf_rotation_e1_baseline_comparison_20260707.md`; `reports/workspace_dispatch/etf_rotation_e1_baseline_comparison_20260707.csv` |
| `ETF-E1-5` | Pre-registered parameter grid | `reports/workspace_dispatch/etf_rotation_e1_pre_registered_grid_20260707.md`; `reports/workspace_dispatch/etf_rotation_e1_pre_registered_grid_20260707.json` |
| `ETF-E1-6` | Walk-forward validation | `reports/workspace_dispatch/etf_rotation_e1_walk_forward_validation_20260707.md`; `reports/workspace_dispatch/etf_rotation_e1_walk_forward_validation_20260707.csv` |
| `ETF-E1-7` | Cost and slippage stress | `reports/workspace_dispatch/etf_rotation_e1_cost_slippage_stress_20260707.md`; `reports/workspace_dispatch/etf_rotation_e1_cost_slippage_stress_20260707.csv` |
| `ETF-E1-8` | Regime attribution | `reports/workspace_dispatch/etf_rotation_e1_regime_attribution_20260707.md`; `reports/workspace_dispatch/etf_rotation_e1_regime_attribution_20260707.csv` |
| `ETF-E1-9` | Group contribution and dependency analysis | `reports/workspace_dispatch/etf_rotation_e1_group_contribution_20260707.md`; `reports/workspace_dispatch/etf_rotation_e1_group_contribution_20260707.csv` |
| `ETF-E1-10` | Bootstrap and permutation test | `reports/workspace_dispatch/etf_rotation_e1_bootstrap_permutation_20260707.md`; `reports/workspace_dispatch/etf_rotation_e1_bootstrap_permutation_20260707.csv` |
| `ETF-E1-11` | Research-only ETF rotation leaderboard | `reports/workspace_dispatch/etf_rotation_e1_research_only_leaderboard_20260707.csv`; `reports/workspace_dispatch/etf_rotation_e1_research_only_leaderboard_notes_20260707.md` |

## Required Universe Versions

- `screenshot_14_etf_universe`
- `liquid_core_etf_universe_20_30`
- `domestic_only_etf_universe`

Each ETF record must include code, name, type, group, listing date, cross-border flag, defensive/bond/money/gold flag where applicable, volume/liquidity filter, and data date range.

## Required Strategy Definition For Reproduction

- `Group4`
- `Top3`
- weights `50/25/25`
- `momentum_window=20`
- `rebalance_days=5`
- `skip_negative=false`
- `group_max=1`
- bottom group excluded if required by the screenshot definition

If reproduction differs from the screenshot, explain whether the cause is universe, time range, data source, cost model, signal timing, or adjustment method.

## Pre-Registered Grid

- `momentum_window`: `10`, `20`, `40`, `60`
- `rebalance_days`: `5`, `10`, `20`
- `top_n`: `1`, `2`, `3`, `4`
- `weights`: `equal`, `50/25/25`, `60/20/20`, `60/15/15/10`
- `skip_negative`: `true`, `false`
- `group_constraint`: `true`, `false`
- `domestic_only`: `true`, `false`

Write the grid before running it. Do not change the grid after seeing test results.

## Timing Rules

- Signal uses close data through `T`.
- Trade executes at `T+1` according to documented execution price.
- No same-day close-to-close execution.
- Rebalance dates must handle holidays and missing sessions explicitly.

## Stop Conditions

- `HG_EXEC_REQUIRED_FOR_ETF_DATA_FETCH`
- `NETWORK_PROVIDER_FETCH_ATTEMPTED_WITHOUT_HG_EXEC`
- `DB_OR_CACHE_WRITE_ATTEMPTED_WITHOUT_HG_EXEC`
- `SAME_DAY_CLOSE_TO_CLOSE_EXECUTION_USED`
- `POST_HOC_PARAMETER_TUNING_DETECTED`
- `ETF_ROTATION_RESULT_WRITTEN_AS_RECOMMENDATION`
- `ETF_ROTATION_RESULT_WRITTEN_AS_TICKET`
- `ETF_ROTATION_RESULT_WRITTEN_AS_CANDIDATE_OR_READINESS`
- `MARKET_DATA_PRODUCT_ROUTE_ACTIVATION_ATTEMPTED`
- `SECRET_OR_ENV_ACCESS_REQUIRED`

## Validation

Required where applicable:

- `py_compile` for changed Python.
- focused pytest for changed tests.
- JSON parse for JSON artifacts.
- `git diff --check`.
- forbidden overclaim scan.
- no recommendation/ticket/readiness/product/trading wording.
- `strategy_candidate_available=false` unless a later explicitly authorized research candidate protocol exists.

## Callback Envelope

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_20260707
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
KEY_RESULTS:
ETF_DATA_STATUS:
WIDE_OR_LIVE_SIGNAL_STATUS:
STRATEGY_CANDIDATE_AVAILABLE:
BOUNDARY_RESULT:
EXTERNAL_AUDIT_TRIGGER_OPEN:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
