# WINDOWS_WSL2_SIMONLIN_STRATEGY_SUPERBATCH_R20_V2_20260708 Dispatch Summary

Project: quant-proj
Role: Quant-Dispatcher
Prepared: 2026-07-08 Asia/Shanghai
Classification: large research-only SimonLin strategy superbatch
External-audit trigger open for R20_V2: `no`

## Source

- User-attached R20_V2 task package.
- User direct authorization message for R20.
- R20_V2 intake: `reports/workspace_dispatch/windows_wsl2_simonlin_strategy_superbatch_r20_20260708_intake.md`
- R20_V2 authorization: `reports/human_gate/windows_wsl2_simonlin_strategy_superbatch_r20_v2_authorization_20260708.md`
- R20_V2 task packet: `tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/spec.md`
- R20_V2 Human-Gate classification: `tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/human_gate.md`

## Dispatch Matrix

| Target | WSL2 thread | Assigned tasks | Send mode | Status |
|---|---|---|---|---|
| `A_Share_Monitor` | `019f387b-617e-7273-b539-161216ae3002` | Lane 0, Lane 1, Lane 2, Lane 3, Lane 4, Lane 6, Lane 7, Lane 8 | prompt-only, no model/thinking override | dispatched |
| `US_Stock_Monitor` | `019f387b-a161-7ad0-8678-f03a099612ba` | Optional Lane 5 global/US/HK regime support | prompt-only, no model/thinking override | dispatched |
| `market_data` | `019f387b-e763-7c01-ae3d-6be552cdb6dc` | `MD-R20-1` through `MD-R20-2` | prompt-only, no model/thinking override | dispatched |
| `strategy_work` | `019f3881-5293-74a1-8535-814bd83c8681` | `SW-R20-1` through `SW-R20-2` | prompt-only, no model/thinking override | dispatched; final sync gated on accepted source callbacks |

## Handoff Files

- A_Share_Monitor: `tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/handoff_a_share.md`
- US_Stock_Monitor: `tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/handoff_us_stock.md`
- market_data: `tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/handoff_market_data.md`
- strategy_work: `tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/handoff_strategy_work.md`

## Dispatch Notes

- R20_V2 must import R16-R19 evidence before new search.
- R20_V2 must audit R19's 44 initially interesting ETF grid rows before ETF delta search.
- R20_V2 must build experiment-store and failure memory before new strategy search.
- A-share retries are allowed only with new data, new feature, new regime, new universe, or new execution evidence.
- SimonLin sources are research-only inputs and cannot become recommendation, candidate, readiness, product route, or daily signal evidence.

## Boundary

Research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, readiness promotion, product-route activation, market_data activation, broker/order/paper/live/auto, daily signal push, raw-data migration into `quant-proj`, `.env` access, key output, secret handling, active schema/readiness/registry change, or actionable ranking is authorized.

Future product-route activation, readiness change, active registry/schema change, raw-data migration into `quant-proj`, ticket/candidate creation, broker/order/paper/live/auto, daily signal push, or trading path work requires a separate explicit authorization and any required audit gate.
