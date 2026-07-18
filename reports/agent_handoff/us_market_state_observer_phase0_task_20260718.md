# Task — US Market State Observer Phase 0

Date: 2026-07-18  
Target repository: `2604714984-prog/quant-proj`  
Workstream: `US_MARKET_STATE_OBSERVER_READ_ONLY`

## Mission

Determine whether the existing data base can support one causal, lightweight US
market-state observer without using strategy outcomes.

This task does not prove that regime switching is profitable. It creates only a
state-data contract and aggregate episode evidence for later independent strategy
research.

## Hard boundaries

```text
READ_ONLY=true
STRATEGY_RETURNS=false
STRATEGY_SELECTION=false
POSITION_EFFECT=false
ORDER_OR_SIGNAL=false
PROVIDER_CALL=false unless a later explicit user task authorizes one
DATABASE_WRITE=false
NEW_FRAMEWORK=false
STRATEGY_CANDIDATE_AVAILABLE=false
```

Do not implement HMM, machine learning, reinforcement learning, neural networks,
Mixture-of-Experts, a regime registry, a state service, or another CLI.

## Repository boundary

Active code and durable artifacts, if any, live only in `quant-proj`.

The following are read-only references:

```text
2604714984-prog/US_Stock_Monitor
2604714984-prog/us_stock_30w
2604714984-prog/strategy_work
```

Do not import, install or execute their old strategy modules as authority.

## Phase 0A — US data inventory

Inspect the central DuckDB and accepted receipts without mutation. Record exact
snapshot, table, row, date, source, revision and `available_at` identities for the
minimum candidate components:

```text
SPY raw and adjusted daily bars
SPY split and cash-distribution identity
VIX daily close or an explicit absence
VIX3M or other term-structure input, optional
eligible US equity universe and historical membership identity
per-stock raw and adjusted bars
splits, dividends, delistings and terminal actions
market breadth inputs
HYG and LQD raw/adjusted bars, optional
market-wide volume or liquidity inputs, optional
US accepted-session calendar
```

For each component return:

```text
QUALIFIED
RETROSPECTIVE_ONLY
MISSING
CONFLICT
STALE
```

Do not infer missing corporate actions, membership, delistings, VIX, spreads or
availability timestamps.

## Phase 0B — Minimal state contract

Proceed only if sufficient components are qualified for a causal daily observer.
Freeze no more than these outputs:

```text
TREND_UP
RANGE
STRESS
RECOVERY_TAG
UNKNOWN
```

Preferred scores, using only qualified inputs:

```text
trend_score
stress_score
participation_score
state_confidence
```

The minimum preferred feature set is:

```text
SPY medium-term trend
SPY 20-session and 60-session realized volatility
SPY 120-session drawdown
eligible-universe breadth above one frozen medium-term average
eligible-universe positive medium-term return breadth
```

VIX, VIX term structure, HYG/LQD stress and liquidity participation are optional.
If an optional component is not qualified, omit it and lower confidence; do not
substitute another source silently.

Freeze:

```text
calculation timestamp
D-close information cutoff
D+1 earliest activation
thresholds
confirmation duration
minimum state duration
exit rule
UNKNOWN rule
staleness rule
```

No threshold may be selected using a strategy return.

## Phase 0C — Aggregate episode audit

Generate only anonymous aggregates through the accepted historical cutoff:

```text
coverage start/end
daily state counts
number of episodes by state
episode duration distribution
transition count matrix
UNKNOWN count
stale-component count
minimum and maximum confidence
future-row count accessed, which must be zero
```

Do not report:

```text
strategy returns
security rankings
selected securities
state-conditional strategy performance
NAV
Sharpe
recommendations
```

## Deliverables

Maximum three durable files:

```text
research/definitions/us_market_state_observer_v1.json
reports/validation/us_market_state_data_qualification_v1_20260718.json
reports/validation/us_market_state_episode_audit_v1_20260718.json
```

A small pure module and focused tests are permitted only if the data contract passes.
Do not add a runner framework. Default execution must be dry-run and open no database.

## Terminal states

```text
US_STATE_OBSERVER_INPUT_BLOCKED
US_STATE_OBSERVER_DEFINITION_READY
US_STATE_OBSERVER_EPISODE_AUDIT_READY
```

None of these states authorizes strategy work or position effects.

## Validation

```text
strict JSON and duplicate-key rejection
nonfinite rejection
read-only database identity before/after
no WAL
causal timestamp tests
D-close / D+1 boundary tests
UNKNOWN and stale-input tests
full CI
Ruff
git diff --check
```

## GitHub publication

Create one branch and one Draft PR. Push and verify the remote exact head. Do not
merge. Return the exact GitHub links and stop for Manager review.

## Callback

```text
BATCH:US_MARKET_STATE_OBSERVER_PHASE0_20260718
STATUS:
BASE_COMMIT:
PR_URL:
HEAD_SHA:
DATABASE_SHA_BEFORE:
DATABASE_SHA_AFTER:
QUALIFIED_COMPONENTS:
MISSING_OR_CONFLICT_COMPONENTS:
STATE_CONTRACT_CREATED:true|false
EPISODE_AUDIT_CREATED:true|false
STATE_COUNTS:
EPISODE_COUNTS:
UNKNOWN_COUNT:
FUTURE_ROWS_ACCESSED:0
STRATEGY_RETURNS_ACCESSED:false
POSITION_EFFECT_ENABLED:false
STRATEGY_CANDIDATE_AVAILABLE:false
NEXT_ACTION:MANAGER_REVIEW
```
