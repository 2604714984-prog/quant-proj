# DS A-Share C2 R4.1a External Audit Result — 20260714

## Audit target

- repository: `2604714984-prog/quant_research_lab`
- branch: `research/c2-remediation-r4-1a-20260713`
- code-completion commit: `7739ef2ec6233a7a624649054fe5020b067b2515`
- reported smoke-evidence/head commit: `b1e14ea98045d414713cb789f6a08189db4f4926`
- immutable head URL: `https://github.com/2604714984-prog/quant_research_lab/commit/b1e14ea98045d414713cb789f6a08189db4f4926`

## Verdict

`REJECT_R4_1A_CODE_COMPLETE_SMOKE_PASS_CRITICAL_FIXES_REQUIRED`

The branch contains a useful import-safe event-loop prototype and a small passing test set, but it does not satisfy the frozen R4.1a scope and does not support the claimed status:

`R4_1A_CODE_COMPLETE_SMOKE_PASS_WAITING_FOR_DB_SNAPSHOT`

Accepted only as:

`R4_1A_PARTIAL_IMPORT_SAFE_EVENT_LOOP_PROTOTYPE`

The rejection is independent of the pending central-database callback. The method package still lacks real regime allocators, detector/GMM implementation, selection ledger, packet/gate logic, and auditable smoke artifacts. Several committed tests and smoke gates are vacuous or hard-coded, and strategy fidelity defects remain.

## Accepted partial scope

The following may be preserved in the next patch:

1. The package under `src/ds_a_share_r4_1a/` is import-safe in the narrow sense that module imports do not connect to DuckDB or read the full feature cache.
2. `EventLoopEngine` processes queued D orders at the start of D+1 and queues new orders after marking D close.
3. The engine separates same-date sell and buy queues and executes sells first in code.
4. Invalid/non-positive open prices are explicitly rejected.
5. Buy-side limit-up and sell-side limit-down checks exist as fixture-level fields.
6. The engine creates liquidation orders for holdings removed from the target set.
7. The final branch and both immutable commits resolve remotely.
8. The research-only boundary is preserved; `SYSTEM_INTAKE_READY=false` and `strategy_candidate_available=false` remain appropriate.

## Critical findings

### 1. The claimed allocator framework is not implemented

`src/ds_a_share_r4_1a/allocators.py` contains only:

- metric calculation;
- a static function that averages complete equity arrays;
- a `soft_probability_weighted` function that directly calls the static average and is explicitly labelled a proxy.

There is no:

- shared-capital sleeve ledger;
- daily target/realized weights;
- probability-driven soft allocator;
- hard confirmed-state allocator;
- dwell/hysteresis logic;
- fallback allocator;
- allocator trades/costs/switch log.

The smoke pipeline does not call even the static or proxy-soft allocator functions.

### 2. No detector/GMM implementation exists in the R4.1a package

The committed package contains only `types.py`, `event_loop.py`, `signals.py`, `allocators.py`, and `fixtures.py`. There is no detector module or committed code for:

- train-only BIC/component selection;
- scaler/model fit;
- cluster-to-state mapping;
- model/scaler hashes;
- daily out-of-sample probabilities;
- detector diagnostics.

The source-completeness board marks these items fixed despite their absence.

### 3. The smoke runner hard-codes success and writes empty evidence files

`run_smoke()` initializes `smoke_passed=true` and never recomputes it from the individual checks. It:

- defines a no-negative-cash expression over an empty iterable and does not use the result;
- marks `no_negative_cash` PASS unconditionally;
- marks `rejects_logged` PASS unconditionally;
- returns process exit code 0 whenever `smoke_passed` remains true, even if another check is FAIL;
- writes empty DataFrames to orders, fills, rejects, holdings, cash, equity, and reconciliation Parquet paths.

The committed smoke-quality JSON therefore is not accepted as generated evidence.

### 4. The committed smoke run does not exercise three regimes or a test split

The fixture creates 120 business dates beginning 2020-01-02. This ends before 2020-07-01, while the third `SIDEWAYS_NORMAL_VOLATILITY` regime starts only after 2020-07-01. Therefore the fixture contains only two populated regimes, not three.

The smoke split uses test dates after 2020-06-30, but the fixture ends before that boundary, so the test split is empty.

Consequences:

- H7/H8 sideways behavior is not exercised in smoke;
- no test-split smoke evidence exists;
- `all_10_hypotheses_run` counts configured hypotheses with metric rows rather than proving every signal path executed.

### 5. H3 breadth guard remains absent

The final `sig_H3()` accepts an optional `breadth_val` argument but does not check it. It always ranks `return_20` and returns signals. The final self-review commit did not modify `signals.py`, despite the callback claiming the guard was fixed.

### 6. H8 still contains a control-flow defect

`sig_H8()` uses a one-line conditional:

```python
if len(dd) < 5: return []; n = ...
```

When `len(dd) >= 5`, `n` is not defined before it is used. Smoke does not expose this because the fixture never reaches the sideways regime, and the test suite contains no H8 test.

### 7. Bucket percentage is still applied twice

Signal functions already return approximately the top/bottom 20% of their eligible universe. `EventLoopEngine` then applies `bucket_pct` again to the returned signal list. With a 20% configuration, the effective target is roughly 4% of the original eligible universe, not the preregistered 20%.

### 8. Retained target holdings are not resized

The engine:

- sells holdings removed from the target set;
- buys target symbols not already held.

It does not generate incremental orders for symbols that remain in the target set but whose target shares changed. Therefore the claimed target-weight rebalance and shared-capital equal weighting are incomplete.

The buy sizing also divides portfolio value only by the number of new symbols, not the number of all target symbols, which can oversize additions when some targets are already held.

### 9. Accounting evidence is internally incorrect and incomplete

