# US SEC Data Readiness - Bounded Week Result

Date: 2026-07-21
Batch: `US_SEC_DATA_READINESS_WEEK_20260720`
Phase: official-data feasibility and schema qualification
Status: `FIELD_OR_AMENDMENT_IDENTITY_BLOCKED`

## Control and boundary

- PR #111 control HEAD: `037827f85becec1c706c679402a313fcf23922fc`.
- Task SHA256: `e1ef0d0615e75416384a8741df7956f0ddd7591758fe9089db680c259770f3f2`.
- Branch: `evidence/week-d-sec-readiness-20260721`.
- Base commit/tree: `6751fa4f3acf30e41a06cb6f90c0d8c50abdc095` / `8e3fa35ce60b5edb64f2cbd4e81492472114c28e`.
- Samples are exactly 2024 Q1 and 2026 Q1 for each family. Optional 2020 Q2 was unnecessary.
- ZIPs, extracted tables, and disposable analysis stayed Git-external.
- No issuer-level values, price values, returns, signals, rankings, or portfolio outputs were produced.

## Official SEC sources and immutable files

Documentation:

- https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets
- https://www.sec.gov/files/insider_transactions_readme.pdf
- https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets
- https://www.sec.gov/dera/data/fsds.pdf
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces

Files came directly from `www.sec.gov`, with no mirror, redirect, retry, crawler, or authenticated route.

| Family | Official URL | Bytes | Retrieved at (Asia/Shanghai) | SHA256 |
|---|---|---:|---|---|
| Insider 2024 Q1 | https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/2024q1_form345.zip | 13,874,620 | 2026-07-21 07:16:14 | `8e9bb34335416829a88e4ca7d09bb8aaceca689da9718fef22c298d6f18c9b04` |
| Insider 2026 Q1 | https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/2026q1_form345.zip | 13,874,904 | 2026-07-21 07:16:16 | `3dcb680593f5829bc951cb0969e858b60fc21a6835b094838218093a849592d6` |
| Financial 2024 Q1 | https://www.sec.gov/files/dera/data/financial-statement-data-sets/2024q1.zip | 124,336,804 | 2026-07-21 07:16:24 | `94c7894b00903f8ff7186c4250ba1c1daa1bde8b3a0b26fae68f72608b2ffc9b` |
| Financial 2026 Q1 | https://www.sec.gov/files/dera/data/financial-statement-data-sets/2026q1.zip | 85,259,424 | 2026-07-21 07:16:31 | `d18c01c615da8f5cd46273b0dacaeee5b1163f4089171da0f84153a5f3c362f6` |

SEC describes both families as flattened, as-filed extracts that can contain filer or extraction errors. These hashes identify current downloaded compilations, not historical ZIP snapshots as of each filing.

## Inspection rule

- Counts exclude one header row per table; coverage means non-null/non-empty rows.
- `P` classification used only non-derivative rows; no amount or issuer result was retained.
- Asset coverage used exact tag `Assets`, unit `USD`, `qtrs=0`, filing period end, no segment, and no co-registrant.
- No fallback tag, label inference, concept blending, imputation, or issuer exception was used.

## Insider data

| Table | 2024 Q1 rows | 2026 Q1 rows |
|---|---:|---:|
| `SUBMISSION` | 67,671 | 69,259 |
| `REPORTINGOWNER` | 71,738 | 72,211 |
| `OWNER_SIGNATURE` | 70,920 | 71,918 |
| `NONDERIV_TRANS` | 111,404 | 103,733 |
| `NONDERIV_HOLDING` | 30,850 | 34,002 |
| `DERIV_TRANS` | 42,891 | 37,910 |
| `DERIV_HOLDING` | 16,003 | 24,118 |
| `FOOTNOTES` | 167,511 | 167,394 |
| Total | 578,988 | 580,545 |

| Entity measure | 2024 Q1 | 2026 Q1 |
|---|---:|---:|
| Submission accessions | 67,671 | 69,259 |
| Issuer CIKs | 4,739 | 5,306 |
| Reporting-owner CIKs | 34,292 | 37,948 |
| Accessions with non-derivative transactions | 53,758 | 50,330 |
| Accessions with derivative transactions | 24,925 | 22,102 |
| Accessions with footnotes | 58,973 | 58,861 |

Issuer CIK/name/trading symbol, accession, filing date, period, and form are 100% populated in both submission samples.

