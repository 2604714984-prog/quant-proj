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

Recorded execution uses `runbooks/recorded_execution_mode.md`. L1-L4 work is allowed only when the Human-Gate record, command transcript, bounded command flags, manifest/status evidence, and Codex acceptance requirements are satisfied.

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
- `permission_level`;
- `scope`;
- `allowed_actions`;
- `allowed_paths`;
- `forbidden_paths`;
- command flag requirements such as `requires_allow_network` or `requires_allow_write` when applicable;
- `expires_at` or `one_time_use`;
- `requires_codex_acceptance`;
- `requires_codex_dev_validation`;
- `requires_codex_audit`;
- `requires_chatgpt_external_audit`;
- explicit non-authorization boundaries.

## Permission Levels

- `L0_RESEARCH_DIAGNOSTIC`: allowed by default; no DB write, network ingest, registry activation, readiness change, or ticket emission.
- `L1_CONTROLLED_DB_WRITE`: requires Human-Gate record, `--allow-write`, explicit snapshot id, command transcript, manifest/counts/hashes, and Codex acceptance.
- `L2_CONTROLLED_NETWORK_INGEST`: requires Human-Gate record, `--allow-network`, explicit provider, bounded date/symbol scope, no `.env` read, no key output, command transcript, and Codex acceptance.
- `L3_REGISTRY_READINESS_CHANGE`: requires Human-Gate record, old/new diff, rollback path, command transcript, and Codex acceptance. Broker/live/auto readiness remains forbidden.
- `L4_PENDING_HUMAN_REVIEW_TICKET`: requires Human-Gate record and all gates passing; may emit only `PENDING_HUMAN_REVIEW`, never orders, trade plans, allocations, fills, or execution instructions.

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

## Recorded Execution Record Template

Use this shape for L1-L4 execution records:

```json
{
  "decision_id": "HG-YYYYMMDD-XXX",
  "task_id": "TASK-ID",
  "approved_by_user": true,
  "decision": "APPROVED_FOR_SCOPE",
  "permission_level": "L1_CONTROLLED_DB_WRITE | L2_CONTROLLED_NETWORK_INGEST | L3_REGISTRY_READINESS_CHANGE | L4_PENDING_HUMAN_REVIEW_TICKET",
  "scope": "exact bounded scope",
  "allowed_actions": ["network_ingest", "duckdb_write"],
  "allowed_paths": ["target database or output paths"],
  "forbidden_paths": [".env", "broker/", "live/", "order/"],
  "provider": "nasdaq_api | yahoo_chart | tushare | baostock | none",
  "max_symbols": 300,
  "max_rows": null,
  "snapshot_id_prefix": "example_YYYYMMDD",
  "requires_allow_network": true,
  "requires_allow_write": true,
  "requires_command_transcript": true,
  "requires_manifest_counts_hashes": true,
  "requires_codex_acceptance": true,
  "requires_codex_audit": false,
  "requires_chatgpt_external_audit": false,
  "one_time_use": true,
  "expires_at": "YYYY-MM-DDTHH:MM:SS+08:00",
  "non_authorization": "No broker, no order routing, no auto execution, no paper/live trading, no trade plan."
}
```

## Hard Rules

- Approval is not transferable across unrelated scopes unless a standing authorization record explicitly covers that category.
- Approval is not a trading authorization.
- Approval to draft SQL is not approval to write a database unless a standing or task-level DB-write authorization exists and recorded execution requirements are satisfied.
- Approval to research a strategy is not approval to emit a HITL ticket unless a standing or task-level HITL-gate authorization exists and L4 gates pass.
- Approval to prepare an external audit packet is not the external audit verdict.
- A missing Human-Gate record means not approved.
- Human-Gate approval never authorizes broker APIs, order routing, order submission, system-generated orders, system-generated fills, broker-synced fills, auto execution, paper trading, live trading, trade plans, entry price instructions, target weights, position sizing, or allocation.
