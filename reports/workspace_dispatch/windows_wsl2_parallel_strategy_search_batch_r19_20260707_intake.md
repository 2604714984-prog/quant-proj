# WINDOWS_WSL2_PARALLEL_STRATEGY_SEARCH_BATCH_R19_20260707 Intake

Project: quant-proj
Role: Quant-Dispatcher
Imported: 2026-07-08 Asia/Shanghai
Source: user-attached GitHub connector external-audit result and R19 next-task list
Status: `DISPATCH_PREPARED`

## Classification

Ordinary research-only parallel strategy search batch.

External-audit trigger opened by R19 intake: `no`.

Reason:

- Fastpath external audit returned `VERIFIED_ACCEPT_WITH_WARNINGS`.
- R18 external audit returned `PRELIMINARY_VERIFIED_ACCEPT_WITH_WARNINGS`.
- Fixes required: `none before the next ordinary research-only task batch`.
- R19 explicitly preserves research-only scope and forbids recommendation, ticket, eligibility candidate, strategy candidate promotion, readiness, product route, daily signal push, trading path, market_data route activation, full-frame wide strategy search, test-result parameter selection, and secret/env access.

## Accepted Carry-Forward Facts

- Fastpath catchup closed as `CLOSED_ACCEPTED_RESEARCH_ONLY_WITH_WARNINGS`.
- ETF E1 data exists as research-only dataset `etf_rotation_e1_20260707` with 30 ETF symbols and 55,726 qfq OHLCV rows.
- ETF timing rule: close `T` signal and `T+1` open execution; no same-day close-to-close execution.
- ETF screenshot reproduction is research-only and non-actionable.
- East Money broad reconciliation remains provider-blocked; prior split remains `77 CROSSCHECK_PASS / 121 CROSSCHECK_DATE_GAP / 2870 CROSSCHECK_MISSING_EAST_MONEY`.
- US current-universe research staging completed with 270 symbols and 559,959 daily rows.
- R18 closed accepted research-only with warnings in controller records.
- R18 wide research probe eligible count: `0`.
- R18 `strategy_candidate_available=false`.
- market_data product-route preparation remains inactive and separately gated.

## Dispatch Targets

- `A_Share_Monitor`: ETF rotation lane and A-share equity signal lane, `ETF-R19-1` through `ETF-R19-7` and `A-WIN-R19-1` through `A-WIN-R19-5`.
- `market_data`: ETF research manifest schema and overclaim tests, `MD-R19-1` through `MD-R19-2`.
- `strategy_work`: parallel strategy memo and final sync, `SW-R19-1` through `SW-R19-2`.
- `quant-proj`: intake, dispatch, result summary, and closeout.

## Boundary

Research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, strategy candidate promotion, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, daily signal push, raw-data migration, `.env` access, key output, secret handling, active schema/readiness/registry change, market_data activation, or ranked actionable list is authorized.

Future DB write, registry/readiness/product-route activation, raw-data migration, daily signal push, ticket/candidate creation, or trading path work requires separate explicit authorization and any required external audit gate.
