# WINDOWS_WSL2_MATERIALIZED_FEATURE_STRATEGY_LAB_R22_20260708 Intake

Classification: ordinary research-only strategy diagnostics batch.

## Trigger

R21/C1 produced materialized ETF amount/turnover rows and pass77 A-share feature rows. The next stage should run limitation-aware diagnostics on actual materialized rows, not more rule cleanup or source-review-only work.

## Baseline

- ETF amount/turnover rows: 32,482.
- ETF NAV/premium: partial/unresolved; preserve limitations.
- A-share pass77 feature rows: 136,767.
- Fixed features: peg_proxy, funds_flow_proxy_score, hot_money_proxy_score, amount_z20, turnover_z20.
- Fixed-feature diagnostics show validation/test divergence.
- Global/news/macro context rows: 100.
- US/global regime support: 13 symbols.
- Wide eligible count remains 0.
- Strategy candidate availability remains false.

## Required reads

- `tasks/in_progress/windows-wsl2-materialized-feature-strategy-lab-r22-20260708/spec.md`
- `reports/agent_handoff/windows_wsl2_materialized_feature_strategy_lab_r22_dispatcher_prompt_20260708.md`
- C1 result summary and closeout.

## Boundary

Research-only. No actionable output, no candidate promotion, no readiness/product-route activation, no daily signal push, no raw-data migration into controller, no active schema/registry activation, and no credential output.
