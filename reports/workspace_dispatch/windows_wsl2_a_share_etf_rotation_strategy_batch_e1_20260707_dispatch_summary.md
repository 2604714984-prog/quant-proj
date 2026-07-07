# WINDOWS_WSL2_A_SHARE_ETF_ROTATION_STRATEGY_BATCH_E1_20260707 Dispatch Summary

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-07 Asia/Shanghai
Classification: ordinary research-only A-share ETF rotation strategy-family batch
External-audit trigger open for E1: `no`

## Source

- E1 intake: `reports/workspace_dispatch/windows_wsl2_a_share_etf_rotation_strategy_batch_e1_20260707_intake.md`
- E1 task packet: `tasks/in_progress/windows-wsl2-a-share-etf-rotation-strategy-batch-e1-20260707/spec.md`
- E1 Human-Gate classification: `tasks/in_progress/windows-wsl2-a-share-etf-rotation-strategy-batch-e1-20260707/human_gate.md`

## Dispatch Matrix

| Target | WSL2 thread | Assigned tasks | Send mode | Status |
|---|---|---|---|---|
| `A_Share_Monitor` | `019f387b-617e-7273-b539-161216ae3002` | `ETF-E1-1` through `ETF-E1-11` | prompt-only, no model/thinking override | dispatched |

## Handoff Files

- A_Share_Monitor: `tasks/in_progress/windows-wsl2-a-share-etf-rotation-strategy-batch-e1-20260707/handoff_a_share.md`

## Boundary

E1 is research-only and non-actionable. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, daily signal push, raw-data migration, `.env` access, key output, secret handling, provider/network fetch, DB/cache write or rebuild, schema/readiness/registry change, market_data activation, or actionable ranking is authorized.

If local ETF data is unavailable, downstream must stop with `HG_EXEC_REQUIRED_FOR_ETF_DATA_FETCH`.
