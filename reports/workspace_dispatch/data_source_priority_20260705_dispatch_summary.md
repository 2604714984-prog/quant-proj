# DATA_SOURCE_PRIORITY_20260705 Dispatch Summary

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-05
Classification: ordinary research/data-source evidence work
External-audit trigger open: no

## Reason For Dispatch

The user requested that `FeatureStore.build()` be fixed first, then the attached simonlin1212 repository review be prioritized with data-source issues first. The FeatureStore memory guard is pushed in A_Share_Monitor commit `18c19016809210780272512b99b6dd07be074425`.

Controller coordination record:

- `reports/workspace_dispatch/data_source_coordination_20260705.md`

## Dispatched Tasks

| Task | Target | Thread | Status |
|---|---|---|---|
| `DS-US-1` | `US_Stock_Monitor` | `019f32bd-af98-7eb0-bc5c-d1067e1fb145` | sent |
| `MD-DS-1` | `market_data` | `019f3283-a821-7002-961b-6f533d3518c2` | sent |
| `DS-A-1` | `A_Share_Monitor` | `019f32bd-082d-73e2-b902-3d48b8d198ba` | sent as after-R12 follow-up |
| `SW-DS-1` | `strategy_work` | `019f30c3-247e-7f43-af60-96164539a183` | sent |

## Task Intent

`DS-US-1`:

- Build a research-only provider/export contract from `simonlin1212/global-stock-data`.
- Cover Yahoo chart, Yahoo quoteSummary, SEC CIK/EDGAR/XBRL, Eastmoney, Sina, and Tencent as possible sources.
- No network, no DB write, no provider-data persistence.

`MD-DS-1`:

- Add negative evidence-misuse contract tests.
- Prove provider code or endpoint existence does not imply imported evidence, data-clear, product-read, readiness, ticket, or runtime permission.

`DS-A-1`:

- After A-share R12 closeout, build a research-only provider/export contract from `simonlin1212/a-stock-data`.
- Cover K-line, adjustment policy, amount/turnover/market cap, industry/concept, announcements/news, interactive Q&A, hot lists, limit-up boards, 龙虎榜, 解禁, financing, shareholder counts, dividends, ETF/options, and sentiment sources.
- No network, no DB write, no provider-data persistence.

`SW-DS-1`:

- Park `investment-news`, `astock-peg`, `TradingAgents-astock`, `globalpercent`, and `Hiring-Radar` as research-only memo/enrichment ideas.
- Do not promote trader/investment-plan/valuation advice language.

## Boundary Statement

This dispatch does not authorize recommendations, `PENDING_HUMAN_REVIEW`, ticket emission, eligibility candidates, product-route activation, production readiness, broker/order/paper/live/auto behavior, DB writes, network ingest, provider-data persistence, registry/readiness changes, raw-data migration into quant-proj, `.env` reads, key output, or secret handling. Future fetch/import work requires task-level `HG-EXEC`, transcript, source artifacts, Codex-Dev validation, and appropriate audit gates before affecting research data state.
