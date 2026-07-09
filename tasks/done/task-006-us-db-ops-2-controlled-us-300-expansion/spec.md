# TASK-006 US-DB-OPS-2 Controlled US 300-Symbol Expansion

## Status

BACKLOG_READY_FOR_DISPATCH

## Source

ChatGPT task list: `tasks/inbox/20260704-updated-night-batch-recorded-execution-mode.md`

## Target Project

`US_Stock_Monitor`

## Recommended Agent

`codex_dev`

## Permission Level

- `L1_CONTROLLED_DB_WRITE`
- `L2_CONTROLLED_NETWORK_INGEST`

Human-Gate record available:

- `HG-NIGHT-BATCH-20260704-L1-L4`

If that record is expired or scope no longer matches, create a replacement Human-Gate record before execution.

## Scope

Run a controlled US 300-symbol expansion using the controlled DB ops helper accepted in TASK-003.

Allowed only when explicitly flagged:

- network ingest with `--allow-network`;
- DuckDB write with `--allow-write`;
- bounded provider/date/symbol scope;
- manifest/readiness/crosscheck report generation.

## Explicit Non-Scope

- no product route activation unless separately approved by L3 task;
- no recommendation runtime;
- no HITL ticket emission;
- no broker/order/paper/live/auto behavior.

## Forbidden Actions

- `.env` read;
- key value output;
- broker API;
- order routing or submission;
- paper trading;
- live trading;
- auto execution;
- system-generated orders or fills;
- broker-synced fills;
- trade plan, entry price, target weight, position sizing, or allocation.

## Dependencies

- Source base: `US_Stock_Monitor` branch `codex/duckdb-provider`, commit `c046c0ce56e5ea501aa2600df410b80b58d412fb`, tree `4c042e79c23584af3fca173a6817ea26d9e3ee81`.
- TASK-003 warning must be preserved: existing AAPL duplicate daily rows were detected by read-only audit.

## Inputs

- controlled helper: `scripts/db_ops/expand_us_universe.py`
- old-path shim: `scripts/expand_us_300.py`
- maximum symbols: `300`
- required snapshot id prefix: `us_expand_20260704`

## Expected Outputs

- command transcript;
- manifest with counts and hashes;
- readiness/crosscheck report;
- Codex acceptance report under the source project;
- no raw data committed.

## Validation Expectations

- safety check;
- targeted DB ops helper tests;
- manifest/hash validation;
- source-project smoke checks relevant to the change;
- `git diff --check`;
- Codex acceptance verdict.

## Human Approval Needed?

Yes. `HG-NIGHT-BATCH-20260704-L1-L4` is available for this bounded batch until `2026-07-05T08:00:00+08:00`, but execution still needs command transcript and Codex acceptance.
