# Handoff: A_Share_Monitor ETF Rotation E1

Target thread: `019f387b-617e-7273-b539-161216ae3002`
Target repo: `/home/rongyu/workspace/A_Share_Monitor`
Controller repo: `/home/rongyu/workspace/quant-proj`
Callback target: Quant-Dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`
Batch: `WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_20260707`

## Context

User supplied a screenshot of an A-share ETF momentum rotation strategy:

- Group4 / Top3 / `50/25/25`.
- 20-day momentum.
- Rebalance every 5 trading days.
- 14 ETFs grouped into broad/style/overseas/defensive.
- Reported 640-day backtest around `+63.84%`.

Treat this as a research hypothesis only, not evidence.

## Goal

Add ETF momentum rotation as a separate research-only strategy family.

Do not create recommendation, ticket, eligibility candidate, readiness, product route, broker/order/paper/live/auto, daily signal push, or strategy candidate promotion.

## Tasks

1. `ETF-E1-1` ETF universe freeze.
2. `ETF-E1-2` ETF data audit and no-future timing.
3. `ETF-E1-3` Screenshot strategy reproduction.
4. `ETF-E1-4` Baseline comparison.
5. `ETF-E1-5` Pre-registered parameter grid.
6. `ETF-E1-6` Walk-forward validation.
7. `ETF-E1-7` Cost and slippage stress.
8. `ETF-E1-8` Regime attribution.
9. `ETF-E1-9` Group contribution and dependency analysis.
10. `ETF-E1-10` Bootstrap and permutation test.
11. `ETF-E1-11` Research-only ETF rotation leaderboard.

## Deliverables

- `reports/workspace_dispatch/etf_rotation_e1_universe_freeze_20260707.md`
- `reports/workspace_dispatch/etf_rotation_e1_universe_freeze_20260707.csv`
- `reports/workspace_dispatch/etf_rotation_e1_data_audit_20260707.md`
- `reports/workspace_dispatch/etf_rotation_e1_data_audit_20260707.json`
- `reports/workspace_dispatch/etf_rotation_e1_screenshot_reproduction_20260707.md`
- `reports/workspace_dispatch/etf_rotation_e1_screenshot_reproduction_20260707.csv`
- `reports/workspace_dispatch/etf_rotation_e1_baseline_comparison_20260707.md`
- `reports/workspace_dispatch/etf_rotation_e1_baseline_comparison_20260707.csv`
- `reports/workspace_dispatch/etf_rotation_e1_pre_registered_grid_20260707.md`
- `reports/workspace_dispatch/etf_rotation_e1_pre_registered_grid_20260707.json`
- `reports/workspace_dispatch/etf_rotation_e1_walk_forward_validation_20260707.md`
- `reports/workspace_dispatch/etf_rotation_e1_walk_forward_validation_20260707.csv`
- `reports/workspace_dispatch/etf_rotation_e1_cost_slippage_stress_20260707.md`
- `reports/workspace_dispatch/etf_rotation_e1_cost_slippage_stress_20260707.csv`
- `reports/workspace_dispatch/etf_rotation_e1_regime_attribution_20260707.md`
- `reports/workspace_dispatch/etf_rotation_e1_regime_attribution_20260707.csv`
- `reports/workspace_dispatch/etf_rotation_e1_group_contribution_20260707.md`
- `reports/workspace_dispatch/etf_rotation_e1_group_contribution_20260707.csv`
- `reports/workspace_dispatch/etf_rotation_e1_bootstrap_permutation_20260707.md`
- `reports/workspace_dispatch/etf_rotation_e1_bootstrap_permutation_20260707.csv`
- `reports/workspace_dispatch/etf_rotation_e1_research_only_leaderboard_20260707.csv`
- `reports/workspace_dispatch/etf_rotation_e1_research_only_leaderboard_notes_20260707.md`

## Rules

- If ETF data is not locally available, stop and output `HG_EXEC_REQUIRED_FOR_ETF_DATA_FETCH`.
- Do not perform provider/network fetch without separate HG-EXEC.
- Do not perform DB/cache write or rebuild without separate HG-EXEC.
- Signal timing must be close `T` signal and `T+1` execution unless otherwise documented.
- No same-day close-to-close execution.
- No post-hoc parameter tuning.
- No strategy candidate promotion.
- No recommendation/advice.
- No product route activation.
- No market_data activation.
- Research-only leaderboard must not be actionable.

## Validation

- `py_compile` PASS if code changed.
- focused pytest PASS if code/tests changed.
- JSON parse PASS.
- `git diff --check` PASS.
- forbidden overclaim scan PASS.
- no recommendation/ticket/readiness/product/trading wording.
- `strategy_candidate_available=false` unless a later explicitly authorized research candidate protocol exists.

## Callback

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
