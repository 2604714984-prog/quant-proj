# TASK-008 Market Data Registry / Readiness Controlled Update

## Status

BACKLOG_READY_FOR_DISPATCH

## Source

ChatGPT task list: `tasks/inbox/20260704-updated-night-batch-recorded-execution-mode.md`

## Target Project

`market_data`

## Recommended Agent

`codex_dev`

## Permission Level

- `L3_REGISTRY_READINESS_CHANGE`

Human-Gate record available:

- `HG-NIGHT-BATCH-20260704-L1-L4`

## Scope

Controlled registry and readiness updates for research routes and product-read candidates.

Allowed:

- mark research route active;
- mark `product_read_candidate`;
- update registry facts from fresh DB snapshots;
- update readiness JSON for research or HITL-data prerequisites.

## Explicit Non-Scope

Not allowed by default:

- `production_recommendation_data_ready=true`;
- `broker_execution_data_ready=true`;
- `auto_execution_data_ready=true`;
- `live_trading_allowed=true`.

## Forbidden Actions

- broker API;
- order routing or submission;
- paper trading;
- live trading;
- auto execution;
- system-generated orders or fills;
- trade plan, entry price, target weight, position sizing, or allocation;
- `.env` read or key output.

## Dependencies

- Source base: `market_data` branch `main`, commit `ff24166479638b0f35e1cd7a8d0f1d01cdafb495`, tree `03ff42577d23784924511efcc7ccc7f9f3217fc4`.
- Fresh registry or DB snapshot evidence from source projects.

## Inputs

- old registry route;
- new registry route;
- reason;
- snapshot id;
- row count;
- symbol count;
- date range;
- crosscheck status;
- rollback path.

## Expected Outputs

- command transcript;
- old/new registry diff;
- rollback path;
- readiness/status report;
- Codex acceptance report under the source project.

## Validation Expectations

- structured registry/readiness parse;
- diff review;
- rollback path documented;
- safety/boundary checks;
- `git diff --check`;
- Codex acceptance verdict.

## Human Approval Needed?

Yes. `HG-NIGHT-BATCH-20260704-L1-L4` is available for bounded research/readiness updates until `2026-07-05T08:00:00+08:00`.
