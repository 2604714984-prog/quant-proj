# Repository-wide Audit — Part 2

## Backtest and validation reliability for a personal CNY 400,000 quant project

**Audit date:** 2026-07-14  
**Scope:** repository-wide tracked-file inventory with risk-based line-level semantic review of all active backtest, portfolio, execution, validation, robustness, regime-allocation, and research-statistics paths; supplemented by deterministic dynamic reproductions.  
**Operating context:** one owner, one WSL host, research-only, approximately CNY 400,000 deployable capital, no broker/order/paper/live/auto route in scope.

# Audit targets

## A-share current research takeover

- repository: `2604714984-prog/quant_research_lab`
- implementation commit: `d074e3cb8ab1f3936a48c86a00aa4dcc21d6f158`
- smoke/evidence commit: `d5e902af4beab6826ebc34c9a940b881f25ad750`
- branch: `codex/a-share-independent-research-takeover-r5-20260714`

## A-share legacy research/search engine

- repository: `2604714984-prog/A_Share_Monitor`
- reviewed active preservation commit: `1a64e70873fc8a3c3d998e509cbcf690010ffef0`
- included prior backtest repair commit: `9642e0b921bbdc654f59797b4a5e1aacefb0fa52`

## US active research engine

- repository: `2604714984-prog/US_Stock_Monitor`
- reviewed main commit: `872f54211e56a162e713d987d904b49d2521bd25`

## Independent US strategy project

- repository: `2604714984-prog/us_stock_30w`
- R3 implementation: `2e34749f0830e000c5c577200ef3b0f65e2c70b0`
- progress/blocker commit: `6880e2c8f55e86f678f45bad5a5b149c22222d98`

## Research statistics and archived prototype

- `strategy_work`: `a1cf3e0978e47529b8ee2e7686ea7950e0d226ed`
- `qts`: archive decision `3565b0b927e75625c77480f619b3f4700530965f`

## Data-semantics dependencies

- `market_data`, `central-data-ingestion`, central DuckDB contracts, and read-only clients were reviewed where they determine PIT, adjustment, membership, corporate-action, or raw-close semantics.
- Part 1 established that no complete accepted canonical A-share/US dataset is currently available for a trustworthy full replay.

# Method

The review did not treat reports, test counts, or callback labels as proof. It read the executable paths that determine:

- signal date and execution date;
- order queue chronology;
- cash, holdings, settlement, costs, and valuation;
- suspension, limit, listing, delisting, and missing-price behavior;
- adjusted prices and corporate actions;
- historical universe and point-in-time metadata;
- train/validation/test isolation;
- walk-forward, robustness, parameter search, leaderboard, and candidate gates;
- static, soft, hard, and fallback allocation;
- multiple-testing and overlapping-observation inference.

Low-risk reports/configurations were reviewed through repository inventories and their relationship to active code. Line-level review concentrated on paths capable of overstating returns or accepting a false strategy edge.

# Reframed question

The project previously behaved as if more gates, more tests, and more reports automatically made a backtest reliable. The correct question for this project is narrower:

> Can a single operator reproduce a causal portfolio simulation with correct data semantics, cash/cost accounting, a genuinely untouched evaluation period, and enough independent evidence to decide whether an edge is worth further paper validation?

For CNY 400,000, institutional microstructure, distributed risk services, and hundreds of approval artifacts are unnecessary. Causal timing, point-in-time data, correct accounting, honest multiple-testing control, and a small set of failure-sensitive tests are non-negotiable.

# Overall verdict

