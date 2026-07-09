# WINDOWS_WSL2_EVIDENCE_BACKED_STRATEGY_PROBE_R27_20260709

## Classification

Ordinary research-only evidence-backed strategy probe batch after R25/R26 audit.

## Evidence basis

R25 closed with no local or wide probe eligibility for the targeted pass77 and ETF lines. The final R25 board preserved one A-share continue-research row, four A-share repair-on-new-data-only rows, and three retired ETF rotation rows. No strategy candidate availability was created.

R26 remediated report evidence. The key new usable research evidence is:

- SmallCap Low Turnover evidence package in A_Share_Monitor, with committed engine/rules fixes, evidence generator, tests, and tracked source-local evidence package.
- US30W-R22-002 reproducible real-data research-only observation evidence, local-only in us_stock_30w with no remote configured.
- US30W-R22-001 prior unsupported phase2/deep-validation framing corrected and downgraded.

## Objective

Move strategy research toward evidence-backed probes by focusing only on strategy families with source-local reproducible evidence or clear accepted repair needs. Do not reopen retired ETF rotation or pass77 proxy lines unless new accepted evidence changes their failed premise.

Primary active lines:

1. A-share SmallCap Low Turnover research evidence package.
2. US30W-R22-002 baseline/adaptive_quality reproducible observation evidence.
3. A-share direct/proxy feature source improvement only if it can repair pass77 evidence.

## Boundary

Research-only. No actionable output, no candidate promotion, no readiness/product route, no daily signal, no broker/order/paper/live/auto path, no active registry/schema change, no secret output, no full-frame wide3068, no test-result parameter selection.

## Lane 0 - Evidence freeze and lineage

- R27-0-1: Freeze R25/R26 accepted state and no-probe/no-candidate baseline.
- R27-0-2: Import SmallCap evidence package into experiment store.
- R27-0-3: Import US30W-R22-002 observed metrics and local-only caveat into experiment store.
- R27-0-4: Mark retired or blocked lines from R25: ETF rotation retired; pass77 repair only on new accepted data.

Deliverables:

- reports/workspace_dispatch/r27_r25_r26_evidence_freeze_20260709.md
- reports/workspace_dispatch/r27_experiment_store_import_20260709.md
- reports/workspace_dispatch/r27_failure_memory_update_20260709.json

## Lane 1 - SmallCap Low Turnover robustness lab

Use only the committed R26 A_Share_Monitor evidence package and engine/rules fixes as baseline.

Tasks:

- SC-R27-1: Re-run evidence generator and verify deterministic output hashes where feasible.
- SC-R27-2: Increase permutation test count beyond the R26 10-run smoke; target 200+ if runtime allows.
- SC-R27-3: Walk-forward and anchored split stress across train/validation/test periods.
- SC-R27-4: Cost/slippage sensitivity and turnover/capacity stress.
- SC-R27-5: Universe sensitivity: small-cap threshold variants, liquidity floors, ST/suspend/limit filters where available.
- SC-R27-6: Feature timing/leakage audit for turnover-based signal.
- SC-R27-7: Failure memory decision: continue, repair, benchmark-only, or local research probe eligible.

Deliverables:

- reports/workspace_dispatch/smallcap_r27_reproducibility_rerun_20260709.md
- reports/workspace_dispatch/smallcap_r27_permutation_bootstrap_stress_20260709.json
- reports/workspace_dispatch/smallcap_r27_walk_forward_stress_20260709.csv
- reports/workspace_dispatch/smallcap_r27_cost_capacity_stress_20260709.csv
- reports/workspace_dispatch/smallcap_r27_universe_sensitivity_20260709.csv
- reports/workspace_dispatch/smallcap_r27_timing_leakage_audit_20260709.md
- reports/workspace_dispatch/smallcap_r27_research_probe_board_20260709.csv

## Lane 2 - US30W real-data observation hardening

Use US30W-R22-002 only as research-only observation evidence. Because us_stock_30w has no remote configured, preserve hashes and transcripts in controller and supporting repos where possible.

