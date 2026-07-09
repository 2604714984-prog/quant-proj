# TASK-031 US 44-Symbol Metadata Gap Repair Plan

Status: `ASSIGNED`
Target project: `US_Stock_Monitor`
Agent: `Codex-Dev`
Priority: `P0`
Permission: `L0_RESEARCH_DIAGNOSTIC`

## Goal

Handle the remaining `TASK-023` blocker: 44 missing metadata symbols.

## Must Deliver

- missing metadata symbol list;
- source table expected fields;
- whether existing `source_symbol_metadata` can repair the gap;
- whether Nasdaq response or local cache can bootstrap metadata;
- whether network ingest is needed later;
- metadata bootstrap dry-run;
- duplicate/collision checks;
- next executable `HG-EXEC` task proposal.

## Output

- `reports/codex_dev/task_031_us_44_symbol_metadata_gap_repair_plan.md`
- `reports/codex_dev/task_031_us_44_symbol_metadata_gap_repair_plan.json`

## Forbidden

No network, no DuckDB write, no product route activation, no HITL readiness claim, no recommendation, no ticket, no broker/order/paper/live/auto, no `.env` access, no secret handling.
