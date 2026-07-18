# External Audit — PR #84 Terminal Capital Feasibility and US-First Regime Route

Date: 2026-07-18  
Repository: `2604714984-prog/quant-proj`

## Exact review target

```text
PR=84
HEAD=cae11d0574a4b3dd18e0eafd3839c8e945a7d009
TREE=4a233e66be41ba256a2557a10e474c52d64ea903
BASE=10facd2d26832bcd24e278dd263c1fe57e9396d4
CHANGED_FILES=5
ADDITIONS=1483
CI_RUN=29644637574
CI_STATUS=SUCCESS
```

## Verdict

```text
VERDICT=ACCEPT_TERMINAL_LIVE_FEASIBILITY_FAIL_NO_OUTCOME
PR_84_DISPOSITION=CLOSE_WITHOUT_MERGE
FAMILY_STATUS=PERMANENTLY_CLOSED
HISTORICAL_VALIDATION_AUTHORIZED=false
HOLDOUT_AUTHORIZED=false
FORWARD_AUTHORIZED=false
SHADOW_AUTHORIZED=false
PAPER_AUTHORIZED=false
STRATEGY_CANDIDATE_AVAILABLE=false
```

## Accepted findings

The exact head closes the earlier semantic findings:

```text
closed Family42 runtime dependency removed
candidate exclusions frozen exhaustively
one QFQ secondary economic-screen representation frozen
no account-level or strict-PIT claim
CNY 400,000 capital and 100-share lot gate frozen before outcomes
```

The capital scan uses raw next-session opens for lot, cash, commission, limit and
capacity arithmetic. It preserves the fixed 30-stock basket, allows no replacement,
and forbids post-result changes to capital, basket size, exposure, commission,
capacity or market rules.

Terminal aggregate evidence:

```text
retained_intervals=75
invalid_capital_intervals=75
minimum_target_nonzero_comparator_positions=12
minimum_filled_comparator_positions=6
minimum_comparator_invested_ratio=0.190275
minimum_target_nonzero_managed_positions=1
minimum_filled_managed_positions=1
minimum_managed_invested_ratio=0.003195
maximum_one_lot_target_threshold_cny=41584738.33494295
capacity_rejections=4
market_rule_rejections=34
```

The failure is robust to order-level cash allocation: in the worst interval the
comparator has only 12 nonzero lot targets before cash clipping, and the managed
path has only one. It cannot satisfy the frozen 30-position / 90-percent comparator
or 24-position managed gates through a different deterministic order.

No holding-period return, validation return, holdout, forward, security identifier,
provider call, database write, Shadow, Paper, broker or candidate boundary was
crossed. The central database remained byte-identical and exact-head CI passed.

## Why the PR should not merge

The branch and PR already preserve the full negative evidence. Merging 1,483 lines
of definition, research module, preflight, tests and terminal result would make a
closed, unusable strategy an active mainline dependency and enlarge the lightweight
repository without a consumer.

Required disposition:

```text
close PR #84 without merge
preserve exact head and review
add one concise closure entry to the controlling roadmap
never rerun or reinterpret the family as a regime specialist
```

## Research-direction adjudication

The project should not return to an all-weather-strategy objective. It should
operate a continuous US-first regime-specialist program.

A valid specialist is jointly preregistered as:

```text
causal market-state rule
+ strategy
+ activation and exit rule
+ cash outside the state
+ costs, lag and execution
```

A failed historical strategy cannot be rescued by assigning it a favorable state
after results are known.

US research is primary. New A-share families require an explicit user override.
Archived `US_Stock_Monitor`, `us_stock_30w` and `strategy_work` repositories are
reference and failure-memory sources only; they must not become runtime dependencies.

## US state program

Phase 0 is read-only and outcome-free. It should qualify the minimum inputs for:

```text
TREND_UP
RANGE
STRESS
RECOVERY_TAG
UNKNOWN
```

Preferred source-qualified components are SPY trend/drawdown, realized volatility,
VIX, market breadth, HYG/LQD stress and market liquidity participation. Missing or
stale inputs produce `UNKNOWN` or `US_STATE_OBSERVER_INPUT_BLOCKED`.

The state observer cannot access strategy returns, choose strategies or affect
positions.

## Initial US specialist slate

The Phase 0 scout should assess, without outcomes:

```text
TREND_UP:
US liquid large-cap absolute trend plus breadth participation.

STRESS:
long-only quality or low-risk equities if revision-safe PIT fundamentals and beta
inputs are complete.

RANGE_OR_STRESS_LIQUIDITY:
short-term market-residual reversal in highly liquid equities, subject to strict
spread, turnover, cost and next-open feasibility.

RECOVERY_TAG:
breadth recovery after a frozen market drawdown, with cash or broad exposure as
the default comparator.
```

Relevant primary research includes:

- Daniel and Moskowitz, `Momentum Crashes`: https://www.nber.org/papers/w20439
- Nagel, `Evaporating Liquidity`: https://academic.oup.com/rfs/article-abstract/25/7/2005/1602153
- Asness, Frazzini and Pedersen, `Quality Minus Junk`: https://papers.ssrn.com/abstract=2312432
- Frazzini and Pedersen, `Betting Against Beta`: https://doi.org/10.1016/j.jfineco.2013.10.005

The citations establish priors, not local strategy evidence.

## Continuous-search control

Outcome-free literature, data and capital-feasibility scouting may continue. Formal
outcomes remain sequential:

```text
one code-writing family at a time
one formal outcome lane per state at a time
one primary and at most one robustness variant
all attempted families retained in the ledger
failed families permanently closed
```

Historical evaluation must include inactive cash and compare:

```text
B0 cash
B1 always-on strategy
B2 state-gated simple market exposure
B3 state-gated specialist
```

Only `B3` incremental value can establish specialist evidence. Historical pass is
`HISTORICAL_SPECIALIST_PASS`, not candidate status. External review is required
before `SHADOW_ELIGIBLE`.

The Shadow pool is capped at two specialists per state and eight total. Real
prospective episodes, not historical optimization, decide which specialists remain.

## Immediate actions

```text
1. Close PR #84 without merge.
2. Close superseded Draft PR #86 and #87 without merge.
3. Merge the documentation-only roadmap update after CI.
4. Start the US Market State Observer Phase 0 task.
5. Start the US Regime Specialist Scout Phase 0 task.
6. Return both read-only results to the user before selecting the first US family.
7. Do not create strategy code or open outcomes until that user selection.
```