Tasks:

- US30W-R27-1: Re-run pipeline and compare baseline/adaptive_quality metrics to accepted R26 hashes.
- US30W-R27-2: Confirm synthetic_data=false in generated JSON outputs.
- US30W-R27-3: Add or update remote-preservation plan for us_stock_30w; do not require remote if user does not configure one.
- US30W-R27-4: Robustness checks: alternate splits, cost/slippage sensitivity, symbol subset stress.
- US30W-R27-5: Research board: observation only, continue research, or stop until remote preservation.

Deliverables:

- reports/workspace_dispatch/us30w_r27_pipeline_reproduction_20260709.md
- reports/workspace_dispatch/us30w_r27_metric_drift_check_20260709.json
- reports/workspace_dispatch/us30w_r27_remote_preservation_plan_20260709.md
- reports/workspace_dispatch/us30w_r27_robustness_stress_20260709.csv
- reports/workspace_dispatch/us30w_r27_research_board_20260709.csv

## Lane 3 - Pass77 direct/proxy evidence improvement gate

R25 says four pass77 features require better source/proxy evidence before reopening. This lane is a gate, not a strategy rerun.

Tasks:

- A-R27-1: For funds_flow_proxy_score and hot_money_proxy_score, attempt bounded public/no-secret direct field validation smoke.
- A-R27-2: For amount_z20 and turnover_z20, verify source lineage and whether they should be controls, not alpha signals.
- A-R27-3: For peg_proxy, decide whether to retain as valuation context, reverse-only research, or retire until direct valuation fields improve.
- A-R27-4: Produce pass77 repair gate board.

Deliverables:

- reports/workspace_dispatch/pass77_r27_direct_proxy_validation_smoke_20260709.md
- reports/workspace_dispatch/pass77_r27_lineage_alpha_vs_control_board_20260709.csv
- reports/workspace_dispatch/pass77_r27_repair_gate_board_20260709.csv

## Lane 4 - Strategy decision board

Combine R27 findings into one research board.

Allowed labels:

- LOCAL_RESEARCH_PROBE_ELIGIBLE
- CONTINUE_RESEARCH
- OBSERVATION_ONLY
- BENCHMARK_ONLY
- REPAIR_ON_NEW_EVIDENCE_ONLY
- REMOTE_PRESERVATION_REQUIRED
- RETIRE
- DO_NOT_RETRY

Deliverables:

- reports/workspace_dispatch/r27_final_strategy_research_board_20260709.csv
- reports/workspace_dispatch/r27_final_strategy_research_memo_20260709.md

## Lane 5 - Support repos

market_data:

- MD-R27-1: Update research contract for SmallCap/US30W observation and probe labels.
- MD-R27-2: Overclaim regression for SmallCap, US30W, and pass77 repair gate labels.

strategy_work:

- SW-R27-1: Evidence-backed strategy probe memo.
- SW-R27-2: Final sync after accepted source callbacks.

quant-proj:

- QP-R27-1: Intake and dispatch.
- QP-R27-2: Result summary and closeout.

## Validation

- JSON parse PASS.
- CSV parse PASS.
- git diff check PASS.
- focused tests PASS if code changed.
- source evidence manifests present.
- no test-result parameter selection.
- no actionable output.
- no full-frame wide3068.
- no secret access.

## Stop conditions

- SmallCap evidence promoted beyond research-only status.
- US30W local-only evidence treated as remote-preserved evidence without remote.
- pass77 strategy rerun attempted without improved direct/proxy evidence.
- old ETF rotation reopened without new accepted evidence.
- test result used to choose parameters.
- product/route/readiness/trading path attempted.

## Callback envelope

Return callback with batch id, repo, branch, commit, tree, tasks completed, artifacts, validation, SmallCap status, US30W status, pass77 repair gate status, final board counts, probe eligible count, strategy candidate availability, boundary result, fixes required, and next source action.
