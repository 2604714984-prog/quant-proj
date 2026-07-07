# Task Packet Validation Rule

Status: active
Rule id: `TASK_PACKET_VALIDATION_V1`
Owner: `Quant-Dispatcher`

Use this rule before sending any task packet to a downstream agent.

## Required Files

Every dispatched task must include:

- `spec.md`
- `handoff.md`
- `human_gate.md`

Optional context files are allowed, but task packets must not include raw databases, parquet caches, `.env` files, API keys, raw payloads, broker credentials, or generated runtime data.

## Permission Check

Classify the task before dispatch:

- `L0_RESEARCH_DIAGNOSTIC`: read-only diagnosis, tests, reports, advisory review, or controller docs. No Human-Gate execution record is required.
- `RESEARCH_DATA_FAST_PATH`: bounded research-only public/no-secret network fetch, source-local research cache/staging/report/test write, or research cache rebuild. No per-task HG-EXEC is required; task scope, transcript, manifest/count/hash evidence, validation, and callback are required.
- `L1_CONTROLLED_DB_WRITE`: boundary-affecting DB write outside the research-data fast path.
- `L2_CONTROLLED_NETWORK_INGEST`: boundary-affecting provider/network ingest outside the research-data fast path.
- `L3_REGISTRY_READINESS_CHANGE`: any active registry activation, readiness status change, product-read route activation/replacement, or rollback-affecting active update.
- `L4_PENDING_HUMAN_REVIEW_TICKET`: any HITL ticket-gate entry or ticket emission attempt.

## Hard Gate

For any boundary-changing L1-L4 task, validation fails unless `human_gate.md` or `reports/human_gate/decisions.jsonl` already contains a unique pre-execution record with:

- `decision_id` beginning with `HG-EXEC-TASK-`;
- matching `task_id`;
- `decision=APPROVED_FOR_SCOPE`;
- exact permission level;
- bounded command or command family;
- allowed actions and paths;
- forbidden actions and paths;
- source commit/tree or snapshot;
- stop conditions;
- expected transcript, manifest, validation, and Codex acceptance.

Standing authorization does not satisfy this hard gate by itself.

## HOLD Rule

If a boundary-changing L1-L4 task lacks a unique pre-execution `HG-EXEC-TASK-*` record, do not send it as executable work. Mark it `HOLD_FOR_MISSING_HG_EXEC_TASK_RECORD` and use `reports/human_gate/templates/hg_exec_task_hold_example.json` as the shape for the hold note.

The downstream prompt may ask for a read-only plan or diagnosis, but it must explicitly forbid boundary-changing execution, registry activation, readiness change, ticket emission, product-route activation, secret handling, raw-data migration, and trading paths.

## Dispatch Checklist

Before sending:

- preserve the original ChatGPT task text in `tasks/inbox/`;
- create or update the task packet under `tasks/backlog/`;
- classify permission level;
- use research-data fast path for bounded research-only public/no-secret fetch/cache work;
- check for a unique `HG-EXEC-TASK-*` record when boundary-changing L1-L4 is requested;
- confirm project and agent boundary;
- confirm no broker/order/paper/live/auto, recommendation, trade plan, allocation, `.env`, or key-output scope is included;
- send prompt-only to Codex threads; do not pass model or thinking overrides;
- for Reasonix, use the fixed role session policy in `runbooks/reasonix_sessions.md`.

## Non-Authorization

Passing this validation only authorizes dispatch posture. It does not authorize recommendation, buy/sell advice, broker APIs, order routing, order submission, auto execution, paper trading, live trading, trade plans, entry prices, target weights, position sizing, allocation, `.env` reads, key output, secret handling, raw-data migration, or external-audit PASS.
