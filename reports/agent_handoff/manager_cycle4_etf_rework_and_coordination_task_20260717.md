# Manager Task — Cycle 4 ETF Rework, Source Qualification, and Repository Closure

Date: 2026-07-17  
Repository: `2604714984-prog/quant-proj`  
Default branch: `v2-main`  
Status: `AUTHORIZED_COORDINATION_ONLY`

## Authority

Read in this order:

1. `reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md`
2. `reports/agent_handoff/user_dispatch_manager_v2_post_audit_roadmap_v2_20260716.md`
3. `AGENTS.md`
4. `reports/external_audit/cycle4_three_etf_external_audit_verdict_20260717.md`
5. this task

The controlling external verdict is:

```text
REWORK_REQUIRED
```

This task incorporates the preceding repository review and the Cycle 4 external
audit. It authorizes coordination and publication of exactly two bounded work
lanes. It does not authorize Cycle 4 strategy code, an ETF import, an outcome
run, a prospective observation, or a trading path.

## Current state

```text
V2_MAIN_BASE_FOR_AUDIT=042eb40a00c823641370dc36361f9cdfd0f04ba0
CYCLE_3=CLOSED_PREFLIGHT_STRUCTURAL_INFEASIBLE_NO_OUTCOME
CYCLE_4=REWORK_REQUIRED_BEFORE_DATA_IMPORT
VALIDATED_HISTORICAL_SPECIALIST_COUNT=0
PREFLIGHT_STATUS=NOT_RUN
OUTCOME_STATUS=NOT_RUN
FORWARD_STATUS=CLOSED
STRATEGY_CANDIDATE_AVAILABLE=false
STRATEGY_SYNTHESIZER=NOT_AUTHORIZED
```

Accepted repository findings:

```text
architecture remains reliable and lightweight
Cycle 3 is permanently closed without outcome access
Macro Risk Shadow may proceed independently as read-only/no-position-effect
PR #62 is stale and must close without merge
no new control constitution, framework, registry, engine or platform is needed
```

## Manager mission

Coordinate exactly these two Cycle 4 lanes:

```text
Lane A — listed-fund cash-distribution semantic repair
Lane B — fixed-three-ETF read-only source qualification
```

The task files are:

```text
reports/agent_handoff/cycle4_listed_fund_cash_distribution_semantic_repair_task_20260717.md
reports/agent_handoff/cycle4_three_etf_read_only_source_qualification_task_20260717.md
```

The lanes may run in parallel because Lane B is read-only and may not edit Lane A
files. They do not coordinate directly; all cross-lane questions return to the
Manager.

Normal concurrency remains:

```text
one code-writing semantic subagent
one read-only source-qualification subagent
one temporary external-review subagent when required
```

## Required repository actions

Execute in order:

1. Treat PR #68 as the external-audit and task-publication packet only.
2. Verify PR #68 contains documentation only, CI is green, and no data or runtime
   file is committed.
3. Merge PR #68 only as audit/task evidence.
4. Close stale PR #62 without merge and record `SUPERSEDED_BY_PR_64_AND_PR_65`.
5. Do not create another constitution or roadmap version for this decision.
6. Update the existing merged roadmap only when the next normal roadmap state
   update is otherwise required; until then this task and verdict control Cycle 4.
7. Dispatch Lane A and Lane B using the exact GitHub task-file links.

## Lane A control

Lane A may implement only the listed-fund cash-distribution semantics specified
in its task file.

The Manager must enforce:

```text
one small implementation PR
existing Portfolio, CorporateActionIdentity and event-loop paths only
no new module unless the task explicitly permits one focused test file
no corporate-action service, registry or framework
no ETF strategy implementation
no database/provider access
stop for full independent external review before merge
```

The Manager may not merge the semantic PR merely because CI is green.

## Lane B control

Lane B is a bounded read-only source qualification for exactly:

```text
510300.SH
511010.SH
518880.SH
```

It may evaluate explicit canonical sources per dataset. It may not:

```text
write the central database
import the recovery CSV
calculate returns, NAV or trend states
change the frozen ETF universe or ten-month rule
automatically choose or fuse sources
invent historical available_at
infer amount from close times volume
assume no suspension
fabricate daily limit values
```

