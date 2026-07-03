# TASK-010 Handoff

Role: `Codex-Dev`
Target project: `/Users/rongyuxu/Desktop/US_Stock_Monitor`
Task: `US strategy experiment to ticket refresh attempt`

## Base

- branch: `codex/duckdb-provider`
- commit: `c046c0ce56e5ea501aa2600df410b80b58d412fb`
- tree: `4c042e79c23584af3fca173a6817ea26d9e3ee81`

## Authorization

Use recorded execution mode only:

- Human-Gate: `HG-NIGHT-BATCH-20260704-L1-L4`
- permission: `L4_PENDING_HUMAN_REVIEW_TICKET`
- may emit `PENDING_HUMAN_REVIEW` only if all gates pass
- requires command transcript, gate report, schema validation, and Codex acceptance

## Work

Run US strategy experiments and ticket refresh. If blocked, preserve `NO_RECOMMENDATION_AVAILABLE` and do not emit a ticket.

## Must Return

- status: `ACCEPTED`, `ACCEPTED_WITH_WARNINGS`, or `REJECTED`
- commands run and transcript path
- gate status
- eligibility candidate status
- ticket emitted true/false
- ticket path if emitted
- validation results
- explicit boundary flags

## Forbidden

No broker/order/paper/live/auto, no production recommendation runtime, no direct buy/sell advice, no trade plan, no entry price, no target weight, no position sizing, no allocation, no system-generated order/fill, no key output.