```text
BACKTEST_RELIABILITY_VERDICT: REBUILD_SELECTED_COMPONENTS
CURRENT_STRATEGY_EVIDENCE: NOT_TRUSTED_FOR_SYSTEM_INTAKE
A_SHARE_R5_EVENT_LOOP: USABLE_WITH_CRITICAL_VALUATION_FIX
A_SHARE_R5_ALLOCATORS: REWRITE_REQUIRED_LOOKAHEAD
A_SHARE_LEGACY_ENGINE: RESEARCH_ONLY_DIAGNOSTIC
US_STOCK_MONITOR_ENGINE: USABLE_WITH_LIMITATIONS
US_STOCK_30W_RESULTS: ARCHIVE_REBUILD_IF_REOPENED
STRATEGY_WORK_STATISTICS: KEEP_AND_INTEGRATE
QTS: KEEP_ARCHIVED_REFERENCE_ONLY
FULL_CANONICAL_REPLAY: BLOCKED_BY_DATA
SYSTEM_INTAKE_READY: false
STRATEGY_CANDIDATE_AVAILABLE: false
```

No current A-share or US strategy result is accepted as a validated strategy candidate.

# Critical findings

## 1. R5 soft and hard allocators use same-date state information to earn same-date returns

Source:

- `quant_research_lab/src/a_share_research_r5/allocators.py`
- `quant_research_lab/scripts/run_a_share_research_r5.py`

`run_allocator()` calls the weight function on row *t*, immediately sets target weights, and computes portfolio return from the sleeve returns in that same row. Soft allocation merges date-t GMM probabilities with date-t sleeve returns. Hard allocation merges date-t confirmed state with date-t sleeve returns.

This is incompatible with the R5 contract that regime/state information is known after close and portfolio changes execute on the next session. State/probability observed on D must determine weights for D+1, not returns on D.

The committed soft/hard tests verify only that weights vary, dwell is respected, and costs exist. They do not verify a one-bar decision/exposure lag.

### Dynamic reproduction

Two sleeve fixture:

```text
Day 1: A +10%, B -10%, state/probability chooses A
Day 2: A -10%, B +10%, state/probability chooses B
cost: 5 bps
```

Current same-date implementation:

```text
ending normalized equity: 1.2087903025
```

Causal after-close/D+1 implementation:

```text
Day 1 remains cash
Day 2 holds the sleeve chosen on Day 1
ending normalized equity: 0.89955
```

This is a decisive lookahead reproduction. All R5 allocator returns, comparison metrics, and smoke statements involving dynamic allocation are invalid until target weights are shifted to the next trading session and tested with adversarial fixtures.

## 2. R5 values a held stock at zero when the close is missing

`EventLoopEngine._market_value()` uses `prices.get(symbol, 0.0)`. If a held symbol has no row or no close on a suspension/provider-gap day, its market value becomes zero. Position evidence uses the same zero fallback.

Dynamic reproduction:

```text
100 shares × CNY 10 prior close = CNY 1,000
missing close map             = CNY 0 market value
```

This creates an artificial near-100% loss rather than failing closed or applying a bounded, explicitly stale valuation policy. Real A-share data frequently has missing bars around suspensions, delistings, and provider gaps, so this must be fixed before full replay.

## 3. The legacy A-share engine has the opposite missing-price failure: indefinite stale carry-forward

`A_Share_Monitor/qta/backtest/portfolio.py` carries `last_mark_price` whenever a held symbol has no close. It exposes a flag but has no maximum stale-day limit, delisting return, forced liquidation, or strategy-level rejection.

Dynamic reproduction:

```text
100 shares marked at CNY 10
20 consecutive missing bars
reported equity remains CNY 1,000
reported drawdown remains 0%
```

The project therefore has two A-share engines with opposite invalid behaviors:

- R5: missing position becomes zero immediately;
- legacy engine: missing position may remain at the old price forever.

A single explicit missing-price policy is required.

## 4. A-share monthly and yearly return metrics are wrong at period boundaries

`A_Share_Monitor/qta/backtest/metrics.py` groups each month/year and computes `last / first - 1`. That omits the return from the previous period-end into the first observation of the new period.

Dynamic reproduction:

