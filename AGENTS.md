# Workspace Agent Rules

This is a personal, research-only quant workspace. Keep the controller small.

## Hard boundaries

1. Never read, print, copy, log, or commit `.env` files or credential values.
2. Do not commit databases, raw payloads, caches, generated outputs, or logs.
3. Do not enable broker APIs, orders, paper/live trading, auto execution, or
   actionable buy/sell advice.
4. Research or data readiness is not strategy or trading readiness.
5. Preserve repository history and existing audit evidence.

## Routine work

Use the shortest path that safely completes the change:

```text
one GitHub issue -> one branch/PR -> focused CI -> short closeout
```

Routine work does not require an inbox copy, a per-task packet folder, a fixed
callback UUID, a fixed model, or a second acceptance pass. Keep scope and tests
in the issue or PR. Runtime repositories should have no more than two required
PR jobs unless a reproduced defect justifies another.

## Elevated controls

Use explicit authorization and independent review only when a task materially
changes one of these boundaries:

- research-engine or backtest semantics;
- data provenance, PIT availability, provider acquisition, or schema contracts;
- central database writes, destructive operations, migration, or rollback;
- strategy intake, candidate promotion, or an execution-stage boundary.

For elevated work, record only the evidence needed for that risk: exact scope,
immutable refs, validation, and rollback where mutation is involved. Do not
turn those controls into a mandatory framework for routine edits.

## Roles

- The Manager owns scope, priority, and boundary decisions.
- The implementation agent owns the code, tests, and PR.
- A separate read-only reviewer is optional for routine work and required only
  when an elevated boundary calls for it.
- External audit is reserved for the elevated boundaries above, not routine
  controller bookkeeping.

Historical task packets, callbacks, and model-routing records remain evidence.
They are not active requirements for new routine work.
