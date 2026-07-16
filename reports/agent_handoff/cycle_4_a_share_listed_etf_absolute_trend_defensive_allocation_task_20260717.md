# Cycle 4 Task — A-Share Listed-ETF Absolute Trend Defensive Allocation

Date: 2026-07-17
Repository: `2604714984-prog/quant-proj`
Default branch: `v2-main`
Status: `AUTHORIZED_FOR_DATA_IDENTITY_QUALIFICATION_ONLY`

## Authority and base

Read, in order:

1. `reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md`
2. `reports/agent_handoff/user_dispatch_manager_v2_post_audit_roadmap_v2_20260716.md`
3. `AGENTS.md`

Research ID:

```text
A_SHARE_LISTED_ETF_ABSOLUTE_TREND_DEFENSIVE_ALLOCATION_V1_20260717
```

Current state:

```text
ACTIVE_FAMILY=CYCLE_4_A_SHARE_LISTED_ETF_ABSOLUTE_TREND
ACTIVE_STAGE=DATA_IDENTITY_QUALIFICATION
PR_A=NOT_STARTED
PREFLIGHT_STATUS=NOT_RUN
OUTCOME_STATUS=NOT_RUN
FORWARD_STATUS=CLOSED
STRATEGY_CANDIDATE_AVAILABLE=false
```

Publication of this task authorizes the read-only data qualification described
below. It does not authorize provider calls, database writes, PR A code, or
strategy outcomes.

## Frozen economic hypothesis

A fixed equity, government-bond and gold allocation may reduce dependence on a
single return source. Applying one absolute-trend rule independently to each
fixed one-third sleeve, with failed sleeves left in non-interest-bearing cash,
may improve net downside-adjusted outcomes without selecting a winning asset.

This is not a rerun or rescue of US31, US36, US41, US46, Relative Strength,
Defensive Low Volatility or Cycle 3.

## Fixed universe and variants

Fixed listed ETFs:

```text
510300.SH: domestic equity
511010.SH: government bond
518880.SH: gold
```

Cash is an internal uninvested balance with exactly zero return and no interest.

Freeze exactly two ordered variants:

1. `STATIC_EW_3_ASSET`: one-third target weight in each ETF, comparator only.
2. `TREND10_SLEEVE_TO_CASH`: primary strategy. Each ETF owns one fixed one-third
   sleeve. At decision D, hold that sleeve only when D's qualified adjusted
   close is strictly above the arithmetic mean of the ten preceding complete
   month-end qualified adjusted closes. Otherwise leave the sleeve in cash.

There is no cross-sectional ranking, winner selection, replacement asset,
volatility scaling, regime filter, macro input, parameter grid or third variant.

Missing history or execution evidence invalidates the whole decision; it must
not be interpreted as a negative trend signal.

## Frozen execution contract

```text
capital: CNY 400,000
maximum positions: 3
decision: accepted month-end D, 30 minutes after close
entry/rebalance: D+1 accepted-session open
position unit: SHARES
board lot: 100 shares
primary one-way cost: 50 bps
diagnostic one-way cost: 20 bps
A-share ETF sell stamp tax: 0
benchmark: buy-and-hold 510300.SH through the same shared event loop
cash return: exactly 0
```

Reuse the existing event loop, portfolio, capacity, limit, suspension,
terminalization and blocked-exit paths. If zero ETF stamp tax cannot be expressed
through the current public Portfolio API, stop for full external review; do not
change shared accounting inside PR A.

## Frozen historical and inference contract

```text
development: 2018-01-01 through 2021-12-31, descriptive only
validation: 2022-01-01 through 2023-12-31, minimum 20 complete months
retrospective holdout: 2024-01-01 through 2026-06-30, minimum 24 complete months
embargo: 2026-07-01 through 2026-12-31, closed
prospective shadow: 2027-01-01 through 2029-12-31, closed
```

The first historical outcome contains exactly four primary comparisons:

```text
TREND10 minus 510300 in validation
TREND10 minus STATIC_EW_3_ASSET in validation
TREND10 minus 510300 in retrospective holdout
TREND10 minus STATIC_EW_3_ASSET in retrospective holdout
```

Use circular block bootstrap on paired monthly differences:

```text
block length: 3 months
resamples: 10,000
seed: 4701
family alpha: 0.05
Bonferroni per-comparison alpha: 0.0125
one-sided lower confidence bound: linearly interpolated 1.25th percentile
```

Both gated splits must satisfy all of:

```text
minimum complete-month count
zero invalid decisions, missing valuations and unexpected exceptions
50 bps net annualized return > 0
50 bps net annualized return > 510300
50 bps net annualized return > STATIC_EW_3_ASSET
both paired-difference bootstrap lower bounds > 0
absolute maximum drawdown <= 510300 absolute maximum drawdown
```

Any mandatory failure permanently closes the family. Do not change the ten-month
rule, asset set, costs, cash rule, comparisons or gates after outcome access.

## Current data-identity blocker

The current central snapshot
`a_share_qfq_personal_research_20260716_v5` contains only `510300.SH` from the
fixed universe. `511010.SH` and `518880.SH` have zero rows, so common decision
coverage is zero.

Before PR A, qualify one coherent immutable three-ETF snapshot through the
existing central data contract. Required fields and identities are:

```text
ETF symbol and product identity
trade date and accepted calendar identity
raw and adjusted OHLC in CNY
volume in SHARES
amount in CNY
suspension and executable-state evidence
upper and lower price-limit evidence
listing date
corporate-action / adjustment version
source, snapshot and row hashes
quality and availability classification
```

The read-only qualification must report aggregate-only coverage, duplicates,
nulls, common dates and exact immutable source identities. It must not emit
returns, NAV, trend states, rankings or strategy gates.

An old recovery CSV may be examined only as source evidence. It may not be used
directly by the strategy or silently promoted into the central canonical table.

## Authorization sequence

1. Merge this task and the Cycle 3 terminal closure in one documentation-only PR.
2. Produce a read-only three-ETF source and schema qualification.
3. If completing the snapshot requires any PIT, availability, unit,
   snapshot-contract, cost, limit, suspension or corporate-action semantic
   change, stop and prepare full external review before mutation.
4. If the unchanged existing contract is sufficient, assign the dedicated
   central-data task a bounded append-only import with backup, rollback and
   aggregate parity evidence.
5. Independently accept the resulting immutable snapshot.
6. Only then publish a separate PR A implementation task.
7. PR A may contain definition, adapter, focused tests and repeatable
   outcome-free preflight only.
8. A separate Manager decision is required before one historical outcome.

## External-review triggers

Stop and prepare full external review on the first occurrence of:

```text
shared event-loop or Portfolio change
ETF cost, limit, suspension, corporate-action or settlement semantic change
PIT, availability, unit or snapshot-contract change
first Cycle 4 historical PASS
any prospective result
```

Ordinary data `INPUT_BLOCKED`, outcome-free preflight, or historical FAIL under
unchanged accepted semantics does not require full external review.

## Boundary

Research-only. No provider/network access, database/cache/schema/raw-data write,
historical or prospective outcome, recommendation, ranking, candidate,
readiness/product route, broker, order, paper, live or automatic execution is
authorized by this file. `strategy_candidate_available=false`.