```text
Jan 31 equity: 100
Feb  1 equity: 110
Feb 29 equity: 121
```

Current code reports February:

```text
121 / 110 - 1 = +10%
```

Correct month-end-to-month-end return:

```text
121 / 100 - 1 = +21%
```

Consequently `monthly_win_rate`, `worst_month`, `worst_year`, and dependency diagnostics using these fields are unreliable. `alpha_vs_benchmark` is also only total-return difference, not alpha.

## 5. A-share historical metadata is not point-in-time

`attach_stock_metadata()` deduplicates `stock_basic` to one row per symbol, preferring currently active rows, and merges that row over all historical dates. ST status is derived from the selected name. Industry, name, list status, and delist fields can therefore reflect later/current metadata on earlier dates.

`historical_universe()` can only use symbols already present in the supplied daily table; it cannot remove survivorship bias if the source was built from a current universe.

Until dated name/ST/industry/membership history is accepted from the central database, legacy A-share universe evidence is not suitable for strategy acceptance.

## 6. The A-share legacy engine is not a true cross-sectional rotation engine

On a rebalance date it calculates candidates only for open slots and excludes names already held. If the portfolio is full, newly top-ranked names are ignored until an old holding separately triggers an exit rule.

This is a valid entry/exit strategy design only if documented as such. It is not equivalent to “rebalance to the current top-N” or ETF/equity rotation. Reports that interpret it as a periodically refreshed cross-sectional target portfolio overclaim what the code does.

## 7. A-share validation/test isolation is incomplete in practice

`StrategyEvaluator` bases its label primarily on train and validation, which is a positive safeguard. However:

- every candidate is backtested on the test interval during every research run;
- test metrics and test walk-forward rows are written to artifacts and repeatedly observed;
- `robustness_summary()` includes test return signs in `overfit_risk_status` diagnostics;
- the configured test period starts in 2023 and has been inspected across many batches;
- there is no active global lifetime experiment ledger or deflated-Sharpe/PBO gate in `StrategySearch`.

The regression test that says the overfit gate ignores test data injects a prebuilt status; it does not prove the upstream robustness calculation is independent of test outcomes.

The existing A-share “test” period must be considered contaminated. It can remain diagnostic, but it cannot serve as a final untouched holdout for candidate acceptance.

## 8. R5 selection ledger is a self-reported control, not an access-control boundary

`SelectionLedger.record()` raises when the caller says `actual_splits` contains test. The caller also supplies `actual_splits`; the ledger does not trace DataFrame lineage, enforce APIs, or prevent a selector from reading a test artifact and declaring that it did not.

Keep it as an audit note, but do not count it as proof of no test-result selection. Proof should come from split-specific interfaces, forbidden test handles in development functions, and adversarial tests.

## 9. R5 family sleeves are synthetic averages, not directly tradable sleeves

`family_sleeve_returns()` averages the daily returns of all strategies in a family. It does not maintain a shared capital account inside the family, rebalance family members, or charge internal turnover costs.

The outer allocator then trades these synthetic family return series. This is acceptable for a bounded method smoke, but not for full strategy evidence. Full replay must either:

- define one frozen specialist per state/family; or
- build each family sleeve from actual holdings and internal costs.

## 10. R5 smoke gates prove activity, not causal correctness

The method gate checks nonempty orders/fills/rejects, allocator count, nonzero allocator costs, and populated regimes. It does not check:

- one-session lag between state/probability and allocation return;
- missing-close valuation;
- unique regime state per date;
- tradable family-sleeve construction;
- real data/PIT semantics.

No GitHub Actions run is associated with the R5 smoke commit. Local JUnit evidence is useful but does not independently validate the final commit.

# A-share legacy engine — useful components and limitations

## Useful components to retain temporarily

- next-open order queue;
- sell-before-buy ordering;
- A-share lot size;
- minimum commission, stamp duty, and transfer fee;
- limit-up/limit-down, suspension, amount/volume participation;
- position and trade evidence;
- validation-only strategy grading.

