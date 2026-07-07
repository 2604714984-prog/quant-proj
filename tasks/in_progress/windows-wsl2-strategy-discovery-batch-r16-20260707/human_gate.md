# Human-Gate Classification - WINDOWS_WSL2_STRATEGY_DISCOVERY_BATCH_R16_20260707

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-07 Asia/Shanghai

## Classification

`L0_RESEARCH_ONLY_DISPATCH`

No task-level HG-EXEC is granted by this packet.

## Allowed

- Read existing local source files, reports, manifests, tests, and local research data needed for diagnostics.
- Write research-only reports, CSV/JSON summaries, tests, schemas, and strategy memo artifacts inside assigned repos.
- Run bounded local tests and local research diagnostics that do not rebuild DB/cache, fetch providers, change schema, change readiness, or activate registry/product routes.
- Use chunked-only wide3068 diagnostics when source-side guards confirm the path does not enter full-frame pandas StrategySearch.

## Not Authorized

- recommendation/advice;
- `PENDING_HUMAN_REVIEW`, ticket, or eligibility candidate;
- data-clear promotion;
- product-route activation;
- production readiness;
- broker/order/paper/live/auto;
- raw-data migration;
- `.env`, key, token, auth, credential, or secret access/output;
- network/provider fetch;
- DB write or cache rebuild;
- schema migration;
- readiness change;
- registry activation.

## Stop Conditions

- full-frame wide3068 StrategySearch attempted;
- network/provider fetch required;
- DB/cache rebuild required;
- schema/readiness/registry change required;
- strategy result promoted to candidate, recommendation, ticket, or readiness;
- shadow leaderboard used as recommendation;
- parameter changes made after test results;
- stable parameter region written as readiness;
- secret or environment access required.

If a stop condition is encountered, downstream must stop and return `BLOCKED` with the callback envelope.