| FND_16 field/test | 2024 Q1 | 2026 Q1 |
|---|---:|---:|
| Owner CIK/name | 100.000% | 100.000% |
| Owner relationship | 99.902% | 99.974% |
| Non-derivative date/shares/acquired-disposed/direct-indirect | 100.000% | 100.000% |
| Non-derivative transaction code | 100.000% | 99.997% |
| Non-derivative price present | 92.614% | 91.766% |
| Submission `AFF10B5ONE` present | 94.046% | 84.815% |
| Bulk accepted timestamp | 0.000% | 0.000% |
| Amendment original date | 1.894% | 1.678% |

`AFF10B5ONE` mixes `0`/`1` with `false`/`true` and is submission-level, so it cannot attribute a plan flag to one row in a mixed filing.

### Transaction-code summary

| Non-derivative code | 2024 Q1 | 2026 Q1 | Meaning class |
|---|---:|---:|---|
| `F` | 27,522 | 27,019 | delivery/withholding payment |
| `A` | 25,674 | 24,690 | grant/award/other acquisition |
| `S` | 27,191 | 22,822 | sale |
| `M` | 17,653 | 16,300 | exercise/conversion |
| `P` | 5,954 | 5,935 | purchase code |
| Other | 7,410 | 6,967 | gift/conversion/discretionary/other |

Derivative rows are dominated by `A` and `M` (36,422 and 36,122 combined); derivative and non-derivative tables must remain separate.

| Non-derivative `P` test | 2024 Q1 | 2026 Q1 |
|---|---:|---:|
| Acquired-disposed=`A` | 5,914 / 5,954 (99.328%) | 5,921 / 5,935 (99.764%) |
| Shares present | 100.000% | 100.000% |
| Price present | 99.547% | 99.292% |
| Title contains common-stock/share wording | 85.388% | 91.525% |

Code `P` separates purchases from grants, exercises, gifts, conversions, and sales. It does not prove issuer common stock: `SECURITY_TITLE` is free text and includes units, ordinary shares, classes, and other variants.

### Insider amendment and timing decision

- Amendment form identity is explicit: 1,282 `/A` filings in 2024 Q1 and 1,162 in 2026 Q1.
- `DATE_OF_ORIG_SUB` is populated on amendments, but no predecessor accession is supplied.
- No insider table contains SEC acceptance time. `FILING_DATE` is not a safe public-availability substitute.
- A later task must separately qualify an official accession-to-acceptance join and predecessor rule.

FND_16 status: `FIELD_OR_AMENDMENT_IDENTITY_BLOCKED`.

## Financial statement data

| Measure | 2024 Q1 | 2026 Q1 |
|---|---:|---:|
| Submissions/accessions | 6,028 | 6,169 |
| Issuer CIKs | 5,506 | 5,750 |
| Numeric facts | 3,428,694 | 3,690,955 |
| Presentation rows | 726,155 | 733,134 |
| Taxonomy rows | 86,529 | 91,794 |
| All four table rows | 4,247,406 | 4,522,052 |
| Annual filings including `/A` | 4,479 | 4,802 |
| Annual issuer CIKs | 4,428 | 4,761 |
| Annual amendments | 81 | 56 |

Submission accession, form, filed date, and accepted timestamp are 100% populated. All annual rows have period, fiscal year, filed and accepted time; one 2026 annual row lacks fiscal-period code. Annual SIC coverage is 97.187% and 96.710%.

Acceptance timestamps are 100% populated with observed pattern `YYYY-MM-DD HH:MM:SS.0`, preserving filing-level timing absent from the insider bulk data.

### Exact total-assets test

Exact `Assets` occurs under separately identified US-GAAP and IFRS taxonomy versions. No custom or label-derived substitute was mixed.

| Candidate rule | 2024 Q1 | 2026 Q1 |
|---|---:|---:|
| Annual filings | 4,479 | 4,802 |
| Exactly one eligible period-end fact | 4,317 (96.383%) | 4,621 (96.231%) |
| Multiple eligible candidates | 0 | 0 |
| Missing exact candidate | 162 | 181 |
| Domestic `10-K` coverage | 3,944 / 3,974 (99.245%) | 4,218 / 4,262 (98.968%) |

Structurally matching rows with blank values were excluded: six in 2024 Q1 and three in 2026 Q1. Missing candidates concentrate in foreign forms: 131/442 in 2024 Q1 and 137/493 in 2026 Q1. This forbids silent fallback to a label, custom tag, non-USD unit, segment, or amendment.

### First-as-filed decision

- Each accession is separate and every annual filing has accepted time.
- Original and `/A` forms are distinguishable; no examined issuer-period group has multiple non-amended originals.
- 2024 Q1 has 78 annual amendment groups; 31 include original plus amendment in-quarter, while 47 need another quarter.
- 2026 Q1 has 54; 32 are closed in-quarter and 22 need another quarter.
- `prevrpt` is a retrospective boolean, not a predecessor accession, and can encode later knowledge in a reprocessed ZIP.
- Earliest non-amended accession ordering is mechanically possible with all required quarters, but these non-consecutive samples do not prove consecutive annual periods or complete amendment chains.

