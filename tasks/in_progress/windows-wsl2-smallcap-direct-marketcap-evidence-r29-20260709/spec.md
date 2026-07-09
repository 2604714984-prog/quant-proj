# WINDOWS_WSL2_SMALLCAP_DIRECT_MARKETCAP_EVIDENCE_R29_20260709

## Classification

Ordinary research-only evidence-materialization batch after R28 closeout.

## Accepted baseline

R28 completed SmallCap row-level evidence completion but remained no-probe-eligible.

Preserved R28 facts:

- Row-level pre-trade signal matrix was preserved.
- Universe membership proxy snapshot was preserved.
- Entry candidate diagnostics and post-trade fill linkage were preserved.
- Leakage/timing audit was `PASS_WITH_MARKET_CAP_PROXY_LIMITATION`.
- Robustness status was `MATRIX_REBUILD_DIAGNOSTIC_COMPLETE`.
- Local probe prequalification result was `EVIDENCE_INCOMPLETE`.
- Direct market-cap coverage in the accepted local cache was 0.
- local_research_probe_eligible_count=0.
- wide_research_probe_eligible_count=0.
- strategy_candidate_available=false.

## Objective

Try exactly once to materialize direct market-cap membership evidence for SmallCap Low Turnover. If direct market-cap evidence cannot be produced from bounded public/no-secret or already-local accepted sources, stop SmallCap local-probe reconsideration and label the line `EVIDENCE_BLOCKED_MARKET_CAP_UNAVAILABLE` or `OBSERVATION_ONLY`.

Do not rerun SmallCap strategy diagnostics unless direct market-cap membership is materialized and passes timing/leakage audit.

## Boundary

Research-only. No actionable output, no recommendation, no ticket, no candidate promotion, no readiness/product route, no daily signal, no broker/order/paper/live/auto path, no active registry/schema change, no secret output, no full-frame wide3068, no test-result parameter selection.

## Lane 0 - R28 freeze and stop rule

- R29-0-1: Freeze R28 evidence-incomplete result and direct market-cap blocker.
- R29-0-2: Update failure memory with a stop rule: SmallCap cannot be reconsidered without direct market-cap membership evidence.
- R29-0-3: Define accepted source candidates for direct market-cap evidence.

Deliverables:

- reports/workspace_dispatch/r29_r28_evidence_freeze_20260709.md
- reports/workspace_dispatch/r29_smallcap_marketcap_stop_rule_20260709.json
- reports/workspace_dispatch/r29_marketcap_source_candidate_matrix_20260709.csv

## Lane 1 - Direct market-cap evidence materialization

Attempt bounded public/no-secret and already-local source paths only.

Allowed source classes:

- Existing accepted local parquet/cache fields if they contain direct market cap or total/share/close fields sufficient to reconstruct market cap without future information.
- Tushare-derived local cache if already present and no secret access is required.
- Public/no-secret source-local fetch only if source-health passes and the provider does not require auth, paywall, or anti-abuse bypass.

Tasks:

- MC-R29-1: Field inventory for direct market-cap and reconstructable market-cap inputs.
- MC-R29-2: Source health check before any source-heavy work.
- MC-R29-3: Materialize decision-date market-cap membership snapshot if possible.
- MC-R29-4: Validate decision-time availability and no-future membership construction.
- MC-R29-5: Compare direct membership to R28 proxy membership and quantify drift.

Deliverables:

- reports/workspace_dispatch/smallcap_r29_marketcap_field_inventory_20260709.md
- reports/workspace_dispatch/smallcap_r29_marketcap_source_health_20260709.json
- reports/runops/smallcap_r29_direct_marketcap_membership_20260709/direct_marketcap_membership_snapshot.parquet or .csv
- reports/runops/smallcap_r29_direct_marketcap_membership_20260709/manifest.json
- reports/workspace_dispatch/smallcap_r29_direct_marketcap_timing_audit_20260709.md
- reports/workspace_dispatch/smallcap_r29_proxy_vs_direct_membership_drift_20260709.csv

