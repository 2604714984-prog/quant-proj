# Implementation Task — US SPY 200-Session Trend/Cash Baseline Result

Date: 2026-07-19  
Repository: `2604714984-prog/quant-proj`  
Research ID: `US_SPY_200D_TREND_CASH_RETROSPECTIVE_BASELINE_V1_20260719`

## 1. Objective

Produce one actual, immutable historical result using data already present in the central DuckDB.

This is:

```text
broad-market state benchmark
retrospective secondary evidence
not a new stock-selection family
not strict PIT evidence
not a strategy candidate
```

Do not inspect or reuse archived strategy returns, parameters beyond the formula frozen below, or any Holdout result before the definition/code commit is pushed.

## 2. Exact data identity

Preferred object:

```text
us_equity_research.us_daily_total_return_research
snapshot_id=tiingo_raw_20260711T142010Z_5c24877d23cfc4a0
symbol=SPY
```

Required fields or unambiguous equivalents:

```text
trade_date
adjusted_open
adjusted_close
```

Requirements:

```text
positive finite values
one row per trade_date
strictly increasing dates
coverage sufficient for 200-session warm-up and all frozen splits
read-only database
before/after SHA-256 identical
no WAL
```

If adjusted open or adjusted close cannot be identified without guessing, emit `INPUT_BLOCKED` and stop. Do not call a provider or modify the database.

The historical classification is fixed:

```text
RETROSPECTIVE_SECONDARY_NOT_STRICT_PIT
```

No historical `available_at`, revision, account-level corporate-action, or candidate claim is permitted.

## 3. Frozen strategy mechanics

### State

At each month-end accepted SPY row after at least 200 complete sessions:

```text
TREND_ON when adjusted_close > arithmetic mean of the latest 200 adjusted_close values, including the decision close
TREND_OFF otherwise
```

No tolerance band, confirmation period, alternative moving average, volatility rule, breadth rule, or parameter variant.

### Execution proxy

```text
decision: month-end adjusted close
execution: next available SPY row adjusted open
TREND_ON target: 100% SPY
TREND_OFF target: 100% cash
cash return: 0
leverage: false
shorting: false
```

If no next row exists, purge the incomplete terminal interval.

### Costs

Charge cost on absolute exposure change:

```text
primary one-way cost = 15 bps
stress one-way cost = 30 bps
```

Include first entry and final liquidation. No additional slippage model or parameter scan.

## 4. Frozen periods

Use rows only through `2026-06-30`.

```text
warm-up source: earliest available SPY history

development diagnostic:
2000-01-01 through 2009-12-31

validation gated:
2010-01-01 through 2017-12-31

retrospective holdout gated:
2018-01-01 through 2026-06-30

forbidden:
after 2026-06-30
```

Intervals crossing a split boundary are assigned by execution date and must end within the same split; otherwise purge them.

Development may be reported but cannot alter mechanics or gates.

## 5. Comparators

Calculate complete-calendar monthly returns for:

```text
B0_CASH:
0 return

B1_SPY_BUY_HOLD:
100% SPY throughout, using the same adjusted-open proxy and entry/final-exit costs

B2_SPY_200D_TREND_CASH:
frozen state gate above
```

No stock selection, breadth input, VIX, QQQ, HYG/LQD, or alternative ETF.

## 6. Required metrics

For validation, holdout, combined validation+holdout, and full post-warm-up history, report at both cost levels:

```text
complete_month_count
cumulative_net_return
CAGR
annualized_volatility
maximum_drawdown
Calmar
positive_month_fraction
time_in_market
state_transition_count
one_way_turnover
cost_drag
```

Also report:

```text
missing_or_nonfinite_count
duplicate_date_count
purged_boundary_interval_count
database_sha256_before_after
input_snapshot_identity
```

Do not publish daily rows or a trade list in the terminal result.

## 7. Frozen adjudication

Primary gates use 15 bps.

`RETROSPECTIVE_BASELINE_PASS_TO_SHADOW_REVIEW` requires all:

```text
1. validation B2 CAGR > 0
2. holdout B2 CAGR > 0
3. holdout B2 maximum drawdown is strictly less severe than B1
4. holdout B2 Calmar is strictly greater than B1
5. combined validation+holdout B2 CAGR >= 50% of B1 CAGR
6. combined validation+holdout time_in_market is between 20% and 90%
7. at 30 bps, combined validation+holdout B2 CAGR > 0
8. zero duplicate, missing, nonfinite, or identity failures
```

If any gate fails:

```text
RETROSPECTIVE_BASELINE_FAIL
```

If required inputs cannot be identified safely:

```text
INPUT_BLOCKED
```

No retuning or alternate lookback is permitted.

## 8. Deliverables

Create only:

```text
research/definitions/us_spy_200d_trend_cash_retrospective_baseline_v1.json
src/quant_system/research/us_spy_200d_trend_cash.py
scripts/run_us_spy_200d_trend_cash_result.py
tests/test_us_spy_200d_trend_cash.py
reports/validation/us_spy_200d_trend_cash_retrospective_baseline_v1_result.json
reports/validation/us_spy_200d_trend_cash_retrospective_baseline_v1_run.json
```

The result and run receipt are committed only after definition/code/tests are committed and pushed.

No roadmap edit. No new framework. No external audit document in the implementation PR.

## 9. Verification

Required:

```text
focused tests
full pytest
Ruff
wheel build
fresh wheel install
pip check
repository-external quant info
git diff --check
strict JSON duplicate-key and nonfinite rejection
worktree clean
remote HEAD exact
GitHub CI green
```

## 10. Boundaries

Always:

```text
strategy_candidate_available=false
shadow_authorized=false
paper_authorized=false
broker_authorized=false
live_authorized=false
auto_trading_authorized=false
```

A PASS only authorizes an exact-head external review of possible read-only Shadow.

## Callback

```text
STATUS:
RESEARCH_ID:
BASE_COMMIT:
DEFINITION_COMMIT:
RESULT_COMMIT:
RESULT_STATUS:
VALIDATION_PRIMARY_METRICS:
HOLDOUT_PRIMARY_METRICS:
COMBINED_PRIMARY_METRICS:
COMBINED_STRESS_METRICS:
GATE_COUNTS:
DATABASE_IDENTITY_STATUS:
RESULT_URL:
RUN_RECEIPT_URL:
CI_URL:
STRATEGY_CANDIDATE_AVAILABLE: false
NEXT_ACTION:
```
