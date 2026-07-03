# Human-Gate - TASK-021

Required for default execution: no.

Default permission:

- `L0_RESEARCH_DIAGNOSTIC`

Human-Gate is required before any escalation to:

- DB write;
- network ingest;
- registry/readiness change;
- HITL ticket gate or ticket emission;
- source-project promotion beyond diagnostic reporting.

Future L1-L4 rule:

- create a unique `HG-EXEC-TASK-*` record before execution.

Non-authorization: no recommendation, no ticket, no broker/order/paper/live/auto, no trade plan, no `.env`, no secrets.
