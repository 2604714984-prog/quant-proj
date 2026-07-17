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

Do not start until the Manager confirms:

```text
PR_69=CLOSED_WITHOUT_MERGE
CYCLE_4=CLOSED_DATA_AND_SEMANTIC_CONTRACT_INCOMPLETE_NO_OUTCOME
```

Start from the then-current `v2-main` and record the exact base commit and tree.

## Mandatory fix

The shared Event Loop currently permits a decision timestamp equal to the next execution-session open. Change the boundary so the decision satisfies:

```text
signal.close_at <= decision_at < execution.open_at
```

The exact execution-open timestamp must fail closed.

Required tests:

```text
one microsecond before signal close -> rejected
signal close exactly -> accepted
one microsecond before next open -> accepted
next open exactly -> rejected
one microsecond after next open -> rejected
```

Do not alter any frozen strategy timestamp.

## Optional small hardening

The Portfolio currently keeps separate applied-ID sets for distributions, splits, and terminal actions. If it remains a small change, enforce event-ID uniqueness across action types and add cross-type collision tests.

If this would require a registry, serialization migration, or broad refactor, report it as deferred.

## Allowed files

Mandatory scope:

```text
src/quant_system/backtest/event_loop.py
tests/test_event_loop.py
```

Optional action-ID scope:

```text
src/quant_system/backtest/portfolio.py
tests/test_backtest_core.py
```

No other runtime files are authorized.

## Forbidden scope

```text
listed-fund distribution implementation
CorporateActionIdentity date-rule changes
new product identity type
strategy logic
new framework or database layer
data access or database mutation
historical or prospective result access
```

## Validation

```text
focused tests
full repository tests
Ruff
git diff --check
wheel build
installed CLI smoke
small runtime line delta
```

Keep the PR unmerged pending independent external review because the execution-time boundary is shared financial semantics.

## Callback

```text
STATUS:
BASE_COMMIT:
PR_URL:
HEAD_SHA:
CHANGED_FILES:
RUNTIME_NET_LINE_DELTA:
STRICT_PREOPEN_TESTS:
GLOBAL_ACTION_ID_FIX:INCLUDED|DEFERRED
GLOBAL_ACTION_ID_TESTS:
FULL_TEST_COUNT:
CI_STATUS:
OUTCOME_OR_DB_ACCESS:false
STRATEGY_CANDIDATE_AVAILABLE:false
NEXT_ACTION:EXTERNAL_REVIEW
```
