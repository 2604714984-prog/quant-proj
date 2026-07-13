# User-Dispatch Prompt — DS A-Share C2 R4.1 Critical Methodology Patch

Copy the complete fenced prompt below into the user-controlled DS A-share research conversation.

```text
RUN DS_A_SHARE_C2_REMEDIATION_R4_1_CRITICAL_METHOD_PATCH_20260713

WORKSTREAM:
DS_A_SHARE_RESEARCH_USER_CONTROLLED

TARGET REPOSITORY:
https://github.com/2604714984-prog/quant_research_lab

SOURCE BRANCH:
research/c2-remediation-r4-20260713

SOURCE COMMIT:
f6ed87dbf30c41c7ba13b6aa2d4910a439fbdc5b

CREATE AND USE A NEW BRANCH:
research/c2-remediation-r4-1-20260713

EXTERNAL AUDIT RESULT:
https://github.com/2604714984-prog/quant-proj/blob/29cd6203bcc572bf8fe92a6ecb2d8ef5de052532/reports/agent_handoff/ds_a_share_c2_r4_method_external_audit_result_20260713.md

CONTROL AND INDEPENDENCE

This DS A-share research conversation is controlled only by the user.
Quant Manager, central-database manager, Codex, DS US, and other agents must not select
strategy formulas, winners, parameters, regime thresholds, candidate labels, or conclusions.

The central-database manager may publish immutable snapshots and read-only exports.
DS must consume them read-only and must not write to the central database or create a
competing provider/data chain.

Return the final callback, full GitHub SHAs, immutable URLs, artifact URLs, tests, and remaining
blockers to the user only.

==================================================
R4 EXTERNAL AUDIT STATUS
==================================================

The R4 method-completion claim was externally rejected:

REJECT_R4_METHOD_COMPLETION_CRITICAL_FIXES_REQUIRED

Accepted only as:

PARTIAL_METHOD_REMEDIATION_SOURCE_ARTIFACTS

Current verified status:

T1_EXECUTION_STATUS: CHRONOLOGY_INVALID
BEHAVIORAL_TEST_STATUS: INSUFFICIENT
SOFT_ALLOCATOR_STATUS: NOT_IMPLEMENTED
HARD_ALLOCATOR_STATUS: NOT_IMPLEMENTED
PROBABILISTIC_DETECTOR_STATUS: PARTIALLY_FIXED_TRAIN_MAPPING_ONLY
PACKET_SCHEMA_STATUS: INVALID_REFERENCES
A_SHARE_DB_CALLBACK_STATUS: WAITING
FAMILY_COUNT_GATE: FAILED
DRAWDOWN_SANITY_GATE: FAILED
SYSTEM_INTAKE_READY: false
STRATEGY_CANDIDATE_AVAILABLE: false
S2_STATUS: S2_CONTINUE_REQUIRED

R4.1 is a narrow critical-method patch.

Do not rebuild the data foundation.
Do not rerun H1/H2/H3/H11/H9 against an unverified database snapshot.
Do not claim system intake readiness.

R4.1 must complete the method fixes that are independent of the database callback.
After completion, return:

R4_1_METHOD_PATCH_COMPLETE_WAITING_FOR_DB_SNAPSHOT

unless the immutable A-share database callback has already been delivered by the user.

==================================================
PART 0 — FREEZE R4 AND CREATE A CRITICAL FIX BOARD
==================================================

Read line-by-line:

scripts/run_c2_remediation_r4_pipeline.py
tests/test_c2r4_behavioral.py
reports/ds_a_share/remediation_r4/
reports/runops/ds_a_share_c2r4_20260713/

Produce:

reports/ds_a_share/remediation_r4_1/r4_1_r4_source_freeze_20260713.md
reports/ds_a_share/remediation_r4_1/r4_1_critical_fix_board_20260713.csv

The board must include at least:

1. future D+1 fills applied to D account state;
2. invalid or NaN D+1 open not rejected correctly;
3. suspension/limit/listing/delist execution checks incomplete;
4. sell-side commission missing;
5. buy allocation may overspend cash;
6. retained holdings not resized toward target weights;
7. row-level accounting identity not preserved;
8. H3 breadth guard not implemented;
9. 20% bucket truncated to top 10;
10. soft allocator is arithmetic mean, not probability allocation;
11. hard allocator is arithmetic mean, not state switching;
12. allocator daily weights and switch log are synthetic/hard-coded;
13. allocator equity artifact is a summary table, not daily equity;
14. behavioral tests contain weak or empty assertions;
15. behavioral matrix is hard-coded VERIFIED;
16. test-selection audit is tautological;
17. GMM component count not train-only;
18. scaler/model hashes and daily OOS probabilities missing;
19. packets reference the wrong commit;
20. packets claim PIT verified while DB callback is pending;
21. packet schema validation is superficial;
22. exit gates are hard-coded true.

Each item must end as:

FIXED_AND_TESTED
WAITING_FOR_DB_CALLBACK
ACCEPTED_NEGATIVE_EVIDENCE
BLOCKED_WITH_REASON

==================================================
PART 1 — IMPLEMENT A TRUE EVENT-LOOP T+1 ENGINE
==================================================

The R4 simulator must be replaced or refactored so that account state changes only when the
event loop reaches the fill date.

Required event order:

On date D:

1. Process any queued orders scheduled for D.
2. Validate D execution prices and tradability.
3. Execute eligible orders.
4. Update cash and holdings.
5. Mark the portfolio at D close.
6. Form new signals using D-close-available information.
7. Queue new orders for the next valid trading session D+1.

Never:

- read D+1 open while still recording D account state;
- add D+1 holdings to D holdings;
- let D signals earn D returns;
- mark a fill as D+1 while applying it on D.

Required state objects:

pending_orders
executed_orders
rejected_orders
holdings
cash
fills
portfolio_value

Required order fields:

strategy_id
split
order_id
signal_date
scheduled_execution_date
symbol
side
target_shares
target_weight
reason

Required fill/reject fields:

order_id
execution_date
symbol
side
shares
raw_open
execution_price
notional
commission
stamp_duty
slippage_cost
reject_reason

Required tests:

- D equity uses pre-D+1-fill holdings;
- D+1 equity uses post-fill holdings;
- fill date is strictly after signal date;
- queued order is not applied before scheduled execution date;
- no D signal earns D return;
- split-boundary positions are handled by an explicit frozen policy.

==================================================
PART 2 — COMPLETE EXECUTION-DATE TRADABILITY
==================================================

Validate tradability on the actual execution date, not only the signal date.

Required checks:

- execution open exists, is finite, and is greater than zero;
- symbol row exists on execution date;
- suspension status permits trading;
- buy is rejected at locked limit-up;
- sell is rejected at locked limit-down;
- ST status uses a valid dated field contract;
- listing-age rule is applied if preregistered;
- delisted/inactive symbols cannot be bought;
- unavailable execution data creates a reject row;
- no rejection test may use `len(rejects) >= 0`.

If a required dated tradability field is unavailable before the database callback, return the
specific field as WAITING_FOR_DB_CALLBACK. Do not silently omit the check.

Required artifact:

reports/ds_a_share/remediation_r4_1/r4_1_execution_tradability_contract_20260713.md

==================================================
PART 3 — CORRECT CASH, COST, AND TARGET-WEIGHT ACCOUNTING
==================================================

Implement a shared portfolio account with incremental target-weight rebalancing.

Requirements:

1. Apply commission to buys and sells according to the declared cost contract.
2. Apply stamp duty to sells only.
3. Apply slippage through execution price or explicit slippage cost, but not both twice.
4. Size purchases so cash cannot become negative.
5. Remove the `per_stock * 1.1` overspend allowance.
6. Rebalance retained holdings toward target shares.
7. Execute incremental net trades instead of only add/remove names.
8. Lot-size rounding must be deterministic.
9. Unfilled target residuals must be documented.
10. No-trade rebalance produces zero cost.

For every execution date preserve this identity:

pre_trade_cash
+ pre_trade_holdings_value
- commission
- stamp_duty
- slippage_cost
= post_trade_cash + post_trade_holdings_value

Store:

reports/runops/ds_a_share_c2r4_1_20260713/trade_reconciliation.parquet
reports/runops/ds_a_share_c2r4_1_20260713/cash_daily.parquet
reports/runops/ds_a_share_c2r4_1_20260713/holdings_daily.parquet
reports/ds_a_share/remediation_r4_1/r4_1_accounting_error_summary_20260713.csv

The maximum absolute reconciliation error must be reported and bounded by a declared numeric
tolerance.

==================================================
PART 4 — RESTORE PREREGISTRATION FIDELITY
==================================================

Correct the implementation/registration mismatch.

Mandatory fixes:

- H3 must apply an explicit breadth guard from a dated regime/breadth field.
- H1/H2/H3 and every other hypothesis must respect the preregistered bucket size.
- Do not return a 20% bucket and then truncate it to top 10.
- If the strategy declares top/bottom 20%, execute that selection subject to capacity and lot
  constraints.
- Apply declared liquidity floors.
- Apply declared universe rules.
- Apply sector/board neutrality where preregistered.
- Apply dated ST/suspension/listing/delist filters.
- H8 must produce no signal when its liquidity-shock condition is false.
- H5 composite ordering must be verifiable with a deterministic toy example.

Produce a machine-derived fidelity matrix. Do not assign `MATCH` unconditionally.

reports/ds_a_share/remediation_r4_1/r4_1_hypothesis_fidelity_20260713.csv

Required columns:

hypothesis_id
formula_test
bucket_test
universe_test
guard_test
regime_test
execution_test
cost_test
status
blocking_reason
source_code_ref

==================================================
PART 5 — BUILD REAL SHARED-CAPITAL ALLOCATORS
==================================================

The R4 soft/hard implementations are rejected.

Implement actual allocators using daily sleeve returns or sleeve holdings under one shared
capital account.

A. STATIC_EQUAL_WEIGHT_SLEEVES

- frozen sleeve weights before validation;
- daily portfolio return from prior-day realized sleeve weights;
- explicit sleeve rebalance costs;
- one daily equity curve.

B. STATIC_PREREGISTERED_FIXED_WEIGHT_SLEEVES

- frozen weights selected using train/validation only;
- no test-based weight choice.

C. SOFT_PROBABILITY_WEIGHTED_ALLOCATOR

- consume daily out-of-sample GMM probabilities;
- map state probabilities to sleeve target weights;
- apply confidence floor;
- apply weight floor/ceiling;
- apply maximum weight change per rebalance;
- normalize to the declared risk budget;
- use actual prior realized weights to compute trades and costs;
- preserve daily target and realized sleeve weights.

D. HARD_CONFIRMED_STATE_ALLOCATOR

- consume the dated confirmed deterministic state;
- use a preregistered state-to-sleeve map;
- switch only when state confirmation and minimum dwell permit;
- apply confidence threshold;
- use fallback under low confidence or missing specialist;
- calculate actual sleeve-level trades and costs;
- preserve every switch and the exact reason.

E. FALLBACK

- cash/no-trade or a preregistered defensive sleeve;
- activated only by explicit low-confidence/unavailable-specialist rules.

Required daily outputs:

reports/runops/ds_a_share_c2r4_1_20260713/allocator_equity_daily.parquet
reports/runops/ds_a_share_c2r4_1_20260713/allocator_target_weights_daily.parquet
reports/runops/ds_a_share_c2r4_1_20260713/allocator_realized_weights_daily.parquet
reports/runops/ds_a_share_c2r4_1_20260713/allocator_trades.parquet
reports/ds_a_share/remediation_r4_1/r4_1_allocator_switch_log_20260713.csv
reports/ds_a_share/remediation_r4_1/r4_1_allocator_cost_reconciliation_20260713.csv
reports/ds_a_share/remediation_r4_1/r4_1_allocator_comparison_20260713.csv

The daily equity artifact must contain daily dates and equity values, not summary metrics.

Required comparison metrics by train / validation / test_diagnostic_only:

- total return;
- CAGR;
- annual volatility;
- Sharpe;
- Sortino;
- maximum drawdown;
- turnover;
- traded notional;
- transaction cost;
- switch count;
- average dwell;
- fallback percentage;
- state attribution.

`NO_REGIME_SWITCHING_EDGE_WITH_CURRENT_EVIDENCE` is forbidden until this comparison is real.

==================================================
PART 6 — COMPLETE TRAIN-ONLY PROBABILISTIC DETECTOR EVIDENCE
==================================================

R4.1 requirements:

1. Choose feature set using train information only.
2. Choose component count using a preregistered train-only rule.
3. Fit scaler on train only.
4. Fit GMM/model on train only.
5. Derive cluster-to-state mapping on train only.
6. Freeze all parameters before validation.
7. Apply unchanged to validation and test.
8. Preserve scaler parameters or serialized model hash.
9. Preserve model parameters or serialized model hash.
10. Preserve component-selection evidence.
11. Preserve daily OOS state probabilities and confidence.
12. Do not use validation/test agreement to alter the model.

Required outputs:

reports/ds_a_share/remediation_r4_1/r4_1_probabilistic_detector_manifest_20260713.json
reports/ds_a_share/remediation_r4_1/r4_1_component_selection_train_only_20260713.md
reports/ds_a_share/remediation_r4_1/r4_1_model_hashes_20260713.json
reports/runops/ds_a_share_c2r4_1_20260713/regime_probabilities_daily.parquet
reports/ds_a_share/remediation_r4_1/r4_1_detector_oos_diagnostics_20260713.csv

If the sidecar covers only a subset of semantic states, disclose that limitation and do not
claim full regime coverage.

==================================================
PART 7 — REPLACE WEAK TESTS WITH FAILURE-SENSITIVE TESTS
==================================================

Create tests that fail against R4 and pass only against the corrected R4.1 implementation.

Required test modules:

tests/test_c2r4_1_event_loop_timing.py
tests/test_c2r4_1_execution_tradability.py
tests/test_c2r4_1_cash_cost_reconciliation.py
tests/test_c2r4_1_hypothesis_fidelity.py
tests/test_c2r4_1_soft_allocator.py
tests/test_c2r4_1_hard_allocator.py
tests/test_c2r4_1_gmm_train_only.py
tests/test_c2r4_1_selection_and_packets.py

Mandatory assertions:

- unavailable open must produce at least one expected reject in the toy case;
- no negative cash;
- exact account identity within tolerance;
- sell commission is charged;
- no trade means zero cost;
- retained holdings are resized when targets change;
- H3 guard prevents signals when breadth condition is false;
- H8 returns no signals below the shock threshold;
- 20% selection size is respected;
- soft weights vary with probabilities;
- hard weights change only on valid state transitions;
- dwell/hysteresis is enforced;
- fallback activates under low confidence;
- daily allocator weights sum to the allowed budget;
- switch log matches daily weights;
- test split is not read by any selector;
- packet commit equals the implementation commit;
- gates fail when artifacts/tests fail.

No `pass`-only test.
No `>= 0` assertion where positive behavior is required.
No existence-only assertion for behavioral requirements.
No hand-written behavioral matrix.

Generate the behavioral matrix directly from pytest/JUnit results and link each row to a test
node id.

Required outputs:

reports/ds_a_share/remediation_r4_1/r4_1_pytest_results.xml
reports/ds_a_share/remediation_r4_1/r4_1_behavioral_test_matrix_20260713.csv
reports/ds_a_share/remediation_r4_1/r4_1_test_transcript_20260713.txt

==================================================
PART 8 — PROVE NO TEST-RESULT SELECTION
==================================================

Implement an explicit selection ledger.

For each selected:

- model architecture;
- strategy formula;
- strategy family;
- detector threshold;
- allocator mapping;
- allocator weight;
- packet winner;
- final label;

record:

selection_item
allowed_input_split
actual_input_artifacts
selected_value
selection_code_ref
test_artifact_accessed
status

Required artifact:

reports/ds_a_share/remediation_r4_1/r4_1_selection_ledger_20260713.csv

Any test-period access in a selection path must force:

TEST_RESULT_SELECTION_DETECTED
SYSTEM_INTAKE_READY=false

==================================================
PART 9 — PACKETS AND TWO-STEP COMMIT FINALIZATION
==================================================

Packets cannot reference their own future commit.
Use a two-step Git procedure.

STEP 1 — IMPLEMENTATION COMMIT

Commit and push:

- corrected source;
- tests;
- run artifacts;
- detector/allocator evidence;
- temporary blocked packet templates if needed.

Capture:

IMPLEMENTATION_COMMIT_SHA

STEP 2 — PACKET FINALIZATION COMMIT

Regenerate final packets so they reference:

implementation_commit = IMPLEMENTATION_COMMIT_SHA
packet_finalization_commit = current metadata commit after creation
central_snapshot_id = WAITING_FOR_A_SHARE_DB_SNAPSHOT unless user delivered an immutable callback
PIT_status = PENDING unless verified by DB callback
system_intake_ready = false while DB callback is pending

Commit and push the finalized packets and callback.

Required packet fields:

strategy_id
exact_formula
exact_universe
exact_bucket_rule
execution_model
cost_model
implementation_commit
packet_finalization_commit
central_database_contract_url
central_snapshot_id
central_export_hashes
PIT_status
validation_metrics
test_diagnostic_metrics
artifact_urls
artifact_hashes
generator_command
known_blockers
system_intake_ready

Required outputs:

reports/ds_a_share/remediation_r4_1/a_share_strategy_packet_static_20260713.json
reports/ds_a_share/remediation_r4_1/a_share_strategy_packet_regime_20260713.json
reports/ds_a_share/remediation_r4_1/r4_1_packet_schema_validation_20260713.json

Do not claim packet validity through a hard-coded boolean.
Validate required fields, commit references, artifact existence, and hashes.

==================================================
PART 10 — EVIDENCE-DERIVED EXIT GATES
==================================================

No gate may be assigned `True` directly.

Each gate must reference:

- source artifact;
- test node ids;
- numeric threshold;
- derived result;
- blocking reason.

Required gates:

EVENT_LOOP_T1_VALID
EXECUTION_TRADABILITY_VALID
ACCOUNT_RECONCILIATION_VALID
HYPOTHESIS_FIDELITY_VALID
STATIC_ALLOCATOR_VALID
SOFT_ALLOCATOR_VALID
HARD_ALLOCATOR_VALID
FALLBACK_VALID
GMM_TRAIN_ONLY_VALID
NO_TEST_SELECTION_VALID
BEHAVIORAL_TESTS_VALID
PACKETS_VALID
DB_CALLBACK_AVAILABLE
FAMILY_COUNT_GE_4
DRAWDOWN_SANITY

Required artifact:

reports/ds_a_share/remediation_r4_1/r4_1_exit_gate_results_20260713.json

If the DB callback is pending, the final method status may be:

R4_1_METHOD_PATCH_COMPLETE_WAITING_FOR_DB_SNAPSHOT

It must not be:

SYSTEM_INTAKE_READY

==================================================
PART 11 — DATABASE CALLBACK DEPENDENCY
==================================================

The database manager is separately responsible for circ_mv PIT, join coverage, key
normalization, anti-join, immutable snapshot, and hashes.

Do not rerun H1/H2/H3/H11/H9 against an unverified snapshot.
Do not replace circ_mv with total_mv.
Do not create a cosmetic fourth family.

If the user provides an immutable A_SHARE_DB_CALLBACK during R4.1:

1. freeze the callback URL, commit, snapshot, and hashes;
2. validate the snapshot contract;
3. rerun only the data-dependent strategies;
4. preserve method-patch results separately;
5. produce a post-DB replay commit and packet-finalization commit.

If no callback is available, finish R4.1 method repairs and stop at:

WAITING_FOR_A_SHARE_DB_SNAPSHOT

==================================================
FINAL LABELS
==================================================

Allowed:

R4_1_METHOD_PATCH_COMPLETE_WAITING_FOR_DB_SNAPSHOT
EVENT_LOOP_T1_BLOCKED
EXECUTION_TRADABILITY_BLOCKED
ACCOUNT_RECONCILIATION_BLOCKED
SOFT_ALLOCATOR_BLOCKED
HARD_ALLOCATOR_BLOCKED
PROBABILISTIC_DETECTOR_PARTIAL
TEST_RESULT_SELECTION_DETECTED
PACKET_FINALIZATION_BLOCKED
FAMILY_COUNT_GATE_FAILED
DRAWDOWN_SANITY_GATE_FAILED
S2_CONTINUE_REQUIRED

SYSTEM_INTAKE_READY is forbidden in R4.1 unless:

- all method gates pass;
- immutable DB callback is accepted;
- data-dependent replay is complete;
- packets reference exact implementation and snapshot evidence;
- external audit accepts the result.

STRATEGY_CANDIDATE_AVAILABLE must remain false.

==================================================
MANDATORY GITHUB COMMIT, PUSH, AND REMOTE VERIFICATION
==================================================

Completion is invalid until both implementation and packet-finalization commits are pushed.

Required flow:

```bash
git status --short --branch
git branch --show-current
git diff --check

