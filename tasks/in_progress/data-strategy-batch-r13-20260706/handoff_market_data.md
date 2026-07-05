# Handoff: market_data R13

Send to `market_data` Codex-Dev thread `019f3283-a821-7002-961b-6f533d3518c2`.

Prompt-only. Do not pass model or thinking overrides.

```text
You are Codex-Dev for /Users/rongyuxu/Desktop/market_data.

Task batch: DATA_STRATEGY_BATCH_R13_20260706

Task: MD-R13-1 / derived-feature evidence boundary note

Objective:
Create a research-only evidence boundary note for the A-share 3068-symbol features_daily work.

The note must state:
- features_daily is a derived research feature artifact;
- it is not raw data migration;
- it is not a product route;
- it is not DATA_CLEAR_RESEARCH promotion;
- it is not production readiness;
- it does not change US-300A status;
- it does not change A-share product-read flags;
- any local_market DuckDB schema/write/readiness/registry change still requires separate HG-EXEC.

Do not activate any route. Do not change product_read_allowed, production_recommendation_data_ready, broker/live/auto/paper/order flags, registry activation, or readiness status.

Required final output:
CODEX_ACCEPTANCE with changed files, validation, commit, and boundary statement.

Boundary:
Research-only. No recommendation/advice, ticket, PENDING_HUMAN_REVIEW, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, .env access, key output, or secret handling.
```
