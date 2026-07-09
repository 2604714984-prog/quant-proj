# Handoff: market_data R13C

Send to active `market_data` Codex-Dev thread `019f3283-a821-7002-961b-6f533d3518c2`, rooted at `/home/rongyu/workspace/market_data`.

Note: prior local-main thread `019f2957-de0a-7721-ade9-1abfef298127` is archived and should be treated as reference-only unless explicitly reopened by the user.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /home/rongyu/workspace/market_data.

Task batch: DATA_STRATEGY_BATCH_R13_CHUNKED_SEARCH_20260706

Task: MD-R13C-1 / features_daily derived-feature boundary contract.

Objective:
Record the boundary semantics for A-share wide features_daily and chunked backtest evidence.

The note/contract must state:
- features_daily is a derived research feature artifact;
- it is not raw data migration;
- it is not data-clear promotion;
- it is not product-read route;
- it is not production readiness;
- it does not change US-300A status;
- it does not change A-share product flags;
- it cannot be interpreted directly as ticket eligibility.

Add negative tests or document checks proving:
- wide features_daily exists != strategy valid;
- chunked backtest passes != recommendation;
- positive Sharpe != ticket;
- data quality PASS != production-ready.

Do not activate routes, change product/readiness flags, write DB, ingest network data, or change registry status.

Required final output:
CODEX_ACCEPTANCE with changed files, validation, commit, and boundary statement.

Boundary:
Research-only. No recommendation/advice, PENDING_HUMAN_REVIEW, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, .env access, key output, or secret handling.
```