# Implementation commit
git add <approved R4.1 source, tests, reports, manifests, bounded artifacts>
git diff --cached --check
git commit -m "A-share C2 R4.1: fix T+1 event loop, accounting, allocators, and tests"
git push -u origin "$(git branch --show-current)"
IMPLEMENTATION_COMMIT_SHA="$(git rev-parse HEAD)"

# Regenerate packets/callback with IMPLEMENTATION_COMMIT_SHA
# Then packet-finalization commit
git add <final packets, callback, validation manifests>
git diff --cached --check
git commit -m "A-share C2 R4.1: finalize packet metadata and remote evidence"
git push
PACKET_FINALIZATION_COMMIT_SHA="$(git rev-parse HEAD)"

git ls-remote origin "refs/heads/$(git branch --show-current)"
git status --short --branch
```

Do not commit:

- central DB files;
- database backups;
- credentials;
- `.env`;
- tokens;
- private connection strings;
- unbounded raw data;
- virtual environments.

Remote verification requires the final branch ref to match PACKET_FINALIZATION_COMMIT_SHA.

==================================================
BOUNDARY
==================================================

Research-only.

No recommendation, ticket, strategy candidate, readiness/product route, daily signal,
broker/order/paper/live/auto activation, secret output, or database write.

==================================================
CALLBACK
==================================================

CALLBACK_ENVELOPE:
BATCH: DS_A_SHARE_C2_REMEDIATION_R4_1_CRITICAL_METHOD_PATCH_20260713
WORKSTREAM: DS_A_SHARE_RESEARCH_USER_CONTROLLED
REPOSITORY_URL:
BRANCH:
IMPLEMENTATION_COMMIT_SHA:
PACKET_FINALIZATION_COMMIT_SHA:
TREE_SHA:
IMMUTABLE_IMPLEMENTATION_COMMIT_URL:
IMMUTABLE_FINALIZATION_COMMIT_URL:
REMOTE_BRANCH_URL:
REMOTE_VERIFICATION_OUTPUT:
WORKTREE_STATUS:
PUSH_STATUS:
STATUS:
R4_SOURCE_FREEZE_STATUS:
EVENT_LOOP_T1_STATUS:
EXECUTION_TRADABILITY_STATUS:
ACCOUNT_RECONCILIATION_STATUS:
HYPOTHESIS_FIDELITY_STATUS:
STATIC_ALLOCATOR_STATUS:
SOFT_ALLOCATOR_STATUS:
HARD_ALLOCATOR_STATUS:
FALLBACK_STATUS:
GMM_TRAIN_ONLY_STATUS:
GMM_MODEL_HASHES:
NO_TEST_SELECTION_STATUS:
BEHAVIORAL_TEST_RESULT:
BEHAVIORAL_TEST_COUNT:
PACKET_COUNT:
PACKET_SCHEMA_STATUS:
A_SHARE_DB_CALLBACK_STATUS:
CENTRAL_SNAPSHOT_ID:
FAMILY_COUNT_GATE:
DRAWDOWN_SANITY_GATE:
FINAL_METHOD_LABEL:
SYSTEM_INTAKE_READY: false
STRATEGY_CANDIDATE_AVAILABLE: false
ARTIFACT_GITHUB_URLS:
VALIDATION:
BOUNDARY_RESULT:
FIXES_REQUIRED:
NEXT_ACTION:
```
