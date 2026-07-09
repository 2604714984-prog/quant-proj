# TASK-023 Handoff

To: `Codex-Dev`
Target project: `/Users/rongyuxu/Desktop/US_Stock_Monitor`
Task: `US DB preflight blocker repair`

## Base Evidence

- TASK-006 commit: `f3b3b10b6cb70babe47e1e44fad490e9f9366b17`
- TASK-006 tree: `68670cd858cffbec553f76af390db8f823112565`
- attempted snapshot: `us_expand_20260704_nasdaq_300`
- result: `INGEST_PREFLIGHT_BLOCKED`
- rows written: `0`
- network fetch: not run
- DuckDB write: not run
- blockers: `BLOCKED_BY_EXISTING_DB_DUPLICATES`, `BLOCKED_BY_SYMBOLS_MISSING_FROM_METADATA`

## Work

Repair or document the preflight blockers so a future separately authorized US expansion attempt can run cleanly. Default to read-only diagnostics and helper hardening.

## Must Return

- status: `ACCEPTED`, `ACCEPTED_WITH_WARNINGS`, or `REJECTED`
- duplicate summary
- missing metadata symbol summary
- read-only dry-run output
- validation results
- changed files
- commit/tree if committed
- explicit non-authorization boundary

## Boundary

No network ingest or DB write unless a new task-level `HG-EXEC-TASK-*` record exists before execution. No product route activation, no recommendation, no ticket, no broker/order/paper/live/auto.
