# WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707 Dispatch Summary

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-07 Asia/Shanghai
Classification: ordinary research-only strategy signal mining batch
External-audit trigger open for R17: no

## Source

- Post-R15 external-audit result: `reports/agent_handoff/windows_wsl2_post_r15_development_external_audit_result_20260707.md`
- R17 intake: `reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_intake.md`
- Task packet: `tasks/in_progress/windows-wsl2-strategy-signal-mining-batch-r17-20260707/spec.md`
- Human-Gate classification: `tasks/in_progress/windows-wsl2-strategy-signal-mining-batch-r17-20260707/human_gate.md`

## Dispatch Matrix

| Target | WSL2 thread | Assigned tasks | Send mode | Initial status |
|---|---|---|---|---|
| `A_Share_Monitor` | `019f387b-617e-7273-b539-161216ae3002` | `A-WIN-R17-1` through `A-WIN-R17-8` | prompt-only, no model/thinking override | callback received: BLOCKED_GPU_POWER_CAP_NOT_VERIFIED |
| `market_data` | `019f387b-e763-7c01-ae3d-6be552cdb6dc` | `MD-WIN-R17-1` through `MD-WIN-R17-2` | prompt-only, no model/thinking override | callback received: accepted |
| `strategy_work` | `019f3881-5293-74a1-8535-814bd83c8681` | `SW-WIN-R17-1` through `SW-WIN-R17-2` | prompt-only, no model/thinking override | handoff prepared |

## Send Status

Controller handoff artifacts are prepared. Direct app thread-send was attempted but the current Codex app tool handler returned unavailable. Subsequent prompt-only downstream callbacks were received from A_Share_Monitor and market_data.

Handoff files:

- A_Share_Monitor: `tasks/in_progress/windows-wsl2-strategy-signal-mining-batch-r17-20260707/handoff_a_share.md`
- market_data: `tasks/in_progress/windows-wsl2-strategy-signal-mining-batch-r17-20260707/handoff_market_data.md`
- strategy_work: `tasks/in_progress/windows-wsl2-strategy-signal-mining-batch-r17-20260707/handoff_strategy_work.md`

## Callback Records

- A_Share_Monitor: `reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_a_share_callback.md`
- market_data: `reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_market_data_callback.md`
- Result summary: `reports/workspace_dispatch/windows_wsl2_strategy_signal_mining_batch_r17_20260707_result_summary.md`

## Callback Target

All downstream threads must send prompt-only callbacks to:

```text
019f3830-4b44-7a83-944d-247a0d4dc169
```

## Boundary

R17 is research-only and non-actionable. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, `.env` access, key output, secret handling, schema/readiness/registry change, market_data activation, or >400W GPU operation is authorized.

Future provider/network fetch, DB/cache write or rebuild, route activation, and GPU operation above 400W require separate task-level authorization.
