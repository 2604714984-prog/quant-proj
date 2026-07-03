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

## Reasonix Role

Reasonix is an advisory reviewer and local codebase assistant. Use it for read-only second opinions, semantic indexing, test-gap review, report-overclaim review, and research planning.

Reasonix advisory output is not a final verdict. It does not replace Codex-Audit or ChatGPT external audit.

## Migration Rule

Prefer the controller-workspace pattern first:

- keep existing repos in place;
- reference them from `registry/projects.yaml`;
- refresh registry facts before any physical move;
- use submodules or a staged path-rewrite migration only after clean checkpoints.

