# Cycle 4 External-Review Checkpoint — Three-ETF Data and Cost Semantics

Date: 2026-07-17
Repository: `2604714984-prog/quant-proj`
Default branch: `v2-main`
Status: `EXTERNAL_REVIEW_REQUIRED_BEFORE_IMPORT_OR_SHARED_SEMANTIC_CHANGE`

## Review boundary

This checkpoint asks for a narrow decision before any Cycle 4 provider call,
database write, shared-core change or strategy outcome. It does not ask the
reviewer to redesign the strategy.

Controlling identities:

```text
v2-main commit: 042eb40a00c823641370dc36361f9cdfd0f04ba0
tree: 63ca2a7733110c89f7bc89ed48bcaa4b1e36c72c
Cycle 4 task SHA256: 4b2db941f1f43a957e43d76f5cfd3727f4d4d64adac6e6d2ff6c2d41e429cca2
active research ID: A_SHARE_LISTED_ETF_ABSOLUTE_TREND_DEFENSIVE_ALLOCATION_V1_20260717
strategy_candidate_available: false
```

Cycle 3 is closed as
`CLOSED_PREFLIGHT_STRUCTURAL_INFEASIBLE_NO_OUTCOME`; no Cycle 3 result or
parameter is reused here.

## Frozen Cycle 4 design

The fixed universe is:

```text
510300.SH: domestic equity
511010.SH: government bond
518880.SH: gold
cash: uninvested balance with zero return
```

The only primary strategy is a fixed one-third sleeve per ETF. A sleeve is held
only when its qualified adjusted month-end close is strictly above the mean of
the preceding ten complete qualified month-end closes; otherwise that sleeve is
cash. The only comparator is static equal weight. No ranking, winner selection,
parameter grid, macro filter or regime filter is allowed.

No return, NAV, trend state, ranking or performance gate has been opened.

## Read-only data qualification

Central database:

```text
path: /home/rongyu/workspace/quant-data/quant_research.duckdb
SHA256 before and after: e636bb80e300f89e46831e91275c6f2167e370e81a00b21b300e253f6107bee0
size: 4,671,156,224 bytes
mode: 0600
WAL: absent
mutation: none
```

Current central snapshot
`a_share_qfq_personal_research_20260716_v5`:

| Instrument | Rows | Dates | Volume/amount null | Limit null | Result |
|---|---:|---:|---:|---:|---|
| 510300.SH | 2,058 | 2018-01-02–2026-06-30 | 0 | 2,058 | present, ETF limits structurally absent |
| 511010.SH | 0 | 0 | n/a | n/a | absent |
| 518880.SH | 0 | 0 | n/a | n/a | absent |

The central three-instrument common-date count is zero. The symbol master,
adjustment-factor table and limit-status table contain no records for the fixed
three-ETF set.

Local source evidence inspected read-only:

```text
path: /home/rongyu/workspace/quant-data/recovery/legacy-local/A_Share_Monitor/data/cache/etf_rotation_e1_20260707/etf_daily_qfq_tencent_20260707.csv
SHA256: c5f37bc0ad3a086ab24c50e84ebc1333ef716effd397bd46972f36d9d8b7c1b6
size: 8,730,091 bytes
```

Through the frozen cutoff 2026-06-30, each fixed ETF has 2,058 unique dates,
zero duplicate keys and complete OHLC/volume. Their common-date count is 2,058.
However, the CSV has:

```text
amount: null on all 6,174 fixed-universe rows
available_at: absent
listing identity: absent
suspension evidence: absent
upper/lower limits: absent
corporate-action and adjustment lineage: absent beyond the label qfq
immutable row hash: absent
```

Promoting these rows by deriving amount, assuming no suspension, inventing
historical availability, calculating limits without an accepted rule, or
treating the `qfq` label as a corporate-action chain would fabricate required
evidence. It is prohibited.

## Cost-path clarification

The shared `Portfolio` constructor already exposes all required primitives:

```text
TransactionCostModel.sell_tax_rate=0
lot_size=100
share_t_plus_one=true
a_share_stamp_tax_schedule=false
```

`Portfolio.a_share()` is stock-specific and forces the statutory stock stamp-tax
schedule. Cycle 4 must not reuse strategy-specific wrappers that assert that
schedule. An adapter-local factory can use the existing public constructor and
existing event loop without editing shared accounting. External review should
confirm whether this is an acceptable use of the already-public API. No shared
cost-code change is currently proposed.

## Narrow proposed continuation

The Manager recommends the fail-closed route:

1. Do not import the recovery CSV.
2. Qualify exactly one public canonical provider for the fixed three ETFs and
   frozen cutoff. It must supply actual CNY amount plus sufficient product,
   listing, suspension, limit and adjustment evidence; no automatic source
   fusion.
3. Historical availability may be classified as
   `UNKNOWN_NOT_PIT_QUALIFIED`; it must not be backfilled or claimed as strict
   PIT. The snapshot remains retrospective personal-research grade and cannot
   authorize prospective use.
4. If all frozen fields can be populated under the unchanged central schema,
   append one new immutable three-ETF snapshot. Do not overwrite or extend v5.
5. If a provider cannot supply explicit limit/suspension/corporate-action
   evidence, keep Cycle 4 `INPUT_BLOCKED`. Do not relax the execution contract.
6. Only an independently accepted snapshot may unlock outcome-blind PR A.

No new database layer, provider fusion, runner, event loop, portfolio core or
evidence framework is proposed.

## Requested external verdict

Return one of:

```text
ACCEPT_NARROW_CONTINUATION
```

The existing public Portfolio primitives may express ETF zero stamp tax without
a shared-core edit. Continue with one bounded canonical-provider qualification;
import only if every frozen field fits the unchanged central contract.

```text
ACCEPT_BLOCKED_REQUIRE_COMPLETE_SOURCE
```

The proposed contract is sound, but no current source is sufficient. Keep the
family blocked until one complete source is independently qualified.

```text
REWORK_REQUIRED
```

Name only the concrete data-contract or cost-semantic defect. Do not propose a
new engine, broader universe, parameter change or alternative strategy.

Any proposal to treat ETF limit fields as structural nulls during execution,
infer suspension, derive amount, fabricate historical `available_at`, or change
shared accounting requires a separate explicit semantic review.

## Current state

```text
ACTIVE_FAMILY=CYCLE_4_A_SHARE_LISTED_ETF_ABSOLUTE_TREND
ACTIVE_STAGE=EXTERNAL_REVIEW_CHECKPOINT
PREFLIGHT_STATUS=NOT_RUN
OUTCOME_STATUS=NOT_RUN
FORWARD_STATUS=CLOSED
DATABASE_WRITE=false
PROVIDER_CALL=false
STRATEGY_CANDIDATE_AVAILABLE=false
```
