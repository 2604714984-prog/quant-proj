# WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708 Dispatch Summary

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-08 Asia/Shanghai
Classification: ordinary research-only feature materialization and strategy-delta batch
External-audit trigger open for R21: `no`

## Source

- User-provided R20_V2 GitHub connector external audit result.
- R21 intake: `reports/workspace_dispatch/windows_wsl2_feature_materialization_and_strategy_delta_r21_20260708_intake.md`
- R21 task packet: `tasks/in_progress/windows-wsl2-feature-materialization-and-strategy-delta-r21-20260708/spec.md`
- R21 checklist: `tasks/checklists/r21_execution_checklist_20260708.md`
- R20 external audit result: `reports/agent_handoff/windows_wsl2_simonlin_strategy_superbatch_r20_v2_external_audit_result_20260708.md`

## Dispatch Matrix

| Target | WSL2 thread | Assigned tasks | Send mode | Status |
|---|---|---|---|---|
| `A_Share_Monitor` | `019f387b-617e-7273-b539-161216ae3002` | Lane 0, Lane 1, Lane 2, Lane 3 partial, Lane 4 | prompt-only, no model/thinking override | dispatched |
| `US_Stock_Monitor` | `019f387b-a161-7ad0-8678-f03a099612ba` | Optional `G-R21-1` global/US/HK regime support | prompt-only, no model/thinking override | dispatched |
| `market_data` | `019f387b-e763-7c01-ae3d-6be552cdb6dc` | `MD-R21-1` through `MD-R21-2` | prompt-only, no model/thinking override | dispatched |
| `strategy_work` | `019f3881-5293-74a1-8535-814bd83c8681` | `SW-R21-1` through `SW-R21-2` | prompt-only, no model/thinking override | dispatched; final sync gated |

## Handoff Files

- A_Share_Monitor: `tasks/in_progress/windows-wsl2-feature-materialization-and-strategy-delta-r21-20260708/handoff_a_share.md`
- US_Stock_Monitor: `tasks/in_progress/windows-wsl2-feature-materialization-and-strategy-delta-r21-20260708/handoff_us_stock.md`
- market_data: `tasks/in_progress/windows-wsl2-feature-materialization-and-strategy-delta-r21-20260708/handoff_market_data.md`
- strategy_work: `tasks/in_progress/windows-wsl2-feature-materialization-and-strategy-delta-r21-20260708/handoff_strategy_work.md`

## Dispatch Notes

- R21 must freeze R20 evidence and limitations before new diagnostics.
- R21 must import R20 outputs into experiment store and failure memory before diagnostics.
- R21 must run source-health before fetch-heavy work.
- R21 should materialize ETF amount/NAV/premium if possible, otherwise preserve limitation labels.
- R21 should materialize A-share PEG/event/funds/hot-money rows if sources pass health checks.
- R21 should skip strategy diagnostics if no validated local feature rows or no improved ETF fields exist.

## Boundary

Research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, readiness promotion, product-route activation, market_data activation, broker/order/paper/live/auto, daily signal push, raw-data migration into `quant-proj`, `.env` access, key output, secret handling, active schema/readiness/registry change, or actionable ranking is authorized.
