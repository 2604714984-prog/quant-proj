# DATA_STRATEGY_BATCH_R13_20260706 Intake

Project: quant-proj
Role: Quant-Dispatcher
Imported: 2026-07-06
Source: GPT Pro external-audit result pasted by user
Prior packet: `DATA_STRATEGY_BATCH_R12_20260705`

## Classification

Ordinary research-only data/strategy batch.

External-audit trigger opened: `no`

## Objective

Safely generate derived `features_daily` for the cleaned 3068-symbol A-share `data/cache`, validate feature coverage/leakage, then rerun research-only `low_vol_quality` strategy diagnostics on the wider cross-section.

## Hard R13 Execution Rule

`StrategySearch.run()` must not be allowed to auto-fallback to full in-memory `FeatureStore.build()` over the 3068-symbol `data/cache`.

Required sequence:

1. Read-only preflight inventory of `data/cache`.
2. Build `features_daily` only through `python -m qta features build` or equivalent `FeatureStore.build_to_store()`.
3. Validate `features_daily` coverage/leakage.
4. Prepare R13-specific `strategy_work` configs.
5. Run `bare_minimum` only after feature validation passes.
6. Run `lowvol_quality_focused` only if the wide `bare_minimum` run has positive test Sharpe and data quality does not fail.

## Tasks

### A_Share_Monitor

- `A-R13-1`: 3068-symbol cache preflight inventory.
- `A-R13-2`: safe `features_daily` build through chunked path only.
- `A-R13-3`: `features_daily` coverage and leakage validation.
- `A-R13-4`: run `bare_minimum` on 3068-symbol cache after validation passes.
- `A-R13-5`: conditional wide `lowvol_quality_focused` rerun.

### strategy_work

- `SW-R13-1`: prepare wide-cache research configs.
- `SW-R13-2`: archive wide-cache run artifacts after source runs finish.
- `SW-R13-3`: final R13 memo sync after source acceptances only.

### market_data

- `MD-R13-1`: derived-feature evidence boundary note.

## Boundary

No recommendation/advice, ticket, `PENDING_HUMAN_REVIEW`, eligibility candidate, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto, raw-data migration, `.env` access, key output, or secret handling is authorized.
