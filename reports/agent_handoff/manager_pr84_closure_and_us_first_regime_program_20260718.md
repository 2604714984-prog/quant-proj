# Manager Task — Close PR #84 and Start the US-First Regime-Specialist Program

Date: 2026-07-18  
Repository: `2604714984-prog/quant-proj`

## Controlling inputs

Read, in order:

1. latest explicit user instruction;
2. `reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md`;
3. `AGENTS.md`;
4. `reports/external_audit/pr84_relative_variance_terminal_and_us_first_regime_audit_20260718.md`;
5. the updated current Manager roadmap in this branch.

## Part 1 — Repository closure

Confirm PR #84 still has exact head:

```text
cae11d0574a4b3dd18e0eafd3839c8e945a7d009
```

Then:

```text
close PR #84 without merge
record A_SHARE_RELATIVE_VARIANCE=LIVE_FEASIBILITY_FAIL_NO_OUTCOME
record historical_outcome_opened=false
record strategy_candidate_available=false
```

Do not cherry-pick its result, definition, module, preflight or tests. The PR history
is the controlling negative evidence.

Close the following superseded documentation PRs without merge:

```text
PR #86
PR #87
```

Do not execute their older strategy-to-Paper route. The current user instruction
supersedes the finite-lane and first-usable-strategy planning assumptions.

## Part 2 — Merge the current documentation update

The external-audit/roadmap PR must remain documentation-only. Verify it changes
only:

```text
current Manager roadmap
one external-audit report
this Manager task
US Market State Observer Phase 0 task
US Regime Specialist Scout Phase 0 task
```

Run CI and merge only after the exact file scope is confirmed. Do not change runtime,
data, strategy or workflow code in the documentation PR.

## Part 3 — Operating model

Set:

```text
PRIMARY_RESEARCH_MARKET=US
SECONDARY_RESEARCH_MARKET=A_SHARE_USER_OVERRIDE_ONLY
ACTIVE_FAMILY=NONE
ACTIVE_STAGE=US_REGIME_PROGRAM_PHASE0
VALIDATED_SPECIALISTS=0
STRATEGY_CANDIDATE_AVAILABLE=false
```

Research continues indefinitely at the outcome-free scouting layer. Formal outcome
runs remain sequential and fully logged.

The program searches for state specialists, not an all-weather strategy. Each
formal family must jointly freeze:

```text
state rule
specialist strategy
activation and exit rule
cash outside the state
cost, lag and execution
```

Do not relabel any closed strategy as a specialist.

## Part 4 — Dispatch two independent read-only subagents

Open exactly two Phase 0 workstreams.

### A. US Market State Observer

Use:

```text
reports/agent_handoff/us_market_state_observer_phase0_task_20260718.md
```

This workstream may inspect data and create causal state/episode aggregates. It may
not access strategy returns or choose a strategy.

### B. US Regime Specialist Scout

Use:

```text
reports/agent_handoff/us_regime_specialist_scout_phase0_task_20260718.md
```

This workstream may research primary literature, inspect data readiness and return a
candidate slate. It may not write a strategy adapter or open outcomes.

The two subagents do not coordinate directly. Cross-workstream findings return to
the Manager.

## Part 5 — US repository boundary

Treat these repositories as read-only references:

```text
2604714984-prog/US_Stock_Monitor
2604714984-prog/us_stock_30w
2604714984-prog/strategy_work
```

Do not import them, install them, run their old strategy code as authority, or make
`quant-proj` depend on them. Their rejected strategies remain rejected.

Useful data or market-semantic work may be migrated only after a task identifies the
exact primitive, source identity, files and tests. Any runtime migration requires a
separate narrow review.

## Part 6 — Selection gate for the first US specialist

After both Phase 0 callbacks, produce one user-facing candidate slate containing no
more than four hypotheses. For each include:

```text
state
primary economic mechanism
primary research source
data readiness
historical membership / survivorship risk
capital and fractional-share assumptions
expected turnover and holding period
execution risks
independence from closed strategies
recommended PASS / BLOCKED decision
```

Do not include strategy returns.

The user selects the first family. Only after selection may the Manager create a
Strategy Builder task file.

## Part 7 — Continuous-search constraints

```text
one code-writing family at a time
one formal outcome lane per state at a time
one primary variant
at most one preregistered robustness variant
maximum two Shadow specialists per state
maximum eight Shadow specialists total
```

All formal attempts remain in the experiment ledger. No result-dependent filter,
parameter, state definition, provider substitution or additional variant is allowed.

## Part 8 — Paper and live boundary

No current task may create:

```text
position effect
recommendation
order
Paper account path
broker gateway
manual live pilot
automatic trading
```

A specialist must first obtain reviewed `HISTORICAL_SPECIALIST_PASS`, then reviewed
prospective Shadow evidence. A later Paper task requires a new explicit user
instruction.

## Required callback

```text
STATUS:
V2_MAIN_HEAD:
PR_84_STATUS:
PR_84_REVIEWED_HEAD:
PR_86_STATUS:
PR_87_STATUS:
ROADMAP_URL:
EXTERNAL_AUDIT_URL:
US_STATE_TASK_URL:
US_SCOUT_TASK_URL:
US_STATE_WORKSTREAM_STATUS:
US_SCOUT_WORKSTREAM_STATUS:
ACTIVE_FAMILY:NONE
ACTIVE_STAGE:US_REGIME_PROGRAM_PHASE0
STRATEGY_CANDIDATE_AVAILABLE:false
PAPER_OR_LIVE_PATH_CREATED:false
BLOCKERS:
NEXT_ACTION:RETURN_PHASE0_RESULTS_AND_CANDIDATE_SLATE_TO_USER
```
