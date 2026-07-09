# TASK-025 market_data Access-Gate Regression

## Status

QUEUED_P1

## Target Project

`market_data`

## Recommended Agent

`Codex-Dev`

## Goal

Add tests proving:

- A-share 1000-symbol `WARNING` Level 1 route cannot become `product_read_allowed=true`;
- US blocked route cannot become `product_read_allowed=true`;
- `production_recommendation_data_ready` cannot become true;
- broker/live/auto cannot become true.

## Expected Output

`CODEX_ACCEPTANCE_TASK_025_MARKET_DATA_ACCESS_GATE`

## Boundary

No production readiness, no recommendation, no ticket, no broker/order/paper/live/auto.
