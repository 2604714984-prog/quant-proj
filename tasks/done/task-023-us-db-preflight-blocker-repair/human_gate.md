# Human-Gate - TASK-023

Required for default read-only repair/dry-run: no.

Required before any controlled execution:

- DB write: yes, unique `HG-EXEC-TASK-*` required before command.
- network ingest: yes, unique `HG-EXEC-TASK-*` required before command.
- readiness change: yes, unique `HG-EXEC-TASK-*` required before command.

Default permission:

- `L0_RESEARCH_DIAGNOSTIC`

Non-authorization: no recommendation, no ticket, no broker/order/paper/live/auto, no `.env`, no secrets.
