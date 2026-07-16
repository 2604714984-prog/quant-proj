# Task — Macro Risk Shadow Phase 1
shadow records with no position effect do not require full external review.
shadow records with no position effect do not require full external review.
Date: 2026-07-17
Repository: `2604714984-prog/quant-proj`
Default branch: `v2-main`
Status: `PUBLISHED_SHADOW_ONLY_NOT_STARTED`

## Authority and separation

Read, in order:

1. `reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md`
2. `reports/agent_handoff/user_dispatch_manager_v2_post_audit_roadmap_v2_20260716.md`
3. `AGENTS.md`

This task is for a separate read-only Macro Risk Shadow lane. It must not edit
Cycle 3 files, select Cycle 3 parameters, inspect Cycle 3 outcomes, or coordinate
directly with the Cycle 3 implementation task. Cross-task questions return to
the Manager.

Publication of this file does not authorize repository edits, provider access,
database writes or position effects. A separate Manager start callback is
required before the first shadow computation.

## Purpose

Measure whether a small, interpretable set of existing local-market aggregates
can describe broad A-share risk conditions. The output is diagnostic only.

## Frozen Phase 1 inputs

Use only existing, read-only local-market data:

```text
510300 120-session trend
20-session realized volatility
60-session realized volatility
120-session drawdown
share of stocks with positive 60-session return
share of stocks above one frozen medium-term moving average
market amount / turnover breadth
limit-down share
suspension share
```

Before the first record, freeze the exact formula, direction, scaling,
staleness rule and missing-input behavior for every component. Missing or stale
components must be reported, not silently imputed. Do not add an external macro
provider in Phase 1.

## Output contract

At most one aggregate record per week:

```text
risk_score: integer or deterministic decimal on 0–100
risk_level: GREEN | AMBER | RED
confidence
component contributions
stale components
as_of timestamp
input snapshot identity
```

Do not output security identifiers, rankings, strategy returns, NAV, orders or
signals. Run through current strategy cycles before judging usefulness.

## Hard boundary

```text
SHADOW_ONLY
NO_POSITION_EFFECT
NO_STRATEGY_SELECTION
NO_ORDER_OR_SIGNAL
NO_USE_AS_A_STRATEGY_GATE
STRATEGY_CANDIDATE_AVAILABLE=false
```

The shadow cannot rescue, relabel or filter Relative Strength, Defensive Low
Volatility, Cycle 3, or any other failed family. It cannot become an ensemble or
synthesizer input during Phase 1.

## Engineering boundary

No new CLI, configuration system, database layer, event loop, portfolio core,
runner, registry, dispatcher, agent framework or automatic provider fusion.
Use read-only access through existing paths. No provider/network access and no
database/cache/schema/raw-data write.

## Start conditions and callback

The Manager may start the read-only lane only after:

- this task file is merged;
- the final `v2-main` HEAD is recorded;
- Cycle 3 files are isolated from the shadow lane;
- the exact read-only input snapshot is named;
- a short-lived scope review confirms zero position effect.

At start, return Callback D from the current Manager roadmap. Ordinary weekly
shadow records with no position effect do not require full external review.
