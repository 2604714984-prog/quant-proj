# Human-Gate Runbook

Human-Gate is the approval and boundary-control role for work that could change data, readiness, migration state, source-project promotion, or trading-adjacent posture.

Human-Gate records are required before execution for:

- physical repository migration;
- DuckDB or SQLite writes;
- schema migration;
- bulk data ingest or expansion;
- physical DB movement;
- registry activation;
- data-readiness status changes;
- strategy promotion into A-share or US-stock source repos;
- stage opening when the stage could be mistaken for recommendation or trading readiness;
- external audit submission;
- any broker, order, paper-trading, live-trading, or auto-execution adjacent request.

## Decision Record

Durable decisions live in:

- `reports/human_gate/decisions.jsonl`

Task-local copies or summaries may live in:

- `tasks/backlog/<task-id>/human_gate.md`

Each approval record must include:

- `decision_id`;
- `task_id`;
- `approved_by_user`;
- `decision`;
- `scope`;
- `allowed_paths`;
- `forbidden_paths`;
- `expires_at` or `one_time_use`;
- `requires_codex_dev_validation`;
- `requires_codex_audit`;
- `requires_chatgpt_external_audit`;
- explicit non-authorization boundaries.

## Decision Values

- `APPROVED_FOR_SCOPE`: approved only for the exact scope and paths listed.
- `DENIED`: not approved.
- `HOLD_FOR_CLARIFICATION`: cannot proceed until the user clarifies scope.
- `EXPIRED`: previous approval is no longer usable.

## Hard Rules

- Approval is not transferable across tasks.
- Approval is not a trading authorization.
- Approval to draft SQL is not approval to write a database.
- Approval to research a strategy is not approval to emit a recommendation ticket.
- Approval to prepare an external audit packet is not the external audit verdict.
- A missing Human-Gate record means not approved.

