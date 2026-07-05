# DATA_STRATEGY_BATCH_R13_CHUNKED_SEARCH_20260706 Intake

Project: quant-proj
Role: Quant-Dispatcher
Imported: 2026-07-06
Source: GPT Pro external-audit result pasted by user
Prior packet: `DATA_STRATEGY_BATCH_R13_20260706` interim

## Classification

Ordinary research-only data/strategy execution batch.

External-audit trigger opened: `no`

## Objective

Implement and validate chunked strategy search/backtest for A-share wide-cache diagnostics so the already-built 3068-symbol `features_daily` can be consumed safely without full in-memory pandas materialization.

## Task List

### A_Share_Monitor

- `A-R13C-1`: StrategySearch memory blocker confirmation and unsafe full-frame guard.
- `A-R13C-2`: chunked feature reader for strategy search.
- `A-R13C-3`: chunked backtest state model.
- `A-R13C-4`: full-frame vs chunked equivalence test on small cache.
- `A-R13C-5`: wide3068 `bare_minimum` chunked dry run.
- `A-R13C-6`: conditional wide3068 `low_vol_quality` chunked rerun.

### strategy_work

- `SW-R13C-1`: chunked wide-run configs and archive plan.
- `SW-R13C-2`: final interim-to-closeout memo sync after A-share and market_data source acceptances.

### market_data

- `MD-R13C-1`: `features_daily` derived-feature boundary contract.

## Boundary

R13C is research-only. No recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, `.env` access, key output, or secret handling is authorized.
