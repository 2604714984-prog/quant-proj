# Quant Workspace

This folder is the controller workspace for the local quant system.

## Consolidated External Re-audit (2026-07-14)

Use
[`reports/external_audit/workspace_external_reaudit_consolidated_20260714.md`](reports/external_audit/workspace_external_reaudit_consolidated_20260714.md)
as the current external-review entry point. It incorporates the prior audit package,
R1/R2 remediation, targeted re-audit bindings, Gate-B controller evidence, and the
completed A0-A6/U0-U6/X1/X2 central-database adjudication. The package is ready for
independent review but explicitly retains blocked data-source outcomes and
`strategy_candidate_available=false`.

The personal-project complexity addendum is
[`reports/external_audit/central_database_lean_architecture_external_review_addendum_20260714.md`](reports/external_audit/central_database_lean_architecture_external_review_addendum_20260714.md).
It asks whether the central database should be simplified and must be reviewed as a single-user
local research system, not as an institutional platform.

## External Audit (2026-07-12)

Start the GitHub-based external review with
[`reports/external_audit/workspace_external_audit_packet_20260712.md`](reports/external_audit/workspace_external_audit_packet_20260712.md).
The adjacent JSON manifest pins the repositories, branches, commits, CI runs,
publication exclusions, and current fail-closed research conclusions.

It does not yet contain the source repos. The current source-of-truth project roots are:

- `/home/rongyu/workspace/A_Share_Monitor`
- `/home/rongyu/workspace/US_Stock_Monitor`
- `/home/rongyu/workspace/market_data`
- `/home/rongyu/workspace/strategy_work`

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
