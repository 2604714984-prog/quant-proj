# TASK-006 Handoff

Role: `Codex-Dev`
Target project: `/Users/rongyuxu/Desktop/US_Stock_Monitor`
Task: `US-DB-OPS-2 controlled US 300-symbol expansion`

## Base

- branch: `codex/duckdb-provider`
- commit: `c046c0ce56e5ea501aa2600df410b80b58d412fb`
- tree: `4c042e79c23584af3fca173a6817ea26d9e3ee81`

## Authorization

Use recorded execution mode only:

- Human-Gate: `HG-NIGHT-BATCH-20260704-L1-L4`
- permission: `L1_CONTROLLED_DB_WRITE + L2_CONTROLLED_NETWORK_INGEST`
- requires `--allow-network` before any network ingest
- requires `--allow-write` before any DB write
- requires command transcript, manifest/counts/hashes, and Codex acceptance

If the authorization is expired or scope does not match, stop and request a new Human-Gate record.

## Work

Run the controlled US expansion path for up to 300 symbols with explicit provider/date/symbol bounds.

Preserve TASK-003 warning: existing AAPL duplicate daily rows were detected. Do not hide this state; either stop before write or document the accepted bounded handling.

## Must Return

- status: `ACCEPTED`, `ACCEPTED_WITH_WARNINGS`, or `REJECTED`
- commands run and transcript path
- provider/date/symbol bounds
- snapshot id
- manifest/counts/hashes
- changed files
- validation results
- explicit boundary statement

## Forbidden

No `.env`, no key output, no broker/order/paper/live/auto, no recommendation, no HITL ticket, no product route activation unless separately authorized.
