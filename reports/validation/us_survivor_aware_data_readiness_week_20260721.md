# US Survivor-Aware Data Readiness — Week C

Date: 2026-07-21
Phase: outcome-blind local data qualification
Status: `DATA_BLOCKED_SURVIVOR_OR_TERMINAL_VALUE`
Strategy candidate available: `false`

## Control binding

- Control worktree HEAD: `037827f85becec1c706c679402a313fcf23922fc`
- Control worktree tree: `f58c233c935227c84ccc455530e0d1e819a212dd`
- Task: `reports/agent_handoff/us_survivor_aware_stock_data_readiness_week_task_20260720.md`
- Task SHA256: `f70014ecfe170268d6858c0f9e3653c9c5910aa5b0c73c009fde2d7ba74494bd`
- Execution branch: `evidence/week-c-survivor-readiness-20260721`
- Base commit: `6751fa4f3acf30e41a06cb6f90c0d8c50abdc095`
- Base tree: `8e3fa35ce60b5edb64f2cbd4e81492472114c28e`

## Scope and method

The central DuckDB was opened with `read_only=True`. Queries were limited to
schema, field types, row and distinct-key counts, date coverage, null counts,
duplicate-key counts, status aggregates, and identifier coverage. No query
selected, exported, printed, retained, compared, or transformed a per-security
price, volume, or dollar-volume value.

The task did not use a provider, network route, database writer, return engine,
signal code, or portfolio code. Provider-route findings below are limited to
the frozen task contract and local evidence; no new provider claim was made.

## Local snapshot identity

- Database: Git-external `quant_research.duckdb`
- Size: `4,671,156,224` bytes
- Mode: `0600`
- SHA256 before and after all accepted queries:
  `e636bb80e300f89e46831e91275c6f2167e370e81a00b21b300e253f6107bee0`
- Warehouse version: `1.0`, description `central research warehouse v1`
- Relevant snapshots:
  - `tushare_wsl2_20260712`
  - `local_research_batch_20260712_ef36ab32_9c597fa8`
  - `sina_us_etf_20160101_20251231_e4c60497095e76f9`
  - `tiingo_raw_20260711T142010Z_5c24877d23cfc4a0`

These snapshots are not one accepted survivor-aware, cross-table identity.

## Local inventory

| Local table group | Coverage observed from keys and metadata only | Qualification |
|---|---|---|
| Main US symbol master | 6,000 rows and distinct symbols; 6,000 listed, 0 inactive, 0 delisted; one current snapshot | FAIL — active-only master |
| Main US daily raw | 1,547 rows, 11 symbols, 2025-05-30 to 2026-06-02; 0 within-snapshot duplicate symbol-date keys; 5 symbols have at least 252 date keys | PARTIAL — raw fields only, very narrow, no survivor identity |
| Nasdaq security metadata | 270 rows/symbols; 270 active, 0 inactive; 270 start and end metadata dates; 0 non-null `available_at`; 0 canonical-eligible | FAIL — current-active-only and non-PIT |
| Nasdaq daily bars | 559,959 rows, 270 symbols, 2018-01-02 to 2026-07-06; all 270 have at least 252 date keys; 0 duplicate snapshot-symbol-date keys | PARTIAL — raw fields exist but adjustments and corporate actions are absent |
| Sina daily bars | 7,542 rows, 3 fund symbols, 2016-01-04 to 2025-12-31; raw only; 0 duplicate keys | FAIL for stock universe — fund-only and no actions |
| Tiingo total-return research | 20,737 rows, 3 fund symbols, 1993-01-29 to 2026-07-10; raw/adjusted fields exist; 0 non-null `available_at`; 0 duplicates | FAIL for stock universe — retrospective fund-only evidence |
| Corporate-action research | 224 events for 2 fund symbols, 1993–2026 across 34 years; 0 declaration dates; 0 non-null `available_at` | FAIL — EOD-derived, unqualified PIT, not stock-universe coverage |
| US trade calendar | 0 rows | FAIL |

