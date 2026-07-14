# Repository-wide personal-quant audit addendum — 2026-07-14

## Purpose

This addendum extends the primary report:

`reports/external_audit/repository_wide_personal_quant_static_dynamic_audit_20260714.md`

It adds the full repository-role inventory, legacy A-share and US-engine findings, independent dynamic reproductions, and an explicit instruction to supersede speculative full-database ingestion.

## Consolidated verdict

```text
WHOLE_PROJECT:
SIMPLIFY_NOW

CENTRAL_DATABASE_RUNTIME:
REBUILD_MINIMAL_WITH_COMPATIBILITY_BRIDGE

BACKTEST_RELIABILITY:
MIXED_NOT_YET_PROJECT_WIDE

A_SHARE_R5:
CONDITIONAL_ACCEPT_AFTER_ALLOCATOR_TIMING_AND_MISSING_PRICE_FIX

LEGACY_A_SHARE_ENGINE:
DEPRECATE_AFTER_PARITY

US_ENGINE:
KEEP_AS_CANONICAL_WITH_WALK_FORWARD_RENAME_OR_REFIT

STRATEGY_RESEARCH_PROCESS:
PROCESS_BOUND_AND_OVER_AUDITED

SYSTEM_INTAKE_READY:
false

STRATEGY_CANDIDATE_AVAILABLE:
false
```

---

# 1. Full repository-role inventory

| Repository | Decision | Active role |
|---|---|---|
| `quant-proj` | SIMPLIFY | Thin controller and reports |
| `central-data-ingestion` | REBUILD_MINIMAL | Sole DB writer |
| `quant_research_lab` | KEEP | Canonical A-share research |
| `US_Stock_Monitor` | KEEP | Canonical US research |
| `A_Share_Monitor` | DEPRECATE | Legacy parity/reference |
| `market_data` | SIMPLIFY | Read-only DB adapter |
| `us_stock_30w` | ARCHIVE | US specs and evidence |
| `strategy_work` | ARCHIVE | Notes and failure memory |
| `quant-project-shared-reports` | MERGE/ARCHIVE | Move useful reports to controller |
| `STRATEGY_VAULT` | ARCHIVE | Historical failures only |
| `a-share-canonical-evidence-data-room` | CLOSE/ARCHIVE | Preserve closed review evidence |
| `quant`, `qts` | KEEP ARCHIVED | Historical only |
| `FinGPT`, `RD-Agent` | VENDOR | Exclude from project CI |
| private migration shells | KEEP ARCHIVED | No active runtime |

Target active topology:

```text
quant-proj
central-data-ingestion
quant_research_lab
US_Stock_Monitor
```

Add a fifth execution-adapter repository only after a strategy passes full replay, prospective observation, and explicit user authorization.

---

# 2. Legacy A-share selection leakage

The legacy A-share research path is not fully selection-safe.

`qta.research.robustness.robustness_summary()` reads train, validation, and test metrics when calculating:

- positive split count;
- return spread;
- sample size;
- `overfit_risk_status`.

`StrategySearch` passes that robustness-derived overfit status into `StrategyEvaluator.grade()`. The evaluator’s direct metric thresholds use train and validation, but the test segment can still influence the final grade indirectly through `checks.overfit_risk_status`.

Deterministic reproduction:

```text
train return      +5%
validation return -5%
test return       +5%

legacy three-split sign rule: PASS
selection-only sign rule:     WARNING
```

The test result changes a selection-time status. This must be fixed immediately if the legacy engine remains callable.

Required patch:

- selection robustness may read train and validation only;
- test metrics may be appended to the final report only after status is frozen;
- a regression test must demonstrate that changing test returns cannot change candidate status.

The legacy walk-forward summary also uses test-positive counts and minimum test trade counts in its status. Those fields may be reported but must not gate selection.

Decision:

```text
PATCH TEST LEAK
FREEZE LEGACY ENGINE
ARCHIVE AFTER R5 FULL-DATA PARITY
```

---

# 3. R5 allocator timing dynamic reproduction

The R5 soft and hard allocator code merges date-D state/probability with date-D sleeve returns and applies date-D target weights to date-D returns.

For close-derived state features, the allocation may become effective only on D+1.

Independent deterministic reproduction used two sleeves whose winner alternates each period. The current date state identifies the current date winner:

```text
periods: 20
winner return: +2%
loser return:  -2%

same-day state -> same-day return:
final equity = 1.485947

state shifted one period:
final equity = 0.681233

static 50/50:
final equity = 1.000000
```

The example is adversarial by design; its purpose is to prove materiality. A one-session timing error can reverse the allocator ranking.

Required R5 fix:

- add `signal_date` and `effective_date`;
- shift dynamic target weights one trading session;
- calculate D return using weights already effective before D;
- add a test where a state first observed at D close cannot capture D return;
- define an explicit rebalance cadence for static allocators rather than implicitly rebalancing every day.

A second R5 fix is required: held instruments with missing close prices must not be silently valued at zero. The full run should fail closed, quarantine the symbol/date, or apply an explicit delisting settlement rule.

---

# 4. US engine review

