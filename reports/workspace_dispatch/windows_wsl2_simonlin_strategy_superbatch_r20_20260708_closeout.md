# WINDOWS_WSL2_SIMONLIN_STRATEGY_SUPERBATCH_R20_V2_20260708 Closeout

Project: quant-proj
Role: Quant-Dispatcher
Closed: 2026-07-08 Asia/Shanghai
Status: `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`
Classification: ordinary research-only SimonLin strategy superbatch
External-audit trigger open: `no`

## Source Results

| Target | Commit | Tree | Status |
|---|---|---|---|
| `A_Share_Monitor` | `a501694533f8548c44237ac746b525348fc18173` | `76cbaecf9d8f7f492ec4f8f9820d5505436a4ec3` | accepted and pushed; R20 source lanes complete |
| `market_data` | `e72b45de8bb7998dee411beaff8f7736b906da2e` | `0e7fe7a53a2a04b4d7598661907411d1de6c403e` | accepted and pushed; source contract and overclaim support complete |
| `US_Stock_Monitor` | `9099a0b40eb48cddff8161e3357286b34f1623d0` | `5d1985de1f427866a409dccf04ae6eee777c0f22` | accepted and pushed; optional global support complete |
| `strategy_work` | `0b9f9e72824090a902a644749220505c0940c370` | `037c3b2f23e7d63537b2c8213c9b61568f1e860d` | final sync accepted and pushed |

## Result

R20_V2 is closed as research-only with warnings.

Accepted outcomes:

- market_data completed `MD-R20-1` and `MD-R20-2`.
- strategy_work completed `SW-R20-1` and `SW-R20-2`.
- A_Share_Monitor completed assigned Lane 0, Lane 1, Lane 2, Lane 3, Lane 4, Lane 6, Lane 7, and Lane 8 work.
- US_Stock_Monitor completed optional global support `G-R20-1` and `G-R20-2`.
- Source health checks passed before source-heavy work.
- Source-local experiment store and failure memory were created before new delta search.
- R16-R19 evidence was frozen before new search.
- All 44 R19 initially interesting ETF rows were audited before ETF delta search.
- R20 ETF delta rows remained `UNSTABLE=24` and `COST_LIMITED=20`.
- Combined research board emitted 3 non-actionable rows.
- Conditional wide result is `NO_R20_WIDE_RESEARCH_PROBE_ELIGIBLE`.
- No wide probe and no full-frame wide3068 were run.

## Preserved Facts

- `STRATEGY_CANDIDATE_AVAILABLE=false`.
- `WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT=0`.
- `wide_probe_executed=false`.
- `full_frame_wide3068_executed=false`.
- ETF E1 dataset remains research-only: `etf_rotation_e1_20260707`, 30 symbols, 55,726 qfq OHLCV rows.
- ETF timing remains close T signal and T+1 open execution.
- Same-day close-to-close execution remains false.
- R19 ETF grid v2 was not repeated.
- East Money split remains `77 CROSSCHECK_PASS`, `121 CROSSCHECK_DATE_GAP`, `2870 CROSSCHECK_MISSING_EAST_MONEY`.
- market_data product-route preparation remains inactive and separately externally gated.
- US/global support produced research-only regime evidence only.

## Warnings

- ETF amount/NAV/premium remain unavailable in the local Tencent qfq source; liquidity-related ETF results use a volume proxy and must keep that limitation label.
- A-share new-feature lane is source-review only; `features_daily_v2_research` generated no validated local feature rows.
- News/macro attribution remains context-only with `direct_signal_use=false`.
- TradingAgents-astock output is role-template structure only, not directional decision output.
- Optional US/global support had an optional raw GitHub reference WARN, while required public endpoints passed.
- R20_V2 created no candidate, no readiness, no route activation, and no daily signal.

## Boundary

Research-only boundary preserved. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, readiness/product-route/market_data activation, production readiness, broker/order/paper/live/auto path, daily signal push, raw-data migration into `quant-proj`, active schema/registry change, full-frame wide3068, actionable ranking, directional TradingAgents decision output, news/macro direct signal use, test-result parameter selection, or secret output occurred.

External-audit trigger open: `no`.

## Next Action

No R20_V2 implementation task remains open. A future ETF, equity, SimonLin-source, or global-regime research batch may continue diagnostics, but it must be dispatched as a separate task unless the user explicitly changes scope.