Null-count inspection confirmed the declared raw fields are physically present
in the populated bar tables. This is field-existence evidence only, not price
quality, adjustment correctness, or strategy readiness.

## Required-field qualification

| Required identity or field | Status | Decisive evidence |
|---|---|---|
| `permanent_security_id` | FAIL | No matching US column or mapping table |
| `historical_ticker` | FAIL | No effective-dated symbol history tied to a permanent ID |
| `share_class_id` | FAIL | No matching US field |
| `primary_exchange` | PARTIAL | Current market/exchange metadata exists, not effective-dated or canonical |
| `security_type` | PARTIAL | Current `asset_type` exists for 270 records only |
| `listing_start` | PARTIAL | Dates exist, but lack accepted PIT availability identity |
| `listing_end` | FAIL | No qualified delisting/end-of-listing semantics |
| `active_as_of_date` | FAIL | Active flags are current-only and have no accepted `available_at` |
| `delisting_reason` | FAIL | Absent |
| terminal value or missing-terminal policy | FAIL | No explicit field, table, or policy identity |
| raw OHLC fields | PARTIAL | Broad local fields exist, but cannot join to a survivor-aware identity |
| adjusted OHLC fields | FAIL | Present only for 3 retrospective fund symbols, not broad stocks |
| volume | PARTIAL | Field exists; broad identity remains non-canonical |
| dollar volume | FAIL | Not available with explicit units across the broad stock panel |
| split events | FAIL | One fund-only EOD-derived event; no broad stock coverage |
| cash dividends | FAIL | Fund-only EOD-derived coverage with unknown availability |
| special distributions | FAIL | No qualified explicit coverage |
| symbol changes | FAIL | No effective-dated mapping |
| mergers and acquisitions | FAIL | No qualified event identity |
| bankruptcy or liquidation identity | FAIL | Absent |
| trading halt/status history | FAIL | No US halt/status table found |
| row-level provenance | PARTIAL | Hash fields exist, but sources are separate unaccepted snapshots |
| `available_at` or retrospective label | PARTIAL | Labels exist, but all relevant Nasdaq and total-return rows are non-PIT/unknown |

## Survivor-bias tests

- Active/inactive/delisted counts in the primary master: `6000 / 0 / 0`.
- Separate Nasdaq metadata sample: `270 / 0 / 0`.
- Securities with qualified terminal values or an explicit missing-terminal
  policy: `0 representable`; the required policy field is absent.
- Historical symbols mapped to permanent IDs: `0 representable`; both required
  identities are absent.
- Within-snapshot bar duplicate keys: `0` in main raw, Nasdaq, Sina, and Tiingo
  research tables. This does not create a canonical cross-source union.
- Share-class collision testing: not possible because `share_class_id` and
  permanent-security mapping are absent.
- Corporate-action coverage: 224 EOD-derived events across 34 calendar years,
  but only 2 fund symbols, with unknown availability and no declaration dates.
- Event counts by ex-date year:
  `1993:4, 1994:4, 1995:4, 1996:4, 1997:4, 1998:4, 1999:4, 2000:5,
  2001:4, 2002:4, 2003:5, 2004:6, 2005:6, 2006:8, 2007:8, 2008:8,
  2009:8, 2010:8, 2011:8, 2012:8, 2013:8, 2014:9, 2015:8, 2016:8,
  2017:8, 2018:8, 2019:8, 2020:8, 2021:8, 2022:8, 2023:9, 2024:8,
  2025:8, 2026:4`.
- Current-constituent backfill: cannot be ruled out; both stock masters contain
  zero inactive names and lack effective-dated membership identity.
- Dead-security retention through terminal event: cannot be tested; there are
  no inactive/delisted securities and no terminal-value policy.

The zero inactive and delisted counts are decisive. Missing dead securities
cannot be interpreted as evidence that no failures occurred.

## Mechanism probes

