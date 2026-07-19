# PR #94 Terminal Audit and Result-First Research Program

Date: 2026-07-19  
Repository: `2604714984-prog/quant-proj`  
Controlling PR: `https://github.com/2604714984-prog/quant-proj/pull/94`  
Reviewed head: `7cfe3b5a37e9d244c43465782eeb4d888f5429ba`

## 1. External-audit verdict

```text
VERDICT=ACCEPT_TERMINAL_RETROSPECTIVE_REPLICATION_FAIL
PR_94_MERGE_ALLOWED=EXACT_HEAD_ONLY
LINEAGE=US_SPY_CLASSIC_TURN_OF_MONTH_V1_20260719
LINEAGE_STATUS=PERMANENTLY_CLOSED
HISTORICAL_SPECIALIST_PASS=false
SHADOW_AUTHORIZED=false
PAPER_AUTHORIZED=false
LIVE_AUTHORIZED=false
STRATEGY_CANDIDATE_AVAILABLE=false
FIXES_REQUIRED=none
```

The frozen classic SPY turn-of-the-month specification passed `5/8` gates and failed its three most important robustness gates:

```text
combined 5 bps CAGR                 1.6625%
combined 15 bps CAGR               -0.7201%
bootstrap 95% lower bound          -0.05720%
holdout B2 maximum drawdown        -10.5857%
holdout B1 maximum drawdown        -33.5694%
holdout B2 Calmar                   0.1407
holdout B1 Calmar                   0.4326
largest calendar-year contribution 48.50%
largest episode contribution       20.61%
```

The result shows a weak positive point estimate and lower raw drawdown at low cost, but no stable statistical edge, insufficient holdout risk-adjusted return, high cost sensitivity and excessive profit concentration.

The exact `T` through `T+3` lineage is closed. The following are prohibited within that lineage:

```text
moving the entry or exit window
adding quarter-end, weekday, trend or volatility filters
adding interest-bearing cash and calling it the same strategy
lowering transaction costs
rerunning after a parameter change
promoting the result to Shadow, Paper or candidate status
```

A future calendar strategy must have a genuinely different economic event and a new preregistration. It cannot be presented as a repair of PR #94.

## 2. Project diagnosis after two real US results

The project now has two direct US numerical outcomes:

```text
US_SPY_200D_TREND_CASH_RETROSPECTIVE_BASELINE_V1
= RETROSPECTIVE_BASELINE_FAIL

US_SPY_CLASSIC_TURN_OF_MONTH_V1
= RETROSPECTIVE_REPLICATION_FAIL
```

This is useful negative evidence. It also establishes that the lightweight repository, read-only database path, deterministic calculations, cost handling and one-use result publication can produce adjudicable results.

The bottleneck is no longer architecture. It is selecting mechanisms with:

```text
stronger economic prior
inputs already present in the warehouse
low turnover
USD 40,000 whole-share feasibility
genuinely different economic exposure
one directly executable result sprint
```

## 3. Research objective

The next phase is a rolling, result-first research program.

```text
PRIMARY_OBJECTIVE=produce numerical PASS/FAIL results
PRIMARY_MARKET=US
ACTIVE_CODE_FAMILY_LIMIT=1
NEW_ARCHITECTURE_BUDGET=0
PLAN_ONLY_PR_BUDGET=0
```

Every formal strategy sprint must end in one PR containing either:

```text
A. frozen definition + implementation + focused tests + result JSON + run receipt

or

B. one concise INPUT_BLOCKED result proving that the existing input cannot support the frozen strategy
```

The following are not accepted as completion:

```text
candidate slate only
data-gap memo only
roadmap update only
Phase 0 report only
future-provider recommendation only
```

## 4. Immediate result queue

### Sprint 1 — SPY/QQQ/GLD dual momentum with cash

```text
research_id=US_SPY_QQQ_GLD_DUAL_MOMENTUM_V1_20260719
priority=1
status=AUTHORIZED_AFTER_PR94_MERGE
```

Economic mechanism:

```text
relative momentum chooses the strongest of SPY, QQQ and GLD
absolute momentum requires the selected asset's trailing return to be positive
otherwise the account holds cash
```

This is different from the rejected US31/US36/US41/US46 fixed-weight portfolios. Those lines held fixed ETF weights. This sprint dynamically selects one asset or cash.

Frozen high-level shape:

