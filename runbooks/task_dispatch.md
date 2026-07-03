# Task Dispatch Runbook

Use this when the user brings a task list from ChatGPT and wants the work assigned to downstream agents.

## Flow

```text
ChatGPT task list
  -> Quant-Dispatcher
  -> registry refresh when current project state matters
  -> tasks/inbox/<timestamp>-chatgpt-task-list.md
  -> tasks/backlog/<task-id>/spec.md
  -> tasks/backlog/<task-id>/handoff.md
  -> human_gate decision record when approval is required
  -> task packet validation
  -> downstream agent
  -> task report
  -> audit / external audit when needed
```

## Dispatcher Responsibilities

- Preserve the original task list.
- Split broad items into independently reviewable tasks.
- Keep project boundaries explicit.
- Assign each task to one primary downstream agent.
- Mark unsafe or ambiguous tasks as `HOLD`.
- Require human approval for migration, trading-adjacent, or scope-expanding work.
- Refresh the registry before assigning work that depends on current source-project state.
- Record Human-Gate decisions durably when approval is required.
- Validate task packets before dispatch using `runbooks/task_packet_validation.md`.

## Downstream Agent Choices

| Task type | Agent |
|---|---|
| Code/config/test/doc implementation | `codex_dev` |
| Database maintenance diagnosis, schema/readiness review, SQL/manifest draft | `reasonix_db_maintainer` |
| Strategy research, factor hypotheses, config drafts, backtest diagnosis | `reasonix_strategy_researcher` |
| Read-only second review or test-gap review | `reasonix_advisory` |
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

## Required Task Packet Files

Each dispatched task should have:

- `spec.md`
- `handoff.md`
- `human_gate.md`
- optional `context.md`
- optional `dependencies.md`

Before dispatch, validate the permission level. L1-L4 execution requests require a unique pre-execution `HG-EXEC-TASK-*` record. Standing authorization alone is not enough. If the record is missing, mark the task `HOLD_FOR_MISSING_HG_EXEC_TASK_RECORD` and only allow read-only planning or diagnosis.

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
- Do not dispatch raw data migration or DB-write tasks without `human_gate`.
- Do not dispatch L1-L4 execution without a unique pre-execution `HG-EXEC-TASK-*` record.
- Do not treat a missing Human-Gate record as approval.
- Do not treat a stale registry snapshot as current source-project truth.
- Do not let Reasonix-DB write physical databases or change readiness/registry activation without `human_gate` and Codex-Dev validation.
- Do not let Reasonix-Strategy promote research drafts into A-share/US source repos without Codex-Dev.
- Do not let Reasonix-Advisory edit files unless the task is explicitly converted into a Codex-Dev implementation task.
- Do not let Codex-Audit fix code.
