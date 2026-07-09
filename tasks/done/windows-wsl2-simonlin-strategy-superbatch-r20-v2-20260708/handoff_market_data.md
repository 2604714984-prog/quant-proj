# Handoff - market_data R20_V2

Target repo: `/home/rongyu/workspace/market_data`
Controller repo: `/home/rongyu/workspace/quant-proj`
Callback target: Quant-Dispatcher thread `019f3830-4b44-7a83-944d-247a0d4dc169`
Batch: `WINDOWS_WSL2_SIMONLIN_STRATEGY_SUPERBATCH_R20_V2_20260708`

## Read First

- `/home/rongyu/workspace/quant-proj/reports/human_gate/windows_wsl2_simonlin_strategy_superbatch_r20_v2_authorization_20260708.md`
- `/home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/spec.md`
- `/home/rongyu/workspace/quant-proj/tasks/in_progress/windows-wsl2-simonlin-strategy-superbatch-r20-v2-20260708/human_gate.md`
- `/home/rongyu/workspace/quant-proj/reports/workspace_dispatch/windows_wsl2_parallel_strategy_search_batch_r19_20260707_closeout.md`

## Assigned Scope

- `MD-R20-1` SimonLin research source contract.
- `MD-R20-2` R20 overclaim regression.

Deliverables:

- `reports/codex_dev/simonlin_r20_research_source_contract.md`
- `reports/codex_dev/simonlin_r20_research_source_contract.json`
- `tests/test_simonlin_r20_overclaim_regression.py`

## Required Negative Tests

Reject overclaims that treat:

- PEG low valuation as recommendation.
- News heat as buy signal.
- Macro probability as trading signal.
- ETF leaderboard as daily signal.
- TradingAgents decision as candidate.
- globalpercent probability as forecast certainty.
- `R20_RESEARCH_INTERESTING` as readiness.
- Shadow leaderboard as actionable ranking.

## Boundary

Research-only contract and overclaim tests only. No product-route activation, active registry change, readiness change, market_data activation, raw-data import into active route, adapter/schema production change, recommendation/advice, ticket, eligibility candidate, strategy candidate promotion, broker/order/paper/live/auto, daily signal push, raw-data migration into `quant-proj`, or secret access/output.

## Required Validation

- Focused pytest PASS.
- JSON parse PASS.
- `git diff --check` PASS.
- Forbidden overclaim scan PASS.
- No active registry/readiness/product-route/schema/adapter production change.

## Callback

Return the R20_V2 callback envelope. `SOURCE_HEALTH`, `EXPERIMENT_STORE_STATUS`, and `FAILURE_MEMORY_STATUS` may be `N/A - market_data contract lane` unless contract/test artifacts encode these fields.
