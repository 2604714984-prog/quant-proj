# TASK-022 A-Share L1 Snapshot Capability Repair Plan

## Status

BACKLOG_READY_FOR_DISPATCH

## Target Project

`A_Share_Monitor` / `market_data`

## Recommended Agent

`Reasonix-DB` first, then Codex-Dev only if implementation is needed.

## Permission Level

`L0_RESEARCH_DIAGNOSTIC`

## Input

`TASK-007` snapshot:

- snapshot: `a_expand_20260704_l1_local1000_0317`
- warning: suspension events missing
- warning: limit price coverage low

## Goal

Produce a data repair plan for moving the A-share 1000-symbol snapshot from Level 1 warning research data toward evidence-ready.

## Must Answer

- what table/source should provide suspension events;
- why limit price coverage is low;
- whether data exists in local DB but is not canonicalized;
- whether network ingest is required;
- what exact DB ops task is needed next.

## Expected Outputs

- `reports/deepseek_db/task_022_a_share_l1_capability_repair_plan.md`
- `reports/deepseek_db/task_022_a_share_l1_capability_repair_plan.json`

## Forbidden

No DB write, no network ingest, no schema migration, no registry activation, no readiness change, no recommendation, no ticket emission, no broker/order/paper/live/auto, no `.env` read, no secrets.
