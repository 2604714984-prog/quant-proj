# Manager Task — Close PR #85 Rework and Coordinate PR #84

Date: 2026-07-18  
Status: `USER_DISPATCH_AFTER_JOINT_EXTERNAL_AUDIT`

Read first:

```text
reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md
reports/external_audit/pr84_pr85_joint_external_audit_20260718.md
```

## Authority boundary

```text
one active code-writing family=Relative Variance only
architecture expansion=forbidden
new provider/database work=forbidden
historical outcome=not yet authorized
holdout and forward=closed
strategy_candidate_available=false
```

## Part 1 — Correct PR #85

Modify only the compact roadmap. Do not change the accepted price-volume feasibility JSON.

Required text changes:

1. Restore the controlling constitution to the precedence chain.
2. Replace the ambiguous `high-prior` budget with a prospective all-lane budget:

```text
budget_effective_from=PR_85_MERGE_COMMIT
maximum_additional_research_lanes=2
consumed_after_effective_commit=0
remaining_additional_research_lanes=2
```

Every new economic hypothesis counts when opened, even if it closes at feasibility or preflight. Data-only maintenance and Macro Risk Shadow do not count.

After correction:

```text
run exact-head CI
request delta review
merge PR #85 first only after acceptance
```

## Part 2 — Coordinate PR #84

After PR #85 merges:

1. Rebase PR #84 onto current `v2-main`.
2. Remove PR #84's roadmap modification completely.
3. Dispatch the separate Relative Variance rework task:

```text
reports/agent_handoff/relative_variance_pr84_narrow_rework_20260718.md
```

4. Do not authorize validation until that task is complete and externally delta-reviewed.
5. Do not allow changes to formula, windows, cost, alpha, split, or gates.

## Part 3 — After PR #84 acceptance

Authorize only the 2022-2023 validation screen.

```text
validation PASS -> return for external review before holdout
validation FAIL -> close permanently
INPUT_BLOCKED -> repair only a concrete input/semantic defect; no hypothesis change
```

Retrospective holdout remains unopened until a separate accepted validation PASS. Prospective forward remains closed.

## Part 4 — Next research queue

Do not start a second code-writing family while Relative Variance is open.

After Relative Variance closes or enters the validation-review gate:

```text
priority 1: low abnormal-turnover / anti-speculation input identity feasibility
priority 2: one final user-selected high-prior lane
```

For each future lane:

```text
one-page frozen hypothesis
aggregate outcome-free feasibility before adapter
one primary variant plus at most one robustness variant
one role-specific primary endpoint
ordinary FAIL closes without full architecture review
```

Macro Risk remains Shadow-only with no position or strategy-selection effect. No synthesizer until two independently passing families have prospective Shadow evidence.

## Required callback

```text
STATUS:
PR_85_NEW_HEAD:
PR_85_PRECEDENCE_FIXED:
PR_85_BUDGET_FIXED:
PR_85_CI:
PR_85_MERGE_COMMIT:
PR_84_REBASED_HEAD:
PR_84_ROADMAP_FILE_REMOVED:
RELATIVE_VARIANCE_TASK_DISPATCHED:
HISTORICAL_VALIDATION_AUTHORIZED:false
ACTIVE_CODE_WRITING_FAMILY:
ADDITIONAL_RESEARCH_LANES_REMAINING:
BLOCKERS:
NEXT_ACTION:
```
