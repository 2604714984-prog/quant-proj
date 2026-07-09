# Human-Gate Classification: R15

Batch: `WINDOWS_WSL2_DATA_STRATEGY_AND_BASE_BATCH_R15_20260706`
Classification: ordinary research-only data/strategy/data-base batch
External-audit trigger opened: `no`

## Current Permission Level

Default allowed work: `L0_RESEARCH_DIAGNOSTIC` plus ordinary source-code,
test, report, and config edits in downstream repos.

## Not Authorized In This Batch

- network/provider fetch;
- DB/cache rebuild;
- physical DB write;
- schema migration;
- bulk ingest;
- readiness change;
- registry activation;
- product route activation;
- `PENDING_HUMAN_REVIEW` ticket emission;
- eligibility candidate creation;
- broker/order/paper/live/auto behavior;
- raw-data migration;
- `.env`, key, token, auth, credential, or secret handling.

## Plan-Only Controlled Work

`A-WIN-R15-3` is a plan-only task for a future East Money expansion HG-EXEC
packet. It must output `HG_EXEC_REQUIRED_FOR_EAST_MONEY_COVERAGE_EXPANSION` if
execution would require provider/network fetch. It must not fetch data.

## Boundary

Missing task-level HG-EXEC means not approved for L1-L4 actions. If a downstream
task discovers that network, DB write, schema/readiness/registry change, raw
data migration, or secret handling is needed, it must stop and return
`BLOCKED`.
