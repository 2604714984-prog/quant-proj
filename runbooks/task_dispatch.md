# Task Dispatch Runbook

Use this when the user brings a task list from ChatGPT and wants the work assigned to downstream agents.

## Flow

```text
ChatGPT task list
  -> Sol Quant-Manager
  -> Luna Quant-Dispatcher
  -> registry refresh when current project state matters
  -> tasks/inbox/<timestamp>-chatgpt-task-list.md
  -> tasks/backlog/<task-id>/spec.md
  -> tasks/backlog/<task-id>/handoff.md
  -> human_gate decision record when approval is required
  -> task packet validation
  -> Luna downstream executor
  -> automated gate
  -> Luna read-only acceptance
  -> Sol evidence review only if evidence remains insufficient or conflicting
  -> Luna final acceptance
  -> audit / external audit when needed
```

## Dispatcher Responsibilities

- Preserve the original task list.
- Convert the Manager split into independently reviewable task packets.
- Keep project boundaries explicit.
- Assign each task to one primary downstream agent.
- Mark unsafe or ambiguous tasks as `HOLD`.
- Require human approval for migration, trading-adjacent, or scope-expanding work.
- Refresh the registry before assigning work that depends on current source-project state.
- Record Human-Gate decisions durably when approval is required.
- Validate task packets before dispatch using `runbooks/task_packet_validation.md`.
- Apply `runbooks/model_routing.md`: Sol Manager coordinates; Luna Dispatcher
  operates the queue; Luna executes and accepts; automated gates block
  deterministic rework.
- For final ChatGPT external-audit publications, create post-tag final publication metadata using `runbooks/final_publication_metadata.md`.
- Include the downstream completion callback requirement in every Codex-Dev handoff. Downstream Codex threads must send a prompt-only callback to the active Quant-Dispatcher thread after finishing, or include the callback envelope in their final answer if thread messaging is unavailable. Never reuse a retired legacy dispatcher id; resolve the current callback target before dispatch.

## Codex Model Routing

- Coordination and dependency decomposition: `gpt-5.6-sol`, effort `high`.
- Queue, packet, callback, and stall operations: `gpt-5.6-luna`, effort
  `medium`.
- Implementation, batch work, deterministic validation, and rework:
  `gpt-5.6-luna`, effort `medium`.
- Routine read-only final acceptance: `gpt-5.6-luna`, effort `high`.
- Sol evidence escalation is allowed only for the two reasons listed in
  `registry/model_routing.yaml`.
- Existing desktop tasks can retain older settings. Every dispatch must select
  the required model/effort explicitly; new project sessions also inherit the
  role layers under `.codex/`.
- A green automated gate is required before Luna acceptance. A red gate returns
  to Luna as rework/requeue or `BLOCKED`; it does not trigger Sol review.
- Any Sol ruling is limited to the disputed evidence slice and returns to Luna
  for the final acceptance result.

## External Audit Trigger Policy

Do not create ChatGPT external-audit packets for ordinary task lists, dispatcher routing, Reasonix advisory output, Codex acceptance output, research-only candidates, blocked/no-recommendation states, or controller process bookkeeping.

Ordinary Codex source execution should end with `LUNA_EXECUTION_COMPLETE` or
`BLOCKED`, plus commit/tree and automated-gate evidence when files changed.
`LUNA_ACCEPTANCE` may be emitted only by the separate read-only
`codex_acceptance` role. Reasonix work ends with `REASONIX_REPORT`.

Only prepare a ChatGPT external-audit packet when one of these gates is being opened or changed:

- A-share research candidates are proposed for real `PENDING_HUMAN_REVIEW`.
- US creates a real `eligibility_candidate` for `PENDING_HUMAN_REVIEW`.
- `market_data` changes an A-share or US route into an active product route.
- readiness moves from research/warning into HITL data prerequisite or production recommendation readiness.
- broker/order/paper/live/auto behavior is introduced or changed.
- the Human-Gate permission model, registry activation rules, secret handling, or broker/live boundary changes.

If none of those triggers are present, do not start Codex-Audit or ChatGPT external audit for the controller. Ask which blocker to repair next.

## Downstream Agent Choices

