# US SEC Insider and Fundamental Data Readiness — Week Task

Date: 2026-07-20  
Role: official-data feasibility and schema qualification  
Outcome access: prohibited

## Goal

Use public SEC bulk data to determine whether two independent future research mechanisms can be supported without building a generalized SEC platform:

1. `FND_16_CLUSTER_INSIDER_PURCHASES`;
2. `FND_22_ASSET_GROWTH`.

A third mechanism, `FND_07_FILING_LAG_REPORTING_DELAY`, may be assessed only as a metadata by-product. Do not implement or select any strategy.

## Official sources

### Insider transactions

- https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets
- coverage begins January 2006;
- quarterly flattened Forms 3, 4, and 5 data;
- as-filed data, with known limitations and possible extraction errors.

### Financial statements

- https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets
- coverage begins January 2009;
- as-filed primary financial statement facts;
- quarterly files and accession-level identifiers.

### Filing identity

- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data

## Allowed work

- download a bounded public sample to Git-external scratch storage;
- inspect schemas and documentation;
- count rows, filings, issuers, reporting owners, transaction codes, accessions, tags, and accepted timestamps;
- test deterministic parsing and amendment lineage;
- assess CIK-to-security mapping requirements;
- produce field and coverage qualification.

## Prohibited work

- no central database write;
- no price or return join;
- no insider signal or asset-growth rank;
- no portfolio construction;
- no broad EDGAR crawler;
- no generalized XBRL taxonomy engine;
- no NLP or filing-text platform;
- no full-history bulk ingestion unless needed for a bounded count and kept Git-external.

## Bounded sample

Use at most:

```text
Insider data: 2024 Q1 and 2026 Q1
Financial statement data: 2024 Q1 and 2026 Q1
Optional stress sample: 2020 Q2 only when needed to test unusual filings
```

Do not download every quarter merely because it is available.

## FND_16 field contract

Determine whether the official insider data expose and consistently populate:

```text
issuer CIK
issuer name
reporting owner ID
reporting owner name
owner role / relationship
accession number
filing date
accepted timestamp
transaction date
transaction code
acquired or disposed
shares
price
security title
direct or indirect ownership
10b5-1 flag
amendment flag
footnote or derivative indicator
```

Qualification must distinguish:

- open-market purchases from grants, exercises, gifts, conversions, and derivative transactions;
- distinct human insiders from duplicate owner records;
- original filings from amendments;
- issuer common stock from other securities;
- public filing time from private transaction date.

A future signal may act only after filing acceptance.

## FND_22 field contract

Determine whether the official financial statement data support first-as-filed annual total assets for two consecutive periods with:

```text
CIK
accession
form
filed date
accepted timestamp
fiscal year
fiscal period
period end
XBRL tag
unit
value
version / amendment identity
SIC or financial-sector classification
```

Test candidate asset tags and report tag coverage. Do not silently mix concepts across issuers.

The readiness result must identify whether a deterministic first-as-filed asset value can be selected without later amendments overwriting prior availability.

## FND_07 metadata by-product

Only assess whether accession, form, fiscal period, filed date, and accepted timestamp are sufficient to measure historical filing cadence. Do not build an expected-date model.

## Permanent security mapping

SEC CIK identifies issuers, not necessarily tradable share classes.

Report whether the project has an existing mapping with:

```text
CIK
permanent security ID
historical ticker
share class
listing interval
exchange
corporate-action lineage
```

Without this mapping and survivor-aware prices, mark each mechanism `DATA_PARTIAL` even if SEC fields are complete.

## Required deliverable

One compact report under 300 lines with:

- exact SEC files and SHA256 hashes;
- row and entity counts;
- field coverage percentages;
- transaction-code distribution summary;
- amendment and accepted-timestamp coverage;
- asset-tag coverage and ambiguity;
- permanent-security-mapping status;
- mechanism-specific readiness;
- no issuer ranking or signal output.

Raw ZIPs, extracted TSVs, and disposable scripts remain Git-external.

## Allowed statuses

```text
SEC_SCHEMA_READY_MAPPING_BLOCKED
FND16_DATA_READY_EXCEPT_SECURITY_MAPPING
FND22_DATA_READY_EXCEPT_SECURITY_MAPPING
FIELD_OR_AMENDMENT_IDENTITY_BLOCKED
BOUNDED_SAMPLE_INSUFFICIENT
```

## Time box

Maximum effort: four working days.

Stop once the decisive field or mapping blocker is known. Do not turn the task into a complete SEC ingestion project.

## Callback

```text
BATCH=US_SEC_DATA_READINESS_WEEK_20260720
STATUS=
INSIDER_FILES=
FINANCIAL_FILES=
SOURCE_HASHES=
INSIDER_ROW_COUNT=
INSIDER_OWNER_COUNT=
OPEN_MARKET_PURCHASE_CLASSIFICATION_STATUS=
ACCEPTED_TIMESTAMP_STATUS=
AMENDMENT_STATUS=
ASSET_TAG_COVERAGE_STATUS=
FIRST_AS_FILED_STATUS=
CIK_SECURITY_MAPPING_STATUS=
FND16_READINESS=
FND22_READINESS=
FND07_METADATA_READINESS=
REPORT_URL=
PRICE_ACCESS=false
RETURN_ACCESS=false
DATABASE_WRITE=false
STRATEGY_CANDIDATE_AVAILABLE=false
```
