# Task: US intraday, options and text-data availability scout

Task ID: `US_INTRADAY_OPTIONS_TEXT_AVAILABILITY_SCOUT_20260720`  
Mode: read-only availability and mechanism research only

## 1. Objective

Map high-cost research directions without buying data, implementing strategies or opening outcomes.

Minimum delivery:

```text
15 mechanism cards
5 provider or official-source route assessments
```

This is the lowest-priority scout. It must not delay the active Lane B identity task or a ready daily-data result.

## 2. Required mechanism domains

### A. Intraday macro events

- FOMC pre-announcement drift;
- FOMC announcement-to-close reaction;
- CPI announcement reaction;
- NFP announcement reaction;
- PCE announcement reaction;
- GDP and ISM announcement reaction;
- Treasury refunding and auction reaction;
- cross-asset event response in SPY, TLT, GLD and dollar proxies.

### B. Intraday market structure

- opening-gap continuation;
- opening-gap reversal;
- first-hour momentum;
- last-hour momentum;
- close-auction imbalance;
- open-auction imbalance;
- intraday volatility seasonality;
- order-flow imbalance;
- ETF-versus-futures lead/lag;
- index-rebalance closing pressure.

### C. Options

- variance-risk premium;
- implied-minus-realized volatility;
- volatility skew;
- term structure of implied volatility;
- earnings implied-volatility premium;
- put/call volume and open interest;
- option-volume disagreement signals;
- dealer-gamma or expiry pressure where data is causal and available.

### D. News and text

- timestamped news sentiment;
- event-category classification;
- 10-K/10-Q textual change;
- risk-factor change;
- management discussion change;
- earnings-call tone;
- analyst-estimate revision;
- filing-to-news disagreement;
- uncertainty and litigation language.

## 3. Provider/route requirements

For each data route record:

```text
coverage_start
symbols or universe
resolution
timestamp timezone
RTH/extended-hours labels
corporate-action treatment
historical corrections
license and redistribution limits
API or bulk-download method
sample access
total annual cost
reproducible snapshot method
```

Official or direct provider documentation is required.

Known boundary to verify rather than assume:

- commonly available US equity minute flat files begin around September 2003, which cannot satisfy a frozen 1994-start intraday contract;
- a shorter-period mechanism must use a new research identity rather than silently changing an old split.

## 4. Purchase gate

No purchase is authorized.

A future purchase proposal must satisfy all of:

```text
one exact mechanism already selected
sample event days successfully reproduced
coverage adequate for the preregistered period
license permits local research use
immutable export possible
total one-year cost stated
simpler daily data cannot answer the question
```

## 5. High-cost mechanism-card schema

```text
mechanism_id
economic_mechanism
primary_original_source
market_role
universe
signal_and_holding_period
required_data
provider_routes
coverage_start
estimated_sample_size
estimated_annual_cost
license_risk
reproducibility
turnover_and_cost_risk
USD_40000_execution_fit
closed_lineage_duplicate_screen
simpler_daily_proxy_valid=false|true
recommendation=ADVANCE_DATA_SAMPLE|PARK|CLOSE
```

No historical strategy returns are allowed.

## 6. Data-route ceiling

Review no more than:

```text
3 intraday price routes
3 options routes
3 news/text routes
```

Do not create a vendor comparison platform.

## 7. Advancement criteria

Recommend `ADVANCE_DATA_SAMPLE` only when:

- the mechanism has a strong original prior;
- the data covers the frozen period;
- a sample download is available;
- timestamp and corporate-action semantics are explicit;
- expected sample size is adequate;
- projected implementation is small;
- execution is plausible for USD 40,000;
- no daily-data mechanism can answer the same question.

## 8. Deferred tools

Qlib, RD-Agent, FinGPT and NLP models remain deferred.

The scout may state where they could later fit, but may not install, integrate or run them.

## 9. Prohibited actions

```text
data purchase
credential use
price or return query
strategy code
parameter grid
Validation/Holdout access
canonical database write
new provider framework
Qlib/RD-Agent/FinGPT integration
candidate or trading promotion
```

## 10. Callback

```text
TASK_ID
BRANCH
COMMIT
CARD_COUNT
PROVIDER_ROUTE_COUNT
ADVANCE_DATA_SAMPLE_COUNT
PARK_COUNT
CLOSE_COUNT
TOP_FIVE_IDS
LOWEST_ESTIMATED_COST_USD
EARLIEST_COVERAGE_DATE
PURCHASE_PERFORMED=false
PRICE_RETURN_ACCESS=false
DATABASE_WRITE=false
WORKTREE_STATUS
```
