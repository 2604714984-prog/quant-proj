# User-Dispatch Prompt — DS A-Share C2 R4 Method Fix and Central-DB Resume

Copy the complete fenced prompt below into the user-controlled DS A-share research conversation.

```text
RUN DS_A_SHARE_C2_REMEDIATION_R4_METHOD_FIX_AND_DB_RESUME_20260713

WORKSTREAM:
DS_A_SHARE_RESEARCH_USER_CONTROLLED

TARGET REPOSITORY:
https://github.com/2604714984-prog/quant_research_lab

SOURCE BRANCH:
research/c2-remediation-r3-20260713

SOURCE COMMITS:
R3 implementation: 808629b72224ac24f080599903a083cc69864682
R3 progress report: fae383317c35f807c728078ccddda019eba523bc

CREATE AND USE A NEW BRANCH:
research/c2-remediation-r4-20260713

EXTERNAL AUDIT BASIS:
https://github.com/2604714984-prog/quant-proj/blob/3e0fbde8cc592b5d5044aa2ce5734e84b57bed9d/reports/agent_handoff/ds_c2r_r2_callbacks_external_audit_result_20260713.md

R3 PROGRESS REPORT:
https://github.com/2604714984-prog/quant_research_lab/blob/fae383317c35f807c728078ccddda019eba523bc/reports/ds_a_share/ds_a_share_c2_progress_report_20260713.md

CONTROL AND INDEPENDENCE

This DS A-share research conversation is controlled only by the user.
Quant Manager, the central-database manager, Codex, DS US, and other agents must not select
formulas, thresholds, strategy winners, parameters, regime labels, or conclusions.

The central-database manager may publish data contracts and immutable snapshots. DS may
consume them read-only, but must not change the database, request hidden credentials, or
create a competing data source.

Return the final callback, full GitHub commit SHA, tree SHA, artifact URLs, validation result,
and any remaining database gap request to the user only.

CURRENT STATUS

R3 contains meaningful work but is not system-intake ready.

Current verified status:

A_SHARE_R3_STATUS: MIXED_DATABASE_AND_METHOD_BLOCKED
FAMILY_COUNT_GATE: FAILED
DRAWDOWN_SANITY_GATE: FAILED
H1_H2_H3_H11: ZERO_FILLS
SOFT_ALLOCATOR: NOT_IMPLEMENTED_AS_DYNAMIC_ALLOCATOR
HARD_ALLOCATOR: NOT_IMPLEMENTED_AS_SWITCHING_ALLOCATOR
BEHAVIORAL_TEST_COVERAGE: INCOMPLETE
PACKET_COMMIT_REFERENCE: INVALID_PENDING
STRATEGY_CANDIDATE_AVAILABLE: false
S2_STATUS: S2_CONTINUE_REQUIRED

This R4 task has two independent tracks:

TRACK A — methodology/code repairs that can proceed immediately.
TRACK B — data-dependent replay that must wait for the central-database callback.

Do not block TRACK A while waiting for data.
Do not run TRACK B against an unverified or stale snapshot.

==================================================
PART 0 — FREEZE R3 EVIDENCE AND CREATE A DEFECT BOARD
==================================================

Read line-by-line:

scripts/run_c2_remediation_r3_pipeline.py
tests/test_c2r3_execution_timing.py
tests/test_c2r3_cost_reconciliation.py
tests/test_c2r3_hypothesis_fidelity.py
tests/test_c2r3_allocator_construction.py
tests/test_c2r3_exit_gates_and_packets.py
reports/ds_a_share/remediation_r3/
reports/runops/ds_a_share_c2r3_20260713/

Produce:

reports/ds_a_share/remediation_r4/r4_r3_source_freeze_20260713.md
reports/ds_a_share/remediation_r4/r4_defect_board_20260713.csv

The defect board must include at least:

- circ_mv / daily_basic join coverage not proven;
- H1/H2/H3/H11 zero fills;
- runops orders/fills/holdings are placeholder rows;
- soft allocator is an arithmetic average of independent equity arrays;
- hard allocator is the same arithmetic average;
- allocator switch log contains no real switches;
- allocator weights artifact contains only one fixed row;
- GMM cluster-to-regime mapping uses full-sample labels;
- validation/static filter operator-precedence bug can include H12 test rows;
- multiple focused tests contain only `pass`;
- cost reconciliation report is declarative, not row-level accounting evidence;
- packet `code_commit` remains pending;
- drawdown gate fails;
- only three active strategy families;
- data and local feature parquet are mixed without full snapshot reconciliation.

Every defect must be marked:

FIXED
WAITING_FOR_DB_SNAPSHOT
ACCEPTED_NEGATIVE_EVIDENCE
BLOCKED_WITH_REASON

==================================================
PART 1 — REPLACE PLACEHOLDER TESTS WITH BEHAVIORAL TESTS
==================================================

The following files currently contain empty `pass` tests and must be replaced with real
assertions against code and generated artifacts:

- tests/test_c2r3_cost_reconciliation.py
- tests/test_c2r3_hypothesis_fidelity.py
- tests/test_c2r3_allocator_construction.py
- tests/test_c2r3_exit_gates_and_packets.py

Create R4 versions or update them on the R4 branch.

Required behavioral coverage:

1. Close-D signal cannot earn D return.
2. Fill date is strictly after signal date.
3. Orders with unavailable D+1 open are rejected, not silently skipped as success.
4. Buy and sell transaction costs reconcile to actual traded notional.
5. No trade means zero commission, zero stamp duty, and zero slippage charge.
6. Cash + holdings after execution equals pre-trade value minus real costs.
7. H1 formula is exactly `(return_60 + return_20) / 2` under its declared guard.
8. H3 breadth condition is actually applied.
9. H5 low-volatility + PB composite is actually applied.
10. H8 liquidity/volume shock guard is actually applied.
11. Top-80% circ_mv universe returns nonempty rows when valid data exists.
12. Static ensemble generates one shared sleeve-level portfolio curve.
13. Soft allocator weights vary with frozen regime probabilities.
14. Hard allocator changes only when confirmed state, dwell, hysteresis, and confidence permit.
15. Low-confidence state invokes fallback.
16. Weight sums and risk budget are valid on every date.
17. Switch log is consistent with actual daily weights.
18. `family_count_ge_4` fails with three active families.
19. Drawdown gate blocks >70% drawdowns and flags >50% drawdowns.
20. Packet source commit is exactly 40 hexadecimal characters.
21. No test-period result enters train/validation strategy selection.
22. GMM scaler/model/mapping are all frozen from train only.

No test may consist only of `pass`, a comment, a hard-coded true value, or existence checks
when behavior should be tested.

Required result:

reports/ds_a_share/remediation_r4/r4_behavioral_test_matrix_20260713.csv

==================================================
PART 2 — FIX THE T+1 SIMULATOR AND PRESERVE REAL ROW-LEVEL EVIDENCE
==================================================

Review the R3 T1PortfolioSimulator for accounting correctness.

Mandatory fixes/checks:

- sell proceeds must not be double-counted;
- buy allocation must include all buy fees and slippage before sizing;
- cash must never be silently reused twice;
- unchanged holdings must remain held;
- target weights must be attainable subject to lot size and cash;
- ST/suspension/limit/listing/delist filters must use decision-time information;
- all orders, fills, rejects, holdings, and equity rows must come from actual simulations;
- no placeholder `N/A` rows;
- no constant 1,000,000 portfolio rows used as evidence.

Preserve actual run-level outputs for every strategy and allocator:

reports/runops/ds_a_share_c2r4_20260713/orders.parquet
reports/runops/ds_a_share_c2r4_20260713/fills.parquet
reports/runops/ds_a_share_c2r4_20260713/rejects.parquet
reports/runops/ds_a_share_c2r4_20260713/holdings_daily.parquet
reports/runops/ds_a_share_c2r4_20260713/equity_daily.parquet
reports/runops/ds_a_share_c2r4_20260713/cash_reconciliation.parquet
reports/runops/ds_a_share_c2r4_20260713/execution_manifest.json

The manifest must contain row counts, hashes, strategy ids, split names, source snapshot id,
and generator commit.

==================================================
PART 3 — FIX VALIDATION/TEST SELECTION LOGIC
==================================================

Correct any operator-precedence or filtering bug such as:

`valid and H11 or H12`

which can include H12 rows from train or test.

Use explicit conditions:

split == validation
AND hypothesis in declared validation set

Create an automated scan and focused tests proving:

- no test row contributes to strategy selection;
- no test row selects allocator mapping;
- no test row selects detector component count or thresholds;
- no test row selects family or packet winner;
- 2024-2026 remains diagnostic-only under the frozen split.

Required artifact:

reports/ds_a_share/remediation_r4/r4_test_selection_audit_20260713.json

==================================================
PART 4 — TRAIN-ONLY GMM AND CLUSTER MAPPING
==================================================

The scaler and GMM may be fit on train only, but cluster-to-semantic-state mapping must also
be learned on train only and frozen before validation/test.

Required process:

1. Fit scaler on train features only.
2. Fit GMM on train features only.
3. Derive cluster-to-state interpretation using train dates only.
4. Freeze the mapping.
5. Apply unchanged to validation and test.
6. Save model parameters, scaler parameters, mapping, feature order, random seed, dates,
   and hashes.
7. Report train, validation, and test agreement separately.
8. Do not use test agreement to select model settings.

Required artifacts:

reports/ds_a_share/remediation_r4/r4_probabilistic_detector_manifest_20260713.json
reports/ds_a_share/remediation_r4/r4_gmm_cluster_mapping_train_only_20260713.json
reports/ds_a_share/remediation_r4/r4_detector_oos_diagnostics_20260713.csv

==================================================
PART 5 — IMPLEMENT REAL STATIC, SOFT, HARD, AND FALLBACK ALLOCATORS
==================================================

Do not average independent equity arrays and call the result a regime allocator.

Use actual sleeve-level daily returns/holdings under one portfolio capital account.

Required allocators:

A. BEST_SINGLE_CONTINUOUS
B. STATIC_EQUAL_WEIGHT_SLEEVES
C. STATIC_PREREGISTERED_FIXED_WEIGHT_SLEEVES
D. SOFT_PROBABILITY_WEIGHTED_ALLOCATOR
E. HARD_CONFIRMED_STATE_ALLOCATOR
F. LOW_CONFIDENCE_DEFENSIVE_OR_CASH_FALLBACK

Static allocator:

- fixed sleeve weights frozen before validation;
- one shared portfolio account;
- daily sleeve P&L aggregation;
- rebalance and actual cost accounting.

Soft allocator:

- consume train-frozen GMM probabilities by date;
- map probabilities to sleeve targets;
- apply confidence floor;
- apply maximum daily/rebalance weight change;
- apply allocation ceilings/floors;
- preserve daily target and realized weights;
- charge actual traded-notional costs.

Hard allocator:

- consume confirmed deterministic state only;
- use a preregistered state-to-sleeve map;
- minimum dwell and hysteresis must be observable in the switch log;
- apply confidence threshold and fallback;
- charge actual traded-notional costs.

Fallback:

- cash/no-trade or preregistered defensive sleeve;
- used only under explicit low-confidence or unavailable-specialist state.

Required outputs:

reports/runops/ds_a_share_c2r4_20260713/allocator_equity_curves.parquet
reports/runops/ds_a_share_c2r4_20260713/allocator_target_weights_daily.parquet
reports/runops/ds_a_share_c2r4_20260713/allocator_realized_weights_daily.parquet
reports/ds_a_share/remediation_r4/r4_allocator_comparison_20260713.csv
reports/ds_a_share/remediation_r4/r4_allocator_switch_log_20260713.csv
reports/ds_a_share/remediation_r4/r4_allocator_cost_reconciliation_20260713.csv
reports/ds_a_share/remediation_r4/r4_allocator_state_attribution_20260713.csv

Report train, validation, and test_diagnostic_only separately.

`NO_REGIME_SWITCHING_EDGE_WITH_CURRENT_EVIDENCE` is allowed only after these real portfolios
are compared under identical data, costs, and risk budget.

==================================================
PART 6 — CENTRAL DATABASE CALLBACK DEPENDENCY
==================================================

The central-database manager is separately responsible for:

- validating a_share_daily_basic.circ_mv as point-in-time;
- normalizing ts_code and trade_date keys;
- publishing pre/post join coverage;
- publishing anti-join samples;
- publishing a new immutable A-share snapshot;
- publishing industry/sector fields if needed;
- publishing adj_factor/adjusted-price semantics if available.

Do not invent a workaround while waiting.
Do not silently replace circ_mv with total_mv.
Do not allow NaN circ_mv rows into a strategy whose premise requires direct circ_mv.

Expected database callback fields:

A_SHARE_DB_CALLBACK:
CENTRAL_DATABASE_CONTRACT_URL:
PHYSICAL_DATABASE:
DATASET:
SCHEMA_VERSION:
SNAPSHOT_ID:
AS_OF_MARKET_DATE:
CIRC_MV_PIT_STATUS:
CIRC_MV_NON_NULL_COVERAGE:
CIRC_MV_JOIN_COVERAGE:
TS_CODE_NORMALIZATION_STATUS:
TRADE_DATE_NORMALIZATION_STATUS:
ANTI_JOIN_ARTIFACT_URL:
INDUSTRY_FIELD_STATUS:
ADJ_FACTOR_STATUS:
READ_ONLY_EXPORT_URLS:
EXPORT_HASHES:
FULL_COMMIT_SHA:

If this callback is not yet available, complete Parts 0-5 and return:

WAITING_FOR_A_SHARE_DB_SNAPSHOT

Do not claim system intake readiness.

==================================================
PART 7 — DATA-DEPENDENT REPLAY AFTER DB CALLBACK
==================================================

Only after the immutable database callback is received:

1. Freeze the new snapshot id and hashes.
2. Verify circ_mv non-null coverage by date and symbol.
3. Verify join coverage before and after key normalization.
4. Produce anti-join diagnostics.
5. Rerun H1/H2/H3/H11.
6. Confirm these strategies produce meaningful candidate universes and fills.
7. If direct circ_mv PIT evidence is sufficient, separately preregister H9 SmallCap Quality.
8. Do not activate H9 merely to satisfy the family-count gate.
9. Run H9 only after preregistration and validation criteria are frozen.
10. Preserve H7/H8 reversal losses as negative evidence; do not repair them without a new
    hypothesis and materially new data premise.

Required artifacts:

reports/ds_a_share/remediation_r4/r4_circ_mv_join_coverage_20260713.csv
reports/ds_a_share/remediation_r4/r4_circ_mv_anti_join_samples_20260713.csv
reports/ds_a_share/remediation_r4/r4_zero_fill_resolution_20260713.md
reports/ds_a_share/remediation_r4/r4_post_db_specialist_diagnostics_20260713.csv
reports/ds_a_share/remediation_r4/r4_h9_preregistration_or_blocker_20260713.md

If circ_mv evidence is insufficient, keep:

H9 = BLOCKED_BY_DIRECT_MARKET_CAP
FAMILY_COUNT_GATE_FAILED

Do not create a cosmetic fourth family.

==================================================
PART 8 — PACKETS, GATES, AND FINAL LABEL
==================================================

Packets must reference:

- exact central dataset;
- immutable snapshot id;
- schema version;
- export hashes;
- exact formula implementation;
- actual execution and cost model;
- validation-only metrics;
- diagnostic-only test metrics;
- final 40-character code commit;
- exact artifact URLs/hashes.

Generate packets after the final commit SHA is known, or perform a final metadata commit that
replaces temporary commit placeholders with the immutable SHA.

Do not mark a packet valid when `code_commit_40char` is false.

Required outputs:

reports/ds_a_share/remediation_r4/a_share_strategy_packet_static_20260713.json
reports/ds_a_share/remediation_r4/a_share_strategy_packet_regime_20260713.json
reports/ds_a_share/remediation_r4/r4_packet_schema_validation_20260713.json
reports/ds_a_share/remediation_r4/r4_exit_gate_results_20260713.json
reports/ds_a_share/remediation_r4/r4_final_research_board_20260713.csv
reports/ds_a_share/remediation_r4/r4_final_research_memo_20260713.md

Allowed final labels:

WAITING_FOR_A_SHARE_DB_SNAPSHOT
FAMILY_COUNT_GATE_FAILED
DRAWDOWN_SANITY_GATE_FAILED
STATIC_SINGLE_STRATEGY_BEST
STATIC_ENSEMBLE_BEST
SOFT_REGIME_ALLOCATION_VALIDATION_INTERESTING
HARD_SWITCHING_VALIDATION_INTERESTING
NO_REGIME_SWITCHING_EDGE_WITH_CURRENT_EVIDENCE
REGIME_SWITCHING_COMPARISON_BLOCKED
SYSTEM_INTAKE_READY
S2_CONTINUE_REQUIRED

SYSTEM_INTAKE_READY requires all methodology gates, behavioral tests, packet checks, and
central-data snapshot checks to pass. It is not a strategy-candidate label.

==================================================
MANDATORY GITHUB COMMIT, PUSH, AND REMOTE VERIFICATION
==================================================

Completion is invalid until all approved R4 code, tests, reports, manifests, and bounded
research artifacts are committed and pushed.

Required Git flow:

```bash
git status --short --branch
git branch --show-current
git rev-parse HEAD

