# V2 Manager Roadmap

Date: 2026-07-18  
Repository: `2604714984-prog/quant-proj`  
Default branch: `v2-main`  
Status: `CURRENT_MANAGER_HANDOFF`

## 1. Control and architecture

This is the only active Manager roadmap. It is subordinate to:

```text
latest explicit user instruction
> reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md
> merged AGENTS.md
> this roadmap
> accepted task artifact
```

```text
architecture_rebuild_required=false
one_repository=true
one_python_package=true
one_CLI=true
one_DuckDB_access_layer=true
one_event_loop_and_portfolio_core=true
one_CI_workflow=true
primary_research_market=US
secondary_research_market=A_SHARE_USER_OVERRIDE_ONLY
active_code_writing_family=none
validated_specialists=0
strategy_candidate_available=false
```

Do not add a CLI, database layer, second backtester, registry, dispatcher, agent
platform, automatic source fusion, broker path, or parallel runtime. Archived US
repositories are read-only references and must not become runtime dependencies.

## 2. Current terminal state

Closed families cannot be rerun, retuned, regime-relabeled, filtered, or rescued.

Key controlling closures:

```text
A_SHARE_RELATIVE_STRENGTH=HISTORICAL_SCREENING_FAIL
A_SHARE_DEFENSIVE_LOW_VOLATILITY=HISTORICAL_GATED_FAIL
A_SHARE_LIQUIDITY_SHOCK_REVERSAL=CLOSED_PREFLIGHT_STRUCTURAL_INFEASIBLE_NO_OUTCOME
A_SHARE_THREE_ETF_TREND=SOURCE_QUALIFICATION_INCOMPLETE_CLOSE_CYCLE4
A_SHARE_SWING_COUNT=HISTORICAL_SCREENING_FAIL_CLOSED_EXECUTION_ERROR
A_SHARE_POST_IPO_AGE=VALIDATION_FAIL
A_SHARE_CHINA_PRICE_VOLUME_REPLICATION=FEASIBILITY_BLOCKED_CLOSE_NO_ADAPTER_NO_OUTCOME
A_SHARE_RELATIVE_VARIANCE=LIVE_FEASIBILITY_FAIL_NO_OUTCOME
```

Relative Variance controlling evidence:

```text
PR=https://github.com/2604714984-prog/quant-proj/pull/84
reviewed_head=cae11d0574a4b3dd18e0eafd3839c8e945a7d009
external_review=ACCEPT_TERMINAL_LIVE_FEASIBILITY_FAIL_NO_OUTCOME
merge_policy=CLOSE_WITHOUT_MERGE
capital_cny=400000
basket_size=30
invalid_capital_intervals=75_of_75
historical_outcome_opened=false
```

The branch and PR preserve negative evidence. Do not merge dormant strategy code
into the lightweight mainline. Record only the terminal status here.

Shared semantic state:

```text
H3_STRICT_PREOPEN=CLOSED_ACCEPTED
M1_CROSS_TYPE_CORPORATE_ACTION_ID=DEFERRED
MACRO_RISK=SHADOW_ONLY_NO_POSITION_EFFECT
```

## 3. Research mission

Stop searching for one all-weather strategy. Operate a continuous US-first
regime-specialist research program.

A formal research unit is:

```text
causal market-state rule
+ specialist strategy
+ activation and exit rule
+ state-outside cash rule
+ cost, lag and execution contract
```

A failed all-sample strategy cannot be relabeled after the fact as a regime
specialist. State, strategy, activation and exit rules must be frozen before any
strategy outcome is opened.

US research receives at least three of every four new formal economic-hypothesis
lanes. New A-share families remain paused unless the user explicitly authorizes
one. Broad US ETFs may be used as state inputs or benchmarks; the primary
specialist research universe remains US-listed equities unless a task explicitly
freezes an ETF strategy.

## 4. Shared US market-state observer

Phase 0 may use only source-qualified, causally available US market data. The
first preferred components are:

```text
SPY medium-term trend and drawdown
20-session and 60-session realized volatility
VIX level and, only if qualified, term structure
eligible-universe breadth above a frozen medium-term average
eligible-universe positive medium-term return breadth
HYG versus LQD relative stress, only if qualified
market-wide liquidity or volume participation, only if qualified
```

Output states:

```text
TREND_UP
RANGE
STRESS
RECOVERY_TAG
UNKNOWN
```

The observer must be independent of strategy returns. It may output state scores,
confidence, episodes, transitions and stale-component flags. It may not select a
strategy, change a position, emit an order, or use future information.

If required identities are incomplete, return:

```text
US_STATE_OBSERVER_INPUT_BLOCKED
```

Do not build an HMM, neural network, reinforcement learner, or general regime
framework in Phase 0.

## 5. Continuous specialist discovery

Outcome-free scouting may continue indefinitely. Formal outcome access remains
bounded and sequential.

```text
one code-writing family at a time
one formal historical outcome lane per state at a time
one primary variant
at most one preregistered robustness variant
one role-specific primary endpoint
all formal attempts retained in the experiment ledger
failed families permanently closed
```

Shadow-pool limits:

```text
maximum_two_specialists_per_state
maximum_eight_specialists_total
```

When a new Shadow specialist enters a full state bucket, archive the weakest
prospective-evidence specialist. Historical backtests alone cannot decide the
winner.

## 6. Specialist validation contract

Every specialist must be evaluated over the complete calendar, including cash
when inactive.

Mandatory benchmarks:

