# Cycle 4 External Audit Verdict — Three-ETF Data and Corporate-Action Semantics

Date: 2026-07-17  
Repository: `2604714984-prog/quant-proj`  
Review target: PR #68  
Reviewed head before this report: `ade21c4c90931f22fda563239996bf41fabd3432`  
Reviewed base: `v2-main@042eb40a00c823641370dc36361f9cdfd0f04ba0`

## Verdict

```text
REWORK_REQUIRED
```

This is a narrow semantic rework verdict. It does **not** authorize a new engine,
a new database layer, a broader ETF universe, a parameter change, a strategy
outcome, or any trading path.

Cycle 4 remains:

```text
ACTIVE_FAMILY=CYCLE_4_A_SHARE_LISTED_ETF_ABSOLUTE_TREND
ACTIVE_STAGE=REWORK_REQUIRED_BEFORE_DATA_IMPORT
PREFLIGHT_STATUS=NOT_RUN
OUTCOME_STATUS=NOT_RUN
FORWARD_STATUS=CLOSED
DATABASE_WRITE=false
STRATEGY_CANDIDATE_AVAILABLE=false
```

## Accepted findings

The following conclusions in the PR #68 checkpoint are accepted:

1. The legacy recovery CSV must not be imported. It lacks actual CNY amount,
   historical availability, product/listing identity, suspension evidence,
   price-limit evidence, corporate-action lineage, and immutable row identity.
2. The current central snapshot does not contain a coherent fixed-universe
   three-ETF panel. `511010.SH` and `518880.SH` are absent.
3. The generic public `Portfolio` constructor can express the Cycle 4 transaction
   cost shape without changing shared cost code:

   ```text
   sell_tax_rate=0
   lot_size=100
   share_t_plus_one=true
   a_share_stamp_tax_schedule=false
   ```

   `Portfolio.a_share()` must not be used because it forces the stock stamp-tax
   schedule.
4. Cycle 3 is correctly closed as
   `CLOSED_PREFLIGHT_STRUCTURAL_INFEASIBLE_NO_OUTCOME` and supplies no parameter,
   result, or specialist to Cycle 4.
5. No return, NAV, trend state, ranking, gate, provider call, database write, or
   prospective observation has been opened.

## Blocking finding — the shared core cannot currently account for A-share ETF distributions

A complete market-data source is not sufficient by itself.

The current shared core has two incompatible boundaries:

- `src/quant_system/backtest/event_loop.py` rejects ordinary corporate-action
  identities when `market == "a_share"`;
- `src/quant_system/backtest/portfolio.py::apply_cash_distribution()` rejects
  every portfolio that is not configured as a US portfolio.

Therefore an A-share ETF position cannot receive an ex-date entitlement and a
pay-date cash distribution through the accepted event loop.

This is material for the fixed Cycle 4 sample. The Shanghai Stock Exchange
records a `510300` distribution with ex-date 2025-06-18 and another with ex-date
2026-01-19, both inside or adjacent to the frozen historical coverage:

- https://www.sse.com.cn/assortment/options/disclo/update/c/c_20250611_10781544.shtml
- https://www.sse.com.cn/assortment/options/disclo/update/c/c_20260112_10804960.shtml

A 2018-2026 backtest that uses raw execution prices but cannot credit ETF cash
distributions can misstate cash, NAV, subsequent target sizes, comparator
returns, and paired-difference tests. Using a `qfq` label alone does not repair
this: adjusted prices are not a substitute for account-level cash entitlements,
board-lot execution, and actual share quantities.

This defect triggers the repository constitution's full-review rule for shared
corporate-action semantics.

## Required semantic rework

Before any ETF import or Cycle 4 PR A, create one narrow implementation task and
one implementation PR for **listed-fund cash distributions only**.

The allowed behavior is:

```text
source-bound action identity
explicit subject_id and event_id
cash_dividend or special_dividend only
explicit ex_date, record_date and pay_date
explicit CNY cash amount per share
source.available_at no later than the frozen decision cutoff
entitlement frozen from session-open shares on ex-date
cash credited on pay-date exactly once
no automatic reinvestment
no duplicate credit
no use of adjusted prices to double-count the distribution
```

The implementation must reuse the existing `CorporateActionIdentity`, `Portfolio`,
and event-loop paths. It must not create a corporate-action framework, service,
registry, or second engine.

