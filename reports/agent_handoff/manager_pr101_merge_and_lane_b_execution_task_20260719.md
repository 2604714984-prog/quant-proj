# Manager task — PR #101 closure and Lane B result execution

Date: 2026-07-19  
Repository: `2604714984-prog/quant-proj`  
Controlling audit: `reports/external_audit/pr101_exact_head_audit_and_lane_b_research_plan_20260719.md`

## Objective

Close the current review point and produce the next actual numerical result without opening a new strategy shortlist or architecture project.

## Controlling verdict

```text
PR_101_HEAD=70f1acf97a80b3a0da0d4c7bf06c1e23bab3b14e
VERDICT=ACCEPT_EXACT_HEAD_WITH_FORWARD_ONLY_CLARIFICATION
REVIEW_ID=4731100512
```

## Part 1 — PR #101 disposition

1. Confirm the PR HEAD is unchanged.
2. Confirm exact-head CI is green.
3. Mark PR #101 Ready.
4. Merge PR #101.
5. Return the merge commit.
6. Do not edit the checkpoint merely to restate the external review.

If the HEAD changed, stop and request incremental review.

## Part 2 — Freeze current program state

Record:

```text
RECENT_FORMAL_US_RETROSPECTIVE_OUTCOMES=5
VALIDATED_SPECIALISTS=0
STRATEGY_CANDIDATE_AVAILABLE=false
ACTIVE_RESEARCH_LINEAGE=US_SCHEDULED_EVENT_ATLAS_DEVELOPMENT_V1
ACTIVE_ROUTE=LANE_B_DAILY_SCHEDULED_EVENTS
ACTIVE_CODE_WRITING_FAMILY=none
```

Do not reopen PRs #93, #94, #96, #98 or #100.

Do not rank their gate counts.

Do not start another SPY/QQQ/GLD allocation strategy.

## Part 3 — Dispatch one data-only task

Publish or directly dispatch:

```text
reports/agent_handoff/us_lane_b_m3_input_materialization_task_20260719.md
```

This is the only authorized active task until it returns.

The task may:

```text
retrieve official public source material
write a versioned local evidence bundle outside Git
create narrow parser code and focused tests
create aggregate manifests and hashes in Git
read the existing SPY development slice
```

The task may not:

```text
calculate any strategy or event return
read 2010-or-later event outcomes
write canonical DuckDB
create a new database layer
create a Provider framework
create a strategy module
open Validation or Holdout
```

## Part 4 — M3 mechanical decision

When the data task returns, accept only one of:

```text
M3_INPUT_QUALIFIED
M3_INPUT_BLOCKED
```

### If qualified

Create one narrow result task using the already merged PR #97 definition.

The result task must:

```text
use 1994-2009 only
run once
publish aggregate M3 development metrics
preserve the frozen eight-test family
assign p=1 to blocked mechanisms
stop at PASS / FAIL / INPUT_BLOCKED
```

No new formula or parameter is allowed.

### If blocked

Record the exact blocker and move to M6/M7 input materialization.

Do not create a substitute event or daily proxy.

## Part 5 — M6/M7 sequence

After M3 reaches a terminal point:

1. Materialize exact monthly expiration identities.
2. Materialize exact quarterly options/futures expiration identities.
3. Reconcile to the accepted XNYS calendar.
4. Run each qualified mechanism once.

M4/M5 controls may be materialized afterwards or in parallel by a read-only data subagent, but they cannot become promoted strategies.

## Part 6 — Lane A/C budget decision

Create no minute-data platform.

Use the combined cap:

```text
USD 400
5 working days
```

Return either:

```text
EXACT_MINUTE_DATA_ROUTE_ACCEPTED
```

or:

```text
TERMINAL_DATA_UNAVAILABLE_WITHIN_BUDGET_NO_OUTCOME
```

Do not purchase data before sample-day verification.

## Part 7 — Future result queue

After Lane B is terminal, use this order:

```text
1. SPY overnight versus intraday
2. SPY pre-holiday effect
3. HYG/LQD credit stress, if adjusted identities qualify
4. survivor-aware 52-week-high mechanism
5. residual reversal
6. PEAD after filing-time qualification
```

Only one code-writing mechanism may be active.

## Forward evidence rule

The 2010-2017 and 2018-2026-06 periods are secondary evidence only.

A historical PASS may be submitted for exact-head review and then, under a separate authorization, enter zero-capital prospective Shadow from post-cutoff events.

It cannot by itself create candidate, Paper, live or funded status.

## Overdesign stop conditions

Stop and return `SCOPE_EXPANSION_REQUIRES_USER_APPROVAL` if any task proposes:

```text
new database layer
new Provider framework
new runner framework
new evidence framework
Qlib or RD-Agent
Broker or Paper integration
parallel strategy implementations
parameter grid
new ETF allocation variant
canonical DuckDB write without separate authority
```

## Required callback A — PR #101 closure

```text
STATUS:
PR_101_HEAD:
PR_101_MERGE_COMMIT:
EXACT_HEAD_CI:
ACTIVE_RESEARCH_LINEAGE:
ACTIVE_ROUTE:
NEXT_TASK_URL:
BLOCKERS:
```

## Required callback B — M3 input

```text
STATUS:
EVIDENCE_BUNDLE_ID:
FOMC_EVENT_COUNT:
FOMC_EVENT_YEARS:
ACCEPTED_XNYS_SESSION_COUNT:
SPY_SESSION_COUNT:
CALENDAR_DIFFERENCE_COUNT:
COMPLETE_M3_EVENT_COUNT:
M3_COMPLETENESS:
M3_INPUT_QUALIFIED:
MANIFEST_URL:
NEXT_ACTION:
```

## Required callback C — M3 result

```text
STATUS:
RESULT_STATUS:
EVENT_COUNT:
YEAR_COUNT:
MEAN_15BPS:
MEAN_30BPS:
BOOTSTRAP_LOWER_BOUND:
RAW_P:
HOLM_ADJUSTED_P:
LARGEST_EVENT_CONTRIBUTION:
LARGEST_YEAR_CONTRIBUTION:
GATES:
RESULT_URL:
RUN_RECEIPT_URL:
STRATEGY_CANDIDATE_AVAILABLE:false
NEXT_ACTION:
```
