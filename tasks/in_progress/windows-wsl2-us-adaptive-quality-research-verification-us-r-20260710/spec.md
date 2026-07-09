# WINDOWS_WSL2_US_ADAPTIVE_QUALITY_RESEARCH_VERIFICATION_US_R_20260710

## Classification

Ordinary research-only US strategy verification batch.

## Objective

Evaluate the US Adaptive+Quality line as a research lead after the US30W report
remediation, local simulation boundary documentation, and Strategy Vault cleanup.
The objective is classification, not proof of usability.

Allowed final labels for US-01:

- CONTINUE_RESEARCH
- BENCHMARK_ONLY
- REPAIR_REQUIRED
- DO_NOT_RETRY

## Baseline Facts

- `us_stock_30w/scripts/run_pipeline.sh` is the offline reproducible research
  pipeline for US30W-R22-002 evidence.
- `us_stock_30w/scripts/run_daily.sh` remains disabled and must not launch daily
  signals or local simulation.
- `US_Stock_Monitor/scripts/evidence_trader.py` is preserved as manually invoked
  local simulation evidence collection, not as daily signal, active strategy,
  paper/live path, broker/order path, route, or readiness.
- `STRATEGY_VAULT` is a formal research-lead catalog, not an active strategy
  registry.

## Required Work

1. Freeze current US30W and US_Stock_Monitor evidence, including commits,
   manifest/hash status, and disabled daily launcher state.
2. Reproduce baseline and Adaptive+Quality JSON outputs with `run_pipeline.sh`.
3. Verify synthetic/real labels and cache hash evidence.
4. Audit the 107-symbol universe for selection bias and missing-symbol rationale.
5. Cross-check a bounded public/no-secret sample against an alternate source if
   feasible.
6. Run walk-forward and bootstrap diagnostics without test-result parameter
   selection.
7. Run cost/slippage and rebalance sensitivity diagnostics.
8. Attribute returns by market beta, sector exposure, symbol concentration, and
   regime.
9. Emit final US-01 decision board with exactly one allowed label.

## Support Repos

- `US_Stock_Monitor`: main implementation and validation artifacts.
- `us_stock_30w`: reproducible pipeline and output artifacts, local only if no
  remote is configured.
- `STRATEGY_VAULT`: research-lead status update only.
- `strategy_work`: optional memo/final sync if source callbacks are produced.
- `quant-proj`: intake, result summary, and closeout.

## Boundary

Research-only. No recommendation, no ticket, no active strategy status, no
candidate promotion, no readiness, no product route, no daily signal, no
broker/order/paper/live/auto execution, no raw-data migration into controller,
no active schema/registry activation, no test-result parameter selection, and no
secret access/output.

## Deliverables

- `reports/workspace_dispatch/us_r_adaptive_quality_evidence_freeze_20260710.md`
- `reports/workspace_dispatch/us_r_adaptive_quality_reproduction_20260710.md/json`
- `reports/workspace_dispatch/us_r_universe_selection_bias_audit_20260710.md/csv`
- `reports/workspace_dispatch/us_r_source_crosscheck_20260710.md/csv`
- `reports/workspace_dispatch/us_r_walkforward_bootstrap_20260710.md/csv`
- `reports/workspace_dispatch/us_r_cost_rebalance_sensitivity_20260710.md/csv`
- `reports/workspace_dispatch/us_r_return_attribution_20260710.md/csv`
- `reports/workspace_dispatch/us_r_adaptive_quality_decision_board_20260710.csv`
- `reports/workspace_dispatch/us_r_final_research_memo_20260710.md`

## Validation

- JSON parse PASS.
- CSV parse PASS.
- `git diff --check` PASS.
- focused pytest PASS if code changed.
- safety/overclaim scan PASS.
- `run_daily.sh` disabled state verified.
- no direct invocation of `evidence_trader.py` from US-R.
- no test-result parameter selection.

## Callback Envelope

Return:

```text
CALLBACK_ENVELOPE:
BATCH: WINDOWS_WSL2_US_ADAPTIVE_QUALITY_RESEARCH_VERIFICATION_US_R_20260710
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
TASKS_COMPLETED:
ARTIFACTS:
VALIDATION:
REPRODUCTION_STATUS:
UNIVERSE_BIAS_STATUS:
SOURCE_CROSSCHECK_STATUS:
DIAGNOSTICS_STATUS:
FINAL_US01_LABEL:
STRATEGY_CANDIDATE_AVAILABLE:
BOUNDARY_RESULT:
FIXES_REQUIRED:
NEXT_SOURCE_ACTION:
```
