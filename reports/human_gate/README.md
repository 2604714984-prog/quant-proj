# Human-Gate Records

This directory stores durable Human-Gate decision records for the controller workspace.

`decisions.jsonl` is append-only. A missing approval record means the task is not approved.

Do not store secrets, `.env` values, raw data, raw database files, or broker credentials here.

Recorded execution mode:

- L0 research/diagnostics can run by default when it stays read-only and non-networked.
- L1 DB writes require Human-Gate, `--allow-write`, snapshot id, command transcript, manifest/counts/hashes, and Codex acceptance.
- L2 network ingest requires Human-Gate, `--allow-network`, provider/date/symbol bounds, command transcript, and Codex acceptance.
- L3 registry/readiness changes require Human-Gate, old/new diff, rollback path, command transcript, and Codex acceptance.
- L4 `PENDING_HUMAN_REVIEW` ticket emission requires Human-Gate and all gates passing. It is not an order, recommendation, trade plan, fill, broker action, or execution instruction.

See `runbooks/recorded_execution_mode.md` and `runbooks/human_gate.md`.
