# WINDOWS_WSL2_VALIDATION_DIVERGENCE_BREAKTHROUGH_R23_20260708

## Classification

Ordinary research-only strategy diagnostics batch after R22 closeout.

## Evidence basis

R22 completed materialized-row diagnostics and produced no local or wide probe eligibility.

Preserved R22 facts:

- ETF amount/turnover rows: 32,482.
- ETF NAV/premium evidence remains partial.
- pass77 A-share feature rows: 136,767.
- global/news/macro context rows: 100.
- ETF R22 is blocked by instability with amount/turnover context.
- A-share pass77 fixed features are blocked by validation/test divergence.
- local_research_probe_eligible_count=0.
- wide_research_probe_eligible_count=0.
- strategy_candidate_available=false.

## Objective

Break down the validation/test divergence and instability blockers using the materialized R22 evidence. R23 must not perform broad grid search, rule cleanup, or route/readiness work. It must produce research diagnostics that explain whether the observed validation-positive/test-negative patterns are caused by time period, regime, universe scope, feature proxy construction, cost/turnover, missingness, or signal direction.

## Boundary

Research-only. No actionable output, no candidate promotion, no readiness/product-route activation, no daily signal push, no raw-data migration into controller, no active schema/registry activation, no credential output, no full-frame wide3068, no test-result parameter selection.

## Lane 0 - R22 evidence freeze and failure memory

- R23-0-1: Freeze R22 source state and no-probe result.
- R23-0-2: Import R22 diagnostics into experiment store.
- R23-0-3: Update failure memory with ETF instability and pass77 validation/test divergence.
- R23-0-4: Create a do-not-retry list for R19-R22 stale grids and failed transformations.

Deliverables:

- reports/workspace_dispatch/r23_r22_evidence_freeze_20260708.md
- reports/workspace_dispatch/r23_experiment_store_import_20260708.md
- reports/workspace_dispatch/r23_failure_memory_update_20260708.json
- reports/workspace_dispatch/r23_do_not_retry_update_20260708.md

## Lane 1 - A-share validation/test divergence autopsy

Use pass77 rows and the five R22 fixed features.

- A-R23-1: Period attribution by year, half-year, quarter, and month.
- A-R23-2: Symbol-cohort attribution by liquidity, turnover, listing age, industry/board if available, and missingness buckets.
- A-R23-3: Feature construction audit for proxy vs direct fields.
- A-R23-4: Outlier and winsorization sensitivity.
- A-R23-5: Regime attribution using global/news/macro context rows.
- A-R23-6: Cost/turnover attribution.

Deliverables:

- reports/workspace_dispatch/a_share_r23_period_attribution_20260708.csv
- reports/workspace_dispatch/a_share_r23_symbol_cohort_attribution_20260708.csv
- reports/workspace_dispatch/a_share_r23_feature_construction_audit_20260708.md
- reports/workspace_dispatch/a_share_r23_outlier_winsor_sensitivity_20260708.csv
- reports/workspace_dispatch/a_share_r23_regime_attribution_20260708.csv
- reports/workspace_dispatch/a_share_r23_cost_turnover_attribution_20260708.md

## Lane 2 - Pre-registered transformations, validation-only design

Do not select transformations from test outcomes. Pre-register transformations based on validation and feature construction hypotheses, then report holdout/test as diagnostic only.

Allowed transformations:

- date-neutralized feature score
- liquidity-neutralized score
- turnover-neutralized score
- volatility-neutralized score
- rank residualization
- feature smoothing
- lagged signal confirmation
- low-turnover entry filter
- regime guard defined before evaluation
- opposite-signal diagnostic as failure analysis only

Deliverables:

- reports/workspace_dispatch/a_share_r23_pre_registered_transformations_20260708.md
- reports/workspace_dispatch/a_share_r23_transformation_diagnostics_20260708.csv
- reports/workspace_dispatch/a_share_r23_holdout_diagnostic_report_20260708.md

## Lane 3 - Direct source validation and feature row improvement