## Limitations requiring retirement from candidate acceptance

- current/static metadata used historically;
- stale price carried indefinitely;
- no true top-N target rebalance;
- incorrect monthly/yearly metrics;
- plain-close benchmark and misnamed alpha;
- repeated exposure of test results;
- no global multiple-testing ledger;
- no accepted canonical data snapshot.

Recommendation: keep this engine as a parity/reference tool during R5 development, but stop using it as the authoritative candidate-acceptance engine.

# US_Stock_Monitor assessment

## Strengths

The US engine is the strongest existing legacy engine:

- union calendar rather than intersection;
- after-close signals and next-session open execution;
- target-weight rebalance including removals and retained-position resizing;
- sells before buys;
- missing held valuation fails closed;
- adjusted open/close required by `PricePanel`;
- raw Sina closes explicitly cannot enter `PricePanel`;
- train/validation/test split is recorded;
- `selection_equity_curve` normally excludes the test segment;
- robustness uses validation metrics.

## Remaining limitations

### Selection fail-open when split boundaries are missing

`selection_equity_curve` returns the full curve when `val_end_index < 0`. Production engine results set the boundary, but hand-built/imported results can silently include test. It should fail closed instead of falling back to full history.

### “Walk-forward” is temporal segmentation, not walk-forward refitting

`walk_forward()` partitions one already-realized fixed-strategy equity curve. It does not re-estimate or re-select a model in each training window and then execute in the following window. Rename it `temporal_fold_stability` or implement true fit/validate transitions.

### Split and dependence model are too simple

Splits are fractions of observation count, with no purge/embargo for overlapping labels. The current strategy family may use daily/overlapping features, so confidence intervals require block bootstrap or HAC.

### Settlement assumptions are historically inaccurate

The engine uses T+1 cash settlement over the full backtest. US equities settled T+2 for much of the likely history. The helper uses weekdays rather than an exchange calendar. For a cash account, this can overstate reinvestable cash before the settlement-rule change.

### Costs are incomplete

The model is one flat bps charge. It omits spread variation, broker/SEC/TAF details, FX conversion, and a capacity rule. For a roughly USD 50–60k account, elaborate market-impact modeling is unnecessary, but a dated fee/settlement policy and conservative spread/slippage tiers are appropriate.

### Fractional shares are assumed

This is acceptable only if the intended broker/account supports fractional shares for every instrument. Otherwise shares must be rounded and residual cash preserved.

### No global multiple-testing correction

Candidate ranking does not consume the lifetime experiment ledger or deflated-Sharpe/PBO utilities already present in `strategy_work`.

## Verdict

```text
US_ENGINE_MECHANICS: USABLE_WITH_LIMITATIONS
US_STRATEGY_EDGE_EVIDENCE: NOT_YET_TRUSTED
FULL_REAL_DATA_VALIDATION: BLOCKED
```

# us_stock_30w assessment

The repository’s own R3 report records that R2 was externally rejected for:

- first 63 sessions in cash;
- costs not removed from portfolio value;
- EMA “probabilistic” sidecar not independent;
- specialist formulas not matching preregistration;
- hard/fallback allocators absent;
- raw, unadjusted Sina close.

R3 created data blockers and blocker-contract tests; it did not produce a corrected full backtest. All prior US46/allocator performance numbers must remain archived. If the project is reopened after central data is ready, rebuild on the `US_Stock_Monitor` engine or a small shared engine rather than repairing the R2 scripts again.

# strategy_work statistics assessment

`analysis/research_statistics.py` contains valuable, fail-closed tools:

- controller-pinned lifetime experiment ledger;
- frozen holdout contract predating experimentation;
- purge/embargo mask;
- probabilistic and deflated Sharpe;
- CSCV probability of backtest overfitting;
- HAC/Newey-West inference for overlapping IC values;
- hash-bound code/config/data/output artifacts.

