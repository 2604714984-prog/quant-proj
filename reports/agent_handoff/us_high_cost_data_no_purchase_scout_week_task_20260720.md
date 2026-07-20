# US High-Cost Data No-Purchase Scout — Week Task

Date: 2026-07-20  
Role: market-data feasibility scout  
Purchase authorization: USD 0

## Goal

Produce a current, source-cited map of high-cost data routes that could unlock future intraday, options, or transcript mechanisms, without creating accounts, trials, integrations, or code.

This is a procurement and feasibility report only.

## Scope

Evaluate these existing Atlas categories:

### Intraday macro and market structure

- FOMC pre-announcement drift;
- FOMC immediate reaction;
- opening and closing auction imbalances;
- ETF/futures price discovery;
- large opening-gap execution.

### Options

- variance risk premium;
- implied-volatility skew;
- term structure;
- earnings options;
- option-volume sentiment.

### Text and transcripts

- SEC filing-text changes;
- material weakness disclosure;
- earnings call tone.

Do not add mechanisms or modify Atlas R1.

## Providers and official routes to inspect

At minimum:

- NYSE Daily TAQ and auction data;
- Cboe DataShop option quote intervals, volatility surfaces, and sentiment products;
- Massive stock historical and reference coverage;
- Databento equities/futures coverage;
- LSEG StreetEvents transcripts;
- SEC EDGAR filings and structured data;
- any official Federal Reserve or BLS timestamp archive relevant to event identity.

## Required matrix fields

For each route record:

```text
provider_or_owner
product
official_url
asset_class
frequency
history_start
history_end_or_current
regular_hours
extended_hours
timezone
raw_or_adjusted
corporate_actions
symbol_or_contract_history
delisted_coverage
point_in_time_identity
bulk_or_API
file_format
license_for_personal_research
redistribution_limits
minimum_plan_or_price
sample_available_without_account
source_last_checked
mechanisms_unlocked
blocking_gaps
recommendation
```

## Recommendation enum

```text
DEFER_NO_CLEAR_VALUE
CONSIDER_ONLY_AFTER_HISTORICAL_SPECIALIST_PASS
SAMPLE_REVIEW_WORTHWHILE_WITH_USER_APPROVAL
REJECT_COVERAGE_OR_LICENSE_MISMATCH
OFFICIAL_FREE_ROUTE_PREFERRED
```

No route may receive `PURCHASE` or `START_TRIAL`.

## Specific tests

### Intraday history

Verify whether the route covers the frozen start date required by the relevant mechanism. Do not describe 2003, 2004, or 2018 coverage as sufficient for a 1994-start contract.

### FOMC timestamps

Separate:

- event-time identity;
- minute-bar availability;
- execution-price evidence.

A minute data source does not solve missing official first-publication timestamps.

### Options

Identify whether the data provide:

- full option chains;
- bid/ask quotes;
- implied volatilities or raw prices;
- Greeks methodology;
- underlying prices;
- expiration and corporate-action adjustments;
- survivorship of expired contracts.

### Transcripts

Separate:

- event metadata;
- transcript text;
- historical revisions;
- speaker identity;
- redistribution rights.

Do not treat SEC filings as a free replacement for proprietary earnings call transcripts.

## Lightweight boundary

Do not:

- install SDKs;
- use API keys;
- create provider accounts;
- download paid samples;
- write integration code;
- propose a provider abstraction layer;
- build a procurement workflow;
- estimate strategy returns.

## Deliverable

One Markdown or JSON under 300 lines containing:

- a narrow comparison matrix;
- current official URLs;
- coverage and license caveats;
- approximate price tier only when publicly visible;
- one recommendation per route;
- no purchase action.

Detailed screenshots and exploratory notes remain Git-external.

## Time box

Maximum effort: three working days.

## Callback

```text
BATCH=US_HIGH_COST_DATA_NO_PURCHASE_SCOUT_WEEK_20260720
STATUS=
ROUTES_REVIEWED=
INTRADAY_ROUTE_COUNT=
OPTIONS_ROUTE_COUNT=
TEXT_ROUTE_COUNT=
FREE_OFFICIAL_ROUTES=
PAID_ROUTES=
SAMPLE_REVIEW_CANDIDATES=
PURCHASES_MADE=0
TRIALS_STARTED=0
ACCOUNTS_CREATED=0
REPORT_URL=
STRATEGY_RESULT_ACCESS=false
DATABASE_WRITE=false
NEXT_USER_DECISION_REQUIRED=
```
