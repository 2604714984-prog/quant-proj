# Quant Workspace

This folder is the controller workspace for the local quant system.

It does not yet contain the source repos. The current source-of-truth project roots are:

- `/Users/rongyuxu/Desktop/A_Share_Monitor`
- `/Users/rongyuxu/Desktop/US_Stock_Monitor`
- `/Users/rongyuxu/Desktop/market_data`
- `/Users/rongyuxu/Desktop/strategy_work`

Start with:

- `QUANT_WORKSPACE_CODEX_REASONIX_PLAN.md` for the Codex + Reasonix collaboration plan.
- `AGENTS.md` for workspace-wide hard rules.
- `registry/projects.yaml` for the current project inventory.
- `registry/agents.yaml` for the current agent roles.
- `prompts/task_dispatcher.md` for dispatching ChatGPT task lists.
- `prompts/reasonix_db_maintainer.md` and `prompts/reasonix_strategy_researcher.md` for DS-backed Reasonix task roles.
- `runbooks/registry_refresh.md` before batch dispatch, migration planning, or external packet publication.
- `runbooks/human_gate.md` for durable human approval records.
- `tasks/board.md` for the local task queue.

## Current Decision

Use this folder as an orchestration layer first. Do not physically move or merge the existing repositories until each repo has a clean checkpoint and absolute-path registry references have been refreshed.

## Tool Split

- Quant-Dispatcher: receives ChatGPT task lists, creates task packets, and assigns downstream agents.
- Codex CLI: primary implementation, integration, validation, Git-aware delivery.
- Reasonix-DB: DS-backed database maintenance diagnostics and draft plans.
- Reasonix-Strategy: DS-backed strategy research, factor/config drafts, and evidence-gap planning.
- Reasonix-Advisory: read-only second review, test-gap review, report-overclaim review.
- Codex-Audit: separate read-only process review.
- ChatGPT external audit: final external audit after packets are prepared.

## Dispatch Flow

```text
ChatGPT task list
  -> Quant-Dispatcher
  -> registry refresh when current project state matters
  -> tasks/backlog/<task-id>/spec.md
  -> Human-Gate record when approval is required
  -> Codex-Dev / Reasonix-DB / Reasonix-Strategy / Reasonix-Advisory / Codex-Audit / ChatGPT external audit / Human-Gate
```

## Boundaries

This workspace must not enable broker APIs, order routing, auto execution, live trading, or real buy/sell recommendations. Empty or blocked states are valid outcomes when supported by evidence.
