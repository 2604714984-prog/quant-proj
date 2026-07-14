# ADR: Central warehouse single-writer boundary

Status: `ACCEPTED_FOR_R2_IMPLEMENTATION / PUBLISHER_DISABLED`

The central database remains `/home/rongyu/workspace/quant_data/quant_research.duckdb`. `A_Share_Monitor`, `US_Stock_Monitor`, `strategy_work`, `quant_research_lab`, and `us_stock_30w` are read-only consumers and may not open it for writes.

The implementation boundary is the existing private `market_data` repository, continuing from its isolated central-warehouse branch. It is the only source repository allowed to contain the central publisher. It must not import strategy, recommendation, ranking, candidate, broker, order, paper, live, or automatic-execution modules.

The pipeline is:

```text
TuShare -> bounded collector -> private staging/checkpoint/quarantine
        -> batch validator -> accepted-batch queue
        -> single writer -> central DuckDB -> read-only consumers
```

Wave 0 authorizes design, code, tests, a byte-identical pre-change backup, and read-only database inspection. It does not authorize provider calls, token access, staging collection, schema migration, central publication, timer activation, canonical snapshot activation, readiness changes, or strategy execution.

Collector and publisher identities are deliberately separated:

- collector may eventually read `TUSHARE_TOKEN` only from a private `0600` credential source and may write only private staging;
- publisher must never receive or read `TUSHARE_TOKEN` and may consume only accepted content-addressed batches;
- publisher execution requires a fresh task-level Human-Gate record, exact implementation commit/tree/script hashes, database pre-hash/bytes, backup path, lock, transcript, postcheck, and independent acceptance;
- partial backfills can never become the active canonical snapshot.

The initial provider endpoints remain limited to `trade_cal`, `stock_basic`, `namechange`, `daily`, `adj_factor`, `daily_basic`, `suspend_d`, and `stk_limit`. Historical values without verifiable publication/availability timestamps are classified as `ENGINEERING_OR_RETROSPECTIVE_RESEARCH_DATA`, with `availability_state=UNKNOWN` and `strict_pit_eligible=false`.

`strategy_candidate_available=false` is invariant throughout this stage.
