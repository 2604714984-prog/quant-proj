# TASK-023 US DB Preflight Blocker Repair

## Status

BACKLOG_READY_FOR_DISPATCH

## Target Project

`US_Stock_Monitor`

## Recommended Agent

`Codex-Dev`

## Permission Level

Default: `L0_RESEARCH_DIAGNOSTIC`.

Escalate to `L1_CONTROLLED_DB_WRITE` only if a unique pre-execution `HG-EXEC-TASK-*` record exists.

## Input

`TASK-006` blocked by:

- `BLOCKED_BY_EXISTING_DB_DUPLICATES`
- `BLOCKED_BY_SYMBOLS_MISSING_FROM_METADATA`

## Goal

Fix preflight logic or metadata preparation so the next US expansion attempt can run cleanly.

## Must Implement Or Report

- duplicate detection summary;
- existing snapshot/symbol pair check;
- missing metadata symbol list;
- metadata bootstrap plan;
- read-only dry-run output;
- no network ingest unless a new `HG-EXEC-TASK-*` exists.

## Expected Output

- `reports/codex_dev/task_023_us_db_preflight_blocker_repair.md`

## Validation Expectations

- safety check;
- focused DB preflight/helper tests;
- read-only dry-run validation;
- source-project smoke or targeted regression as appropriate;
- `git diff --check`;
- commit and push scoped changes if files are changed.

## Forbidden

No network ingest unless a new `HG-EXEC-TASK-*` exists, no DB write unless a new `HG-EXEC-TASK-*` exists, no product route activation, no readiness upgrade, no recommendation, no ticket emission, no broker/order/paper/live/auto, no `.env`, no secrets.
