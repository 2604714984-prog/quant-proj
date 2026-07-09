# Human-Gate Classification: WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_20260707

Decision date: 2026-07-07 Asia/Shanghai
Controller: Quant-Dispatcher

## Classification

Ordinary research-only strategy-family batch.

External-audit trigger open: `no`.

Task-level HG-EXEC present: `no`.

## Allowed

- Local-only research on already available ETF data.
- Report generation.
- Local validation and tests.
- Pre-registered parameter grid, walk-forward, cost/slippage, regime, contribution, bootstrap/permutation, and research-only leaderboard artifacts.

## Not Authorized

- Provider/network fetch.
- DB/cache write or rebuild.
- Schema/readiness/registry change.
- market_data activation.
- product-route activation.
- recommendation/advice.
- `PENDING_HUMAN_REVIEW`.
- ticket.
- eligibility candidate.
- strategy candidate promotion.
- production readiness.
- broker/order/paper/live/auto.
- daily signal push.
- raw-data migration.
- `.env`, key, token, auth, credential, or secret access/output.

## Stop Rule

If required ETF data is not locally available, downstream must stop and return `HG_EXEC_REQUIRED_FOR_ETF_DATA_FETCH`. This classification does not authorize provider/network fetch.