A-share stock-dividend taxation and arbitrary stock corporate actions are out of
scope. The input contract for this patch must state that the supplied amount is
the exact cash credited per fund share under the qualified listed-fund event.

Mandatory focused tests:

```text
A-share ETF held before ex-date receives the frozen entitlement
pay-date credits cash exactly once
selling after ex-date does not remove the already-frozen entitlement
buying on or after ex-date does not receive the prior entitlement
repeated action identity fails closed or is an exact no-op, never double credit
late or incomplete action identity fails before mutation
US distribution behavior remains unchanged
zero ETF sell stamp tax remains unchanged
```

The semantic PR must stop for independent external review before merge.

## Required source-contract rework

The checkpoint's phrase "one public canonical provider for the fixed three ETFs"
must not be interpreted as one vendor supplying every dataset.

The controlling policy is:

```text
one canonical source per dataset
at most one read-only cross-check source per dataset
no automatic source selection or fusion
```

A deterministic snapshot may bind different explicit canonical datasets. For
example, a bounded qualification may evaluate:

```text
market bars and actual amount: Tushare fund_daily
product/listing identity: Tushare fund_basic or etf_basic
adjustment factors: Tushare fund_adj
NAV/announced cumulative distribution cross-check: Tushare fund_nav
cash-distribution event identity: SSE and fund-manager announcements
accepted calendar: the existing accepted SSE calendar source
trading-rule identity: effective-dated official SSE rule evidence
```

Relevant public interface references:

- ETF daily fields: https://tushare.pro/document/2?doc_id=127
- fund basic/listing fields: https://tushare.pro/document/1?doc_id=19
- fund adjustment factor: https://tushare.pro/document/2?doc_id=199
- fund NAV and announcement date: https://tushare.pro/document/2?doc_id=119

This list is a qualification candidate, not an authorization to fetch, import,
or claim completeness.

For `fund_daily`, unit conversion must be explicit and tested:

```text
volume_shares = vol_in_lots * 100
amount_cny = amount_in_thousand_cny * 1000
```

Historical market rows retrieved now remain retrospective and non-strict-PIT.
Do not backdate `available_at`. Preserve actual retrieval time and a separate
historical-availability classification.

## Price-limit, suspension, and settlement boundary

For each of `510300.SH`, `511010.SH`, and `518880.SH`, the source qualification
must produce a small instrument-rule matrix containing:

```text
product type
listing date
board lot
sell stamp-tax rule
same-day-resale model assumption
price-limit rule identity and effective dates
suspension/non-trading evidence rule
corporate-action source rule
```

Do not fabricate daily upper/lower limits. Accept either:

1. authoritative daily values; or
2. an independently reviewed, effective-dated official rule plus exact prior
   close and rounding mechanics.

If neither is available, keep Cycle 4 blocked.

The existing `share_t_plus_one=true` setting may remain as a conservative Cycle 4
model constraint because the frozen strategy has no same-session round trip. It
must be described as a conservative model assumption, not as a universal
exchange fact for all three ETF classes.

## Required continuation sequence

```text
1. Merge PR #68 only as an external-review evidence checkpoint.
2. Do not import ETF data and do not implement Cycle 4 PR A.
3. Close stale PR #62 without merge.
4. Update the Manager roadmap to this verdict and state.
5. Publish one narrow listed-fund distribution semantic task.
6. Implement that task in one small PR and stop for full external review.
7. In parallel, perform read-only per-dataset source qualification.
8. Only after the semantic PR is accepted and the source matrix is complete,
   authorize one append-only immutable three-ETF snapshot.
9. Independently verify the new snapshot without outcomes.
10. Only then authorize Cycle 4 PR A and outcome-free preflight.
```

If the fixed source matrix cannot support raw execution bars, actual CNY amount,
listing identity, non-trading handling, price-limit semantics, and corporate
actions without fabrication, close Cycle 4 as:

```text
CLOSED_DATA_AND_SEMANTIC_CONTRACT_INCOMPLETE_NO_OUTCOME
```

Do not relax the asset set, ten-month rule, cash rule, or gates to avoid this
closure.

## Other repository findings carried forward

- The repository architecture remains accepted as reliable and lightweight.
- Cycle 3's structural preflight closure is accepted.
- Macro Risk Shadow Phase 1 may proceed independently as read-only,
  `NO_POSITION_EFFECT` work.
- Validated specialist count remains zero.
- Strategy synthesizer development remains unauthorized.
- No broker, order, paper, live, or automatic execution is authorized.
