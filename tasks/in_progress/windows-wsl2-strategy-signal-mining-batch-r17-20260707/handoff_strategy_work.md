# Handoff: strategy_work R17 Strategy Signal Mining Memo

Target repo: `/home/rongyu/workspace/strategy_work`
Controller repo: `/home/rongyu/workspace/quant-proj`
Callback target: Quant-Dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`
Batch: `WINDOWS_WSL2_STRATEGY_SIGNAL_MINING_BATCH_R17_20260707`

## Assigned Tasks

- `SW-WIN-R17-1`: Strategy signal mining memo.
- `SW-WIN-R17-2`: Final sync after A-share and market_data callbacks.

## Required Deliverables

- `reports/planning/windows_wsl2_strategy_signal_mining_batch_r17_20260707_strategy_memo.md`
- `reports/planning/windows_wsl2_strategy_signal_mining_batch_r17_final_sync_20260707.md`

## Execution Rule

Create the initial strategy memo from accepted baseline evidence, but do not create final sync until accepted A_Share_Monitor and market_data R17 callback envelopes are available.

Preserve `strategy_candidate_available=false` unless source evidence explicitly changes it. Do not create ranked actionable lists.

## Validation

Run `git diff --check`, forbidden action-word scan, no candidate promotion scan, and no recommendation/advice scan.

## Boundary

Research-only. No recommendation/advice, ticket, eligibility candidate, strategy candidate promotion, product-route activation, readiness, broker/order/paper/live/auto, secrets, or raw-data migration.
