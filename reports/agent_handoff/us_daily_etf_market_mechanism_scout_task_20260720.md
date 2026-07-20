# Task: broad US daily ETF and market-mechanism scout

Task ID: `US_DAILY_ETF_MARKET_MECHANISM_SCOUT_20260720`  
Mode: read-only, outcome-blind, no implementation

## 1. Objective

Produce a broad pool of genuinely distinct US mechanisms that can be studied with daily ETF, index, macro-calendar or cross-asset data.

Minimum delivery:

```text
20 unique mechanism cards
```

No strategy returns may be accessed.

## 2. Existing failure memory

Do not propose parameter variants or disguised rescues of:

```text
SPY 200-session trend/cash
classic SPY turn-of-month
SPY/QQQ/GLD top-one dual momentum
monthly full-liquidation capped inverse volatility
SPY-drawdown GLD/cash stress sleeve
US31 / US36 / US41 / US46
```

Do not propose another SPY/QQQ/GLD weighting, momentum, inverse-volatility or safe-haven variant for at least 90 days.

## 3. Required search domains

Create cards across all of the following domains.

### A. Scheduled macro events

- FOMC date-anchored next-session reaction;
- CPI date effects;
- NFP date effects;
- PCE release effects;
- GDP advance-estimate effects;
- ISM manufacturing and services releases;
- retail-sales releases;
- initial jobless claims;
- Treasury auctions and refunding at daily frequency;
- scheduled macro-announcement premium across multiple event types.

Each card must separate event identity from economic-value data. No event surprise value is required unless a qualified as-released surprise series exists.

### B. Calendar and institutional events

- pre-holiday effect;
- post-holiday reversal or continuation;
- weekend boundary;
- monthly option expiration;
- quarterly option and futures expiration;
- S&P index rebalance dates;
- Russell annual reconstitution;
- quarter-end pension or fund-flow effects;
- tax-year and fiscal-year boundary effects;
- Treasury settlement-calendar effects.

The closed classic turn-of-month lineage remains excluded.

### C. Session decomposition

- SPY overnight versus intraday V2;
- QQQ overnight versus intraday;
- IWM overnight versus intraday;
- GLD overnight versus intraday;
- TLT overnight versus intraday;
- HYG/LQD overnight versus intraday;
- cross-asset overnight lead/lag;
- gap continuation versus gap reversal.

Session Decomposition V1 remains terminal execution-error memory. Any V2 card must define sub-one-share behavior and error taxonomy before price access.

### D. Credit and rates

- HYG/LQD relative-strength stress signal;
- HYG/TLT risk-on versus duration stress;
- investment-grade versus Treasury spread proxy;
- yield-curve steepening or inversion with ETF proxies;
- TLT/IEF duration rotation;
- inflation-linked versus nominal Treasury relative signal;
- credit-stress recovery after spread widening.

### E. Volatility and risk-state mechanisms

- realized-volatility shock and decay;
- volatility-of-volatility proxy;
- drawdown recovery;
- breadth recovery;
- correlation breakdown between equities and bonds;
- correlation breakdown between equities and gold;
- volatility clustering without dynamic portfolio optimization;
- static core plus one bounded risk-off sleeve.

Do not propose a rerun of the closed 200-day trend or GLD safe-haven contract.

### F. Breadth, sectors and participation

- equal-weight versus cap-weight relative trend;
- sector breadth dispersion;
- defensive versus cyclical sector relative strength;
- small-cap versus large-cap participation;
- index concentration and breadth divergence;
- market advance/decline participation where qualified data exists;
- sector-rebalance and month-end institutional flow.

### G. Cross-asset macro mechanisms

- dollar strength versus equities and gold;
- oil shock and equity-sector response;
- commodity inflation proxy versus duration;
- real-rate proxy and gold;
- risk parity only as a static comparator, not another optimized allocation family;
- equity/credit/term-duration joint stress indicators.

## 4. Card requirements

Each card must use:

```text
mechanism_id
economic_mechanism
primary_original_source
market_role
universe
signal_and_holding_period
required_data
current_data_status
sample_size_estimate
turnover_and_cost_risk
USD_40000_execution_fit
survivorship_and_PIT_risk
closed_lineage_duplicate_screen
implementation_size_estimate
result_time_estimate
recommendation=ADVANCE|PARK|CLOSE
```

No card may contain a historical return value.

## 5. Source hierarchy

Use, in order:

1. original academic paper;
2. official agency or exchange material;
3. official product/provider documentation;
4. secondary source only to locate the original.

For current provider coverage or pricing, record the exact access date.

## 6. Data-readiness classes

```text
READY_EXISTING_SNAPSHOT
READY_WITH_SMALL_OFFICIAL_IDENTITY_TASK
BOUNDED_PAID_DATA_NEEDED
PIT_OR_SURVIVORSHIP_BLOCKED
HIGH_COST_DEFER
```

## 7. Advancement criteria

Recommend `ADVANCE` only when:

- the mechanism is economically distinct from closed lines;
- data can be ready within five working days;
- the mechanism has adequate event/session count;
- execution is plausible for USD 40,000;
- expected turnover is compatible with conservative costs;
- a single frozen version is possible.

At least five cards must be recommended `ADVANCE` unless the evidence honestly supports fewer.

## 8. Result-lane recommendation

Rank the top five cards without using returns.

Use this order:

1. data readiness;
2. economic independence;
3. prospective observability;
4. cost and execution fit;
5. implementation size.

Provide one recommended next formal mechanism after Lane B reaches a terminal checkpoint.

## 9. Prohibited actions

```text
price query
return query
Sharpe/CAGR/NAV
strategy code
parameter grid
validation/holdout access
canonical database write
new framework
Qlib/RD-Agent integration
candidate or trading promotion
```

## 10. Callback

```text
TASK_ID
BRANCH
COMMIT
CARD_COUNT
ADVANCE_COUNT
PARK_COUNT
CLOSE_COUNT
TOP_FIVE_IDS
RECOMMENDED_NEXT_FORMAL_ID
SOURCE_COUNT
PRICE_RETURN_ACCESS=false
DATABASE_WRITE=false
WORKTREE_STATUS
```