Verdict:

```text
KEEP_AND_INTEGRATE
```

The problem is not the statistics themselves; they are disconnected from the active A-share and US search pipelines. Integrate a minimal subset into the trusted engines. Do not build another orchestration framework around them.

# qts assessment

The repository is correctly frozen as `FROZEN_REFERENCE_ONLY`. Its archive records later-revision/PIT errors, early EOD availability, missing-price zero returns, flawed walk-forward transitions, current-constituent survivor bias, and incomplete corporate actions/execution.

Keep it archived. Do not revive its backtests or execution surface.

# Dynamic reproduction summary

| Reproduction | Current behavior | Correct/required behavior |
|---|---:|---:|
| R5 same-day dynamic allocator | 1.2087903025 | 0.89955 with one-day lag |
| R5 missing held close | CNY 1,000 -> CNY 0 | fail closed or bounded stale policy |
| Legacy A-share missing close | stays CNY 1,000 indefinitely | stale-day limit/delist policy |
| Legacy February return | +10% | +21% month-end-to-month-end |

These reproductions use minimal deterministic fixtures and isolate the disputed code paths. They are not market-performance estimates.

# Appropriate reliability standard for a CNY 400,000 personal account

The project does not need institutional process overhead. It does need the following compact standard.

## Non-negotiable engine standard

1. after-close signal -> next-session execution;
2. regime/allocator weight is lagged to the next tradable session;
3. one shared cash/holdings ledger with exact cost reconciliation;
4. A-share lots, minimum commission, stamp duty, transfer fee, suspension and limits;
5. US adjusted/total-return prices, corporate actions, dated settlement and fee rules;
6. explicit missing-price policy with stale-day threshold and delisting handling;
7. historical membership and point-in-time status/fundamentals;
8. one immutable snapshot id per run;
9. deterministic order/fill/position/equity artifacts;
10. independent parity tests for simple strategies.

## Compact validation standard

### Development

- preregister formula, universe, holding/rebalance rule, cost model, and expected failure regime;
- train/development and validation only for selection;
- maintain a lifetime experiment ledger across all variants, not just the current grid;
- parameter-neighborhood and universe perturbation;
- base cost plus at least one 2x-cost and wider-slippage scenario;
- block bootstrap or HAC for serially dependent observations.

### Final evaluation

- one genuinely untouched holdout or future forward period;
- after it is viewed, mark it contaminated and never reuse it as a holdout;
- report confidence intervals, not only Sharpe and total return;
- require an independent engine parity run for a simple equivalent strategy.

### Sample sufficiency

No universal trade-count number is scientifically correct. Practical minimums for this project:

- slow ETF allocation: at least 25–30 independent rebalance/holding episodes across multiple regimes;
- individual-stock strategy: preferably at least 80–100 completed trades, with no single year/trade dominating;
- fewer observations may remain research-interesting, but cannot support a candidate claim.

### Capacity appropriate to CNY 400,000

- no institutional market-impact model is needed for liquid ETFs and large-cap stocks;
- require order notional below a conservative fraction of daily amount, such as 0.5%–1%;
- cap the portfolio at roughly 10–20 positions unless the strategy specifically needs more;
- preserve minimum commission/lot effects because they materially affect small orders;
- run one lower-liquidity stress scenario.

# Repository decisions

| Repository/component | Decision |
|---|---|
| R5 A-share event loop/accounting | KEEP, fix missing-price policy |
| R5 dynamic allocators | REWRITE with D+1 lag |
| R5 detector code | KEEP for smoke, validate on accepted snapshot |
| R5 selection ledger | SIMPLIFY to audit record; add real split APIs |
| A_Share_Monitor engine | KEEP as temporary parity/reference only |
| A_Share_Monitor metrics | FIX before further interpretation |
| A_Share_Monitor candidate acceptance | DISABLE after current diagnostics |
| US_Stock_Monitor engine | KEEP and harden |
| us_stock_30w backtests/results | ARCHIVE; rebuild only on trusted engine |
| strategy_work research statistics | KEEP and integrate minimally |
| qts | ARCHIVE |
| raw-close US central client | KEEP fail-closed boundary |

