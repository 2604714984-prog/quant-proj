# Task — Shared-Core Strict Pre-Open Boundary

Date: 2026-07-17  
Repository: `2604714984-prog/quant-proj`  
Status: `AUTHORIZED_ONLY_AFTER_PR_69_CLOSURE`

## Start gate

Read:

1. `reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md`
2. `reports/external_audit/repository_wide_static_semantic_audit_20260717.md`
3. `reports/agent_handoff/manager_repository_wide_audit_followup_task_20260717.md`
4. `AGENTS.md`

Do not start until:

```text
PR_69=CLOSED_WITHOUT_MERGE
CYCLE_4=CLOSED_DATA_AND_SEMANTIC_CONTRACT_INCOMPLETE_NO_OUTCOME
```

Start from the then-current `v2-main` and record its exact commit and tree.

## Mandatory correction

Four shared paths currently accept a decision timestamp equal to the relevant session open:

```text
Event Loop
capacity assessment
universe evaluation
blocked-exit validation
```

All four must require a timestamp strictly earlier than the relevant open.

Required boundary cases:

```text
one microsecond before open: accepted
open exactly: rejected
one microsecond after open: rejected
```

Where the path also owns a signal-close lower bound, preserve acceptance at the close and reject a timestamp before it.

Do not change any frozen strategy timestamp.

## Allowed files

```text
src/quant_system/backtest/event_loop.py
src/quant_system/backtest/capacity.py
src/quant_system/backtest/blocked_orders.py
src/quant_system/markets/universe.py
focused existing test modules for those four paths
```

No other runtime file is authorized.

## Forbidden scope

```text
listed-fund distribution support
corporate-action date changes
product identity changes
strategy logic
data access or database mutation
historical or prospective results
new framework or service
```

## Validation

Run focused tests, the full suite, Ruff, `git diff --check`, wheel build, and installed CLI smoke. Keep runtime growth minimal.

Keep the PR unmerged pending independent external review.

## Callback

```text
STATUS:
BASE_COMMIT:
PR_URL:
HEAD_SHA:
CHANGED_FILES:
RUNTIME_NET_LINE_DELTA:
EVENT_LOOP_BOUNDARY_TESTS:
CAPACITY_BOUNDARY_TESTS:
UNIVERSE_BOUNDARY_TESTS:
BLOCKED_EXIT_BOUNDARY_TESTS:
FULL_TEST_COUNT:
CI_STATUS:
OUTCOME_OR_DB_ACCESS:false
STRATEGY_CANDIDATE_AVAILABLE:false
NEXT_ACTION:EXTERNAL_REVIEW
```