Focus on direct evidence where R21 used proxies.

- A-R23-7: Public funds-flow direct field smoke, bounded public/no-secret only.
- A-R23-8: Hot-money / 龙虎榜 public field validation smoke.
- A-R23-9: PEG direct field sanity check and source lineage update.
- A-R23-10: Decide whether proxy features should be retained, repaired, or retired.

Deliverables:

- reports/workspace_dispatch/a_share_r23_public_funds_flow_direct_smoke_20260708.md
- reports/workspace_dispatch/a_share_r23_hotmoney_direct_smoke_20260708.md
- reports/workspace_dispatch/a_share_r23_peg_source_lineage_update_20260708.md
- reports/workspace_dispatch/a_share_r23_proxy_feature_retire_repair_keep_board_20260708.csv

## Lane 4 - ETF instability blocker decomposition

ETF R22 remained unstable with amount/turnover context. Do not rerun old grids.

- ETF-R23-1: Decompose instability by period, ETF group, liquidity bucket, turnover bucket, and defensive/overseas exposure.
- ETF-R23-2: Test pre-registered turnover-throttled and drawdown-control transformations only.
- ETF-R23-3: NAV/premium public-source status update or final unavailable label.
- ETF-R23-4: ETF do-not-retry board for stale rotation definitions.

Deliverables:

- reports/workspace_dispatch/etf_r23_instability_decomposition_20260708.csv
- reports/workspace_dispatch/etf_r23_turnover_drawdown_transformations_20260708.csv
- reports/workspace_dispatch/etf_r23_nav_premium_status_update_20260708.md
- reports/workspace_dispatch/etf_r23_do_not_retry_board_20260708.csv

## Lane 5 - Probe prequalification

Only after lanes 1-4 complete.

Allowed labels:

- R23_LOCAL_RESEARCH_PROBE_ELIGIBLE
- R23_WIDE_RESEARCH_PROBE_ELIGIBLE
- BLOCKED_BY_VALIDATION_TEST_DIVERGENCE
- BLOCKED_BY_INSTABILITY
- BLOCKED_BY_SOURCE_PROXY_LIMITATION
- BLOCKED_BY_COST_OR_TURNOVER
- BLOCKED_BY_SCOPE_LIMIT
- NO_R23_RESEARCH_PROBE_ELIGIBLE

Deliverables:

- reports/workspace_dispatch/strategy_r23_prequalification_board_20260708.csv
- reports/workspace_dispatch/strategy_r23_local_probe_or_skip_20260708.md
- reports/workspace_dispatch/strategy_r23_wide_probe_or_skip_20260708.md

## Lane 6 - Support repos

market_data:

- MD-R23-1: Update research contract for transformation diagnostics and source-proxy limitation labels.
- MD-R23-2: Overclaim regression for R23 eligible labels and transformation diagnostics.

strategy_work:

- SW-R23-1: Validation divergence breakthrough memo.
- SW-R23-2: Final sync after accepted callbacks.

quant-proj:

- QP-R23-1: Intake and dispatch.
- QP-R23-2: Result summary and closeout.

## Validation

- JSON parse PASS.
- git diff check PASS.
- focused pytest PASS if code changed.
- overclaim scan PASS.
- experiment store update PASS.
- failure memory update PASS.
- source health PASS before source-heavy work.
- no duplicate old-grid search without new evidence.
- no full-frame wide3068.
- no direct signal use from news/macro.
- no candidate promotion or actionable output.

## Stop conditions

- R22 results not imported before new diagnostics.
- Test outcome used to select transformations.
- pass77 result promoted beyond pass77 evidence scope.
- old ETF grid rerun without new evidence.
- proxy feature treated as direct source evidence.
- route/readiness/registry/schema/trading path attempted.
- credential/auth/secret required.

## Callback envelope

Return callback with batch id, repo, branch, commit, tree, tasks completed, artifacts, validation, source health, divergence findings, transformation diagnostics, eligible count, candidate availability, boundary result, fixes required, and next source action.
