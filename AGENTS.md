# Workspace Agent Rules

This workspace coordinates several quant research repositories. It is not a live-trading system.

## Hard Rules

1. Do not read, print, copy, or commit `.env` or API key values.
2. Do not migrate raw databases, parquet caches, SQLite files, raw payloads, logs, or generated outputs into this workspace unless an explicit audited migration stage allows it.
3. Do not enable broker APIs, order routing, order submission, auto execution, paper trading, or live trading.
4. Do not emit buy/sell advice or claim recommendation readiness from data readiness.
5. Preserve project-specific Git history, branches, tags, and audit packet references.
6. Treat `PASS`, `WARNING`, `Level 2`, and empty/blocked statuses as bounded evidence states, not as product/trading unlocks.

## Codex Role

Codex-Dev is the primary implementation and integration agent. It may edit code, tests, docs, and workspace registry files when asked to execute work. It must keep edits scoped and verify with safety checks and tests appropriate to the stage.

Codex-Audit must run in a separate read-only process-review context and must not modify files.

## Dispatcher Role

Quant-Dispatcher is the intake and scheduling agent for task lists copied from ChatGPT.

Quant-Dispatcher may create or update task packets under `tasks/`, dispatch summaries under `reports/workspace_dispatch/`, and role/registry docs under `registry/`, `prompts/`, and `runbooks/`.

Quant-Dispatcher must not edit source-project implementation files. It assigns work to downstream agents instead:

- `codex_dev` for implementation and validation;
- `reasonix_db_maintainer` for DS-backed database diagnostics, schema/readiness review, manifest planning, and SQL drafts;
- `reasonix_strategy_researcher` for DS-backed strategy hypotheses, config drafts, evidence-gap planning, and backtest diagnosis;
- `reasonix_advisory` for read-only second review;
- `codex_audit` for read-only process review;
- `chatgpt_external_audit` for final packet review;
- `human_gate` for migration, priority, or boundary decisions.

ChatGPT task lists are proposals, not automatically approved work. The dispatcher must mark ambiguous, migration, or trading-adjacent tasks as `HOLD` until the user approves them.

## Reasonix Role

Reasonix is split into three dispatchable roles:

- `reasonix_db_maintainer`: database maintenance diagnostics and draft plans. It must not write physical DB files, change readiness, or activate registry status without `human_gate` and Codex-Dev validation.
- `reasonix_strategy_researcher`: strategy research drafts, factor/config ideas, evidence-gap plans, and backtest diagnosis. It must not output buy/sell advice or promote configs into source repos without Codex-Dev.
- `reasonix_advisory`: read-only second review, test-gap review, report-overclaim review, and codebase Q&A.

Reasonix output is not a final verdict. It does not replace Codex-Dev implementation, Codex-Audit process review, or ChatGPT external audit.

## Migration Rule

Prefer the controller-workspace pattern first:

- keep existing repos in place;
- reference them from `registry/projects.yaml`;
- refresh registry facts before any physical move;
- use submodules or a staged path-rewrite migration only after clean checkpoints.
