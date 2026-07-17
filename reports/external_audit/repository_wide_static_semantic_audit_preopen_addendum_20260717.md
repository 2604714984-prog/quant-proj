# Addendum — Shared Strict Pre-Open Boundary

Date: 2026-07-17  
Parent report: `repository_wide_static_semantic_audit_20260717.md`

This addendum supersedes only the scope description of finding H3 in the parent report.

## Corrected H3 scope

The exact-open equality defect is not limited to `run_static_rebalance()`.

The audited baseline uses a non-strict upper boundary in four shared paths:

```text
Event Loop rebalance
capacity assessment
universe evaluation
blocked-exit attempt validation
```

Each path rejects a timestamp later than the relevant session open but accepts a timestamp equal to the open.

The shared contract must consistently require:

```text
decision_at < relevant_session.open_at
```

For paths that also own a lower signal-close boundary, preserve:

```text
signal.close_at <= decision_at < execution.open_at
```

Required focused cases for all four paths:

```text
one microsecond before open -> accepted
open exactly -> rejected
one microsecond after open -> rejected
```

The implementation task controlling this correction is:

```text
reports/agent_handoff/shared_core_strict_preopen_task_20260717.md
```

This expanded scope does not increase the finding count. H3 remains one high-severity shared semantic finding.
