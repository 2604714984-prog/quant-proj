# ADR v2: dedicated central ingestion service boundary

Status: `ACCEPTED_WAVE1_STAGING / PUBLISHER_ABSENT_AND_DISABLED`

This decision supersedes the implementation-repository selection in `CENTRAL_WRITER_BOUNDARY_ADR_20260713.md`; it does not change the frozen Wave 0 database identity or authorize a write.

The private repository `central-data-ingestion` is now the sole implementation boundary for the bounded staging collector and any future central publisher. Commit `287416f79cd1fcb1c066f25fa7bbaedc574b0ce9`, tree `c2a62d079bcb08b04b2425c7160bf9ca8344038a`, passed independent read-only acceptance, 19 focused tests and GitHub Actions run `29204075556`.

`market_data` returns to a registry/read-only access-gate role. `A_Share_Monitor`, `US_Stock_Monitor`, `strategy_work`, `quant_research_lab`, `us_stock_30w`, `market_data`, and the controller remain prohibited from writing `/home/rongyu/workspace/quant_data/quant_research.duckdb`.

Only DB-603 through DB-607 are implemented: private staging/control/quarantine, one-request partitions, provenance, validation and checkpointing. The collector timer is inert (`ExecStart=/usr/bin/false`). No central publisher code, canonical view activation, provider call, token read, central database write, strategy process, or timer activation occurred.

DB-608 and later remain Gate-B work. Any future central publication requires a new exact Human-Gate record, byte-identical backup evidence, OS writer lock, transaction rollback proof, idempotent batch identity, canary reconciliation and independent acceptance. `strategy_candidate_available=false`.
