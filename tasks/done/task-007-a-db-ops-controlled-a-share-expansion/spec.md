# TASK-007 A-DB-OPS Controlled A-Share Expansion

## Status

BACKLOG_READY_FOR_DISPATCH

## Source

ChatGPT task list: `tasks/inbox/20260704-updated-night-batch-recorded-execution-mode.md`

## Target Project

`A_Share_Monitor`

## Recommended Agent

`codex_dev`

## Permission Level

- `L1_CONTROLLED_DB_WRITE`
- `L2_CONTROLLED_NETWORK_INGEST` if a remote provider is used

Human-Gate record available:

- `HG-NIGHT-BATCH-20260704-L1-L4`

## Scope

Controlled A-share 500/1000 data expansion.

Allowed:

- expand canonical snapshot;
- write local DuckDB with `--allow-write`;
- run provider ingest with `--allow-network`;
- write ignored cache/parquet only if scoped;
- generate manifest/counts/coverage.

## Explicit Non-Scope

- active registry unchanged unless an L3 task approves it;
- no recommendation ticket unless a separate L4 task passes all gates;
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

- Source base: `A_Share_Monitor` branch `codex/harden-a-share-research-pipeline`, commit `012006c40897f999f2a2ba5c69e2630b9d50a552`, tree `2447205526791e6bcf3f9b18b512d9fc7093c75c`.
- TASK-004 classification: `scripts/expand_canonical_500.py` is `NEEDS_REWRITE` before use.

## Inputs

- max symbols: `1000`
- provider: explicit at execution time
- snapshot id prefix: `a_expand_20260704`

## Expected Outputs

- command transcript;
- manifest/counts/hashes;
- coverage/readiness report;
- Codex acceptance report under the source project;
- no raw data committed.

## Validation Expectations

- safety check;
- targeted DB ops tests or smoke coverage;
- manifest/hash validation;
- source-project smoke checks relevant to the change;
- `git diff --check`;
- Codex acceptance verdict.

## Human Approval Needed?

Yes. `HG-NIGHT-BATCH-20260704-L1-L4` is available for this bounded batch until `2026-07-05T08:00:00+08:00`, but execution still needs command transcript and Codex acceptance.
