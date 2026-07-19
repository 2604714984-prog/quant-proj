# Execution Task — US SPY/QQQ/GLD Dual-Momentum Result Sprint

Date: 2026-07-19  
Repository: `2604714984-prog/quant-proj`  
Research ID: `US_SPY_QQQ_GLD_DUAL_MOMENTUM_V1_20260719`

## 1. Objective

Produce one real, immutable numerical result for a monthly cross-asset dual-momentum account using existing retrospective Tiingo SPY, QQQ and GLD data.

This is one direct result PR. Do not create a separate Phase 0, candidate-slate, feasibility, roadmap or implementation-only PR.

Allowed terminal states:

```text
RETROSPECTIVE_DUAL_MOMENTUM_PASS_TO_EXTERNAL_REVIEW
RETROSPECTIVE_DUAL_MOMENTUM_FAIL
INPUT_BLOCKED
LEGACY_EXACT_DUPLICATE_CLOSE_NO_OUTCOME
```

## 2. Lineage and duplicate boundary

The rejected US31/US36/US41/US46 lines are fixed-weight ETF portfolios. They may be used only as failure memory or comparators.

This new mechanism is:

```text
monthly relative momentum among SPY, QQQ and GLD
+ absolute momentum cash gate
+ one selected asset or cash
```

Before implementation, inspect only frozen definitions/configuration for an exact prior implementation. Do not inspect prior result values.

Only an exact prior combination of:

```text
same three assets
same 252-session signal
same monthly decision/execution
same highest-return selection
same positive-return cash gate
```

blocks registration. General conceptual momentum overlap does not block this benchmark.

If an exact duplicate exists, publish one concise `LEGACY_EXACT_DUPLICATE_CLOSE_NO_OUTCOME` result in the same PR and stop.

## 3. Frozen data contract

Use only the existing retrospective Tiingo snapshot already present in the central read-only DuckDB:

```text
table=us_equity_research.us_daily_total_return_research
snapshot_id=tiingo_raw_20260711T142010Z_5c24877d23cfc4a0
symbols=SPY,QQQ,GLD
cutoff=2026-06-30
classification=RETROSPECTIVE_SECONDARY_NOT_STRICT_PIT
```

Required fields:

```text
trade_date
symbol
open
adj_open
adj_close
```

If the exact field names differ, use the already stored raw-open and adjusted total-return equivalents only when their identities are explicit. Do not call a provider, write the database or silently substitute close for open.

Use the intersection of exact common source sessions for SPY, QQQ and GLD. No forward fill. A missing required session or nonfinite/nonpositive field is `INPUT_BLOCKED`.

Bind:

```text
database SHA-256 before and after
snapshot identity
consumed row count
consumed common-session hash
symbol/date duplicate count
WAL absence
```

## 4. Frozen strategy

### Decision and signal

At the final common source session of each calendar month:

```text
lookback=252 common accepted sessions
return_i=adj_close_i[t] / adj_close_i[t-252] - 1
selected_asset=argmax(return_SPY, return_QQQ, return_GLD)
tie_break=SPY, then QQQ, then GLD
```

### Absolute gate

```text
if selected_return > 0:
    target selected asset at 100 percent
else:
    target cash at 100 percent
```

No additional trend, volatility, breadth, drawdown, macro, weekday or calendar filter.

### Execution

```text
capital_usd=40000
whole_shares_only=true
fractional_shares=false
leverage=false
shorting=false
rebalance=monthly
decision=month-end common-session close
execution=next common-session open
cash_return=0
```

For share count and transaction notional, use raw open. For subsequent total-return marking and exit value, use the adjusted-open total-return ratio anchored to the raw entry notional.

At each rebalance:

```text
sell the prior asset if the target changes
buy the new target with available cash
if the target asset is unchanged, do not create artificial sell/buy turnover
```

The final evaluated split includes terminal liquidation cost.

### Costs

```text
primary_one_way_cost_bps=15
stress_one_way_cost_bps=30
additional_commission_model=false
```

## 5. Splits

Use complete rebalance intervals only.

