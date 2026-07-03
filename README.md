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

## Current Decision

Use this folder as an orchestration layer first. Do not physically move or merge the existing repositories until each repo has a clean checkpoint and absolute-path registry references have been refreshed.

## Tool Split

- Codex CLI: primary implementation, integration, validation, Git-aware delivery.
- Reasonix CLI: read-only advisory review, semantic indexing, test-gap review, report-overclaim review, research planning.
- Codex-Audit: separate read-only process review.
- ChatGPT external audit: final external audit after packets are prepared.

## Boundaries

This workspace must not enable broker APIs, order routing, auto execution, live trading, or real buy/sell recommendations. Empty or blocked states are valid outcomes when supported by evidence.

