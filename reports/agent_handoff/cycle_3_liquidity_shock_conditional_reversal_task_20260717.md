# Cycle 3 Task — A-Share Liquidity-Shock Conditional Short-Term Reversal

Date: 2026-07-17
Repository: `2604714984-prog/quant-proj`
Default branch: `v2-main`
Status: `AUTHORIZED_FOR_PR_A_ONLY`

## Authority and base

Read, in order:

1. `reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md`
2. `reports/agent_handoff/user_dispatch_manager_v2_post_audit_roadmap_v2_20260716.md`
3. `AGENTS.md`

This task authorizes one outcome-blind PR A only. The implementation branch must
start from the first merged `v2-main` commit containing this task file. Record
that exact base commit and tree before editing.

Research ID:

```text
A_SHARE_LIQUIDITY_SHOCK_CONDITIONAL_SHORT_TERM_REVERSAL_V1_20260717
```

Current state:

```text
ACTIVE_FAMILY=CYCLE_3_LIQUIDITY_SHOCK_CONDITIONAL_REVERSAL
ACTIVE_STAGE=OUTCOME_BLIND_PR_A
PREFLIGHT_STATUS=NOT_RUN
OUTCOME_STATUS=NOT_RUN
FORWARD_STATUS=CLOSED
STRATEGY_CANDIDATE_AVAILABLE=false
```

## Economic hypothesis

A short-term market-relative price decline combined with one explicit abnormal
trading-activity shock, during a normal, liquid, executable market state, may
represent temporary price pressure rather than permanent deterioration.

This is a new family. It is not a repair, filter, regime relabel, or rerun of
Relative Strength or Defensive Low Volatility. Do not implement an unrestricted
"buy the largest losers" strategy.

## Outcome-blind design budget

Freeze exactly four ordered variants before any outcome access:

1. 10-session market-relative reversal comparator without the shock condition.
2. 10-session market-relative reversal with one fixed activity-shock condition.
3. 20-session market-relative reversal comparator without the shock condition.
4. 20-session market-relative reversal with the same fixed shock condition.

The two unconditioned variants are bounded comparators, not standalone families.
The primary economic variants are the two shock-conditioned variants.

PR A must freeze, without reading strategy outcomes:

- the exact market-relative return formula;
- the single trading-activity input, lookback, normalization, direction and
  threshold;
- the normal/liquid/executable-state rule;
- deterministic sorting and tie-breaking;
- candidate count and skip rules;
- entry, exit and holding-period behavior;
- the statistical family, all gates and permanent stop rules.

No parameter grid, alternative shock library, macro filter, regime filter,
post-outcome threshold adjustment, or fifth variant is allowed.

## Reused execution contract

Reuse the existing V2 implementation and semantics:

```text
capital: CNY 400,000
maximum positions: 15
weighting: equal weight
universe: ordinary A shares
minimum listing history: 252 accepted sessions
eligibility: non-ST, non-suspended, liquid and executable
decision time: D after close
entry time: D+1 accepted-session open
benchmark: 510300.SH
currency unit: CNY
position unit: SHARES
```

Reuse existing costs, board-lot, capacity, limit, suspension, terminal and
blocked-exit rules. Do not add or replace a CLI, configuration system, engine,
event loop, portfolio core, runner, registry, manifest framework or database
layer. The strategy adapter should normally remain within 100–300 runtime lines.

## PR A scope

PR A may contain only:

- one frozen strategy definition;
- one small adapter using the shared engine;
- focused deterministic tests;
- one repeatable outcome-free preflight path;
- the minimum documentation needed to reproduce those items.

It must not contain historical returns, NAV, Sharpe, gate outcomes, prospective
observations, security identifiers or rankings from real data.

## Outcome-free preflight contract

The preflight is repeatable and does not consume the one historical outcome.
It must report aggregate-only evidence for:

```text
required history exists
decision count
minimum eligible count
minimum candidate count
invalid decision count
execution panels complete
benchmark initial entry filled
benchmark invested ratio
capacity rejection ratio
unexpected exception count = 0
currency unit = CNY
position unit = SHARES
no embargo or prospective data accessed
```

It must not emit identifiers, rankings, returns, NAV, performance statistics or
gates. An input failure is `INPUT_BLOCKED` and does not consume the one outcome.

## Validation and handoff

Before opening the PR:

- run focused tests;
- run the complete repository test suite;
- run Ruff and `git diff --check`;
- verify the diff contains no new framework or unrelated files;
- verify no database, raw data, cache, credential or large generated result is
  committed;
- verify `strategy_candidate_available=false`.

Return Callback B from the Manager roadmap. Do not run the historical outcome.
The Manager must separately authorize exactly one fresh Run ID after PR A and
the aggregate preflight are accepted.

## Terminal rule for the later outcome

```text
HISTORICAL_SCREENING_FAIL:
close permanently; no retune, rerun, rescue filter or specialist relabel

HISTORICAL_SCREENING_PASS:
enter prospective Shadow; remain non-candidate

INPUT_BLOCKED:
repair only the input or financial-semantic defect under a child lineage
```

## Boundary

Research-only. No broker, order, paper, live or automatic execution. No
prospective access, recommendation, actionable ranking, candidate promotion,
ensemble, synthesizer or Macro Risk position effect.
