# WINDOWS_WSL2_SMALLCAP_EVIDENCE_COMPLETION_R28_20260709

## Classification

Ordinary research-only evidence-completion and local-probe-prequalification batch after R27 closeout.

## Accepted baseline

R27 closed as research-only with no local/wide probe eligibility.

Preserved facts:

- SmallCap Low Turnover is the strongest surviving research line and remains `CONTINUE_RESEARCH`.
- SmallCap is still not local probe eligible because the accepted evidence package lacks a preserved row-level pre-trade signal matrix and market-cap universe membership snapshot.
- US30W-R22-002 remains `REMOTE_PRESERVATION_REQUIRED` / observation-only because `us_stock_30w` has no remote configured.
- pass77 remains `REPAIR_ON_NEW_EVIDENCE_ONLY` because no new direct public source field was accepted.
- ETF amount/turnover rotation remains `RETIRE` under current evidence.
- `local_research_probe_eligible_count=0`.
- `wide_research_probe_eligible_count=0`.
- `strategy_candidate_available=false`.

## Objective

Complete the missing SmallCap evidence required for local research probe reconsideration. This batch should not search for new strategies. It should preserve row-level pre-trade signal evidence, preserve universe membership snapshots, rerun leakage/timing checks, and then decide whether SmallCap remains research-only, becomes local research probe eligible, or must continue as observation-only.

US30W preservation is secondary and should be handled only as a mirror/remote-preservation task if feasible. pass77 and ETF should not be rerun unless their failed premise changes.

## Boundary

Research-only. No actionable output, no recommendation, no ticket, no candidate promotion, no readiness/product route, no daily signal, no broker/order/paper/live/auto path, no active registry/schema change, no secret output, no full-frame wide3068, no test-result parameter selection.

## Lane 0 - Evidence freeze and failure memory

- R28-0-1: Freeze R27 final board and carry-forward blockers.
- R28-0-2: Import R27 SmallCap, US30W, pass77, and ETF statuses into experiment store.
- R28-0-3: Update failure memory so pass77 repairs and ETF rotation cannot be rerun without changed evidence.

Deliverables:

- reports/workspace_dispatch/r28_r27_evidence_freeze_20260709.md
- reports/workspace_dispatch/r28_experiment_store_import_20260709.md
- reports/workspace_dispatch/r28_failure_memory_update_20260709.json

## Lane 1 - SmallCap row-level evidence completion

Use the R26/R27 SmallCap Low Turnover evidence package, committed engine/rules fixes, and existing evidence generator.

Tasks:

- SC-R28-1: Generate row-level pre-trade signal matrix with symbol, trade_date, universe flags, raw signal, rank, entry eligibility, filters, and no-future field availability.
- SC-R28-2: Preserve market-cap universe membership snapshots used to define small-cap membership for every decision date.
- SC-R28-3: Preserve entry candidate ordering and rejected-candidate diagnostics for each rebalance/decision date.
- SC-R28-4: Preserve post-trade fills separately from pre-trade signal rows so signal availability and execution are auditable.
- SC-R28-5: Hash and manifest all new evidence files.

Deliverables:

- reports/runops/smallcap_r28_signal_matrix_20260709/pre_trade_signal_matrix.parquet or .csv
- reports/runops/smallcap_r28_signal_matrix_20260709/universe_membership_snapshot.parquet or .csv
- reports/runops/smallcap_r28_signal_matrix_20260709/entry_candidate_diagnostics.csv
- reports/runops/smallcap_r28_signal_matrix_20260709/post_trade_fill_linkage.csv
- reports/runops/smallcap_r28_signal_matrix_20260709/manifest.json
- reports/workspace_dispatch/smallcap_r28_row_level_evidence_completion_20260709.md

## Lane 2 - SmallCap leakage and timing audit

Run full leakage/timing audit using the newly preserved row-level matrix.

Tasks:

- SC-R28-6: Verify all signal fields are available before trade decision time.
- SC-R28-7: Verify market-cap membership is determined from pre-trade or prior-available information.
- SC-R28-8: Verify entry ranking uses only pre-trade signal_score and does not use realized forward returns.
- SC-R28-9: Verify train/validation/test splits and no cross-split leakage.
- SC-R28-10: Verify no test-result parameter selection happened.

