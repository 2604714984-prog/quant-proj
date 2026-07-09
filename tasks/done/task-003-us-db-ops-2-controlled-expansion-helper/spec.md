# TASK-003: US_DB_OPS_2_CONTROLLED_EXPANSION_HELPER

Task ID: `TASK-003`
Status: `ASSIGNED_READY_TO_SEND`
Priority: `P0`
Primary assignee: `Codex-Dev`
Secondary reviewer if needed: `Reasonix-DB`
Target project: `US_Stock_Monitor`
Target root: `/Users/rongyuxu/Desktop/US_Stock_Monitor`
Dispatcher: `Quant-Dispatcher`
Created at: 2026-07-04T01:25:34+08:00

## Goal

Rewrite the US 300-symbol expansion helper into a controlled DB ops helper without running real network ingest or writing DuckDB as part of this assignment.

## Assignment

Send to `Codex-Dev` first. This is source-project implementation work.

Use `Reasonix-DB` only for a read-only advisory clarification if Codex-Dev needs DB policy review.

## Required Scope

Target rewrite:

```text
scripts/expand_us_300.py -> scripts/db_ops/expand_us_universe.py
```

Required controls:

- add `--allow-network`;
- add `--read-only`;
- add duplicate detection;
- add `snapshot_id` validation;
- add symbol validation against `canonical_symbol_metadata`;
- do not read `.env`;
- do not output keys;
- do not import recommendation, HITL, ticket, broker, order, paper, or live modules.

## Forbidden

- No default networking.
- No default DuckDB writes.
- No real ingest run without Human-Gate.
- No product route activation.
- No HITL readiness claim.
- No recommendation readiness claim.

## Human-Gate Rule

No Human-Gate is required for code rewrite and tests only.

Human-Gate is required before any command that actually uses network access, writes DuckDB/SQLite, performs bulk ingest, changes schema, changes registry activation, or changes readiness.

## Required Executor Output

```text
CODEX_ACCEPTANCE_US_DB_OPS_2

status:
ACCEPTED / ACCEPTED_WITH_WARNINGS / REJECTED

implemented_controls:
...

human_gate_required_before_real_ingest:
true

product_route_activated:
false
```

## Dispatcher Boundary

Quant-Dispatcher only created this packet. No source-project files were edited.

