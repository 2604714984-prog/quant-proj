# Repository-Wide Static Code Audit with Risk-Based Semantic Review

Date: 2026-07-17  
Repository: `2604714984-prog/quant-proj`  
Audited default-branch baseline: `v2-main@e4e0c1538ad73eca5a6900aabd903e9fba8ed15a`  
Open implementation heads additionally reviewed:

```text
PR #69: e68d14f86122831139f1f22b84e5792b8351ef50
PR #70: be3afc5a6220e155285b80aedebeb29742f201d8
```

## 1. Audit method and limits

This is a repository-wide, risk-based audit rather than an equal-depth reread of every historical report.

Line-level semantic review covered the active and high-risk surfaces:

```text
configuration and path isolation
CLI input capture and database path enforcement
DuckDB reader and append-only writer
source, calendar, status, and corporate-action identities
A-share and US market semantics
Portfolio accounting
Event Loop and blocked-exit lifecycle
capacity and transaction costs
active research adapters and split/inference primitives
CI and repository control documents
current PR #69 and PR #70
```

Closed migration and rejected-family modules were inventoried and sampled for latent reuse risk. They were not treated as active strategy authority.

The audit was supplemented with bounded deterministic reproductions of exact control-flow and arithmetic cases. It did not access the private DuckDB, raw payloads, credentials, embargo data, prospective outcomes, or any trading path.

## 2. Executive verdict

```text
REPOSITORY_ARCHITECTURE=ACCEPTED_LIGHTWEIGHT
ACTIVE_DATA_READER_WRITER=ACCEPTED
ACTIVE_PORTFOLIO_EVENT_LOOP=ACCEPT_WITH_NARROW_SHARED_FIXES
PR_69=DO_NOT_MERGE_CURRENT_HEAD
PR_70=ACCEPT_TERMINAL_SOURCE_QUALIFICATION_EVIDENCE
CYCLE_4=CLOSE_DATA_AND_SEMANTIC_CONTRACT_INCOMPLETE_NO_OUTCOME
CRITICAL_FINDINGS=0
HIGH_FINDINGS=3
MEDIUM_FINDINGS=2
FROZEN_LEGACY_FINDINGS=2
ARCHITECTURE_REBUILD_REQUIRED=no
STRATEGY_CANDIDATE_AVAILABLE=false
TRADING_STAGE_AUTHORIZED=false
```

The lightweight rebuild remains healthy. The principal risk is not architecture failure; it is allowing a narrow inactive feature or incomplete data contract to enter the shared core without an active strategy capable of using it.

## 3. Accepted repository properties

### 3.1 Architecture and scope

The active system remains proportionate to one personal research account:

```text
one repository
one Python package
one quant CLI
one configuration path
one DuckDB access layer
one Portfolio / Event Loop core
small market-semantic modules
one test suite
one CI workflow
```

No dispatcher, strategy registry, product route, second formal backtest engine, broker path, paper path, or live path has returned.

### 3.2 Repository and secret boundary

The repository excludes DuckDB, Parquet, raw data, snapshots, private directories, environment files, keys, tokens, and PEM files. Mutable data remains outside Git.

### 3.3 Reader and writer

The reader uses a pinned regular-file descriptor, read-only DuckDB, one SELECT statement, disabled external access, bounded result rows, and path-identity checks.

The writer uses a single-link database file, an exclusive writer lock, a transaction, exact target-column matching, natural-key checks, post-conversion nonfinite checks, duplicate checks, conflict rollback, idempotent batch identity, and commit/path ambiguity detection.

No material writer or reader defect was found in the reviewed baseline.

### 3.4 Market and account core

The shared core correctly includes:

```text
D-close / next-session-open architecture
A-share board lots and T+1 share availability
minimum commission and dated stock stamp tax
conservative limit/slippage non-fills
actual post-blocked-exit position cap
US T+3 / T+2 / T+1 settlement history
source-bound status and calendar identities
exactly-once split, distribution, and terminal ledgers
fail-closed missing marks
```

### 3.5 CI

CI builds a wheel, installs the non-editable package, runs `pip check`, executes a repository-external CLI smoke test, runs Ruff, and executes the full test suite. GitHub Actions are pinned to commit SHAs and the workflow token has read-only contents permission.

## 4. High-severity findings

## H1 — Corporate-action date ordering rejects valid Chinese ETF distributions

Severity: `HIGH / PR_69_BLOCKER`

### Current behavior

`CorporateActionIdentity._require_optional_record_pay_order()` requires:

```text
ex_date <= record_date <= pay_date
```

That ordering is not universal. A valid Chinese ETF distribution can have the rights-registration date before the ex-date.

A concrete 510300 distribution used:

```text
record date: 2025-06-17
ex-date:     2025-06-18
pay date:    2025-06-27
```

The current identity contract rejects this valid event. PR #69 tests avoid the case by setting `record_date == ex_date`, so the tests do not prove compatibility with real Chinese fund announcements.

