# TASK-009 Handoff

Role: `Codex-Dev`
Target project: `/Users/rongyuxu/Desktop/A_Share_Monitor`
Task: `A11 research-to-HITL gated ticket attempt`

## Base

- branch: `codex/harden-a-share-research-pipeline`
- commit: `012006c40897f999f2a2ba5c69e2630b9d50a552`
- tree: `2447205526791e6bcf3f9b18b512d9fc7093c75c`

## Authorization

Use recorded execution mode only:

- Human-Gate: `HG-NIGHT-BATCH-20260704-L1-L4`
- permission: `L4_PENDING_HUMAN_REVIEW_TICKET`
- may emit `PENDING_HUMAN_REVIEW` only if all gates pass
- requires command transcript, gate report, schema validation, and Codex acceptance

## Work

Run A11 research and ticket-gate attempt. If no candidate passes, return `NO_RECOMMENDATION_AVAILABLE` and do not emit a ticket.

## Must Return

- status: `ACCEPTED`, `ACCEPTED_WITH_WARNINGS`, or `REJECTED`
- commands run and transcript path
- gate status
- candidate count
- ticket emitted true/false
- ticket path if emitted
- validation results
- explicit boundary flags

## Forbidden

No broker/order/paper/live/auto, no trade plan, no entry price, no target weight, no position sizing, no allocation, no system-generated order/fill, no key output.