```text
development=2006-01-01..2009-12-31 diagnostic only
validation=2010-01-01..2017-12-31 gated
retrospective_holdout=2018-01-01..2026-06-30 gated
forbidden_after=2026-06-30
```

Purge an interval unless its decision, entry and next rebalance exit all remain within one split.

## 6. Comparators

Evaluate the same USD 40,000 whole-share account and cost assumptions:

```text
B0_CASH
B1_SPY_BUY_HOLD
B2_STATIC_EQUAL_WEIGHT_SPY_QQQ_GLD
B3_DUAL_MOMENTUM_CASH
```

`B2` is initialized one-third per asset at the split start and then held without periodic rebalancing. It is a comparator, not a reopened US41 strategy.

## 7. Required metrics

For each comparator, split and cost:

```text
complete_interval_count
cumulative_net_return
CAGR
annualized_volatility
maximum_drawdown
Calmar
positive_month_fraction
time_in_market
one_way_turnover
cost_drag
whole_share_cash_utilization
```

For B3 also report:

```text
SPY selection count
QQQ selection count
GLD selection count
cash selection count
selection share by target
state transition count
largest calendar-year profit contribution
worst monthly interval return
```

No security-level list beyond the three frozen ETF identifiers is needed.

## 8. Frozen eight gates

At primary 15 bps unless stated otherwise:

```text
1. validation B3 CAGR > 0
2. holdout B3 CAGR > 0
3. holdout B3 maximum drawdown is less severe than B1
4. holdout B3 Calmar is strictly greater than both B1 and B2
5. combined validation+holdout B3 CAGR is positive and at least 50 percent of B1 CAGR
6. combined validation+holdout B3 Calmar is strictly greater than B2 Calmar
7. at 30 bps, combined B3 CAGR > 0 and largest calendar-year contribution < 40 percent
8. zero duplicate, missing, nonfinite, identity, whole-share or database failures
```

Any failed gate returns:

```text
RETROSPECTIVE_DUAL_MOMENTUM_FAIL
```

Do not change the lookback, assets, tie-break, cash gate, costs, splits or gates after outcome access.

## 9. Required files in one PR

```text
research/definitions/us_spy_qqq_gld_dual_momentum_v1.json
src/quant_system/research/us_spy_qqq_gld_dual_momentum.py
scripts/run_us_spy_qqq_gld_dual_momentum_once.py
tests/test_us_spy_qqq_gld_dual_momentum.py
reports/validation/us_spy_qqq_gld_dual_momentum_v1_result.json
reports/validation/us_spy_qqq_gld_dual_momentum_v1_run.json
```

Do not add a new framework, registry, manifest system, CLI command or database layer.

Preferred code budget:

```text
calculation module <= 250 lines
runner <= 300 lines
focused tests <= 200 lines
```

## 10. Validation

Required:

```text
focused tests
full repository pytest
Ruff
py_compile
strict JSON duplicate/nonfinite rejection
dry-run proving no database open or output write
read-only database hash before/after
no WAL
exact-head GitHub CI
```

## 11. Merge and review rule

```text
FAIL or INPUT_BLOCKED:
Manager scope review + green CI + terminal merge

PASS:
keep PR unmerged and request exact-head external review
```

No Shadow, Paper, broker, live, Qlib or RD-Agent work is authorized by this task.

## 12. Required callback

```text
STATUS:
PR_URL:
HEAD_SHA:
TREE_SHA:
RESULT_STATUS:
GATES_PASSED:
VALIDATION_B3_CAGR:
HOLDOUT_B3_CAGR:
HOLDOUT_B3_MAX_DRAWDOWN:
HOLDOUT_B3_CALMAR:
COMBINED_B3_CAGR_15BPS:
COMBINED_B3_CAGR_30BPS:
COMBINED_B1_CAGR:
COMBINED_B2_CALMAR:
SELECTION_COUNTS:
TURNOVER:
RESULT_JSON_URL:
RUN_RECEIPT_URL:
DATABASE_UNCHANGED:
STRATEGY_CANDIDATE_AVAILABLE:false
NEXT_ACTION:
```