References:

- SSE ex-date notice: `https://www.sse.com.cn/assortment/options/disclo/update/c/c_20250611_10781544.shtml`
- Fund announcement summary containing record/ex/pay dates: `https://fund.eastmoney.com/a/202506113425185357.html`

### Bounded reproduction

```text
input:
record_date=2025-06-17
ex_date=2025-06-18
pay_date=2025-06-27

current result:
SourceIdentityError because ex_date <= record_date is false

required result:
valid identity, subject to both ex_date and record_date preceding or equaling pay_date
```

### Required narrow repair if listed-fund distributions are ever activated

Do not impose one cross-market order between ex-date and record date.

Require only:

```text
ex_date <= pay_date
record_date <= pay_date
```

and validate market-specific semantics at the market adapter boundary if needed.

Add golden tests for:

```text
CN ETF: record < ex < pay
US distribution: ex <= record <= pay
invalid: pay before record
invalid: pay before ex
```

Do not create a corporate-action framework or market-rule registry.

## H2 — PR #69 identifies a listed fund only by Portfolio flags

Severity: `HIGH / PR_69_BLOCKER`

### Current behavior

PR #69 treats a Portfolio as a listed-fund account when it has:

```text
non-US cash settlement
100-share lot
share T+1
A-share stamp-tax schedule disabled
sell-tax rate zero
```

The Event Loop then allows A-share cash distributions when those Portfolio flags are present. `ExecutionInput` carries no explicit, source-bound instrument/product type proving that the subject is an exchange-listed fund.

An ordinary A-share stock can therefore be routed through the custom zero-tax Portfolio shape and pass the new listed-fund gate if a caller supplies a cash-action identity.

### Bounded reproduction

```text
symbol=600000.SH
market=a_share
portfolio flags=zero-tax, 100-lot, T+1
explicit product identity=absent
corporate action=cash_dividend

PR #69 gate result:
accepted as listed-fund distribution input
```

The existing ordinary-stock regression uses `Portfolio.a_share()`, which has the stock stamp-tax flag enabled. It does not test an ordinary stock in the custom zero-tax Portfolio shape.

### Required narrow repair if the feature is activated

Require one explicit row-level, source-bound product identity such as:

```text
instrument_type=A_SHARE_LISTED_FUND
instrument_source=<immutable SourceIdentity>
```

The default must be no listed-fund authority.

Add a negative test:

```text
600000.SH
+ zero-tax fund-shaped Portfolio
+ cash distribution
= rejected before mutation
```

Do not create a product registry.

## H3 — The Event Loop accepts a decision exactly at execution open

Severity: `HIGH / SHARED_CORE_SEMANTIC_FIX`

### Current behavior

The shared Event Loop rejects:

```python
cutoff < signal.close_at
cutoff > execution.open_at
```

It therefore accepts:

```text
decision_at == execution.open_at
```

For a close-to-next-open research contract, the decision must exist strictly before the execution open.

### Bounded reproduction

```text
signal close - 1 microsecond: rejected
signal close:                 accepted
execution open - 1 microsecond: accepted
execution open exactly:       accepted  <- defect
execution open + 1 microsecond: rejected
```

### Required fix

Change the upper boundary to strict:

```python
if cutoff < signal.close_at or cutoff >= execution.open_at:
    raise MarketDataError(...)
```

Add exact-equality and one-microsecond-before-open tests.

The reviewed frozen strategies used decision times before the open, so this finding does not automatically invalidate their recorded outcomes.

## 5. Medium-severity findings

## M1 — Corporate-action event IDs are unique only within action type

Severity: `MEDIUM / SHARED_LEDGER_HARDENING`

The Portfolio maintains separate applied-ID sets for splits, cash distributions, and terminal actions. The same ID can be accepted once as a distribution and again as a split in a later call. The Event Loop enforces global uniqueness only within one submitted execution batch, not across sessions or action classes.

### Bounded reproduction

```text
event_id=event-001 applied as cash distribution -> accepted
event_id=event-001 applied later as split        -> accepted
```

### Required narrow fix

Use one global applied-corporate-action identity set, or cross-check every new ID against all existing type-specific sets.

Add cross-type collision tests. Do not build an event registry.

## M2 — Mixed cash-and-stock terminal consideration preserves the full old basis

Severity: `MEDIUM / INACTIVE_US_PATH`

`apply_terminal_action()` can both credit cash recovery and create successor shares. The successor average cost is calculated from the full old basis without allocating any basis to the cash portion.

### Bounded arithmetic reproduction

```text
old cost basis:        100
cash recovery:          20
successor sale value:   80
economic total value:  100
economic PnL:            0

current successor basis: 100
later realized PnL:      -20
```

NAV remains correct, but realized PnL and successor basis are inconsistent.

### Required action

This path is inactive. Do not expand it now.

Before any active US strategy uses mixed cash-and-stock terminal consideration, either:

