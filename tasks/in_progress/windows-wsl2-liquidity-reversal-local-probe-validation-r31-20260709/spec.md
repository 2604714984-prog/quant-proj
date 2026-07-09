# WINDOWS_WSL2_LIQUIDITY_REVERSAL_LOCAL_PROBE_VALIDATION_R31_20260709

## Classification

Research-only local probe validation/hardening batch after R30 strategy factory external audit.

## R30 audit premise

R30 produced one research line labelled `LOCAL_RESEARCH_PROBE_ELIGIBLE`: `liquidity_constrained_reversal`.

R30 evidence for this label:

- train spread: 0.006455.
- validation spread: 0.037909.
- test spread: 0.012947.
- validation IC: 0.079738.
- test IC: 0.05352.
- strategy_candidate_available=false.

Audit caveat:

R30 used a pre-registered rule that included test spread and test IC in the prequalification label. That is not accepted as sufficient for immediate probe execution. R31 must revalidate the line without using test outcomes for selection, and must treat R30 as hypothesis-generation evidence only.

## Objective

Validate or reject `liquidity_constrained_reversal` as a research-only local probe line using stricter evidence:

1. Freeze the formula and universe from R30.
2. Re-score using validation-only selection logic.
3. Preserve the R30 test period as diagnostic only, or create a new forward/rolling pseudo-holdout from unused dates if available.
4. Run local backtest-style probe diagnostics with T+1 execution and conservative fill assumptions.
5. Decide whether the line remains `LOCAL_RESEARCH_PROBE_ELIGIBLE`, becomes `HYPOTHESIS_ONLY_NEEDS_NEW_HOLDOUT`, or is rejected.

## Boundary

Research-only. No recommendation/advice. No ticket. No candidate promotion. No readiness/product route. No daily signal. No broker/order/paper/live/auto. No active registry/schema change. No secret output. No full-frame wide3068. No test-result parameter selection.

## Lane 0 - R30 audit freeze

- R31-0-1: Freeze R30 final board, liquidity_constrained_reversal formula, diagnostics, and prequalification caveat.
- R31-0-2: Update failure memory for the five R30 failed families.
- R31-0-3: Mark R30 test-inclusive eligibility as hypothesis-generation evidence only.

Deliverables:

- reports/workspace_dispatch/r31_r30_evidence_freeze_20260709.md
- reports/workspace_dispatch/r31_failure_memory_update_20260709.json
- reports/workspace_dispatch/r31_r30_test_inclusion_caveat_20260709.md

## Lane 1 - Formula, universe, and data audit

- LCR-R31-1: Freeze liquidity_constrained_reversal score definition exactly as R30 used it.
- LCR-R31-2: Audit required fields: return_5d, amount_z20, forward_return_20d, trade_date, ts_code, split.
- LCR-R31-3: Audit accepted_pass77_local_rows universe, date ranges, symbol count, missingness, duplicates, and split boundaries.
- LCR-R31-4: Confirm no R23/R30 failed-family outputs are used as parameter-selection input.

Deliverables:

- reports/workspace_dispatch/lcr_r31_formula_freeze_20260709.md
- reports/workspace_dispatch/lcr_r31_data_universe_audit_20260709.json
- reports/workspace_dispatch/lcr_r31_missingness_duplicate_audit_20260709.csv

## Lane 2 - Validation-only prequalification

Selection rule must not use test results.

- LCR-R31-5: Evaluate train/validation only for prequalification.
- LCR-R31-6: Use pre-registered thresholds based on R30 validation logic but not on test outcomes.
- LCR-R31-7: Treat test split only as diagnostic report.
- LCR-R31-8: If additional unused forward dates exist, create a forward diagnostic split; otherwise state `NO_UNUSED_FORWARD_HOLDOUT_AVAILABLE`.

Allowed labels:

- VALIDATION_ONLY_LOCAL_PROBE_ELIGIBLE
- HYPOTHESIS_ONLY_NEEDS_NEW_HOLDOUT
- REJECTED_BY_VALIDATION_ONLY
- BLOCKED_BY_NO_UNUSED_HOLDOUT

Deliverables:

- reports/workspace_dispatch/lcr_r31_validation_only_prequalification_20260709.csv
- reports/workspace_dispatch/lcr_r31_test_diagnostic_only_20260709.md
- reports/workspace_dispatch/lcr_r31_forward_holdout_or_unavailable_20260709.md

## Lane 3 - Local probe diagnostics, only if validation-only prequalification passes

Run a bounded local research probe diagnostic, not candidate/readiness/trading.

- LCR-R31-9: Build daily top-decile/bottom-decile long-only or long-short diagnostic portfolios as pre-registered research diagnostics.
- LCR-R31-10: Run T+1 execution, conservative fill, slippage/cost/capacity checks where required fields exist.
- LCR-R31-11: Run walk-forward and quarter/year stress.
- LCR-R31-12: Run permutation/bootstrap significance tests.
- LCR-R31-13: Run turnover/capacity sensitivity.

Deliverables:

- reports/workspace_dispatch/lcr_r31_local_probe_diagnostics_20260709.md
- reports/workspace_dispatch/lcr_r31_local_probe_metrics_20260709.json
- reports/workspace_dispatch/lcr_r31_walkforward_stress_20260709.csv
- reports/workspace_dispatch/lcr_r31_permutation_bootstrap_20260709.json
- reports/workspace_dispatch/lcr_r31_cost_capacity_stress_20260709.csv

## Lane 4 - Final decision board

Allowed labels:

- LOCAL_RESEARCH_PROBE_ELIGIBLE_REVALIDATED
- VALIDATION_ONLY_ELIGIBLE_TEST_DIAGNOSTIC_WEAK
- HYPOTHESIS_ONLY_NEEDS_NEW_HOLDOUT
- REJECTED_BY_VALIDATION_ONLY
- REJECTED_BY_LOCAL_PROBE_DIAGNOSTICS
- BLOCKED_BY_DATA_OR_CAPACITY

Rules:

- No strategy_candidate_available=true.
- No recommendation/ticket/readiness/product/trading language.
- If test was used for any selection decision, output must be rejected as `REJECTED_BY_TEST_RESULT_SELECTION`.

Deliverables:

- reports/workspace_dispatch/lcr_r31_final_decision_board_20260709.csv
- reports/workspace_dispatch/lcr_r31_final_research_memo_20260709.md

## Support repos

market_data:

- MD-R31-1: Contract for liquidity_constrained_reversal local-probe validation labels.
- MD-R31-2: Overclaim regression for revalidated local-probe labels.

strategy_work:

- SW-R31-1: Liquidity reversal local-probe validation memo.
- SW-R31-2: Final sync after accepted callbacks.

quant-proj:

- QP-R31-1: Intake and dispatch.
- QP-R31-2: Result summary and closeout.

## Validation

- JSON parse PASS.
- CSV/parquet read PASS.
- git diff check PASS.
- focused pytest PASS if code changed.
- test-result parameter-selection scan PASS.
- overclaim scan PASS.
- no full-frame wide3068.
- no candidate promotion.

## Stop conditions

- Test results are used for prequalification or parameter selection.
- R30 eligibility is promoted directly without R31 validation-only recheck.
- Candidate/readiness/product/trading output appears.
- Required fields are missing and no blocked label is written.
- Full-frame wide3068 is attempted.

## Callback envelope

Return callback with batch id, repo, branch, commit, tree, tasks completed, artifacts, validation, validation-only prequalification result, local probe diagnostics result, final decision label, local research probe eligible count, strategy candidate availability, boundary result, fixes required, and next source action.
