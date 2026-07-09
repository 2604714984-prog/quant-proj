# Human-Gate - TASK-022

Required for default Reasonix plan: no.

Default permission:

- `L0_RESEARCH_DIAGNOSTIC`

Escalation requires Human-Gate and Codex-Dev:

- `L1_CONTROLLED_DB_WRITE`
- `L2_CONTROLLED_NETWORK_INGEST`
- `L3_REGISTRY_READINESS_CHANGE`
- `L4_PENDING_HUMAN_REVIEW_TICKET`

Future L1-L4 rule:

- create a unique `HG-EXEC-TASK-*` record before execution.

Non-authorization: no recommendation, no ticket, no broker/order/paper/live/auto, no `.env`, no secrets.
