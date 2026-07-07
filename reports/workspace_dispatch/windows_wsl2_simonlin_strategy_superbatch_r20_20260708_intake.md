# WINDOWS_WSL2_SIMONLIN_STRATEGY_SUPERBATCH_R20_V2_20260708 Intake

Project: quant-proj
Role: Quant-Dispatcher
Imported: 2026-07-08 Asia/Shanghai
Source: user-attached R20_V2 task package and direct R20 authorization message
Status: `DISPATCH_PREPARED`

## Classification

Large research-only SimonLin strategy superbatch.

External-audit trigger opened by R20_V2 intake: `no`.

Reason:

- The user explicitly authorized bounded public/no-secret research data fetches, source-local research cache/staging/report/test writes, isolated dependency installation, GPU/CPU numerical research, experiment-store tooling, and friction-reduction tools for this batch.
- The user explicitly did not authorize recommendation, ticket, candidate promotion, readiness, product-route activation, market_data activation, broker/order/paper/live/auto, raw-data migration into `quant-proj`, active schema/registry changes, or secret access/output.
- R20_V2 is designed to absorb R16-R19 failures first, then perform delta research only where new data, new features, new regime evidence, or new execution assumptions justify a retry.

## R19 Facts To Preserve

- R19 is `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`.
- ETF dataset remains `etf_rotation_e1_20260707` with 30 symbols and 55,726 qfq OHLCV rows.
- ETF timing remains close T signal and T+1 open execution.
- Same-day close-to-close execution remains false.
- ETF robust grid v2 emitted 9,600 pre-registered validation rows.
- ETF grid label counts: `COST_LIMITED=3340`, `WEAK=1638`, `UNSTABLE=4578`, `INTERESTING=44`.
- ETF final hypothesis board emitted 0 final `INTERESTING` rows.
- Equity R19 clustered 130 R18 rows into 23 failure-mode/family clusters.
- Equity rescue diagnostics emitted 12 instability rows and 24 validation-failure rows.
- Equity wide eligible count is 0.
- Equity wide result is `NO_R19_EQUITY_WIDE_RESEARCH_PROBE_ELIGIBLE`.
- `STRATEGY_CANDIDATE_AVAILABLE=false`.
- East Money split remains `77 CROSSCHECK_PASS / 121 CROSSCHECK_DATE_GAP / 2870 CROSSCHECK_MISSING_EAST_MONEY`.
- market_data product-route preparation remains inactive and externally gated.

## Primary Objective

Do not repeat R19 blindly. Import R16-R19 evidence first, build experiment-store and negative-result memory, audit the 44 R19 ETF grid rows that were initially `INTERESTING`, explain zero-wide outcomes, then integrate SimonLin public research sources and run only justified delta searches.

## Dispatch Targets

- `A_Share_Monitor`: main R20 execution, including R19 evidence freeze, friction tooling, SimonLin source intake, ETF lane, A-share new-feature lane, news/macro lane, TradingAgents template extraction, combined research board, and conditional wide probe or skip.
- `US_Stock_Monitor`: optional global/US/HK regime support using `global-stock-data` smoke and cross-market regime features.
- `market_data`: SimonLin research source contract and R20 overclaim regression only; no active route or registry changes.
- `strategy_work`: initial R20 master memo and final sync after accepted source callbacks.
- `quant-proj`: intake, authorization record, task packet, dispatch summary, result summary, and closeout.

## Boundary

Research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, readiness promotion, product-route activation, market_data activation, broker/order/paper/live/auto, daily signal push, raw-data migration into `quant-proj`, `.env` access, key output, secret handling, active schema migration, active registry activation, or actionable ranking is authorized.