FND_22 status: `BOUNDED_SAMPLE_INSUFFICIENT`.

## FND_07 metadata by-product

Financial accession, form, fiscal period, period end, filed date, and accepted time support a future outcome-blind cadence design. No expected-date model was built.

FND_07 status: `SEC_SCHEMA_READY_MAPPING_BLOCKED`.

## Permanent security mapping

A read-only repository and central-schema scan found:

- no artifact combining CIK, permanent security ID, historical ticker, share class, listing interval, exchange, and corporate-action lineage;
- no central DuckDB CIK/permanent-security column or CIK-to-ticker table;
- a CIK/accession SEC Company Facts adapter that does not solve issuer-to-share-class history.

`CIK_SECURITY_MAPPING_STATUS=ABSENT`. SEC fields therefore cannot yet join survivor-aware tradable securities. No price join or outcome access is authorized.

## Adjudication

| Mechanism | Status | Decisive reason |
|---|---|---|
| `FND_16_CLUSTER_INSIDER_PURCHASES` | `FIELD_OR_AMENDMENT_IDENTITY_BLOCKED` | No bulk accepted time or predecessor accession; free-text share identity; mapping absent. |
| `FND_22_ASSET_GROWTH` | `BOUNDED_SAMPLE_INSUFFICIENT` | Deterministic exact-tag subset exists, but coverage, consecutive periods, amendment closure, and mapping are incomplete. |
| `FND_07_FILING_LAG_REPORTING_DELAY` | `SEC_SCHEMA_READY_MAPPING_BLOCKED` | Filing metadata are sufficient for design only; no expected-date model or mapping. |

Overall: `FIELD_OR_AMENDMENT_IDENTITY_BLOCKED`. No strategy was implemented or selected. `strategy_candidate_available=false`.

## Narrowest next action

Do not build a generalized SEC platform. If Manager later resumes this lane:

1. qualify one official accession-bound insider acceptance/predecessor route with a tiny aggregate-only sample;
2. freeze one permanent CIK-to-share-class history contract before any SEC-to-market join;
3. add only adjacent financial quarters needed to prove consecutive annual periods and amendment closure, excluding exact-`Assets` failures rather than substituting concepts.

## Callback

```text
BATCH=US_SEC_DATA_READINESS_WEEK_20260720
STATUS=FIELD_OR_AMENDMENT_IDENTITY_BLOCKED
INSIDER_FILES=2024q1_form345.zip,2026q1_form345.zip
FINANCIAL_FILES=2024q1.zip,2026q1.zip
SOURCE_HASHES=8e9bb34335416829a88e4ca7d09bb8aaceca689da9718fef22c298d6f18c9b04,3dcb680593f5829bc951cb0969e858b60fc21a6835b094838218093a849592d6,94c7894b00903f8ff7186c4250ba1c1daa1bde8b3a0b26fae68f72608b2ffc9b,d18c01c615da8f5cd46273b0dacaeee5b1163f4089171da0f84153a5f3c362f6
INSIDER_ROW_COUNT=1159533
INSIDER_OWNER_COUNT=72240_DISTINCT_QUARTER_SUM_NOT_CROSS_QUARTER_DEDUPED
OPEN_MARKET_PURCHASE_CLASSIFICATION_STATUS=CODE_P_PRESENT_COMMON_SHARE_CLASS_UNRESOLVED
ACCEPTED_TIMESTAMP_STATUS=INSIDER_ABSENT_FINANCIAL_COMPLETE
AMENDMENT_STATUS=FORM_FLAGS_PRESENT_PREDECESSOR_ACCESSION_ABSENT
ASSET_TAG_COVERAGE_STATUS=EXACT_RULE_4317_OF_4479_AND_4621_OF_4802
FIRST_AS_FILED_STATUS=ORDERABLE_CROSS_QUARTER_CHAIN_NOT_PROVEN
CIK_SECURITY_MAPPING_STATUS=ABSENT
FND16_READINESS=FIELD_OR_AMENDMENT_IDENTITY_BLOCKED
FND22_READINESS=BOUNDED_SAMPLE_INSUFFICIENT
FND07_METADATA_READINESS=SEC_SCHEMA_READY_MAPPING_BLOCKED
REPORT_URL=reports/validation/us_sec_data_readiness_week_20260721.md
PRICE_ACCESS=false
RETURN_ACCESS=false
DATABASE_WRITE=false
STRATEGY_CANDIDATE_AVAILABLE=false
```