```text
fail closed when recovery_per_share > 0 and a successor is also created
```

or require an explicit source-bound basis-allocation input.

## 6. Frozen legacy findings — record, do not repair now

## L1 — No-fill event observations are charged two-side costs

`event_cohort.resolve_event_return()` substitutes the cash return when an entry is locked limit-up, then still subtracts two-side transaction costs.

```text
no entry fill
cash return=0
50 bps per side
current result=-1%
correct no-trade result=0%
```

This helper belongs to closed evidence and is not part of the top-level active research API. Mark it `FROZEN_CLOSED_NO_REUSE`; do not rewrite historical evidence.

## L2 — Event-cohort bootstrap exposes a parameter that the strict backend forbids

`event_cohort.block_bootstrap_summary()` accepts `block_length`, while `strict_bootstrap` rejects every value except its frozen 20-session block.

```text
block_length=20 -> accepted
block_length=3  -> raises frozen-value error
```

This is a latent API mismatch in closed research support. Do not generalize it. If reactivated later, either expose no parameter or implement a genuinely parameterized backend under a new reviewed contract.

## 7. Current PR adjudication

## PR #69 — do not merge current head

Although PR #69 is narrow, CI-green, and well tested, it is not safe to merge because H1 and H2 remain open.

More importantly, PR #70 establishes that Cycle 4 lacks a usable source matrix. The distribution feature would therefore become dormant shared-core functionality with no active family able to use it. Under the lightweight constitution, dormant functionality should not be merged merely because it may be useful later.

Recommended state:

```text
close without merge
preserve exact head e68d14f86122831139f1f22b84e5792b8351ef50
record BLOCKED_BY_REAL_DATE_CONTRACT_AND_PRODUCT_IDENTITY
```

If a future accepted family genuinely requires listed-fund distributions, reopen a new narrow task incorporating H1, H2, and M1.

## PR #70 — accept terminal evidence

PR #70 truthfully establishes:

```text
511010.SH and 518880.SH absent from the qualified central snapshot
510300.SH lacks qualified product/listing, suspension, limit, and cash-distribution identities
recovery CSV has blank amount and no acceptable identity chain
source_matrix_complete=false
```

No fabrication, provider call, database write, return, NAV, or forward access occurred.

Recommended state:

```text
merge as terminal data-qualification evidence
close Cycle 4 as CLOSED_DATA_AND_SEMANTIC_CONTRACT_INCOMPLETE_NO_OUTCOME
```

Do not change the three ETFs, ten-month trend rule, cash rule, or gates to avoid closure.

## 8. ETF product-semantic warning

Future listed-fund work must bind product-level trading semantics rather than treating every ETF as one generic A-share T+1 product.

Examples:

- SSE rules generally apply price-limit rules to exchange-traded funds, with instrument-specific exceptions.
- Gold ETFs may support same-day sale under applicable exchange rules.
- Some bond-fund categories have product-specific same-day trading treatment.

The current monthly Cycle 4 concept can conservatively use next-session execution, so this is not a reason to expand the core now. It is a reason to require source-bound product identity before any future listed-fund adapter is accepted.

## 9. Process and maintainability findings

1. Do not add another control constitution or roadmap layer.
2. Do not repair closed legacy modules merely to make them reusable.
3. Before writing the next full strategy adapter, perform an outcome-free, aggregate feasibility scan after the economic rule is frozen.
4. If the frozen rule cannot produce the required events or portfolio, close it before implementation.
5. Keep Macro Risk Shadow read-only with no position effect.
6. No strategy synthesizer is authorized: validated specialist count remains zero.

## 10. Required next actions

Execute in this order:

```text
1. Merge PR #70 as terminal source-qualification evidence.
2. Close Cycle 4 with no outcome.
3. Close PR #69 without merge; preserve its exact head.
4. After PR #69 is closed, implement one tiny shared-core PR for H3.
5. Include M1 in that PR only if the change remains small and separately tested;
   otherwise defer it until the next active corporate-action task.
6. Record H1, H2, and M2 as explicit future activation gates.
7. Continue Macro Risk Shadow only under its existing read-only boundary.
8. Before choosing the next strategy family, publish a one-page frozen hypothesis
   and run an aggregate feasibility scan before adapter implementation.
```

## 11. Final state

```text
ARCHITECTURE=RELIABLE_LIGHTWEIGHT
ACTIVE_STRATEGY_OUTCOME=none
VALIDATED_SPECIALIST_COUNT=0
CYCLE_4=CLOSE_NO_OUTCOME
PR_69=DO_NOT_MERGE
PR_70=ACCEPT_TERMINAL_EVIDENCE
NEXT_SHARED_FIX=STRICT_DECISION_BEFORE_EXECUTION_OPEN
MACRO_RISK=SHADOW_ONLY
SYNTHESIZER=NOT_AUTHORIZED
TRADING=NOT_AUTHORIZED
```
