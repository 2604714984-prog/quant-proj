# WINDOWS_WSL2 DeepSeek Audit Fix Summary 20260708

Source audit report: `G:\quant_proj\deepseek_audit_reports\20260708_wsl2_quant_projects_deep_review.md`

## Commits

| Repo | Branch | Commit | Status |
|---|---|---|---|
| `A_Share_Monitor` | `codex/task-packet-r20-v2-20260708` | `75e2e405dda2fc0b88ecedf80ce98a8cb3b54966` | pushed |
| `market_data` | `main` | `cfd67028ee194e84b9b03e9a94356c8edfd6ac1a` | pushed |
| `strategy_work` | `main` | `c8f865267402bcbc24960e040584ac804ff351de` | pushed |
| `US_Stock_Monitor` | `main` | `2a5bce03a71d4cc1637021f485d4c5ddf2d6b3df` | pushed |

## Critical / High Fixes

| Finding | Result |
|---|---|
| C1 market_data macOS registry paths | Replaced with portable workspace-relative paths and `MARKET_DB_ROOT` resolution; validation now records resolved paths. |
| C2 strategy_work macOS chdir | Replaced with dynamic A_Share_Monitor root discovery and `A_SHARE_MONITOR_ROOT` override. |
| C3 A-share amount unit multiplier | Changed default/config from 1,000 to 10,000 for Tushare amount units. |
| H1 feature required columns | Added explicit `trade_date` / `ts_code` validation in A-share backtest engine. |
| H2 low/high degraded stop/take fallback | Added degraded-signal warning metadata when low/high are missing and close fallback is used. |
| H3 limit lock tolerance | Switched to `math.isclose(rel_tol=1e-6, abs_tol=0.001)` plus directional comparisons. |
| H4 Sharpe first-return bias | Changed returns from `pct_change().fillna(0)` to `pct_change().dropna()`. |
| H5 risk model too thin | Expanded risk status checks for drawdown, single-stock loss, monthly win rate, volatility, trade count, and turnover. |

## Medium / Low Fixes

| Finding | Result |
|---|---|
| M1 pending order double filtering | Replaced tuple-comprehension double scan with explicit due/pending split. |
| M2 duplicate daily row index | Existing first-row selection preserved; covered by new engine tests. |
| M3 weekly rebalance cross-year boundary | Changed weekly comparison to `(iso_year, iso_week)`. |
| M4 same-day sale proceeds risk | Due orders now execute buys before sells, preventing same-execute-date sale proceeds from funding buys. |
| M5 Series `.empty` missing-bar check | Replaced with `row is None or len(row) == 0`. |
| M6 affordable quantity loop | Replaced linear lot decrement with bounded binary search. |
| M7 close fallback to avg cost | Position rows now emit `close_missing_fallback_to_avg_cost`. |
| M8 boolean identity in evaluator | Replaced `is False` gate with `is not True`. |
| M9 survivor-bias check | Added list-date evidence, no pre-listing rows, delist evidence, and no post-delist rows. |
| M10 US short split boundary | `_split_indices` now fails explicitly for fewer than three observations. |
| M11 US minimum position weight | Added `min_weight_per_position` config and normalization filter. |
| M12 US hardcoded thresholds | US evaluator accepts threshold overrides while retaining conservative defaults. |
| L2 A-share stamp tax | Updated sell stamp tax default/config to 0.001. |
| L3 duplicate benchmark excess calculation | Computes excess once and reuses it for alpha/excess fields. |

The remaining low-severity items are naming/refactor/backlog items (`run` vs `run_chunked` duplication, `broker_sim.py` compatibility name, extended-hours disabled-by-policy behavior, controller backlog size). They do not block the critical/high runtime fixes and were left as non-behavioral cleanup candidates rather than broad refactors.

## Validation

`A_Share_Monitor`:

- `py_compile` PASS for changed backtest/research modules.
- Focused pytest PASS: `17 passed`.
- `agent_safety_check.py` PASS.
- `git diff --check` PASS.

`market_data`:

- `py_compile` PASS for `adapters/registry.py`.
- Focused pytest PASS: `8 passed`.
- `git diff --check` PASS.

`strategy_work`:

- `py_compile` PASS for `analysis/param_sweep.py`.
- `git diff --check` PASS.

`US_Stock_Monitor`:

- `py_compile` PASS for changed backtest/config/research modules.
- Focused pytest PASS: `13 passed`.
- `agent_safety_check.py` PASS.
- `git diff --check` PASS.

## Boundary

No recommendation/advice, ticket, eligibility candidate, strategy candidate promotion, readiness/product route activation, daily signal push, broker/order/paper/live/auto execution, raw-data migration into controller, active schema/registry activation, or secret output was introduced.
