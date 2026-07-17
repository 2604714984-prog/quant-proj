# Manager Task — Repository-Wide Audit Closure and Next-Step Control

Date: 2026-07-17  
Repository: `2604714984-prog/quant-proj`  
Default branch: `v2-main`  
Status: `AUTHORIZED_COORDINATION_ONLY`

## Authority

Read in this order:

1. `reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md`
2. `reports/agent_handoff/user_dispatch_manager_v2_post_audit_roadmap_v2_20260716.md`
3. `AGENTS.md`
4. `reports/external_audit/repository_wide_static_semantic_audit_20260717.md`
5. this task

This task integrates the repository-wide risk-based audit with the current Cycle 4 work. It authorizes repository closure, one narrow shared-core repair dispatch, and continued read-only Macro Risk Shadow. It does not authorize a new strategy family, data import, outcome run, prospective access, synthesizer, or trading path.

## Controlling audit state

```text
AUDITED_MAIN=e4e0c1538ad73eca5a6900aabd903e9fba8ed15a
PR_69_HEAD=e68d14f86122831139f1f22b84e5792b8351ef50
PR_70_HEAD=be3afc5a6220e155285b80aedebeb29742f201d8
ARCHITECTURE=ACCEPTED_LIGHTWEIGHT
CRITICAL_FINDINGS=0
HIGH_FINDINGS=3
MEDIUM_FINDINGS=2
VALIDATED_SPECIALIST_COUNT=0
STRATEGY_CANDIDATE_AVAILABLE=false
```

## Required repository actions

Execute in this order.

### 1. Accept the Cycle 4 terminal data evidence

PR #70 may be merged as terminal, aggregate-only source-qualification evidence if its exact head and one-file scope remain unchanged.

Record:

```text
CYCLE_4=CLOSED_DATA_AND_SEMANTIC_CONTRACT_INCOMPLETE_NO_OUTCOME
SOURCE_MATRIX_COMPLETE=false
OUTCOME_STATUS=NOT_RUN
FORWARD_STATUS=CLOSED
STRATEGY_CANDIDATE_AVAILABLE=false
```

Do not alter the fixed ETF universe, ten-month trend rule, cash rule, costs, or gates.

### 2. Close PR #69 without merge

PR #69 must not enter `v2-main` now.

Reasons:

```text
valid Chinese ETF record-date/ex-date ordering is rejected
listed-fund status is inferred from Portfolio flags rather than source-bound product identity
Cycle 4 has no complete source matrix and cannot use the feature
merging dormant shared-core functionality would violate the lightweight boundary
```

Preserve exact head:

```text
e68d14f86122831139f1f22b84e5792b8351ef50
```

Record:

```text
PR_69=CLOSED_WITHOUT_MERGE
REASON=BLOCKED_BY_REAL_DATE_CONTRACT_PRODUCT_IDENTITY_AND_NO_ACTIVE_CONSUMER
```

Do not repair PR #69 in place merely to keep it alive.

### 3. Dispatch one narrow shared-core repair

Only after PR #69 is closed, dispatch the task:

```text
reports/agent_handoff/shared_core_strict_preopen_and_action_identity_task_20260717.md
```

The implementation must start from the then-current `v2-main` and obey the file and scope limits in that task.

The strict decision-before-open correction is mandatory.

Global cross-action event-ID uniqueness may be included only if it remains a small, well-tested change. Do not add listed-fund distribution support in that PR.

The shared-core PR requires independent external review before merge.

### 4. Preserve future activation gates

Record these findings in the existing roadmap or failure memory only when the next normal state update occurs. Do not create another governance document.

```text
FUTURE_LISTED_FUND_GATE_1:
allow valid market-specific record/ex/pay ordering

FUTURE_LISTED_FUND_GATE_2:
require explicit source-bound product identity

FUTURE_CORPORATE_ACTION_GATE:
global cross-type event-ID uniqueness

FUTURE_US_MIXED_CONSIDERATION_GATE:
explicit basis allocation or fail closed
```

Do not modify frozen historical evidence.

### 5. Macro Risk Shadow

Macro Risk Shadow may start or continue only under its existing contract:

```text
SHADOW_ONLY
NO_POSITION_EFFECT
NO_STRATEGY_SELECTION
NO_ORDER_OR_SIGNAL
NO_USE_AS_A_STRATEGY_GATE
```

It may not filter or rescue any closed family.

### 6. Next strategy-family selection

Do not immediately implement another adapter.

Before a new family is authorized:

1. Publish one page freezing the economic hypothesis, universe, variants, minimum event/portfolio requirements, and data fields.
2. Run one aggregate, outcome-free feasibility scan.
3. Do not emit returns, NAV, rankings, symbols, or performance gates.
4. If the frozen rule cannot generate the required events or portfolio, close it before implementation.
5. Only a feasibility PASS permits a 100–300-line adapter task.

The Manager must return the proposed next-family slate to the user before authorizing code.

## Prohibited actions

```text
merging PR #69
importing the recovery CSV
changing Cycle 4 assets or parameters
adding an ETF-specific workaround to a strategy adapter
creating a product registry or corporate-action service
repairing closed legacy modules for reuse
adding a new control constitution, roadmap layer, runner, engine, or database layer
opening outcomes or prospective data
building a strategy synthesizer
opening broker, paper, live, or automatic execution
```

If proposed, return:

```text
SCOPE_EXPANSION_REQUIRES_USER_APPROVAL
```

## Required callbacks

### Callback A — repository closure

```text
STATUS:
V2_MAIN_HEAD:
PR_70_STATUS:
PR_70_MERGE_COMMIT:
CYCLE_4_STATUS:
PR_69_STATUS:
PR_69_PRESERVED_HEAD:
MACRO_SHADOW_STATUS:
BLOCKERS:
```

### Callback B — shared-core repair dispatched

```text
STATUS:
TASK_FILE_URL:
BASE_COMMIT:
ALLOWED_FILES:
STRICT_PREOPEN_FIX_REQUIRED:true
GLOBAL_ACTION_ID_FIX_INCLUDED:
LISTED_FUND_FEATURE_INCLUDED:false
EXTERNAL_REVIEW_REQUIRED:true
NEXT_ACTION:
```

### Callback C — next-family feasibility proposal

```text
STATUS:
PROPOSED_FAMILY:
ECONOMIC_HYPOTHESIS:
REQUIRED_DATA_FIELDS:
FROZEN_VARIANTS:
MINIMUM_FEASIBILITY_REQUIREMENTS:
OUTCOME_ACCESS:false
ADAPTER_IMPLEMENTATION_AUTHORIZED:false
USER_DECISION_REQUIRED:true
```

## Final directive

The project remains healthy and lightweight. Close unusable work rather than preserving optional functionality.

The immediate valid path is:

```text
accept PR #70 terminal evidence
→ close Cycle 4
→ close PR #69
→ one tiny shared-core cutoff repair
→ outcome-free feasibility before any next adapter
```
