# WINDOWS_WSL2_PARALLEL_STRATEGY_SEARCH_BATCH_R19_20260707 Dispatch Summary

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-08 Asia/Shanghai
Classification: ordinary research-only parallel strategy search batch
External-audit trigger open for R19: `no`

## Source

- Fastpath / R18 external-audit result: `reports/agent_handoff/windows_wsl2_fastpath_and_r18_external_audit_result_20260708.md`
- R19 intake: `reports/workspace_dispatch/windows_wsl2_parallel_strategy_search_batch_r19_20260707_intake.md`
- R19 task packet: `tasks/in_progress/windows-wsl2-parallel-strategy-search-batch-r19-20260707/spec.md`
- R19 Human-Gate classification: `tasks/in_progress/windows-wsl2-parallel-strategy-search-batch-r19-20260707/human_gate.md`

## Dispatch Matrix

| Target | WSL2 thread | Assigned tasks | Send mode | Status |
|---|---|---|---|---|
| `A_Share_Monitor` | `019f387b-617e-7273-b539-161216ae3002` | `ETF-R19-1` through `ETF-R19-7`; `A-WIN-R19-1` through `A-WIN-R19-5` | prompt-only, no model/thinking override | dispatched |
| `market_data` | `019f387b-e763-7c01-ae3d-6be552cdb6dc` | `MD-R19-1` through `MD-R19-2` | prompt-only, no model/thinking override | dispatched |
| `strategy_work` | `019f3881-5293-74a1-8535-814bd83c8681` | `SW-R19-1` through `SW-R19-2` | prompt-only, no model/thinking override | dispatched; final sync gated on source callbacks |

## Handoff Files

- A_Share_Monitor: `tasks/in_progress/windows-wsl2-parallel-strategy-search-batch-r19-20260707/handoff_a_share.md`
- market_data: `tasks/in_progress/windows-wsl2-parallel-strategy-search-batch-r19-20260707/handoff_market_data.md`
- strategy_work: `tasks/in_progress/windows-wsl2-parallel-strategy-search-batch-r19-20260707/handoff_strategy_work.md`

## Boundary

R19 is research-only and non-actionable. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, daily signal push, raw-data migration, `.env` access, key output, secret handling, active schema/readiness/registry change, market_data activation, full-frame wide strategy search, or ranked actionable list is authorized.

Future DB/cache write outside research fastpath scope, route activation, schema/readiness/registry change, raw-data migration, daily signal push, or market_data activation requires separate explicit authorization and any required audit gate.
