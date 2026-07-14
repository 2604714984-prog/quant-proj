# Task Dispatch Runbook

## Routine flow

Use one GitHub issue, one implementation PR, focused CI, and one short
closeout. The issue or PR is the task record; do not duplicate it into an inbox
file or task-packet folder.

The issue should state:

- target repository and outcome;
- bounded scope and important non-scope;
- validation commands;
- any user decision still needed.

The closeout should state changed files, test results, remaining limitations,
and the PR or commit. No fixed callback UUID, model binding, gate manifest, or
separate acceptance record is required for routine work.

## Routine implementation sequence

1. Confirm the current default branch and create a clean branch or worktree.
2. Make the smallest change that closes the issue.
3. Run focused tests, formatting/static checks, and `git diff --check`.
4. Push one PR. Keep required CI to at most two jobs unless a reproduced defect
   demonstrates a need for another.
5. Post a concise closeout and stop.

An implementation agent may ask for a read-only review when evidence is
unclear. Do not require a duplicate reviewer after deterministic checks already
establish the result.

## Elevated work

Use a separate scoped authorization or review record only for material changes
to:

- research-engine, allocator, fill, cost, or backtest semantics;
- provider acquisition, data provenance, PIT availability, or schema identity;
- central database writes, destructive operations, migration, backup, or
  rollback;
- strategy intake, candidate/readiness promotion, or execution boundaries.

For elevated work, capture the minimum evidence needed for the risk. A task
packet under `tasks/` is optional unless the authorization itself needs a
durable machine-readable record. Existing validators may be used for those
elevated records; they are not prerequisites for ordinary work.

Human approval remains mandatory for destructive DB actions, secret-handling
scope changes, readiness/product-route activation, and any trading-adjacent
boundary. Broker/order/paper/live/auto execution remains forbidden.

## External review

External review is appropriate for engine semantics, data/PIT/schema changes,
destructive DB work, strategy intake, or a future execution-stage opening. Do
not create an external-audit packet for ordinary fixes, blocked research, queue
maintenance, or controller documentation.

## Historical records

Do not rewrite old task packets, callback envelopes, or audit evidence. Their
model names, UUIDs, and multi-stage acceptance paths describe prior work only.
