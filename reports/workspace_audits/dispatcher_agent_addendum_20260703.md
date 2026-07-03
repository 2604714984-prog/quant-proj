# Dispatcher Agent Addendum

Date: 2026-07-03
Workspace: `/Users/rongyuxu/Desktop/quant proj`
Status: PLANNING_UPDATE / NEEDS_REVIEW_BEFORE_OPERATIONAL_USE

## Purpose

This addendum updates the workspace collaboration plan to include a dedicated task scheduling agent:

- `Quant-Dispatcher`

The dispatcher receives task lists copied from ChatGPT, converts them into local task packets, and assigns downstream agents.

## New Flow

```text
ChatGPT task list
  -> Quant-Dispatcher
  -> tasks/inbox/<timestamp>-chatgpt-task-list.md
  -> tasks/backlog/<task-id>/spec.md
  -> downstream agent handoff
```

Downstream agents:

- `codex_dev`: implementation and validation.
- `reasonix_db_maintainer`: DS-backed database diagnostics, schema/readiness review, manifest planning, and SQL drafts.
- `reasonix_strategy_researcher`: DS-backed strategy hypotheses, config drafts, evidence-gap planning, and backtest diagnosis.
- `reasonix_advisory`: read-only second review.
- `codex_audit`: read-only process review.
- `chatgpt_external_audit`: final external packet review.
- `human_gate`: approval and boundary decisions.

## New Files

- `registry/agents.yaml`
- `prompts/task_dispatcher.md`
- `prompts/reasonix_db_maintainer.md`
- `prompts/reasonix_strategy_researcher.md`
- `runbooks/task_dispatch.md`
- `tasks/README.md`
- `tasks/board.md`
- `tasks/inbox/.gitkeep`
- `tasks/backlog/.gitkeep`
- `tasks/in_progress/.gitkeep`
- `tasks/done/.gitkeep`
- `tasks/blocked/.gitkeep`

Updated files:

- `README.md`
- `AGENTS.md`
- `QUANT_WORKSPACE_CODEX_REASONIX_PLAN.md`

## Safety Boundary

Quant-Dispatcher is not an implementation agent. It must not edit source-project implementation files. It may create task-control files only.

Reasonix-DB and Reasonix-Strategy are drafting/diagnostic roles, not final delivery roles. Codex-Dev remains responsible for implementation, tests, validation, and delivery reports.

Forbidden for dispatcher:

- source-project code edits;
- `.env` reads;
- API key output;
- raw database/parquet copy;
- recommendation/trading authorization;
- broker/order/live-trading task execution.

## Operational Rule

ChatGPT task lists are treated as proposals, not automatically approved work.

The dispatcher must mark a task as `HOLD` if it is:

- ambiguous;
- migration-related;
- trading-adjacent;
- boundary-changing;
- missing a target repo or validation expectation.

## External Review Question

Please review whether the dispatcher is sufficiently constrained before using it as the standard intake path for ChatGPT task lists.
