# Task: US earnings, corporate-event and fundamental mechanism scout

Task ID: `US_EARNINGS_CORPORATE_FUNDAMENTAL_SCOUT_20260720`  
Mode: read-only, outcome-blind, no implementation

## 1. Objective

Map the official PIT data path and create at least 20 independent mechanism cards across earnings, corporate actions, insider activity and fundamentals.

No price, return or portfolio output is authorized.

## 2. Official data routes to inspect

Use primary SEC routes first:

```text
EDGAR submissions API
XBRL Company Facts API and bulk companyfacts
Financial Statement Data Sets
Insider Transactions Data Sets
filing index and accepted timestamp
full filing documents and exhibits
```

Official starting points:

- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets
- https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets

Record the exact coverage and update date observed during the task.

## 3. Minimum PIT contract

A filing-derived value is eligible only when bound to:

```text
CIK
accession number
form type
filing accepted timestamp
period end
fiscal period
as-filed value
unit
source document
source or bulk-object SHA-256
restatement or amendment relationship
security identifier mapping
```

Do not use current Company Facts values as if they were historically available at earlier dates.

## 4. Required mechanism domains

### A. Earnings reaction

- post-earnings-announcement drift;
- earnings surprise using a time-series baseline;
- revenue surprise;
- earnings plus revenue double surprise;
- earnings surprise with abnormal volume;
- post-announcement reversal;
- guidance initiation or revision;
- filing-lag and reporting-delay effects;
- restatement announcement reaction;
- 8-K Item 2.02 earnings event.

### B. Earnings-announcement timing

- earnings-announcement premium;
- pre-announcement drift;
- before-market versus after-market announcements;
- Friday announcement effects;
- delay or rescheduling of an expected announcement;
- announcement clustering and market-wide risk;
- prior-announcement-volume conditioning.

### C. Corporate payout and financing

- open-market repurchase announcement;
- accelerated share-repurchase announcement;
- dividend initiation;
- dividend increase;
- dividend cut or omission;
- special dividend;
- seasoned equity offering;
- debt issuance;
- net equity issuance;
- share-count contraction;
- merger termination or completion.

### D. Insider activity

- cluster insider purchases;
- CEO/CFO open-market purchase;
- director purchases;
- insider sales as a negative control;
- 10b5-1 flagged versus unflagged activity;
- purchase following a large drawdown;
- purchase near 52-week high or low;
- filing delay and transaction-to-filing lag.

Use as-filed Forms 3, 4 and 5; no inferred private activity.

### E. Fundamental cross-section

- gross profitability;
- operating profitability;
- asset growth;
- investment growth;
- accruals;
- net operating assets;
- net issuance;
- book-to-market;
- earnings-to-price;
- cash-flow-to-price;
- quality plus value;
- balance-sheet safety;
- earnings stability;
- financial distress;
- low beta plus quality.

### F. Text-light filing metadata

Before full NLP, scout simple deterministic metadata:

- filing length change;
- number of risk-factor changes;
- late filing;
- amendment frequency;
- material weakness disclosure;
- going-concern language presence;
- auditor change;
- 8-K event-category frequency.

Do not build an NLP platform.

## 5. Data-readiness output

For each mechanism classify:

```text
READY_WITH_SEC_ONLY
READY_WITH_SEC_PLUS_SURVIVOR_AWARE_PRICES
ANALYST_DATA_REQUIRED
EVENT_TIME_INCOMPLETE
TEXT_PIPELINE_DEFER
PARK_LICENSE_OR_COST
```

## 6. Mechanism-card schema

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

No return values are allowed.

## 7. Advancement criteria

Recommend `ADVANCE` only if:

- filing time is observable and causal;
- a survivor-aware price universe can be joined;
- the signal does not require proprietary analyst estimates unless a bounded route exists;
- at least six years of events are expected;
- execution can occur after the filing becomes public;
- the strategy is feasible with 5-10 long-only positions or a diversified low-turnover basket.

## 8. Priority groups

Return top candidates in four groups:

```text
A. earnings event
B. corporate event
C. insider event
D. fundamental cross-section
```

Expected high-prior candidates, subject to data review:

```text
PEAD_TIME_SERIES_SURPRISE
EARNINGS_ANNOUNCEMENT_PREMIUM
CLUSTER_INSIDER_PURCHASES
GROSS_PROFITABILITY
ASSET_GROWTH
NET_ISSUANCE
```

## 9. Implementation-size constraint

Estimate the minimum implementation rather than a platform.

Preferred shape:

```text
one immutable SEC extract
one feature builder
one focused mechanism module
one result runner using existing project patterns
```

Reject proposals that first require a general-purpose fundamentals warehouse or NLP framework.

## 10. Prohibited actions

```text
price or return query
backtest
security ranking
Validation/Holdout access
canonical database write
new SEC platform
NLP platform
Qlib/RD-Agent integration
candidate or trading promotion
```

## 11. Callback

```text
TASK_ID
BRANCH
COMMIT
SEC_ROUTES_VERIFIED
CARD_COUNT
READY_WITH_SEC_ONLY_COUNT
READY_WITH_PRICE_JOIN_COUNT
ANALYST_DATA_REQUIRED_COUNT
TEXT_DEFER_COUNT
TOP_EARNINGS_IDS
TOP_CORPORATE_IDS
TOP_INSIDER_IDS
TOP_FUNDAMENTAL_IDS
PRICE_RETURN_ACCESS=false
DATABASE_WRITE=false
WORKTREE_STATUS
```