git add <approved R4 source, tests, reports, manifests, bounded artifacts only>
git diff --cached --check

git commit -m "A-share C2 R4: fix allocators, tests, selection logic, and DB-dependent replay"
git push -u origin "$(git branch --show-current)"

git rev-parse HEAD
git ls-remote origin "refs/heads/$(git branch --show-current)"
git status --short --branch
```

Do not commit central database files, backups, credentials, `.env`, provider tokens, or
unbounded raw data.

If remote SHA does not match local HEAD, return REMOTE_PUSH_FAILED.

==================================================
BOUNDARY
==================================================

Research-only.

No recommendation, ticket, strategy candidate, readiness/product route, daily signal,
broker/order/paper/live/auto path, secret output, or database write.

STRATEGY_CANDIDATE_AVAILABLE must remain false.

==================================================
CALLBACK
==================================================

CALLBACK_ENVELOPE:
BATCH: DS_A_SHARE_C2_REMEDIATION_R4_METHOD_FIX_AND_DB_RESUME_20260713
WORKSTREAM: DS_A_SHARE_RESEARCH_USER_CONTROLLED
REPOSITORY_URL:
BRANCH:
FULL_COMMIT_SHA:
TREE_SHA:
IMMUTABLE_COMMIT_URL:
REMOTE_BRANCH_URL:
REMOTE_VERIFICATION_OUTPUT:
WORKTREE_STATUS:
PUSH_STATUS:
STATUS:
R3_SOURCE_FREEZE_STATUS:
BEHAVIORAL_TEST_STATUS:
T1_EXECUTION_EVIDENCE_STATUS:
COST_RECONCILIATION_STATUS:
TEST_SELECTION_AUDIT_STATUS:
GMM_TRAIN_ONLY_MAPPING_STATUS:
STATIC_ALLOCATOR_STATUS:
SOFT_ALLOCATOR_STATUS:
HARD_ALLOCATOR_STATUS:
FALLBACK_STATUS:
A_SHARE_DB_CALLBACK_STATUS:
CENTRAL_SNAPSHOT_ID:
CIRC_MV_PIT_STATUS:
CIRC_MV_JOIN_COVERAGE:
ZERO_FILL_RESOLUTION_STATUS:
H9_STATUS:
ACTIVE_FAMILY_COUNT:
FAMILY_COUNT_GATE:
DRAWDOWN_SANITY_GATE:
PACKET_COUNT:
PACKET_SCHEMA_STATUS:
FINAL_REGIME_EDGE_LABEL:
SYSTEM_INTAKE_READY:
STRATEGY_CANDIDATE_AVAILABLE: false
ARTIFACT_GITHUB_URLS:
VALIDATION:
BOUNDARY_RESULT:
FIXES_REQUIRED:
NEXT_ACTION:
```
