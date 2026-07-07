# Human-Gate Classification - WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-07 Asia/Shanghai

## Classification

`L0_RESEARCH_ONLY_DISPATCH`

No new task-level HG-EXEC is granted by this packet.

R17 may use existing accepted research artifacts and the already-installed research GPU environment. The prior standing RTX 5090 400W power cap was revoked by the user on 2026-07-07T16:32:56+08:00, so R17 may proceed under host/driver default GPU power policy while recording observed power telemetry.

## Allowed

- Read existing local source files, reports, manifests, tests, and local research data needed for diagnostics.
- Write research-only reports, CSV/JSON summaries, schemas, tests, and strategy memo artifacts inside assigned repos.
- Run bounded local tests and local research diagnostics that do not rebuild DB/cache, fetch providers, change schema, change readiness, or activate registry/product routes.
- Use existing GPU research environment for signal diagnostics under host/driver default GPU power policy.
- Use chunked-only wide3068 probe only if pre-qualified by R17 rules and source-side guards confirm the path does not enter full-frame pandas StrategySearch.

## Not Authorized

- recommendation/advice;
- `PENDING_HUMAN_REVIEW`, ticket, or eligibility candidate;
- strategy candidate promotion;
- data-clear promotion;
- product-route activation;
- production readiness;
- broker/order/paper/live/auto;
- raw-data migration;
- `.env`, key, token, auth, credential, or secret access/output;
- network/provider fetch without separate task-level HG-EXEC;
- DB write or cache rebuild without separate task-level HG-EXEC;
- schema migration;
- readiness change;
- registry activation;
- privileged GPU power-limit changes unless separately requested.

## Stop Conditions

- full-frame wide3068 StrategySearch attempted;
- market_data product-route activation attempted;
- network/provider fetch required;
- DB/cache write or rebuild required;
- schema/readiness/registry change required;
- `R17_WIDE_PROBE_ELIGIBLE` written as candidate, recommendation, ticket, or readiness;
- parameters selected after test results;
- GPU power policy becomes unclear or requires privileged modification;
- secret or environment access required.

If a stop condition is encountered, downstream must stop and return `BLOCKED` with the callback envelope.