A source matrix is complete only if it can support, without fabrication:

```text
raw execution OHLC
actual volume in SHARES
actual amount in CNY
product and listing identity
accepted calendar identity
suspension/non-trading handling
price-limit semantics
adjustment factors
cash-distribution events
source/retrieval/revision identity
row/snapshot identity
```

## Decision gate after both lanes

### Gate 1 — semantic PR accepted and source matrix complete

Only then may the Manager publish a separate, bounded central-data import task:

```text
append-only
new immutable snapshot
no overwrite or extension of v5
backup and rollback proof
unit-conversion tests
aggregate parity and duplicate checks
independent post-write acceptance
no strategy outcome
```

After the snapshot is accepted, publish a separate Cycle 4 PR A task for:

```text
definition
small adapter
focused tests
repeatable outcome-free preflight
```

### Gate 2 — source matrix incomplete

Close Cycle 4 as:

```text
CLOSED_DATA_AND_SEMANTIC_CONTRACT_INCOMPLETE_NO_OUTCOME
```

Do not change the three ETFs, ten-month rule, cash rule, costs, or gates to avoid
closure.

### Gate 3 — semantic PR rejected

Keep Cycle 4 blocked. Do not implement a strategy-specific workaround or use
adjusted prices to substitute for account-level distributions.

## Macro Risk Shadow

Macro Risk Shadow Phase 1 may start or continue independently under its existing
task file only if it remains:

```text
SHADOW_ONLY
NO_POSITION_EFFECT
NO_STRATEGY_SELECTION
NO_ORDER_OR_SIGNAL
NO_USE_AS_A_STRATEGY_GATE
```

It may not filter or rescue Cycle 4.

## Hard stop conditions

Stop and return `SCOPE_EXPANSION_REQUIRES_USER_APPROVAL` if any lane proposes:

```text
new provider framework
new database layer or schema platform
new event loop or Portfolio implementation
broader ETF universe
new trend parameter or strategy variant
automatic source fusion
backdated availability
result-driven contract relaxation
broker, paper, live or automatic execution
```

## Required Manager callbacks

### Callback A — audit packet and dispatch complete

```text
STATUS:
PR_68_STATUS:
PR_68_MERGE_COMMIT:
EXTERNAL_AUDIT_URL:
MANAGER_TASK_URL:
SEMANTIC_REPAIR_TASK_URL:
SOURCE_QUALIFICATION_TASK_URL:
PR_62_STATUS:
MACRO_SHADOW_STATUS:
BLOCKERS:
```

### Callback B — semantic repair PR ready for external review

```text
STATUS:
BASE_COMMIT:
PR_URL:
HEAD_SHA:
CHANGED_FILES:
RUNTIME_LINE_DELTA:
FOCUSED_TESTS:
FULL_CI_STATUS:
A_SHARE_ETF_DISTRIBUTION_TESTS:
US_REGRESSION_STATUS:
ZERO_STAMP_TAX_REGRESSION_STATUS:
OUTCOME_OR_DB_ACCESS:false
NEXT_ACTION:EXTERNAL_REVIEW
```

### Callback C — source qualification terminal

```text
STATUS:
QUALIFICATION_URL:
FIXED_SYMBOLS:510300.SH,511010.SH,518880.SH
SOURCE_MATRIX_COMPLETE:
RAW_OHLC:
VOLUME_SHARES:
AMOUNT_CNY:
LISTING_IDENTITY:
SUSPENSION_HANDLING:
LIMIT_SEMANTICS:
ADJUSTMENT_IDENTITY:
DISTRIBUTION_EVENTS:
HISTORICAL_AVAILABILITY_CLASSIFICATION:
DATABASE_WRITE:false
RETURNS_OR_NAV_OPENED:false
NEXT_ACTION:
```

## Final directive

Do not rush Cycle 4 into strategy implementation. The fastest valid path is:

```text
one narrow shared-semantic repair
+ one read-only source matrix
→ one bounded immutable snapshot, only if both pass
→ one lightweight PR A
```

Any other path is scope expansion or evidence fabrication.
