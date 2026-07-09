# TASK-009 A11 Research-To-HITL Gated Ticket Attempt

## Status

BACKLOG_READY_FOR_DISPATCH

## Source

ChatGPT task list: `tasks/inbox/20260704-updated-night-batch-recorded-execution-mode.md`

## Target Project

`A_Share_Monitor`

## Recommended Agent

`codex_dev`

## Permission Level

- `L4_PENDING_HUMAN_REVIEW_TICKET`

Human-Gate record available:

- `HG-NIGHT-BATCH-20260704-L1-L4`

## Scope

Run A11 research and attempt a gated `PENDING_HUMAN_REVIEW` ticket only if all data, evidence, micro, and risk gates pass.

Allowed:

- run A11 experiments;
- if gates pass, emit `PENDING_HUMAN_REVIEW` only;
- write ignored ticket ledger;
- require `human_review_required=true`.

## Explicit Non-Scope

- no forced ticket if no eligible candidate exists;
- no buy/sell advice;
- no trade plan;
- no entry price;
- no target weight;
- no position sizing;
- no allocation;
- no broker/order/paper/live/auto behavior.

## Dependencies

- Source base: `A_Share_Monitor` branch `codex/harden-a-share-research-pipeline`, commit `012006c40897f999f2a2ba5c69e2630b9d50a552`, tree `2447205526791e6bcf3f9b18b512d9fc7093c75c`.
- Prior A10/A11 outcome may still be `NO_RECOMMENDATION_AVAILABLE`; this must be preserved if no candidate passes gates.

## Inputs

- A11 research runner;
- gate references;
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
- relevant A11/gate/ticket tests;
- schema validation;
- boundary flags false for broker/order/manual-fill/paper/live/auto;
- `git diff --check`;
- Codex acceptance verdict.

## Human Approval Needed?

Yes. `HG-NIGHT-BATCH-20260704-L1-L4` is available for bounded L4 attempt until `2026-07-05T08:00:00+08:00`.
