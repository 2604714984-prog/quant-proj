# Scout task — US daily ETF and broad-market mechanism qualification

Date: 2026-07-20  
Mode: outcome-blind, read-only research  
Formal strategy authority: none

## Objective

Qualify a broad set of daily-frequency market, ETF, macro-event and cross-asset mechanisms without opening any price return, NAV, Sharpe, Validation or Holdout result.

Do not create new mechanism cards merely to increase the count. Review and sharpen the existing Atlas cards, adding a new card only for a genuinely missing economic mechanism.

## Priority mechanism groups

### Scheduled public events

- FOMC pre-announcement drift;
- immediate FOMC reaction;
- date-anchored next-session FOMC response;
- CPI, Employment Situation, PCE, GDP, retail sales, ISM and initial-claims release effects;
- aggregate scheduled-announcement premium;
- Treasury auction and refunding inventory effects;
- standard monthly and quarterly expiration effects.

### Calendar and market-structure effects

- pre-holiday and post-holiday effects;
- closure accumulation and reopening;
- month-end, quarter-end and year-end flows;
- index rebalance and reconstruction demand;
- overnight versus intraday decomposition;
- large opening-gap continuation or reversal;
- early-close and unusual-session effects.

### Cross-asset and risk-state mechanisms

- volatility shock clustering and decay;
- HYG/LQD credit stress and recovery;
- IEF/TLT rate-state proxies;
- TIP/IEF inflation-compensation repricing;
- stock/bond correlation sign shifts;
- SPY/RSP or IWM/SPY participation proxies;
- dollar, oil and gold state interactions only when distinct from closed GLD safe-haven and SPY/QQQ/GLD allocation lines.

## Required analysis per mechanism

For every reviewed mechanism, return:

```text
mechanism_id
economic hypothesis
source class
exact source citation
operational data routes
required instruments and inception dates
causal decision timestamp
holding interval
expected independent observation count
calendar and corporate-action requirements
cost and turnover exposure
USD 40000 execution fit
closed-lineage duplicate screen
prospective observability
qualification status
```

Allowed status:

```text
READY_FOR_PREREGISTRATION
BOUNDED_INPUT_TASK
PARK
CLOSE
```

## Specific audit requirements

### FOMC

Keep these separate:

```text
pre-announcement drift
announcement reaction
next-session response
```

Do not use the Lucca–Moench pre-announcement paper as an exact source for a post-announcement or next-session mechanism.

The exact-time historical route is terminal within the prior bound. A date-anchored daily V2 requires a new identity and a mechanism-specific source classification.

### Volatility shock card

For any cash/risk-off strategy, distinguish:

```text
volatility persistence evidence
volatility-management return evidence
out-of-sample and transaction-cost counterevidence
```

A volatility-clustering paper alone cannot establish a profitable timing rule.

### Closed ETF lineages

Do not propose:

- another SPY/QQQ/GLD momentum window;
- another inverse-volatility window or cap;
- another SPY drawdown/GLD sleeve;
- combinations of the three failed mechanisms;
- a repair of SPY 200-day trend or classic turn-of-month.

## Data boundary

This task may inspect:

- official documentation;
- instrument inception and product identity;
- repository schemas and accepted data contracts;
- small metadata samples after explicit Manager dispatch.

It may not:

- read historical price values or returns;
- calculate event returns;
- query Validation or Holdout;
- write canonical DuckDB;
- purchase data;
- implement a strategy.

## Deliverable

One compact qualification report containing:

```text
mechanisms reviewed >= 20
genuinely new mechanisms added <= 5
READY_FOR_PREREGISTRATION <= 3
one recommended next mechanism at most
formal selection = none
```

The recommendation must state the exact bounded input task required before preregistration.

## Stop rule

If no mechanism can be made ready with one bounded input task, return:

```text
DAILY_MARKET_COHORT_NO_READY_MECHANISM
```

Do not respond by designing a new data platform.