```text
B0 cash
B1 same strategy always on
B2 state-gated simple market exposure
B3 state-gated specialist
```

`B3` must add value beyond both `B1` and `B2`; otherwise the state gate or the
specialist is redundant.

Historical specialist evidence should include:

```text
complete-calendar net return after frozen costs
state-active return and inactive cash return
episode count and episode median return
activation share and turnover
largest single-episode contribution
maximum drawdown and tail loss
```

Initial episode requirements, unless a task justifies a rarer state before
outcomes:

```text
at_least_6_total_episodes
at_least_2_validation_episodes
at_least_2_holdout_episodes
activation_share_between_5_and_60_percent
single_episode_contribution_below_40_percent
```

Robustness checks:

```text
double transaction costs
one decision-period activation delay
one decision-period exit delay
10 percent deterministic state-label perturbation
adverse lot, fill and cash rounding
```

Historical pass creates only:

```text
HISTORICAL_SPECIALIST_PASS
then SHADOW_ELIGIBLE after external review
```

It does not create a strategy candidate, Paper authority, recommendation, or
trading authority.

## 7. US-first research queue

Phase 0 must return a data-qualified candidate slate before any new adapter.
Preferred hypotheses are:

```text
TREND_UP:
  US large-cap absolute trend plus breadth participation; new lineage, no reuse
  of rejected US31/US36/US41/US46 parameters or results.

STRESS:
  long-only high-quality or low-risk liquid equities, only if revision-safe PIT
  fundamentals and beta inputs are qualified.

RANGE_OR_STRESS_LIQUIDITY:
  short-term market-residual reversal in highly liquid equities; high turnover,
  spread and next-open feasibility must pass before implementation.

RECOVERY_TAG:
  breadth recovery after a frozen market drawdown; default to broad exposure or
  cash unless a stock-selection mechanism has an independent prior.
```

Primary research references include Daniel and Moskowitz, `Momentum Crashes`;
Nagel, `Evaporating Liquidity`; Asness, Frazzini and Pedersen, `Quality Minus
Junk`; and the published critiques of mechanical low-beta and volatility-managed
strategies. Literature support is a prior, not strategy evidence.

The first formal family is selected by the user after Phase 0, using economic
prior, data readiness, USD-account feasibility, turnover and independence from
closed strategies. Do not select it using historical strategy returns.

## 8. Repository and data boundaries

All new active work lives in `quant-proj`.

```text
US_Stock_Monitor=ARCHIVED_REFERENCE_ONLY
us_stock_30w=ARCHIVED_FAILURE_MEMORY_ONLY
strategy_work=ARCHIVED_REFERENCE_ONLY
```

No runtime import, editable install, subprocess dependency or data-authority
inheritance from those repositories is allowed. A useful market-semantic or PIT
primitive may be migrated only through a narrow reviewed task.

For each dataset:

```text
one canonical provider
at most one read-only cross-check
immutable snapshot identity
available_at or explicit retrospective-only classification
raw and adjusted price identities separated
splits, dividends, delistings and terminal actions fail closed
```

Provider calls and database writes require separate explicit authority.

## 9. Shadow, Paper and live boundary

A specialist may enter read-only Shadow only after a reviewed historical
specialist pass. Shadow must observe at least one real state episode and one full
activation/exit lifecycle before Paper review.

Paper and live remain closed:

```text
SHADOW_POSITION_EFFECT=false
PAPER_AUTHORIZED=false
BROKER_GATEWAY_AUTHORIZED=false
MANUAL_LIVE_PILOT_AUTHORIZED=false
AUTO_TRADING_AUTHORIZED=false
```

The first live path, if later authorized, is human-reviewed target generation,
manual order entry and imported fill reconciliation. Automatic broker execution
is a later independent stage.

## 10. Combination and Macro Risk

Macro Risk remains a separate Shadow overlay. It may explain or cap total risk
only after its own prospective acceptance; it cannot rescue a failed specialist.

Do not build a strategy synthesizer until at least two economically distinct US
specialists have:

```text
independent historical specialist passes
prospective Shadow episodes
shared-account executable targets
```

Required combination order:

```text
best single specialist
-> equal-weight static sleeves
-> fixed-risk static sleeves
-> static sleeves plus Macro Risk cap
-> soft state allocation
```

Hard winner-takes-all switching is not the default.

## 11. Immediate Manager actions

```text
1. Close PR #84 without merge at reviewed head cae11d0574a4b3dd18e0eafd3839c8e945a7d009.
2. Close superseded Draft PR #86 and PR #87 without merge.
3. Merge the documentation-only external-audit/roadmap PR after CI.
4. Dispatch the US Market State Observer Phase 0 task.
5. Dispatch the US Regime Specialist Scout Phase 0 task.
6. Return both GitHub task links and their read-only callbacks to the user.
7. Do not create strategy code or open outcomes until the user selects the first US family.
```

Current state after those actions:

```text
PRIMARY_RESEARCH_MARKET=US
ACTIVE_FAMILY=US_SPY_CLASSIC_TURN_OF_MONTH_V1
ACTIVE_STAGE=OUTCOME_BLIND_IMPLEMENTATION_READY
VALIDATED_SPECIALISTS=0
STRATEGY_CANDIDATE_AVAILABLE=false
NEXT_ACTION=PUSH_EXACT_CODE_COMMIT_AND_REQUIRE_GREEN_CI_BEFORE_ONE_USE_RETROSPECTIVE_RUN
```
