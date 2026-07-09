# TASK-008 Handoff

Role: `Codex-Dev`
Target project: `/Users/rongyuxu/Desktop/market_data`
Task: `market_data registry/readiness controlled update`

## Base

- branch: `main`
- commit: `ff24166479638b0f35e1cd7a8d0f1d01cdafb495`
- tree: `03ff42577d23784924511efcc7ccc7f9f3217fc4`

## Authorization

Use recorded execution mode only:

- Human-Gate: `HG-NIGHT-BATCH-20260704-L1-L4`
- permission: `L3_REGISTRY_READINESS_CHANGE`
- requires old/new diff, rollback path, command transcript, and Codex acceptance

## Work

Update research-route or product-read-candidate registry/readiness state only if evidence supports it.

Do not set production recommendation, broker execution, auto execution, or live trading readiness true.

## Must Return

- status: `ACCEPTED`, `ACCEPTED_WITH_WARNINGS`, or `REJECTED`
- old route and new route
- snapshot id
- row count, symbol count, date range
- crosscheck status
- rollback path
- commands run and transcript path
- validation results
- explicit boundary statement

## Forbidden

No broker/live/auto readiness, no production recommendation readiness unless separately justified and Codex accepted, no order/trade/position output, no `.env`, no key output.
