# Task: survivor-aware US stock data and mechanism scout

Task ID: `US_SURVIVOR_AWARE_STOCK_MECHANISM_SCOUT_20260720`  
Mode: read-only, outcome-blind, no implementation

## 1. Objective

Determine the narrowest practical path to survivor-aware US stock research, then produce at least 20 independent stock-level mechanism cards.

This task has two outputs:

```text
A. data-readiness and acquisition decision
B. mechanism pool
```

No stock return or ranking may be queried.

## 2. Minimum data contract

A stock-level formal result remains forbidden until the following are qualified:

```text
stable security identifier
listing and delisting dates
survivor-aware universe membership
raw and adjusted OHLCV
splits and cash distributions
delisting terminal value or explicit fail-closed policy
symbol and corporate-name changes
exchange and security type
immutable snapshot identity
historical availability classification
```

Historical index membership is optional if a fixed, survivor-aware major-exchange universe is used. Current membership must never be backfilled into history.

## 3. Provider and acquisition review

Compare no more than five candidate routes.

Required route classes:

- Norgate US Stocks Platinum or equivalent survivor-aware package;
- a single institutional/academic source if already available;
- a single market-data provider plus a separate official/reference identity route only if the join is deterministic;
- SEC data only for filing/event identity, not price survivorship;
- current local central-DB content.

For each route record:

```text
coverage_start
currently listed coverage
delisted coverage
historical membership support
corporate actions
delisting values
identifier history
Python or export method
license restrictions
one-year total cost
sample extract availability
Linux/WSL compatibility
reproducible immutable export method
```

No purchase is authorized.

## 4. Data-route decision

Return one:

```text
DATA_ROUTE_READY_EXISTING
DATA_ROUTE_READY_BOUNDED_PURCHASE_PROPOSAL
DATA_ROUTE_NOT_READY_STOP
```

Any purchase proposal must include one bounded sample acceptance plan before purchase.

## 5. Required mechanism domains

Create cards across all domains below.

### A. Price anchors and trend

- 52-week-high proximity;
- distance from 52-week low;
- residual momentum;
- industry momentum;
- absolute trend with survivor-aware membership;
- gap continuation and reversal;
- post-breakout persistence;
- price-level anchoring around round numbers.

Do not duplicate the closed 12-1 momentum or failed broad trend line.

### B. Short-horizon liquidity and reversal

- five-day market-residual reversal;
- one-week industry-residual reversal;
- VIX-conditioned liquidity provision;
- large overnight-gap reversal;
- high-dollar-volume shock reversal;
- post-limitless US market selloff recovery;
- earnings-adjacent liquidity provision;
- short-term reversal after index or ETF flow shocks.

### C. Overnight and intraday cross-section

- overnight continuation;
- overnight reversal;
- intraday continuation;
- intraday reversal;
- overnight winner / intraday loser interaction;
- opening-gap residual signal;
- close-to-open versus open-to-close factor decomposition.

### D. Liquidity, attention and speculative demand

- Amihud illiquidity;
- dollar-volume change;
- turnover shock;
- abnormal volume;
- MAX / lottery preference;
- idiosyncratic volatility;
- zero-return frequency;
- high-low range;
- attention around 52-week extremes.

### E. Low-risk and defensive stock mechanisms

- low beta long-only;
- low residual volatility;
- downside beta;
- balance-sheet-safe low-risk, once PIT fundamentals exist;
- quality plus low beta;
- defensive sector-neutral variants.

Do not propose leveraged BAB or a short portfolio.

### F. Index and institutional events

- index inclusion;
- index deletion;
- annual reconstitution;
- split events;
- special dividends;
- secondary offerings;
- buyback execution proxies;
- ETF ownership or flow pressure where historical holdings qualify.

## 6. Implementation and account constraints

Every card must assume:

```text
USD 40,000
long only
no leverage
whole shares
5-10 positions preferred
cash allowed
conservative costs
no microcap dependence
```

Reject a card if its economics require:

- shorting;
- high leverage;
- hundreds of positions;
- microcaps or OTC securities;
- unavailable quote-level execution;
- daily turnover incompatible with costs.

## 7. Mechanism-card schema

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

No card may include historical returns.

## 8. Priority shortlist

Return the top eight stock mechanisms based on:

1. survivor-aware data feasibility;
2. independence from closed strategies;
3. economic prior;
4. execution fit;
5. prospective observability;
6. implementation simplicity.

Expected initial leaders, subject to honest review:

```text
52_WEEK_HIGH_PROXIMITY
SHORT_TERM_RESIDUAL_REVERSAL
STOCK_OVERNIGHT_INTRADAY_ATLAS
VIX_CONDITIONED_LIQUIDITY_PROVISION
```

Do not force these to rank first if data or evidence is weak.

## 9. Prohibited actions

```text
price or return query
security ranking
strategy backtest
validation/holdout access
provider purchase
canonical database write
new data platform
Qlib/RD-Agent integration
candidate or trading promotion
```

## 10. Callback

```text
TASK_ID
BRANCH
COMMIT
DATA_ROUTE_DECISION
PROVIDER_ROUTES_REVIEWED
CARD_COUNT
ADVANCE_COUNT
PARK_COUNT
CLOSE_COUNT
TOP_EIGHT_IDS
ESTIMATED_FIRST_SNAPSHOT_COST
ESTIMATED_FIRST_RESULT_DAYS
PRICE_RETURN_ACCESS=false
DATABASE_WRITE=false
WORKTREE_STATUS
```
