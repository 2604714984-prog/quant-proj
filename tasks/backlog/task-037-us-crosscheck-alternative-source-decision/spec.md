# TASK-037 US Crosscheck Alternative Source Decision

Status: `ASSIGNED`
Target project: `US_Stock_Monitor`
Agent: `Reasonix-DB`
Priority: `P1`
Permission: `L0_RESEARCH_DIAGNOSTIC`

## Goal

Decide the safest planning route for obtaining authoritative crosscheck or metadata source coverage for the US 44-symbol metadata gap, without executing network ingest or DB writes.

## Inputs

- `TASK-031` metadata gap repair plan: US commit `4d4e21f35374fd2aca6c6f756830ab9d1b353593`, tree `a1172367829db0a0545701b7e02e194b0b38cf27`.
- Missing symbol count: `44`, hash `b680b7a6d4c82acb`.
- `TASK-023` preflight repair and `TASK-024` eligibility blocker drilldown.

## Must Decide

- whether an offline controlled metadata source is preferable to network provider ingest;
- what fields are mandatory for a metadata-only bootstrap source;
- what crosscheck evidence is required before any write task;
- how to avoid synthetic defaults or stale provider payloads;
- stop conditions for missing, duplicated, delisted, ETF/fund, or unsupported symbols;
- required future `HG-EXEC-TASK-*` record shape for any L1/L2 execution.

## Expected Outputs

- `reports/deepseek_db/task_037_us_crosscheck_alternative_source_decision.md`
- `reports/deepseek_db/task_037_us_crosscheck_alternative_source_decision.json`
- transcript: `reports/workspace_dispatch/reasonix_db_task_037_20260704.jsonl`

## Forbidden

No network ingest, DB write, metadata bootstrap execution, registry/readiness change, product route activation, recommendation, ticket emission, broker/order/paper/live/auto, `.env` access, key output, or secret handling.
