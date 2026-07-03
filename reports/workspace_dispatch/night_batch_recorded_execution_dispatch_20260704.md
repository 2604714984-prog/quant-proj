# Night Batch Recorded Execution Dispatch

Date: 2026-07-04
Owner: `Quant-Dispatcher`
Mode: `RECORDED_EXECUTION_MODE_V1`
Status: `IN_PROGRESS`

## Human-Gate

Active batch record:

- `HG-NIGHT-BATCH-20260704-L1-L4`
- expires: `2026-07-05T08:00:00+08:00`

This authorizes recorded L1-L4 workflows only. It does not authorize broker/order/paper/live/auto execution, system-generated orders/fills, broker-synced fills, trade plans, entry prices, target weights, position sizing, allocation, `.env` reads, or key output.

## Dispatch Order

1. `TASK-006 US-DB-OPS-2 controlled US 300-symbol expansion` -> sent to `US_Stock_Monitor` Codex-Dev thread `019f2913-0031-7513-af16-017b8f990f83`.
2. `TASK-007 A-DB-OPS controlled A-share expansion` -> sent to `A_Share_Monitor` Codex-Dev thread `019f2911-ef0c-7053-aa77-a3b0bf0b05de`.
3. `TASK-008 market_data registry/readiness controlled update` -> pending data-layer results; fixed market_data Codex-Dev thread initialized as `019f2957-de0a-7721-ade9-1abfef298127`.
4. `TASK-009 A11 research-to-HITL gated ticket attempt` -> pending A-share data-layer result.
5. `TASK-010 US strategy experiment to ticket refresh attempt` -> pending US data-layer result.

## Required Evidence For Each Executed Task

- command transcript;
- explicit command flags;
- manifest/status evidence;
- Codex acceptance report;
- commit/tree if files change;
- explicit non-authorization boundary.
