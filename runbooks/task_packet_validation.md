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

New task packets must also include the metadata block defined in
`prompts/task_dispatcher.md`: model role, exact model/effort, immutable source
commit/tree for Codex implementation, automated-gate commands, current callback
target, acceptance role, and a hashed context delta. Codex implementation
packets include concrete `context_delta.md` and automated-gate command files
inside the task packet directory; placeholders fail closed. Acceptance packets
also reference the green gate by path and hash and declare read-only mode.
Dedicated strategy research packets additionally bind `EXECUTION_THREAD_ID:
019f3881-5293-74a1-8535-814bd83c8681` and `EXECUTION_THREAD_TITLE: Strategy
Work — Sol Research`, with manager callback target
`019f4c70-cac3-7211-8e04-47b8b51c819e`.

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
- record `MODEL_ROLE`, exact model, and reasoning effort in every Codex handoff;
- use `gpt-5.6-sol`/`high` for coordination, allowed evidence escalation, or
  the exact `strategy_research_executor` role scoped to `TARGET_PROJECT:
  strategy_work`;
- use `gpt-5.6-luna`/`medium` for normal execution and rework;
- bind the dedicated strategy research thread with
  `RECOMMENDED_AGENT: strategy_research_executor`, `MODEL_ROLE:
  strategy_research_executor`, `MODEL: gpt-5.6-sol`, and
  `REASONING_EFFORT: high`; never label that thread as `dispatcher`;
- use a separate read-only `gpt-5.6-luna`/`high` context for final acceptance;
- require an `AUTOMATED_GATE` JSON manifest before Luna acceptance and validate
  it with `python3 scripts/validate_automated_gate_manifest.py <manifest>`; the
  gate role/model must exactly match the task packet;
- route deterministic failures, missing fields, formatting errors, and
  tool/environment failures back to the task's bound executor rather than to
  evidence escalation;
- send normal Luna executor callbacks to the currently resolved dispatcher task
  id; for the reserved `Strategy Work — Sol Research` binding only, send the
  callback to Quant Manager `019f4c70-cac3-7211-8e04-47b8b51c819e` and then
  route green evidence to independent Luna acceptance;
- for Reasonix, use the fixed role session policy in `runbooks/reasonix_sessions.md`.

Run the machine validator before any new dispatch:

```bash
python3 scripts/validate_task_packet.py tasks/backlog/<task-id>
```

## Non-Authorization

Passing this validation only authorizes dispatch posture. It does not authorize recommendation, buy/sell advice, broker APIs, order routing, order submission, auto execution, paper trading, live trading, trade plans, entry prices, target weights, position sizing, allocation, `.env` reads, key output, secret handling, raw-data migration, or external-audit PASS.
