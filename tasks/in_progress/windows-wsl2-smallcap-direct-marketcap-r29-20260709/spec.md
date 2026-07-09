# WINDOWS_WSL2_SMALLCAP_DIRECT_MARKETCAP_R29_20260709

## Classification

Ordinary research-only evidence completion batch after R28 closeout.

## Accepted baseline

R28 completed row-level evidence preservation for SmallCap Low Turnover but did not open local probe eligibility.

Preserved R28 facts:

- Row-level pre-trade signal matrix preserved.
- Universe membership proxy snapshot preserved.
- Entry candidate diagnostics preserved.
- Post-trade fill linkage preserved.
- Matrix rows: 732,793.
- Membership rows: 732,793.
- Decision date count: 282.
- Candidate diagnostic rows: 14,586.
- Leakage/timing audit: PASS_WITH_MARKET_CAP_PROXY_LIMITATION.
- Direct market-cap coverage: 0.0.
- Local probe result: EVIDENCE_INCOMPLETE.
- local_research_probe_eligible_count=0.
- wide_research_probe_eligible_count=0.
- strategy_candidate_available=false.

## Objective

Resolve the single remaining SmallCap evidence blocker: direct market-cap membership snapshots. If direct market-cap membership cannot be materialized from public/no-secret accepted sources, produce a stop/retry decision and do not continue SmallCap probe reconsideration on the proxy-only premise.

This is not a broad strategy search. It is a narrow evidence-resolution batch.

## Boundary

Research-only. No actionable output, no candidate promotion, no readiness/product route, no daily signal, no broker/order/paper/live/auto path, no active registry/schema change, no secret output, no full-frame wide3068, no test-result parameter selection.

## Lane 0 - R28 evidence freeze

- R29-0-1: Freeze R28 row-level evidence and direct market-cap blocker.
- R29-0-2: Import R28 matrix/audit status into experiment store and failure memory.
- R29-0-3: Mark proxy-only SmallCap membership as insufficient for local probe prequalification.

Deliverables:

- reports/workspace_dispatch/r29_r28_evidence_freeze_20260709.md
- reports/workspace_dispatch/r29_experiment_store_import_20260709.md
- reports/workspace_dispatch/r29_failure_memory_update_20260709.json

## Lane 1 - Direct market-cap source search and materialization

Use bounded public/no-secret sources only. Do not use private/auth/paywalled/anti-abuse-bypassing sources.

Tasks:

- MC-R29-1: Identify public direct market-cap or float-market-cap fields available in existing local cache or public data sources.
- MC-R29-2: Source-health smoke for direct market-cap fields over a small symbol/date sample.
- MC-R29-3: If source health passes, materialize decision-date market-cap membership snapshots for the SmallCap universe.
- MC-R29-4: If direct market cap is unavailable, produce a field-unavailable proof and stop SmallCap local-probe reconsideration until source evidence changes.

Deliverables:

- reports/workspace_dispatch/smallcap_r29_direct_marketcap_source_health_20260709.md
- reports/workspace_dispatch/smallcap_r29_direct_marketcap_materialization_or_unavailable_20260709.md
- reports/runops/smallcap_r29_direct_marketcap_20260709/marketcap_membership_snapshot.parquet or .csv if materialized
- reports/runops/smallcap_r29_direct_marketcap_20260709/manifest.json

## Lane 2 - Direct market-cap membership audit

Only run if Lane 1 materializes direct market-cap rows.

Tasks:

- MC-R29-5: Compare direct market-cap membership against the R28 amount/amount_ma20 proxy membership.
- MC-R29-6: Quantify membership overlap, disagreement, turnover, and date coverage.
- MC-R29-7: Verify membership fields are available before decision time.
- MC-R29-8: Verify no future-return or post-trade fields are used.

Deliverables:

- reports/workspace_dispatch/smallcap_r29_direct_vs_proxy_membership_audit_20260709.csv
- reports/workspace_dispatch/smallcap_r29_marketcap_timing_audit_20260709.md
- reports/workspace_dispatch/smallcap_r29_marketcap_timing_audit_20260709.json

## Lane 3 - SmallCap matrix rebuild with direct market-cap membership

Only run if Lane 2 passes.

Tasks:

- SC-R29-1: Rebuild row-level signal matrix using direct market-cap membership.
- SC-R29-2: Recompute train/validation/test metrics from the direct-membership matrix.
- SC-R29-3: Recompute leakage/timing audit.
- SC-R29-4: Recompute walk-forward, permutation/bootstrap, and cost/capacity summaries only as needed to compare to R28.
- SC-R29-5: Explain drift from R26/R27/R28.

Deliverables:

- reports/runops/smallcap_r29_direct_marketcap_matrix_20260709/pre_trade_signal_matrix.parquet or .csv
- reports/workspace_dispatch/smallcap_r29_direct_marketcap_metric_rebuild_20260709.json
- reports/workspace_dispatch/smallcap_r29_direct_marketcap_leakage_audit_20260709.md
- reports/workspace_dispatch/smallcap_r29_direct_marketcap_robustness_update_20260709.csv
- reports/workspace_dispatch/smallcap_r29_metric_drift_report_20260709.md

## Lane 4 - Decision board

Allowed labels:

- LOCAL_RESEARCH_PROBE_ELIGIBLE
- CONTINUE_RESEARCH
- EVIDENCE_INCOMPLETE
- DIRECT_MARKET_CAP_UNAVAILABLE
- BLOCKED_BY_MEMBERSHIP_DRIFT
- BLOCKED_BY_LEAKAGE_OR_TIMING
- BLOCKED_BY_ROBUSTNESS
- OBSERVATION_ONLY
- DO_NOT_RETRY_UNTIL_NEW_SOURCE

Rules:

- LOCAL_RESEARCH_PROBE_ELIGIBLE is research-only and not candidate/readiness/trading evidence.
- strategy_candidate_available must remain false.
- If direct market-cap remains unavailable, output DIRECT_MARKET_CAP_UNAVAILABLE or DO_NOT_RETRY_UNTIL_NEW_SOURCE and stop.

Deliverables:

- reports/workspace_dispatch/smallcap_r29_marketcap_resolution_board_20260709.csv
- reports/workspace_dispatch/smallcap_r29_final_research_memo_20260709.md

## Lane 5 - Support repos

market_data:

- MD-R29-1: Contract for direct market-cap membership evidence and local probe labels.
- MD-R29-2: Overclaim regression for LOCAL_RESEARCH_PROBE_ELIGIBLE and unavailable labels.

strategy_work:

- SW-R29-1: SmallCap direct market-cap resolution memo.
- SW-R29-2: Final sync after accepted callbacks.

quant-proj:

- QP-R29-1: Intake and dispatch.
- QP-R29-2: Result summary and closeout.

## Validation

- JSON parse PASS.
- CSV/parquet read PASS.
- git diff check PASS.
- focused pytest PASS if code changed.
- source-health PASS or explicit unavailable proof.
- direct membership timing audit PASS if materialized.
- no test-result parameter selection.
- no actionable output.
- no candidate promotion.

## Stop conditions

- Direct market-cap source requires secret/auth/non-public access.
- Direct market-cap source is unavailable and proxy-only path is being reused for probe eligibility.
- Membership timing audit fails.
- Local-probe label is written as candidate/readiness/trading evidence.
- Strategy parameters are selected from test results.

## Callback envelope

Return callback with batch id, repo, branch, commit, tree, tasks completed, artifacts, validation, direct market-cap source status, materialization status, timing audit result, matrix rebuild status, local probe prequalification result, candidate availability, boundary result, fixes required, and next source action.