# Required repair order

## P0 — before any full strategy replay

1. Fix R5 soft/hard allocators so date-D state/probability sets date-D+1 weights.
2. Add adversarial tests that fail under same-day perfect selection.
3. Fix R5 missing-close valuation: fail closed, or use a documented last-valid mark with stale-day ceiling and delisting rule.
4. Mark all existing R5 allocator smoke returns invalid and regenerate evidence.
5. Freeze the A-share legacy test period as contaminated.
6. Keep all strategy candidate/system-intake flags false.
7. Continue central database work until PIT/status/corporate-action/membership contracts are accepted.

## P1 — trusted-engine consolidation

1. Declare R5 the future authoritative A-share engine after P0 fixes and real-data parity.
2. Retain A_Share_Monitor only for temporary cross-engine parity, then retire it from acceptance.
3. Use US_Stock_Monitor as the US engine; do not revive us_stock_30w scripts.
4. Add a shared compact validation module for ledger, holdout, DSR/PBO, HAC/block bootstrap, and parity fixtures.
5. Replace fail-open selection-curve behavior with explicit boundary errors.
6. Rename US walk-forward or implement actual per-fold fit/freeze/evaluate.

## P2 — metrics and practical realism

1. Correct monthly/yearly returns and alpha labels.
2. Add dated US settlement/fee handling and optional integer-share mode.
3. Add A-share stale-price/delisting tests and dated metadata tests.
4. Add benchmark total-return and excess-return alignment.
5. Add cross-engine golden fixtures: buy-and-hold, equal-weight rebalance, one delisting, one suspension, one corporate action, one regime transition.

# Target architecture

Do not create another framework. The target is:

```text
A-share trusted engine: quant_research_lab R5, after P0 fixes
US trusted engine: US_Stock_Monitor, after P1 hardening
shared validation: one small module/library
legacy A-share engine: parity/reference, then archive from acceptance
us_stock_30w and qts: archive
central database: immutable PIT snapshots consumed read-only
```

Each strategy research run should produce only:

```text
config/preregistration
snapshot id and hashes
orders/fills/equity
split metrics and confidence intervals
robustness summary
experiment-ledger update
short final decision
```

# Should repairs start now?

`YES — TARGETED P0 REPAIRS SHOULD START NOW.`

Do not wait for the central database migration to finish before fixing the R5 allocator lag and missing-price policy; both are code-level defects independent of real data.

Do not launch another broad strategy search until:

- P0 code fixes pass adversarial tests;
- R5 smoke evidence is regenerated;
- the central database provides an accepted immutable snapshot;
- the full replay plan uses a new, genuinely protected final evaluation period.

Part 3 may proceed after this report because its task is to simplify the research workflow around these technical findings. Part 3 must not declare a strategy search restart before the P0 and data gates pass.

# Final verdict

```text
PART2_VERDICT: REBUILD_SELECTED_COMPONENTS
IMMEDIATE_BUGFIX_REQUIRED: yes
BROAD_STRATEGY_SEARCH_ALLOWED: no
A_SHARE_FULL_REPLAY_ALLOWED: no
US_FULL_REPLAY_ALLOWED: no
CURRENT_STRATEGY_CANDIDATE_AVAILABLE: false
SYSTEM_INTAKE_READY: false
NEXT_ACTION:
  1. dispatch R5 allocator/valuation P0 patch;
  2. freeze legacy acceptance paths;
  3. integrate compact validation controls;
  4. continue Part 1 DB migration in parallel;
  5. proceed to Part 3 workflow redesign using this audit.
```
