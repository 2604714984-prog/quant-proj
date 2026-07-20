# Scout task — US SEC event, corporate-action and fundamental qualification

Date: 2026-07-20  
Mode: outcome-blind, read-only research  
Formal strategy authority: none

## Objective

Qualify the data and causal timing contracts for filing events, insider activity, corporate actions and fundamental cross-sectional mechanisms using official SEC sources plus a separately qualified survivor-aware price identity.

Do not calculate returns or construct portfolios.

## Official source families

Assess only official or primary routes first:

```text
SEC submissions and filing metadata
SEC EDGAR filing documents and exhibits
SEC XBRL Company Facts / Frames
SEC Financial Statement Data Sets
SEC Insider Transactions Data Sets
Form 4 / 5 source filings
8-K, 10-Q, 10-K, S-3, 424B and related filings
```

For each route record:

```text
coverage start
accepted/filed timestamp
revision and amendment behavior
accession identity
CIK and security mapping needs
bulk/API availability
rate-limit and retrieval policy
as-filed versus later-restated semantics
field/tag coverage
```

## Mechanism groups

### Earnings and reporting timing

- PEAD from time-series earnings surprise;
- revenue surprise;
- filing-lag reporting delay;
- earnings-announcement premium;
- premarket versus after-hours identity only as a timing field, not an automatic new mechanism.

### Insider information

- clustered open-market insider purchases;
- reporting-owner role classification;
- transaction-to-filing lag as a conditioning diagnostic;
- 10b5-1 status as a field, not a separate mechanism unless independently sourced.

### Corporate payout and financing

- open-market repurchase authorization;
- dividend initiation;
- dividend cut or omission avoidance;
- seasoned equity offering avoidance;
- net equity issuance;
- stock-split announcement identity.

### Fundamental cross-section

- gross profitability;
- asset growth;
- accruals quality;
- quality/value balance-sheet safety;
- material-weakness disclosure avoidance.

## Priority finalist checks

Review these existing provisional finalists first:

```text
FND_07_FILING_LAG_REPORTING_DELAY
FND_16_CLUSTER_INSIDER_PURCHASES
FND_22_ASSET_GROWTH
```

For each, determine whether the cited paper supports the exact proposed signal and whether the data can be formed without hindsight.

### FND_07

Freeze an expected-filing-date rule based only on prior public issuer history. Do not use the eventual actual filing date to define delay before it occurs.

### FND_16

Require distinct natural persons, open-market purchase codes, direct/indirect ownership treatment, amendment handling, final accepted filing timestamp and a frozen clustering window. The source must support cluster-specific informativeness or the card must be downgraded to `ECONOMIC_PRIOR_ONLY`.

### FND_22

Use first as-filed asset values and the later of the two required filing acceptance times. Do not overwrite history with restated Company Facts. Acquisitions and fiscal-year changes must have a frozen treatment.

## Permanent security mapping contract

No mechanism is ready until a mapping contract covers:

```text
CIK
accession
issuer legal identity
share class
historical ticker
exchange
permanent security ID
listing/delisting interval
corporate actions
terminal value
```

A CIK-to-current-ticker join is not acceptable.

## Source classification

For every mechanism use:

```text
EXACT_MECHANISM_SOURCE
ECONOMIC_PRIOR_ONLY
OPERATIONAL_ROUTE_ONLY
SOURCE_GAP
```

Operational SEC documentation cannot substitute for mechanism research.

## Readiness output

For at least 15 mechanisms, report:

```text
required SEC forms and fields
causal availability timestamp
amendment policy
security mapping requirement
minimum history
expected event/firm count without returns
turnover and execution risk
USD 40000 fit
implementation size
READY_FOR_PREREGISTRATION / BOUNDED_INPUT_TASK / PARK / CLOSE
```

## Boundaries

This Scout may inspect small official metadata/document samples after explicit Manager dispatch.

It may not:

- download a full price or filing corpus;
- read historical returns;
- rank issuers;
- calculate factor spreads;
- write canonical DuckDB;
- implement parsers as a generalized platform;
- use NLP models;
- use Qlib or RD-Agent;
- access Validation or Holdout.

Any deterministic text extraction proposal must be narrowly mechanism-specific.

## Deliverable

One compact report with:

```text
mechanisms reviewed >=15
exact source bindings verified
minimum SEC data contracts
permanent mapping blocker status
READY_FOR_PREREGISTRATION <=3
one bounded official-data action
one next mechanism recommendation at most
```

If permanent security mapping and survivor-aware prices remain unavailable, return:

```text
SEC_MECHANISMS_PARKED_PENDING_SECURITY_MASTER
```

Do not build a new enterprise security-master platform.