The daily-state fields do not separately track commissions correctly:

- `buy_comm` is assigned total commission for buys and sells;
- `sell_comm` is calculated as total commission minus stamp duty and slippage, which is not a commission value and may be negative.

No row-level reconciliation error is computed or tested. Pre-trade holdings value is marked at close while trades execute at open, so the requested execution-time accounting identity is not represented by the committed daily-state fields.

### 10. Tradability coverage remains fixture-level and incomplete

The engine checks only open validity, static `is_st`, limit-up on buys, and limit-down on sells. It does not implement dated:

- suspension history;
- ST effective history;
- listing/delisting status;
- locked-limit semantics;
- board-specific execution constraints.

These may legitimately remain database blockers, but they must not be marked fully fixed/tested.

### 11. The eight tests are far below the frozen R4.1a test scope

Only two test modules are committed:

- four import tests;
- four event-loop tests.

There are no committed behavioral tests for:

- accounting identity;
- retained-position resizing;
- removal/liquidation/fallback;
- H3 low/high breadth behavior;
- H8 low/high shock behavior;
- exact bucket count;
- static/soft/hard/fallback allocators;
- GMM/BIC and probability sums;
- selection ledger/test-artifact rejection;
- packet validation;
- evidence-derived gates.

The sell-before-buy test does not require a date containing both a sell and a buy; with `rebalance_days=120` on a 120-day fixture, it can pass without any sell. The no-negative-cash test checks only final cash, not the minimum daily cash balance.

### 12. The JUnit evidence is stale relative to the final commit

The JUnit XML timestamp precedes the final self-review commit. The final commit modifies tests and event-loop code, but no regenerated JUnit XML or GitHub Actions run exists for the final branch head.

### 13. Required R4.1a artifacts are absent

The final commit does not contain the frozen required evidence set, including:

- real smoke orders/fills/rejects/holdings/cash/equity/reconciliation rows;
- allocator equity/weights/trades/switch logs;
- detector component-selection and model hashes;
- daily OOS probabilities;
- selection ledger;
- behavioral matrix derived from JUnit;
- packet templates;
- packet schema validation;
- evidence-derived exit gates;
- callback envelope.

### 14. The two-step commit protocol was not completed as frozen

The code-completion commit already included JUnit/smoke summary files. The final reported smoke-evidence commit only changes event-loop and test source and does not regenerate the smoke/JUnit evidence. No packet-template or final callback commit exists.

## Accepted status

```text
R4_1A_STATUS:
REJECTED_AS_CODE_COMPLETE_SMOKE_PASS

IMPORT_SAFETY_STATUS:
PARTIAL_PASS

EVENT_LOOP_STATUS:
PARTIAL_PROTOTYPE

UNIT_TEST_STATUS:
8_TESTS_REPORTED_PASS_BUT_SCOPE_INSUFFICIENT_AND_FINAL_HEAD_UNVERIFIED

SMOKE_PIPELINE_STATUS:
INVALID_HARD_CODED_AND_EMPTY_EVIDENCE

HYPOTHESIS_FIDELITY_STATUS:
FAILED_H3_H8_AND_BUCKET

STATIC_ALLOCATOR_STATUS:
PROXY_ONLY

SOFT_ALLOCATOR_STATUS:
NOT_IMPLEMENTED

HARD_ALLOCATOR_STATUS:
NOT_IMPLEMENTED

FALLBACK_STATUS:
NOT_IMPLEMENTED

GMM_TRAIN_ONLY_STATUS:
NOT_IMPLEMENTED

SELECTION_LEDGER_STATUS:
NOT_IMPLEMENTED

PACKET_STATUS:
NOT_COMMITTED

EXIT_GATE_STATUS:
NOT_COMMITTED

A_SHARE_DB_CALLBACK_STATUS:
WAITING

FULL_REPLAY_STATUS:
NOT_RUN

SYSTEM_INTAKE_READY:
false

STRATEGY_CANDIDATE_AVAILABLE:
false

S2_STATUS:
S2_CONTINUE_REQUIRED
```

## Required next patch

A narrow R4.1b patch is required before the central-database snapshot is used for a full replay:

1. Fix H3 and H8 and apply bucket selection exactly once.
2. Implement incremental rebalancing for retained targets and correct sizing across all targets.
3. Correct separate buy/sell commission fields and add execution-time reconciliation errors.
4. Build a smoke fixture that actually contains at least three populated regimes, a nonempty test split, invalid opens, dated tradability events, target removals, same-day sell/buy funding, fallback, and rejects.
5. Save real, nonempty smoke orders/fills/rejects/holdings/cash/equity/reconciliation artifacts.
6. Make smoke success derived from all checks and fail the process if any check fails.
7. Implement real shared-capital static, soft, hard, and fallback allocators with daily weights, trades, costs, equity, and switch logs.
8. Implement train-only detector component selection, model/scaler hashes, and daily OOS probabilities.
9. Implement an explicit selection ledger and evidence-derived exit gates.
10. Add all missing failure-sensitive tests and regenerate JUnit after the final source commit.
11. Create schema-complete blocked packet templates and a callback referencing the exact final commits.
12. Keep full mode and system intake blocked until the immutable central-database callback arrives and the full replay is externally audited.

## Boundary result

`PASS_RESEARCH_ONLY`

No recommendation, strategy candidate, ticket, readiness/product route, daily signal, broker/order/paper/live/auto activation, or secret output is accepted.

## Quant Manager action

- Register R4.1a as received and externally rejected as code-complete/smoke-pass.
- Continue central-database normalization independently.
- Do not release Codex strategy-packet system validation.
- Require R4.1b before consuming the final database snapshot for full replay.
- Keep `strategy_candidate_available=false` and `S2_CONTINUE_REQUIRED`.
