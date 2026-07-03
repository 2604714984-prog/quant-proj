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

- `STANDING_APPROVAL`: durable user authorization for a category of work, still requiring per-task execution records.
- `APPROVED_FOR_SCOPE`: approved only for the exact scope and paths listed.
- `DENIED`: not approved.
- `HOLD_FOR_CLARIFICATION`: cannot proceed until the user clarifies scope.
- `EXPIRED`: previous approval is no longer usable.

## Standing Authorization

The user may grant standing authorization for repeated operational categories. Standing authorization reduces repeated confirmation prompts, but it does not remove task-level recordkeeping.

When a standing authorization exists, each actual execution still needs a task-level record in `reports/human_gate/decisions.jsonl` before the command runs. The execution record must include:

- task id;
- exact command or command family;
- database or registry path;
- source commit/tree or data snapshot;
- allowed write scope;
- stop conditions;
- validation expected after execution.

Standing authorization may cover:

- DuckDB or SQLite writes;
- schema migration;
- bulk data ingest or expansion;
- registry activation;
- data-readiness status changes;
- entering a real HITL ticket gate.

Standing authorization does not cover:

- broker API enablement;
- order routing or order submission;
- auto execution;
- paper trading;
- live trading;
- reading, printing, copying, or committing `.env` or secret values;
- moving raw DB/parquet/SQLite files into `quant-proj`;
- treating a HITL ticket as an approved trade.

## Hard Rules

- Approval is not transferable across unrelated scopes unless a standing authorization record explicitly covers that category.
- Approval is not a trading authorization.
- Approval to draft SQL is not approval to write a database unless a standing or task-level DB-write authorization exists.
- Approval to research a strategy is not approval to emit a HITL ticket unless a standing or task-level HITL-gate authorization exists.
- Approval to prepare an external audit packet is not the external audit verdict.
- A missing Human-Gate record means not approved.
