# Human-Gate - TASK-009

Required: yes

Available record:

- `HG-NIGHT-BATCH-20260704-L1-L4`

Permission level:

- `L4_PENDING_HUMAN_REVIEW_TICKET`

Execution requirements:

- command transcript;
- all gates pass before ticket emission;
- ticket status exactly `PENDING_HUMAN_REVIEW`;
- `human_review_required=true`;
- broker/order/manual-fill/paper/live/auto flags false;
- Codex acceptance.

Non-authorization:

This record does not authorize recommendations, buy/sell advice, broker/order paths, paper/live trading, auto execution, trade plans, entry prices, target weights, position sizing, allocation, system-generated orders, system-generated fills, broker-synced fills, `.env` reads, or key output.