| Task type | Agent |
|---|---|
| Code/config/test/doc implementation | `codex_dev` |
| Database maintenance diagnosis, schema/readiness review, SQL/manifest draft | `reasonix_db_maintainer` |
| Strategy research, factor hypotheses, config drafts, backtest diagnosis | `reasonix_strategy_researcher` |
| Read-only second review or test-gap review | `reasonix_advisory` |
| Routine final evidence acceptance | `codex_acceptance` |
| Process review of a finished delivery packet | `codex_audit` |
| Final outside review of a prepared packet | `chatgpt_external_audit` |
| Scope, migration, trading-adjacent, or priority decision | `human_gate` |

## Reasonix Dispatch

Use `runbooks/reasonix_sessions.md` for Reasonix work.

Default:

- keep `quant-reasonix-db`, `quant-reasonix-strategy`, and `quant-reasonix-advisory` as fixed persistent sessions;
- send concise `DISPATCH_TASK` envelopes that reference task packets and source refs;
- avoid replaying full project history on every task;
- use Reasonix compact as the default context-control mechanism;
- create manual `SESSION_SUMMARY` artifacts only for audit, handoff, or fresh-session restart;
- keep old mixed Reasonix sessions as reference-only unless the user explicitly asks to continue them.

## Downstream Completion Callback

For Codex-Dev thread dispatches, append this standing instruction:

```text
Completion callback required: after finishing, send a prompt-only callback to the active Quant-Dispatcher thread with LUNA_EXECUTION_COMPLETE/DATA_REPORT/STRATEGY_REPORT or BLOCKED, commit/tree, artifacts, AUTOMATED_GATE manifest, exact validation, residual blockers, and boundary statement. Executor callbacks are delivery evidence, not final acceptance. Resolve the current dispatcher task id at dispatch time; never use a retired legacy id. If the thread tool is unavailable, include the callback envelope in your final answer.
```

Controller protocol record:

- `reports/workspace_dispatch/downstream_completion_callback_protocol_20260706.md`

## Required Task Packet Files

Each dispatched task should have:

- `spec.md`
- `handoff.md`
- `human_gate.md`
- optional `context.md`
- optional `dependencies.md`

Before dispatch, validate the permission level. Ordinary research-only public/no-secret network fetches and source-local research cache/staging/report/test writes use the research-data fast path and do not require per-task HG-EXEC. Boundary-changing execution requests still require a unique pre-execution `HG-EXEC-TASK-*` record. If that record is missing for boundary-changing work, mark the task `HOLD_FOR_MISSING_HG_EXEC_TASK_RECORD` and only allow read-only planning or diagnosis.

## Status Values

- `INBOX`: raw imported task list.
- `BACKLOG`: accepted but not assigned for execution.
- `HOLD`: needs human approval or scope clarification.
- `ASSIGNED`: downstream agent has enough context to start.
- `IN_PROGRESS`: downstream agent is working.
- `DONE`: downstream agent produced report/output.
- `AUDIT_READY`: delivery packet is ready for Codex-Audit.
- `EXTERNAL_AUDIT_READY`: packet is ready for ChatGPT external audit.
- `BLOCKED`: cannot proceed without missing input or external state change.

## Safety Rules

- Do not dispatch broker/order/live-trading tasks as implementation work.
- Do not dispatch buy/sell advice tasks.
- Do not dispatch raw data migration, active schema migration, readiness promotion, registry activation, product-route activation, ticket/candidate creation, secret handling, or trading-adjacent tasks without the required gate.
- Do not require per-task HG-EXEC for research-data fast-path tasks that are bounded, public/no-secret, source-local, and non-actionable.
- Do not dispatch boundary-changing L1-L4 execution without a unique pre-execution `HG-EXEC-TASK-*` record.
- Do not treat a missing Human-Gate record as approval.
- Do not treat a stale registry snapshot as current source-project truth.
- Do not let Reasonix-DB write physical databases or change readiness/registry activation without `human_gate` and Codex-Dev validation.
- Do not let Reasonix-Strategy promote research drafts into A-share/US source repos without Codex-Dev.
- Do not let Reasonix-Advisory edit files unless the task is explicitly converted into a Codex-Dev implementation task.
- Do not let Codex-Audit fix code.
- Do not close a final external-audit publication without recording the final tag object, commit, tree, tag URL, packet path, and manifest path in a final publication metadata closeout.
