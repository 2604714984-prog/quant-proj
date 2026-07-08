# Future External Audit Prompt - R21

Use this only if the user requests external review after R21 closeout.

```text
Please review WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708 using GitHub connector.

Review controller files:
- reports/workspace_dispatch/windows_wsl2_feature_materialization_and_strategy_delta_r21_20260708_intake.md
- reports/workspace_dispatch/windows_wsl2_feature_materialization_and_strategy_delta_r21_20260708_result_summary.md
- reports/workspace_dispatch/windows_wsl2_feature_materialization_and_strategy_delta_r21_20260708_closeout.md
- tasks/in_progress/windows-wsl2-feature-materialization-and-strategy-delta-r21-20260708/spec.md
- reports/agent_handoff/windows_wsl2_simonlin_strategy_superbatch_r20_v2_external_audit_result_20260708.md

Review source callbacks and referenced artifacts for A_Share_Monitor, market_data, US_Stock_Monitor, and strategy_work.

Questions:
1. Can R21 be accepted as a research-only feature materialization / strategy-delta batch?
2. Did R21 preserve R20 limitations and avoid unsupported strategy diagnostics?
3. Were ETF amount/NAV/premium fields truly materialized, or were limitation labels preserved?
4. Were A-share PEG/event/funds/hot-money rows actually materialized and validated before any delta diagnostics?
5. Did global/news/macro remain context-only?
6. Did any output create recommendation, ticket, candidate, readiness, route activation, daily signal, trading path, raw-data migration into controller, active schema/registry change, or secret exposure?
7. What fixes, if any, are required before the next ordinary research batch?
```