`US_Stock_Monitor` is the strongest current canonical backtest implementation.

Accepted properties:

- signal after close;
- next-session adjusted-open execution;
- adjusted-close valuation;
- union trading calendar;
- blocked fills for missing/halted/delisted dates;
- sells before buys;
- cash-settlement control;
- held-out test excluded from `selection_equity_curve`;
- robustness based on validation metrics only;
- evaluator records test metrics without selecting on them.

Required changes:

1. `walk_forward()` currently slices a realized equity curve into sequential segments. For fixed rules, rename this to `temporal_fold_stability`. For fitted models, implement real rolling fit/predict walk-forward.
2. If split-boundary metadata is missing, `selection_equity_curve` must fail closed instead of falling back to the full curve.
3. Apply the shared project-wide invariant suite before calling the US engine canonical.

Decision:

```text
KEEP_AS_CANONICAL_US_ENGINE
```

The separate `us_stock_30w` repository should keep strategy specifications and immutable evidence only. Its custom engines should be retired.

---

# 5. Missing held-price policy

Both active/legacy A-share implementations have used zero valuation for a held symbol with a missing close.

This prevents stale-price concealment but creates another material error: an ordinary provider gap becomes an artificial 100% mark-down.

Required policy:

```text
if held close missing:
    fail run and quarantine date/symbol
    OR execute documented delisting settlement
    OR use an explicitly accepted stale-price rule for one bounded session
```

Never silently convert missing data into zero market value and continue ranking strategies.

---

# 6. Historical holdout contamination

The project has repeatedly examined 2024–2026 and other historical “test” intervals through many R-batches and remediation cycles. Code-level non-leakage is necessary but no longer sufficient: those periods are not organizationally untouched.

Required policy:

- keep historical test as diagnostic evidence;
- freeze final code, formula, parameters, and snapshot;
- start a true prospective observation period from the final freeze date;
- do not relabel an already examined period as a new pristine holdout;
- prohibit parameter changes based on prospective observations without starting a new observation clock.

---

# 7. Database manager instruction that must be superseded

The earlier manager prompt to fill every A0–A6, U0–U6, X1, and X2 dataset is now too broad.

Do not continue speculative ingestion simply because a field family appears in a master checklist.

Immediate database scope:

## A-share P0

- daily OHLCV/amount;
- daily basic and direct `circ_mv`;
- adjustment factors and corporate-action semantics;
- dated ST/suspension/limit/listing/delisting;
- dated industry history.

## US P0

- QQQ, GLD, SPY, TLT, HYG, LQD;
- eleven sector ETFs;
- trade calendar;
- adjusted/total-return semantics;
- corporate actions.

Pause unless an active preregistered hypothesis requests them:

```text
A5 broad PIT fundamentals
A6 event/fund-flow warehouse
U4 macro-vintage warehouse
U5 broad 270-symbol survivorship warehouse
U6 PIT fundamentals/earnings
X1 generic derived feature warehouse
X2 broad automation framework
```

The manager should issue data tasks from actual strategy field requirements, not from architecture completeness goals.

---

# 8. Shared backtest invariant package

Create one small package used by every engine. Target: 300–500 lines of reusable assertions and fixtures.

Required invariants:

- information date precedes effective date;
- D signal cannot earn D return;
- removed holdings sell;
- retained holdings resize;
- same-day sells precede buys;
- zero trade means zero cost;
- account identity holds;
- missing held price fails closed;
- adjusted data and corporate actions are explicit;
- test data cannot enter selectors;
- benchmark/calendar alignment holds;
- packet references exact code and snapshot.

This package replaces repeated custom audit frameworks in each repository.

---

# 9. Proportionate validation defaults for CNY 400,000

These are defaults, not hard universal gates:

```text
positions:              8–12
max position:           10–15%
cash buffer:            5–10%
A-share lot:            100 shares
participation ceiling:  0.5–1% daily amount
cost stress:            1x / 2x / 3x
validation folds:       2–3 anchored periods
ordinary equity trades: about 80–100 total, 20+ validation
validation drawdown:    generally below 25–30%
```

Low-turnover ETF allocation should be judged by years, independent episodes, and bootstrap evidence rather than an arbitrary trade-count gate.

Institutional square-root impact, distributed execution simulation, multi-tenant permissioning, CSCV/PBO, nested cross-validation, and repeated independent audits are unnecessary by default.

---

# 10. Immediate action order

1. Freeze central-database architecture expansion.
2. Supersede broad DB2 ingestion with demand-driven P0 tasks.
3. Build one minimal bulk writer beside the current path.
4. Fix R5 allocator D+1 effectiveness and missing-price handling.
5. Patch legacy A-share test leakage.
6. Create the shared invariant suite and run it against A-share and US engines.
7. Accept one immutable central snapshot.
8. Run one R5 full replay.
9. Limit active strategy research to three or four families.
10. Audit only engine/data changes and promotion events.

## Final boundary

```text
SYSTEM_INTAKE_READY=false
STRATEGY_CANDIDATE_AVAILABLE=false
NO_RECOMMENDATION
NO_BROKER_ORDER_PAPER_LIVE_AUTO
```
