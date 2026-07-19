# Manager Task — Post-PR #94 Result-First Research Program

Date: 2026-07-19  
Repository: `2604714984-prog/quant-proj`  
Authority: user-dispatched, subordinate to the Manager Control Constitution V2

Read first:

```text
reports/external_audit/pr94_terminal_and_result_first_research_program_20260719.md
```

## 1. Required closure sequence

1. Confirm PR #94 still points to:

```text
7cfe3b5a37e9d244c43465782eeb4d888f5429ba
```

2. Merge PR #94 only at that exact head.

3. Record the terminal state:

```text
US_SPY_CLASSIC_TURN_OF_MONTH_V1_20260719
= RETROSPECTIVE_REPLICATION_FAIL_CLOSED
```

4. Do not rerun, retune or relabel the lineage.

5. Merge the documentation-only post-PR #94 research-program PR after CI and scope review.

6. Dispatch exactly one code-writing task:

```text
reports/agent_handoff/us_spy_qqq_gld_dual_momentum_result_task_20260719.md
```

## 2. Project resource allocation

Until a historical US PASS is obtained:

```text
80% direct numerical strategy result sprints
15% bounded input qualification required by the active sprint
5% repository maintenance
0% new architecture, Qlib, RD-Agent, broker, Paper or auto-trading work
```

## 3. One active family

After dispatch:

```text
PRIMARY_RESEARCH_MARKET=US
ACTIVE_FAMILY=US_SPY_QQQ_GLD_DUAL_MOMENTUM_V1_20260719
ACTIVE_STAGE=DIRECT_RESULT_SPRINT
VALIDATED_SPECIALISTS=0
STRATEGY_CANDIDATE_AVAILABLE=false
```

No other code-writing strategy conversation may be active.

## 4. Completion standard

The next substantive PR is complete only if it contains:

```text
frozen definition
calculation implementation
focused tests
one aggregate result JSON
one immutable run receipt
numeric PASS / FAIL / INPUT_BLOCKED
```

The following are not completion:

```text
candidate slate
Phase 0 report
data-gap memo
new roadmap
provider recommendation
implementation without a result
```

## 5. PR and code budget

For the dual-momentum sprint:

```text
one PR only
one variant only
no parameter grid
no separate feasibility PR
no separate result PR
no new framework
preferred calculation module <= 250 lines
preferred one-use runner <= 300 lines
preferred focused tests <= 200 lines
```

If input identity fails before outcomes, publish one concise `INPUT_BLOCKED` result in the same PR and close.

## 6. Review policy

```text
ordinary correctly computed FAIL:
CI + Manager scope check + terminal merge

first historical PASS:
keep PR unmerged and request exact-head external review

shared financial-semantic change:
request external review before merge
```

Do not request a full external audit for another ordinary negative result unless calculation correctness is disputed.

## 7. Queued lanes

Do not dispatch concurrently.

```text
1. US_SPY_QQQ_GLD_DUAL_MOMENTUM_V1_20260719
2. US_SPY_QQQ_GLD_INVERSE_VOLATILITY_V1
3. US_SPY_GLD_STRESS_SAFE_HAVEN_V1
```

After each terminal result:

```text
FAIL -> dispatch next lane
PASS -> external review, then Shadow decision
INPUT_BLOCKED -> close and dispatch next lane unless the repair is a narrow input-identity defect
```

## 8. Parallel data lane

One read-only data-maintenance conversation may run in parallel for at most 10 working days to determine whether a survivor-aware US stock panel can be obtained from one canonical provider.

It must not block ETF strategy results and must not build a provider-fusion platform.

## 9. Required Manager callback

```text
STATUS:
PR_94_MERGE_COMMIT:
PR_94_TERMINAL_STATUS:
POST_PR94_PLAN_PR_URL:
POST_PR94_PLAN_MERGE_COMMIT:
ACTIVE_FAMILY:
DUAL_MOMENTUM_TASK_URL:
CODE_WRITING_CONVERSATION_DISPATCHED:
PARALLEL_DATA_LANE_STATUS:
NEXT_EXPECTED_DELIVERABLE:
BLOCKERS:
```

`NEXT_EXPECTED_DELIVERABLE` must be:

```text
one numerical dual-momentum result PR
```