Deliverables:

- reports/workspace_dispatch/smallcap_r28_leakage_timing_audit_20260709.md
- reports/workspace_dispatch/smallcap_r28_leakage_timing_audit_20260709.json

## Lane 3 - SmallCap robustness update

Use R27 stress outputs as baseline and rerun only if the new evidence matrix passes audit.

Tasks:

- SC-R28-11: Recompute train/validation/test metrics from preserved row-level signal matrix.
- SC-R28-12: Recompute higher-count permutation/bootstrap if runtime allows; record runtime limits if not.
- SC-R28-13: Recompute walk-forward stress and cost/capacity stress from the preserved matrix.
- SC-R28-14: Compare R26/R27/R28 metrics and explain drift.

Deliverables:

- reports/workspace_dispatch/smallcap_r28_metric_rebuild_from_signal_matrix_20260709.json
- reports/workspace_dispatch/smallcap_r28_permutation_bootstrap_update_20260709.json
- reports/workspace_dispatch/smallcap_r28_walkforward_cost_capacity_update_20260709.csv
- reports/workspace_dispatch/smallcap_r28_metric_drift_report_20260709.md

## Lane 4 - Probe prequalification board

Only after Lane 1-3 complete.

Allowed labels:

- LOCAL_RESEARCH_PROBE_ELIGIBLE
- CONTINUE_RESEARCH
- OBSERVATION_ONLY
- EVIDENCE_INCOMPLETE
- BLOCKED_BY_LEAKAGE_OR_TIMING
- BLOCKED_BY_ROBUSTNESS
- BLOCKED_BY_COST_CAPACITY
- DO_NOT_RETRY

Rules:

- `LOCAL_RESEARCH_PROBE_ELIGIBLE` is research-only and not candidate/readiness/trading evidence.
- No `WIDE_RESEARCH_PROBE_ELIGIBLE` label is allowed in R28 unless explicitly added by a later task; R28 is local-only evidence completion.
- `strategy_candidate_available` must remain false.

Deliverables:

- reports/workspace_dispatch/smallcap_r28_local_probe_prequalification_board_20260709.csv
- reports/workspace_dispatch/smallcap_r28_final_research_memo_20260709.md

## Lane 5 - US30W remote or mirror preservation, optional

Do this only if it does not delay SmallCap evidence completion.

Tasks:

- US30W-R28-1: If user configures a remote, push/mirror us_stock_30w evidence; otherwise produce a controller-side mirror manifest of accepted output hashes and transcripts.
- US30W-R28-2: Preserve local-only caveat unless remote or mirror is verified.

Deliverables:

- reports/workspace_dispatch/us30w_r28_remote_or_mirror_preservation_20260709.md
- reports/workspace_dispatch/us30w_r28_remote_or_mirror_manifest_20260709.json

## Lane 6 - Support repos

market_data:

- MD-R28-1: Contract for SmallCap row-level matrix and local-probe labels.
- MD-R28-2: Overclaim regression for local-probe-eligible label.

strategy_work:

- SW-R28-1: SmallCap evidence completion memo.
- SW-R28-2: Final sync after accepted callbacks.

quant-proj:

- QP-R28-1: Intake and dispatch.
- QP-R28-2: Result summary and closeout.

## Validation

- JSON parse PASS.
- CSV/parquet read PASS.
- git diff check PASS.
- focused pytest PASS if code changed.
- evidence manifest hash PASS.
- leakage/timing audit PASS or explicit block label.
- no test-result parameter selection.
- no actionable output.
- no candidate promotion.

## Stop conditions

- Row-level signal matrix cannot be generated or lacks decision-time fields.
- Universe membership cannot be reconstructed or is post-trade/post-return contaminated.
- Test-result parameter selection is found.
- Local-probe label is written as candidate/readiness/trading evidence.
- pass77 or ETF lines are rerun without changed evidence.
- US30W is claimed remote-preserved without verified remote or mirror.
- secret/auth/non-public access is required.

## Callback envelope

Return callback with batch id, repo, branch, commit, tree, tasks completed, artifacts, validation, SmallCap row-level evidence status, leakage/timing audit result, robustness status, local probe prequalification result, US30W preservation status, candidate availability, boundary result, fixes required, and next source action.
