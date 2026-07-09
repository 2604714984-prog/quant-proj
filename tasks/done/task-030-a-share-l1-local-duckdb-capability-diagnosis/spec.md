# TASK-030 A-share L1 Local DuckDB Capability Diagnosis

Status: `ASSIGNED`
Target project: `A_Share_Monitor`
Agent: `Codex-Dev`
Priority: `P0`
Permission: `L0_RESEARCH_DIAGNOSTIC`

## Goal

Run `DB-REPAIR-022-A` as a read-only local DuckDB diagnosis for missing suspension events and low limit-price coverage in snapshot `a_expand_20260704_l1_local1000_0317`.

## Must Check

- suspension/event source tables exist or not;
- limit-price table coverage;
- missing ratio in the 1000-symbol snapshot;
- DB-2 / L1 1000 snapshot symbol coverage;
- whether local raw tables can repair the issue;
- whether network ingest is required later.

## Output

- `reports/codex_dev/task_030_a_share_l1_local_duckdb_capability_diagnosis.md`
- `reports/codex_dev/task_030_a_share_l1_local_duckdb_capability_diagnosis.json`

If the source project prefers a DB report namespace, it may also mirror the report under `reports/deepseek_db/`, but no write/network execution is allowed.

## Forbidden

No DB write, no network, no registry/readiness change, no recommendation/ticket, no broker/order/paper/live/auto, no `.env` access, no secret handling.