| Atlas probe | Readiness | Reason |
|---|---|---|
| `STK_01_52_WEEK_HIGH_PROXIMITY` | FAIL | Date-key length is sufficient for 270 raw series, but split timing, adjusted highs/closes, historical eligibility, dead securities, and terminal values are unqualified |
| `STK_04_FIVE_DAY_MARKET_RESIDUAL_REVERSAL` | FAIL | No accepted US calendar, halt history, corporate-action-complete stock panel, inactive securities, or terminal-value policy |
| `STK_12_AMIHUD_ILLIQUIDITY_AVOIDANCE` | FAIL | Broad dollar-volume units/identity, zero-volume and stale-price semantics, PIT microcap/OTC status, and inactive securities are unqualified |

No residual, return, 52-week-high value, rank, Amihud ratio, portfolio, or
winner/loser outcome was calculated.

## Provider-route classification

- Existing local route: `DATA_BLOCKED_SURVIVOR_OR_TERMINAL_VALUE`.
- Norgate: `PAID_ROUTE_NOT_AUTHORIZED` under the frozen task; not accessed.
- Massive: `UNAVAILABLE_AS_QUALIFIED_INPUT_WITHIN_LOCAL_ONLY_SCOPE`; no claim
  that documented reference history supplies full corporate actions or terminal
  values.
- SEC: `IDENTITY_ONLY_NOT_SURVIVOR_AWARE_PRICE_SOURCE`; CIK is not treated as a
  permanent tradable-security or share-class identifier.
- `PAID_ROUTE_REQUIRED`: not established by this local-only audit. A paid route
  was neither purchased nor trialled.

## Conclusion and blockers

Overall status: `DATA_BLOCKED_SURVIVOR_OR_TERMINAL_VALUE`.

Decisive blockers:

1. Both local stock masters contain zero inactive and zero delisted securities.
2. Permanent-security, historical-symbol, and share-class identities are absent.
3. No explicit delisting return, terminal value, or missing-terminal policy exists.
4. Broad stock bars are raw-only, corporate actions are excluded, and
   `available_at`/canonical eligibility are unqualified.
5. The US calendar and halt/status history are absent.
6. Existing adjusted and corporate-action data cover only a tiny fund set and
   cannot qualify a survivor-aware stock universe.

Narrowest next action: preserve this terminal local-readiness finding. Reopen
only if a bounded source contract supplies inactive/delisted securities,
permanent and share-class mapping, terminal-value policy, corporate actions,
calendar/status history, and immutable provenance. Data qualification alone
must not authorize strategy outcome access.

## Callback

```text
BATCH=US_SURVIVOR_AWARE_DATA_READINESS_WEEK_20260720
STATUS=DATA_BLOCKED_SURVIVOR_OR_TERMINAL_VALUE
LOCAL_SNAPSHOT_ID=quant_research.duckdb@sha256:e636bb80e300f89e46831e91275c6f2167e370e81a00b21b300e253f6107bee0
ACTIVE_SECURITY_COUNT=6000
INACTIVE_SECURITY_COUNT=0
DELISTED_SECURITY_COUNT=0
TERMINAL_VALUE_COVERAGE=FAIL_ABSENT
PERMANENT_ID_STATUS=FAIL_ABSENT
CORPORATE_ACTION_STATUS=FAIL_FUND_ONLY_EOD_DERIVED_UNKNOWN_AVAILABILITY
STK_01_READINESS=FAIL
STK_04_READINESS=FAIL
STK_12_READINESS=FAIL
PAID_ROUTE_REQUIRED=NOT_ESTABLISHED_NO_PURCHASE
REPORT_URL=reports/validation/us_survivor_aware_data_readiness_week_20260721.md
PRICE_FIELD_METADATA_INSPECTED=true
PER_SECURITY_PRICE_VALUES_READ=false
RETURN_COMPUTATION=false
SIGNAL_COMPUTATION=false
DATABASE_WRITE=false
STRATEGY_CANDIDATE_AVAILABLE=false
```

Boundary result:
`PASS_OUTCOME_BLIND_LOCAL_METADATA_ONLY_NO_PRICE_VALUES_NO_RETURNS_NO_DB_WRITE`.
