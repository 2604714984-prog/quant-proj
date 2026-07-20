# Scout task — survivor-aware US stock data and mechanism qualification

Date: 2026-07-20  
Mode: outcome-blind, read-only research  
Formal strategy authority: none

## Objective

Determine which stock-level price, volume, liquidity and market-structure mechanisms can be supported by one bounded survivor-aware daily-data contract.

The task is not a provider purchase request and must not calculate returns.

## Minimum data contract

Assess whether one canonical source can supply:

```text
permanent security identifier
historical ticker and exchange mapping
ordinary common-stock classification
listing and delisting dates
delisting/terminal value or explicit terminal policy
raw OHLCV
split and cash-distribution identity
adjusted OHLCV with documented methodology
inactive and failed securities
trading-status history
immutable snapshot and row hashes
license permitting local research use
```

Index membership is optional for mechanisms that can use a major-exchange/liquidity universe, but today's surviving symbols may never be used as the historical universe.

## Mechanism groups to qualify

### Price anchors and diffusion

- 52-week-high proximity;
- industry momentum;
- residual momentum;
- fresh range breakout persistence;
- large overnight-gap continuation or reversal;
- stock-level overnight versus intraday decomposition.

### Liquidity and short-horizon reversal

- five-day market-residual reversal;
- industry-residual reversal as a robustness condition, not a separate search grid;
- Amihud illiquidity exclusion;
- abnormal-volume attention;
- turnover shock;
- opening-gap residual signal.

### Risk and speculative demand

- MAX lottery avoidance;
- low residual volatility;
- downside beta;
- quality plus low beta only if required fundamentals are separately qualified.

### Corporate-action and benchmark events

- index inclusion/deletion/reconstitution demand;
- stock-split announcement effect;
- seasoned equity offering avoidance where event identity can be joined.

## Required provider assessment

Compare at most three routes. Prefer one canonical source and one read-only cross-check.

For each route record:

```text
historical coverage start
inactive/delisted coverage
terminal return handling
corporate-action method
identifier history
index membership availability
API/export form
cost and license
sample export availability
reproducibility and update policy
WSL/Linux compatibility
```

No purchase is authorized. A paid source may be classified `BOUNDED_PURCHASE_DECISION` only.

## Mechanism qualification output

For at least 15 existing Atlas mechanisms, report:

```text
source class
minimum universe rule
required history
causal signal timing
expected selection size
turnover and conservative cost exposure
USD 40000 whole-share fit
survivorship/PIT failure modes
minimum implementation size
READY_FOR_PREREGISTRATION / BOUNDED_INPUT_TASK / PARK / CLOSE
```

## Required stress screens

A mechanism cannot be `READY_FOR_PREREGISTRATION` if it depends on:

- microcaps for most of the expected spread;
- shorting or leverage;
- current constituents backfilled into history;
- missing delisting outcomes;
- adjusted prices without raw/corporate-action identity;
- a daily turnover level unlikely to survive conservative costs;
- an outcome-informed variant of a closed momentum or trend line.

## Preferred priority order

After data qualification, use this ordering for readiness review:

```text
1. 52-week-high proximity
2. five-day market-residual reversal
3. abnormal-volume attention
4. Amihud liquidity exclusion
5. stock-level overnight/intraday atlas
6. stock-split event
7. low residual volatility or MAX avoidance
```

This is a review order, not implementation authorization.

## Boundaries

Do not:

- read price values or returns;
- construct rankings;
- calculate sample performance;
- download a full paid dataset;
- write canonical DuckDB;
- create a stock backtester;
- use Qlib or RD-Agent;
- open Validation or Holdout.

Small provider sample files may be inspected only after explicit Manager authorization and must contain no strategy calculation.

## Deliverable

One compact report with:

```text
provider routes reviewed <=3
mechanisms qualified >=15
READY_FOR_PREREGISTRATION <=3
one recommended bounded data action
one recommended next mechanism at most
strategy_candidate_available=false
```

If the minimum survivor-aware contract cannot be obtained within the approved budget, return:

```text
US_STOCK_RESEARCH_DATA_NOT_READY
```

Do not build a replacement data platform.
