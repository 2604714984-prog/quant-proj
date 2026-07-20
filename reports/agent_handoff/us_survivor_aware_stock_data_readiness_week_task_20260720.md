# US Survivor-Aware Stock Data Readiness — Week Task

Date: 2026-07-20  
Role: outcome-blind data qualification scout  
Formal strategy selection authority: none

## Goal

Determine whether the project can support any survivor-aware US stock research without purchasing a new provider or building a new data platform.

This task qualifies data identities and coverage only. It does not calculate returns, ranks, signals, portfolios, or strategy outcomes.

## Priority mechanisms for data-readiness testing

Use these existing frozen Atlas mechanisms only as field-requirement probes:

1. `STK_01_52_WEEK_HIGH_PROXIMITY`;
2. `STK_04_FIVE_DAY_MARKET_RESIDUAL_REVERSAL`;
3. `STK_12_AMIHUD_ILLIQUIDITY_AVOIDANCE`.

Do not change their Atlas scores or recommendations and do not select one as a strategy.

## Allowed access

May use:

- read-only local schema, metadata, row counts, date coverage, and identifier tables;
- field names, types, null rates, duplicate-key counts, and coverage aggregates that establish whether raw and adjusted OHLCV fields exist;
- listing, delisting, corporate-action, and security-master metadata;
- public provider documentation;
- Git-external scratch scripts.

May not:

- read, export, print, or retain per-security price, volume, or dollar-volume values;
- calculate raw-to-adjusted ratios or inspect individual split adjustments;
- join price fields to events, filings, fundamentals, or other research inputs;
- compute close-to-close or forward returns;
- calculate 52-week-high signals;
- rank stocks;
- form portfolios;
- inspect winner/loser outcomes;
- write the central database;
- buy or trial a provider.

## Required data contract

Evaluate whether the available data can establish:

```text
permanent_security_id
historical_ticker
share_class_id
primary_exchange
security_type
listing_start
listing_end
active_as_of_date
delisting_reason
delisting_or_terminal_value_policy
raw_open_high_low_close
adjusted_open_high_low_close
volume
dollar_volume
split events
cash dividends
special distributions
symbol changes
mergers and acquisitions
bankruptcy or liquidation identity
row-level provenance
available_at or retrospective-only label
```

## Survivor-bias tests

Report:

- active and inactive security counts;
- securities with delisting dates;
- securities with terminal values or explicit missing-terminal policy;
- historical symbols mapped to permanent IDs;
- duplicate symbol/date collisions;
- share-class collisions;
- corporate-action coverage by year;
- whether current constituents are incorrectly backfilled into history;
- whether dead securities disappear before their terminal event.

No strategy can be marked data-ready when delisted and failed securities are absent.

## Mechanism-specific field checks

### STK_01 — 52-week high proximity

Check only:

- at least 252 accepted sessions per eligible security;
- field and provenance metadata for raw and adjusted high and close series;
- whether source documentation and metadata are sufficient to qualify split timing without inspecting price values; otherwise report the requirement as unqualified;
- historical eligibility as of each date;
- inactive and delisted securities retained through terminal date.

### STK_04 — five-day residual reversal

Check only:

- synchronized stock and market session dates;
- raw/adjusted daily close field and provenance identity, without reading price values;
- trading-status and halt fields;
- event exclusions can be known point-in-time;
- volume and dollar-volume identity;
- terminal-value policy.

Do not calculate residuals.

### STK_12 — Amihud exclusion overlay

Check only:

- daily return inputs could be formed later without unit ambiguity;
- dollar volume definition is explicit;
- zero-volume and stale-price semantics exist;
- microcap and OTC identity can be excluded causally;
- inactive securities remain in the historical panel.

Do not calculate the Amihud ratio.

## Provider-route review

Assess but do not purchase:

### Existing/local route

Determine whether current local data already satisfy the contract.

### Norgate route

Official documentation indicates that historical constituents and delisted securities require appropriate paid US stock subscriptions and that Python support is Windows-oriented.

- https://norgatedata.com/accessibility.php
- https://norgatedata.com/data-content-tables.php

Classify as `PAID_ROUTE_NOT_AUTHORIZED` unless already licensed.

### Massive route

Official reference endpoints can return active-as-of-date ticker details and delisted tickers, with identifiers such as CIK and FIGI. Determine whether the documented historical reference depth, corporate actions, and terminal-value semantics are sufficient; do not assume they are.

- https://massive.com/docs/rest/stocks/tickers/ticker-overview
- https://massive.com/docs/rest/stocks

### SEC route

SEC data can support issuer identity and filings but is not a survivor-aware price source. Do not treat CIK as a permanent tradable-security identifier without a share-class mapping.

## Output statuses

```text
DATA_READY_WITH_EXISTING_LOCAL_INPUTS
DATA_PARTIAL_BOUNDED_GAPS
DATA_BLOCKED_SURVIVOR_OR_TERMINAL_VALUE
PAID_ROUTE_REQUIRED_NOT_AUTHORIZED
```

## Deliverable

One compact JSON or Markdown report under 300 lines containing:

- local schema and snapshot identity;
- counts and coverage, not security names unless necessary for a finding;
- field-level PASS/PARTIAL/FAIL;
- mechanism-specific readiness for the three probes;
- exact blockers;
- no provider recommendation beyond `existing / paid / unavailable`;
- no strategy ranking.

Identifier, status, and key-only row samples and scratch scripts remain Git-external. Price, volume, and dollar-volume values are prohibited even in Git-external samples or logs.

## Time box

Maximum effort: four working days.

Do not extend into provider integration or database repair. If a decisive survivor or terminal-value gap is found, stop and report it.

## Callback

```text
BATCH=US_SURVIVOR_AWARE_DATA_READINESS_WEEK_20260720
STATUS=
LOCAL_SNAPSHOT_ID=
ACTIVE_SECURITY_COUNT=
INACTIVE_SECURITY_COUNT=
DELISTED_SECURITY_COUNT=
TERMINAL_VALUE_COVERAGE=
PERMANENT_ID_STATUS=
CORPORATE_ACTION_STATUS=
STK_01_READINESS=
STK_04_READINESS=
STK_12_READINESS=
PAID_ROUTE_REQUIRED=
REPORT_URL=
PRICE_FIELD_METADATA_INSPECTED=true|false
PER_SECURITY_PRICE_VALUES_READ=false
RETURN_COMPUTATION=false
SIGNAL_COMPUTATION=false
DATABASE_WRITE=false
STRATEGY_CANDIDATE_AVAILABLE=false
```
