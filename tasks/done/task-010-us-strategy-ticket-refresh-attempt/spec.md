# TASK-010 US Strategy Ticket Refresh Attempt

## Status

BACKLOG_READY_FOR_DISPATCH

## Source

ChatGPT task list: `tasks/inbox/20260704-updated-night-batch-recorded-execution-mode.md`

## Target Project

`US_Stock_Monitor`

## Recommended Agent

`codex_dev`

## Permission Level

- `L4_PENDING_HUMAN_REVIEW_TICKET`

Human-Gate record available:

- `HG-NIGHT-BATCH-20260704-L1-L4`

## Scope

Run US strategy experiments and attempt ticket refresh only if feedback, evidence, risk, and eligibility gates pass.

Allowed:

- update evidence re-entry or eligibility precheck;
- call ticket-refresh gate;
- emit `PENDING_HUMAN_REVIEW` only if all gates pass.

## Explicit Non-Scope

- no production recommendation runtime;
- no direct buy/sell advice;
- no trade plan;
- no entry price;
- no target weight;
- no position sizing;
- no allocation;
- no broker/order/paper/live/auto behavior.

## Dependencies

- Source base: `US_Stock_Monitor` branch `codex/duckdb-provider`, commit `c046c0ce56e5ea501aa2600df410b80b58d412fb`, tree `4c042e79c23584af3fca173a6817ea26d9e3ee81`.
- TASK-002 blockers must be preserved unless evidence changes: `evidence_gap`, `insufficient_feedback`, `no_eligibility_candidate`.

## Inputs

- US strategy experiments;
- ticket refresh gate;
- ticket schema;
- ignored ticket ledger path.

## Expected Outputs

- command transcript;
- gate-status report;
- `PENDING_HUMAN_REVIEW` ticket only if all gates pass;
- otherwise `NO_RECOMMENDATION_AVAILABLE`;
- Codex acceptance report under the source project.

## Validation Expectations

- safety check;
- relevant US strategy/ticket gate tests;
- schema validation;
- boundary flags false for broker/order/manual-fill/paper/live/auto;
- `git diff --check`;
- Codex acceptance verdict.

## Human Approval Needed?

Yes. `HG-NIGHT-BATCH-20260704-L1-L4` is available for bounded L4 attempt until `2026-07-05T08:00:00+08:00`.
