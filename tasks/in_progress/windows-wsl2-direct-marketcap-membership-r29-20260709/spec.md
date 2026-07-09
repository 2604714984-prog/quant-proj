# WINDOWS_WSL2_DIRECT_MARKETCAP_MEMBERSHIP_R29_20260709

## Classification

Ordinary research-only evidence completion batch after R28 source/final-sync verification.

## Evidence basis

R28 completed SmallCap row-level evidence completion but remained evidence-incomplete because direct market-cap fields were unavailable in the accepted local cache. R28 preserved:

- pre-trade signal matrix rows: 732,793.
- universe membership proxy snapshot rows: 732,793.
- entry candidate diagnostics rows: 14,586.
- post-trade fill linkage rows: 1,691.
- leakage/timing audit: PASS_WITH_MARKET_CAP_PROXY_LIMITATION.
- local_research_probe_eligible_count=0.
- wide_research_probe_eligible_count=0.
- strategy_candidate_available=false.

## Objective

Materialize direct market-cap membership evidence for SmallCap Low Turnover and rerun the leakage/timing and local probe prequalification checks. Do not search for new strategies. Do not rerun pass77 or ETF. Do not promote any result to candidate/readiness/trading status.

## Boundary

Research-only. No actionable output, no recommendation, no ticket, no candidate promotion, no readiness/product route, no daily signal, no broker/order/paper/live/auto path, no active registry/schema change, no secret output, no full-frame wide3068, no test-result parameter selection.

## Lane 0 - R28 evidence freeze

- R29-0-1: Freeze R28 row-level evidence status and market-cap proxy limitation.
- R29-0-2: Import R28 signal matrix, proxy membership snapshot, leakage audit, and prequalification board into experiment store.
- R29-0-3: Update failure memory: SmallCap remains blocked only by direct market-cap membership evidence.

Deliverables:

- reports/workspace_dispatch/r29_r28_evidence_freeze_20260709.md
- reports/workspace_dispatch/r29_experiment_store_import_20260709.md
- reports/workspace_dispatch/r29_failure_memory_update_20260709.json

## Lane 1 - Direct market-cap source discovery and materialization

Tasks:

- MCAP-R29-1: Search existing local caches for direct total_mv / circ_mv / market_cap fields covering R28 SmallCap dates and symbols.
- MCAP-R29-2: If local cache is insufficient, perform bounded public/no-secret source-local fetch only for required SmallCap universe membership fields and dates, subject to source health and provider limits.
- MCAP-R29-3: Produce direct market-cap membership snapshot with symbol, trade_date, total_mv or circ_mv, source, availability timestamp, membership flag, and missingness reason.
- MCAP-R29-4: Produce fallback mapping documenting where direct market-cap is still unavailable and whether proxy membership remains the only reconstruction path.

Deliverables:

- reports/workspace_dispatch/smallcap_r29_direct_marketcap_source_health_20260709.md
- reports/runops/smallcap_r29_direct_marketcap_membership_20260709/direct_marketcap_membership_snapshot.parquet or .csv
- reports/runops/smallcap_r29_direct_marketcap_membership_20260709/direct_marketcap_missingness.csv
- reports/runops/smallcap_r29_direct_marketcap_membership_20260709/manifest.json
- reports/workspace_dispatch/smallcap_r29_direct_marketcap_materialization_20260709.md

## Lane 2 - Rebuild SmallCap signal matrix with direct membership

Tasks:

- SC-R29-1: Join direct market-cap membership snapshot to the R28 pre-trade signal matrix.
- SC-R29-2: Recompute universe membership using direct market-cap fields where available.
- SC-R29-3: Preserve side-by-side direct membership and R28 proxy membership for drift comparison.
- SC-R29-4: Recompute entry candidate diagnostics using direct membership.
- SC-R29-5: Hash and manifest all outputs.

Deliverables:

- reports/runops/smallcap_r29_direct_marketcap_membership_20260709/pre_trade_signal_matrix_direct_mcap.parquet or .csv
- reports/runops/smallcap_r29_direct_marketcap_membership_20260709/universe_membership_direct_vs_proxy.csv
- reports/runops/smallcap_r29_direct_marketcap_membership_20260709/entry_candidate_diagnostics_direct_mcap.csv
- reports/workspace_dispatch/smallcap_r29_direct_vs_proxy_membership_drift_20260709.md

## Lane 3 - Leakage/timing and robustness rerun

Tasks:

- SC-R29-6: Rerun leakage/timing audit with direct market-cap membership.
- SC-R29-7: Rebuild train/validation/test metrics from direct membership matrix.
- SC-R29-8: Rerun targeted permutation/bootstrap and walk-forward/cost stress only if direct membership coverage is sufficient.
- SC-R29-9: Compare R26/R27/R28/R29 metrics and explain drift.

Deliverables:

- reports/workspace_dispatch/smallcap_r29_leakage_timing_audit_direct_mcap_20260709.md
- reports/workspace_dispatch/smallcap_r29_metric_rebuild_direct_mcap_20260709.json
- reports/workspace_dispatch/smallcap_r29_robustness_update_direct_mcap_20260709.csv
- reports/workspace_dispatch/smallcap_r29_metric_drift_report_20260709.md

## Lane 4 - Local probe prequalification board

Allowed labels:

- LOCAL_RESEARCH_PROBE_ELIGIBLE
- CONTINUE_RESEARCH
- EVIDENCE_INCOMPLETE
- DIRECT_MCAP_COVERAGE_INSUFFICIENT
- BLOCKED_BY_LEAKAGE_OR_TIMING
- BLOCKED_BY_ROBUSTNESS
- BLOCKED_BY_COST_CAPACITY
- RETIRE

Rules:

- LOCAL_RESEARCH_PROBE_ELIGIBLE is research-only, not candidate/readiness/trading evidence.
- Wide probe eligibility is out of scope for R29.
- strategy_candidate_available must remain false.

Deliverables:

- reports/workspace_dispatch/smallcap_r29_local_probe_prequalification_board_20260709.csv
- reports/workspace_dispatch/smallcap_r29_final_research_memo_20260709.md

## Lane 5 - Support repos

market_data:

- MD-R29-1: Contract for direct market-cap membership evidence and local-probe labels.
- MD-R29-2: Overclaim regression for LOCAL_RESEARCH_PROBE_ELIGIBLE and direct market-cap evidence.

strategy_work:

- SW-R29-1: Direct market-cap evidence memo.
- SW-R29-2: Final sync after accepted callbacks.

quant-proj:

- QP-R29-1: Intake and dispatch.
- QP-R29-2: Result summary and closeout.

## Validation

- JSON parse PASS.
- CSV/parquet read PASS.
- git diff check PASS.
- focused pytest PASS if code changed.
- source health PASS before any public fetch.
- evidence manifest hash PASS.
- leakage/timing audit PASS or explicit block label.
- no test-result parameter selection.
- no actionable output.
- no candidate promotion.

## Stop conditions

- Direct market-cap evidence requires secret/auth/non-public access.
- Direct market-cap coverage cannot be tied to decision-time availability.
- Membership snapshot cannot be reconstructed for required dates/symbols.
- Local-probe label is written as candidate/readiness/trading evidence.
- Old pass77 or ETF lines are rerun without changed accepted evidence.
- Full-frame wide3068 attempted.

## Callback envelope

Return callback with batch id, repo, branch, commit, tree, tasks completed, artifacts, validation, direct market-cap coverage status, signal matrix status, leakage/timing audit result, robustness status, local probe prequalification result, candidate availability, boundary result, fixes required, and next source action.
