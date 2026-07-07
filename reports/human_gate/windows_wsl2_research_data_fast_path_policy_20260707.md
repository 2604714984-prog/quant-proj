# Research Data Fast Path Policy

Decision date: 2026-07-07 Asia/Shanghai
Controller: Quant-Dispatcher
Decision id: `HG-POLICY-RESEARCH-DATA-FAST-PATH-20260707`

## User Direction

The user directed Quant-Dispatcher to remove the HG-EXEC requirement from rules that were materially slowing development for ordinary research data work.

## Effective Rule

Per-task `HG-EXEC-TASK-*` records are no longer required for ordinary research-only data work when all of the following are true:

- the task is research-only and non-actionable;
- the source is public/no-secret or an already accepted local/project provider path;
- any network fetch is bounded by provider, symbol/universe, date range, and output path in the task packet or handoff;
- writes are source-local research staging/cache/report/test artifacts only;
- no active registry, readiness, schema, product route, ticket, candidate, broker/order, paper/live, auto, or daily signal state is changed;
- no `.env`, token, key, credential, auth, or secret access/output is required;
- the downstream callback includes command transcript, manifest/count/hash evidence when data is fetched or written.

This fast path covers:

- public/no-secret research network fetch;
- source-local research cache, parquet, CSV, DuckDB, SQLite, or staging writes/rebuilds;
- provider/source diagnostics and coverage probes;
- product-route/readiness prep reports, diffs, rollback plans, and tests that do not activate or change active state.

## Still Gated

The following remain blocked unless explicitly separately authorized and validated:

- `.env`, token, key, credential, auth, or secret access/output;
- raw-data migration into `quant-proj`;
- schema migration that changes an active source/project contract;
- active registry activation;
- readiness promotion into HITL prerequisite, product-read route, production recommendation, broker, paper, live, or auto readiness;
- product-route activation or replacement;
- `PENDING_HUMAN_REVIEW`, ticket emission, eligibility candidate creation, or strategy candidate promotion;
- recommendation/advice, trade plan, entry price, target weight, position sizing, allocation, broker/order/paper/live/auto.

## Required Controls Without HG-EXEC

For research-data fast-path work, downstream must still provide:

- task packet or handoff scope;
- command transcript for network/write tasks;
- manifest/count/hash evidence for generated data artifacts;
- JSON parse where JSON artifacts are written;
- duplicate-key and missingness checks where applicable;
- `git diff --check`;
- focused tests when code/tests change;
- forbidden overclaim scan;
- prompt-only callback to Quant-Dispatcher.

## Boundary

This policy reduces controller friction for research data work only. It does not authorize recommendation, ticket, strategy candidate promotion, readiness promotion, product-route activation, registry activation, schema migration, raw-data migration into `quant-proj`, secret access, or trading paths.