## Lane 2 - Conditional SmallCap local-probe reconsideration

Run only if Lane 1 produces direct market-cap membership evidence and timing audit passes.

Tasks:

- SC-R29-1: Rebuild row-level signal matrix using direct market-cap membership.
- SC-R29-2: Rerun leakage/timing audit.
- SC-R29-3: Recompute metrics from direct-membership matrix.
- SC-R29-4: Compare R26/R27/R28/R29 metrics.
- SC-R29-5: Produce local-probe prequalification board.

Allowed labels:

- LOCAL_RESEARCH_PROBE_ELIGIBLE
- CONTINUE_RESEARCH
- OBSERVATION_ONLY
- EVIDENCE_BLOCKED_MARKET_CAP_UNAVAILABLE
- BLOCKED_BY_LEAKAGE_OR_TIMING
- BLOCKED_BY_ROBUSTNESS
- DO_NOT_RETRY

Deliverables:

- reports/workspace_dispatch/smallcap_r29_direct_membership_signal_matrix_rebuild_20260709.md
- reports/workspace_dispatch/smallcap_r29_direct_membership_leakage_timing_audit_20260709.json
- reports/workspace_dispatch/smallcap_r29_metric_rebuild_direct_membership_20260709.json
- reports/workspace_dispatch/smallcap_r29_metric_drift_report_20260709.md
- reports/workspace_dispatch/smallcap_r29_local_probe_prequalification_board_20260709.csv

## Lane 3 - Stop-or-continue decision

If direct market-cap evidence is not available, do not keep looping.

Tasks:

- DEC-R29-1: If direct evidence is unavailable, mark SmallCap as `OBSERVATION_ONLY` or `EVIDENCE_BLOCKED_MARKET_CAP_UNAVAILABLE`.
- DEC-R29-2: If direct evidence passes, decide whether SmallCap is `LOCAL_RESEARCH_PROBE_ELIGIBLE` or still blocked.
- DEC-R29-3: Preserve final board and memo.

Deliverables:

- reports/workspace_dispatch/r29_final_strategy_research_board_20260709.csv
- reports/workspace_dispatch/r29_final_strategy_research_memo_20260709.md

## Lane 4 - Support repos

market_data:

- MD-R29-1: Contract for direct market-cap membership evidence and local-probe label semantics.
- MD-R29-2: Overclaim regression for `LOCAL_RESEARCH_PROBE_ELIGIBLE` and `EVIDENCE_BLOCKED_MARKET_CAP_UNAVAILABLE`.

strategy_work:

- SW-R29-1: SmallCap direct market-cap evidence memo.
- SW-R29-2: Final sync after accepted callbacks.

quant-proj:

- QP-R29-1: Intake and dispatch.
- QP-R29-2: Result summary and closeout.

## Validation

- JSON parse PASS.
- CSV/parquet read PASS.
- git diff check PASS.
- focused pytest PASS if code changed.
- source health PASS before source-heavy work.
- evidence manifest hash PASS.
- direct membership timing audit PASS or explicit block label.
- no test-result parameter selection.
- no actionable output.
- no candidate promotion.

## Stop conditions

- Source requires secret/auth/paywall/non-public access.
- Direct market-cap membership cannot be reconstructed without future information.
- Direct market-cap evidence is unavailable and no stop label is written.
- Local-probe label is written without direct membership and timing audit passing.
- Local-probe label is treated as candidate/readiness/trading evidence.
- Pass77, ETF, or US30W strategy reruns are attempted without separate evidence-changing task.

## Callback envelope

Return callback with batch id, repo, branch, commit, tree, tasks completed, artifacts, validation, direct market-cap evidence status, leakage/timing audit result, local probe prequalification result, final board counts, strategy candidate availability, boundary result, fixes required, and next source action.