```text
capital_usd=40000
whole_shares=true
leverage=false
shorting=false
rebalance=monthly
signal=trailing 252 accepted-session adjusted total return
selection=highest return among SPY, QQQ, GLD
absolute_gate=selected trailing return strictly greater than zero
execution=next common accepted-session adjusted-open proxy with raw-open whole-share arithmetic
inactive_asset=cash with zero return
primary_one_way_cost_bps=15
stress_one_way_cost_bps=30
parameter_variants=0
```

Mandatory comparators:

```text
B0 cash
B1 SPY buy-and-hold
B2 static equal-weight SPY/QQQ/GLD
B3 dual-momentum selection/cash
```

The sprint must directly produce a numerical result. No separate candidate-selection, feasibility or roadmap PR is allowed.

### Sprint 2 — three-ETF inverse-volatility allocation

```text
research_id=US_SPY_QQQ_GLD_INVERSE_VOLATILITY_V1
priority=2
status=QUEUED_NOT_AUTHORIZED
```

This sprint opens only after Sprint 1 closes or enters external review.

Economic mechanism:

```text
monthly inverse realized-volatility weights across SPY, QQQ and GLD
no trend filter
no asset selection
no leverage
```

It is a risk-allocation hypothesis, not a momentum repair. The future task must freeze one volatility window and one concentration cap before any result access.

### Sprint 3 — stress safe-haven sleeve

```text
research_id=US_SPY_GLD_STRESS_SAFE_HAVEN_V1
priority=3
status=QUEUED_REQUIRES_NEW_FREEZE
```

This is the first explicitly regime-specific lane. It must jointly freeze:

```text
one causal SPY stress condition
one GLD-or-cash action
one activation lag
one exit rule
state-outside cash
```

It may not use PR #93 or PR #94 results to select the state threshold. Exact parameters are frozen only after the first two result sprints and an outcome-free input check.

## 5. Parallel bounded US stock-data unlock lane

ETF result sprints must continue while one bounded data task evaluates whether stock-level US strategies can be unlocked.

Time budget:

```text
maximum=10 working days
one canonical-provider proposal
one read-only cross-check at most
no data-platform rebuild
```

Minimum target dataset:

```text
historical US common-stock membership or a frozen non-index listing rule
raw and adjusted OHLCV
dividends and splits
delistings and terminal values
historical availability or an explicit retrospective-only identity
accepted-session calendar
immutable snapshot hash
```

Decision:

```text
DATA_READY
or
DATA_NOT_READY_STOP
```

If a single bounded provider path cannot satisfy the contract within the time budget, stop the lane. Do not block ETF result sprints and do not construct a multi-provider fusion platform.

## 6. Qlib and RD-Agent activation gates

Qlib and RD-Agent remain deferred.

Qlib may start only when:

```text
one stock-level immutable snapshot is accepted
one deterministic stock-level benchmark result exists
train/validation/holdout exports are physically separated
Qlib remains outside quant-proj runtime dependencies
```

RD-Agent may start only after the Qlib sandbox is reproducible and may access development data only. It may propose code or hypothesis cards but may not read validation, holdout, prospective outcomes or select a winner.

Neither tool is required for Sprint 1, Sprint 2 or Sprint 3.

## 7. Result-sprint engineering budget

For a simple ETF strategy:

```text
one implementation PR
one primary variant
runtime calculation module <= 250 lines preferred
one-use runner <= 300 lines preferred
focused tests <= 200 lines preferred
two terminal artifacts: result + receipt
no new runner/evidence/manifest framework
```

A result PR may update the existing Manager roadmap only by replacing the current-state block. It must not add another roadmap or control document.

## 8. Mechanical promotion path

```text
RETROSPECTIVE_FAIL
-> permanently close
-> start the next queued mechanism

RETROSPECTIVE_PASS_TO_EXTERNAL_REVIEW
-> independent exact-head audit
-> SHADOW_ELIGIBLE only after acceptance

SHADOW
-> at least 20 accepted sessions
-> at least one complete decision/activation/exit lifecycle
-> no parameter change

PAPER
-> only after Shadow acceptance
-> deterministic target-to-order and fill reconciliation

MANUAL_LIVE_PILOT
-> only after separate user authorization and external review
-> human-reviewed targets and manual broker entry first
```

Automatic execution remains outside the current program.

## 9. Manager operating cadence

```text
one formal strategy at a time
one result PR every 3-7 working days when inputs are present
ordinary FAIL: CI + Manager scope check + merge terminal evidence
first PASS: external review before merge/promotion
no full external audit for an ordinary correctly computed FAIL
```

The first active action after PR #94 is merged is Sprint 1, `US_SPY_QQQ_GLD_DUAL_MOMENTUM_V1_20260719`.
