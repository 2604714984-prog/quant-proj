# WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708 Intake

Project: quant-proj
Role: Quant-Dispatcher
Imported: 2026-07-08 Asia/Shanghai
Source: user-provided R20_V2 GitHub connector external audit result
Status: `DISPATCH_PREPARED`

## Classification

Ordinary research-only feature materialization and strategy-delta batch.

External-audit trigger opened by R21 intake: `no`.

Reason:

- R21 is a follow-up to R20_V2 `VERIFIED_ACCEPT_WITH_WARNINGS`.
- The task converts source-review / manifest-only evidence into validated local research feature rows where possible.
- The task preserves the existing research-only boundary and does not request recommendation, ticket, candidate promotion, readiness, product-route activation, market_data activation, broker/order/paper/live/auto, raw-data migration into `quant-proj`, active schema/registry changes, or secret access/output.

## R20 Facts To Preserve

- R20_V2 is `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`.
- `STRATEGY_CANDIDATE_AVAILABLE=false`.
- `WIDE_RESEARCH_PROBE_ELIGIBLE_COUNT=0`.
- Conditional wide output: `NO_R20_WIDE_RESEARCH_PROBE_ELIGIBLE`.
- No wide probe and no full-frame wide3068.
- ETF amount/NAV/premium unavailable in the local Tencent qfq source.
- A-share new-feature lane is source-review only; no validated local feature rows exist.
- News/macro is context-only attribution.
- TradingAgents output is role-template only.
- market_data product-route prep remains inactive and externally gated.

## Primary Objective

Materialize the evidence that R20 could only review or manifest. If real local feature rows or better ETF fields cannot be produced, preserve explicit limitation labels and skip strategy diagnostics. If new materialized evidence exists, run only bounded delta diagnostics.

## Dispatch Targets

- `A_Share_Monitor`: R20 freeze, ETF field materialization, A-share feature materialization, global/news/macro context rows, tooling, and limited delta diagnostics or skip.
- `US_Stock_Monitor`: optional global/US/HK regime row extension support.
- `market_data`: R21 feature materialization research contract and overclaim regression only.
- `strategy_work`: R21 memo and final sync after accepted source callbacks.
- `quant-proj`: intake, task packet, dispatch summary, result summary, and closeout.

## Boundary

Research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, readiness promotion, product-route activation, market_data activation, broker/order/paper/live/auto, daily signal push, raw-data migration into `quant-proj`, `.env` access, key output, secret handling, active schema migration, active registry activation, or actionable ranking is authorized.
