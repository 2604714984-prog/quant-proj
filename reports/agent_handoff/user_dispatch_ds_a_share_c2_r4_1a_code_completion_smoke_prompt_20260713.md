# User-Dispatch Prompt — DS A-Share C2 R4.1a Code Completion and Smoke Validation

Copy the complete fenced prompt below into the user-controlled DS A-share research conversation.

```text
RUN DS_A_SHARE_C2_REMEDIATION_R4_1A_CODE_COMPLETION_AND_SMOKE_20260713

WORKSTREAM:
DS_A_SHARE_RESEARCH_USER_CONTROLLED

TARGET REPOSITORY:
https://github.com/2604714984-prog/quant_research_lab

SOURCE BRANCH:
research/c2-remediation-r4-1-20260713

SOURCE COMMIT:
b8edb61db6018976c9f7c952501f892cc9e4de87

CREATE AND USE A NEW BRANCH:
research/c2-remediation-r4-1a-20260713

EXTERNAL AUDIT RESULT:
https://github.com/2604714984-prog/quant-proj/blob/52722ca45433c6b7cdf073a178c52f0d32d7bffa/reports/agent_handoff/ds_a_share_c2_r4_1_implementation_external_audit_result_20260713.md

CONTROL AND INDEPENDENCE

This DS A-share research conversation is controlled only by the user.
Quant Manager, central-database manager, Codex, DS US, and other agents must not select
strategy formulas, thresholds, model winners, parameters, regime conclusions, or candidate
labels.

The central-database manager is independently building the authoritative database and will
later publish immutable callbacks. DS must not write to the database, create a parallel data
chain, or bypass the central database.

Return all callbacks, commits, artifacts, and remaining blockers to the user only.

==================================================
CURRENT AUDIT STATUS
==================================================

The R4.1 implementation commit was externally rejected:

REJECT_R4_1_IMPLEMENTATION_COMMIT_INCOMPLETE_AND_NONRUNNABLE

Accepted only as:

R4_1_PARTIAL_EVENT_LOOP_DRAFT

Verified blocking state:

R4_1_IMPLEMENTATION_STATUS: REJECTED_INCOMPLETE_NONRUNNABLE
EVENT_LOOP_STATUS: PARTIAL_DRAFT
TEST_COLLECTION_STATUS: EXPECTED_IMPORT_FAILURE
FULL_SIMULATION_STATUS: NOT_RUN
STATIC_ALLOCATOR_STATUS: NOT_COMMITTED
SOFT_ALLOCATOR_STATUS: NOT_COMMITTED
HARD_ALLOCATOR_STATUS: NOT_COMMITTED
FALLBACK_STATUS: NOT_COMMITTED
GMM_TRAIN_ONLY_STATUS: NOT_COMMITTED
SELECTION_LEDGER_STATUS: NOT_COMMITTED
PACKET_STATUS: NOT_COMMITTED
EXIT_GATE_STATUS: NOT_COMMITTED
A_SHARE_DB_CALLBACK_STATUS: WAITING
SYSTEM_INTAKE_READY: false
STRATEGY_CANDIDATE_AVAILABLE: false
S2_STATUS: S2_CONTINUE_REQUIRED

R4.1a is a code-completion and bounded-smoke task.

Do not run the full 8.7M-row research workload until the implementation is complete, import-safe,
unit-tested, and smoke-validated.

Do not claim full method completion merely because source files exist.

==================================================
PRIMARY OBJECTIVE
==================================================

Produce a complete, import-safe, runnable R4.1a implementation package that:

1. contains every declared engine, strategy, allocator, detector, selection, packet, and gate
   component;
2. passes failure-sensitive unit tests on deterministic toy fixtures;
3. passes a bounded smoke simulation that exercises all components end-to-end;
4. preserves evidence and test transcripts;
5. remains waiting for the immutable central-database callback before data-dependent full replay;
6. is committed and pushed to GitHub with remote SHA verification.

The acceptable completion label for this task is:

R4_1A_CODE_COMPLETE_SMOKE_PASS_WAITING_FOR_DB_SNAPSHOT

This label does not mean strategy validation, system intake, candidate status, or full-data
research completion.

==================================================
PART 0 — FREEZE R4.1 AND BUILD A SOURCE-COMPLETENESS BOARD
==================================================

Read line-by-line:

scripts/run_c2_remediation_r4_1_pipeline.py
tests/test_c2r4_1_behavioral.py
reports/ds_a_share/remediation_r4_1/
reports/runops/ds_a_share_c2r4_1_20260713/

Produce:

reports/ds_a_share/remediation_r4_1a/r4_1a_r4_1_source_freeze_20260713.md
reports/ds_a_share/remediation_r4_1a/r4_1a_source_completeness_board_20260713.csv

The board must include at least:

- source file ends during H5;
- H6/H7/H8/H11/H12 absent;
- hypothesis configuration absent;
- simulation execution absent;
- allocators absent;
- GMM/BIC absent;
- model/scaler hashes absent;
- daily OOS probability artifact absent;
- selection ledger absent;
- packet generation absent;
- exit gates absent;
- callback generation absent;
- test imports missing sig_H8;
- module import triggers full database loading;
- no `main()` guard;
- H1 one-line control-flow defect;
- removed targets not liquidated;
- inactive regimes do not liquidate/fallback;
- buy/sell ordering not deterministic;
- execution tradability incomplete;
- bucket percentage applied twice;
- behavioral tests weak or vacuous;
- no pytest/JUnit transcript;
- no bounded end-to-end smoke result.

Each row must end as:

FIXED_AND_TESTED
WAITING_FOR_DB_CALLBACK
ACCEPTED_NEGATIVE_EVIDENCE
BLOCKED_WITH_REASON

The board status must be derived after tests, not assigned in advance.

==================================================
PART 1 — REFACTOR INTO IMPORT-SAFE MODULES
==================================================

Do not keep all implementation and data loading in one top-level script.

Create an import-safe package structure, for example:

src/ds_a_share_r4_1a/
    __init__.py
    types.py
    event_loop.py
    tradability.py
    accounting.py
    signals.py
    regime.py
    detector.py
    allocators.py
    selection.py
    packets.py
    gates.py
    evidence.py

The exact package name may follow the repository convention, but requirements are:

- importing modules must not connect to DuckDB;
- importing modules must not load Parquet files;
- importing modules must not execute simulations;
- reusable classes/functions must be independently unit-testable;
- all file-system and data-source paths must enter through explicit configuration;
- the full pipeline must run only through `main()` or an equivalent CLI entrypoint.

Create:

scripts/run_c2_remediation_r4_1a_pipeline.py

with:

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

Required CLI modes:

--mode unit-fixture
--mode smoke
--mode full
--config <path>
--output-root <path>
--snapshot-contract <path>

`--mode full` must refuse to run when the immutable A-share DB callback is absent unless the
user separately authorizes a forensic run. The default must not silently use an unverified
snapshot.

==================================================
PART 2 — COMPLETE AND CORRECT THE TRUE EVENT-LOOP ENGINE
==================================================

Implement a genuine chronological event loop.

Required daily order:

1. Load only date-D market/tradability rows.
2. Process pending orders whose scheduled execution date is D.
3. Sort executions deterministically: eligible sells first, then eligible buys.
4. Validate execution-date price and tradability.
5. Bound sell shares before calculating notional and costs.
6. Execute incremental trades.
7. Reconcile cash and holdings.
8. Mark D portfolio at D close.
9. Form D-close signals.
10. Build D target portfolio.
11. Queue incremental orders for next valid trading session D+1.
12. Record daily account and queue state.

Required fixes:

- fix the H1 one-line control-flow defect;
- create sell orders for every held symbol removed from the target set;
- when the active regime becomes inactive, follow the preregistered liquidation/fallback rule;
- when the target set is empty, explicitly liquidate or hold according to the frozen rule;
- retained holdings must resize toward target shares;
- sell orders must execute before buys on the same date;
- current holdings must cap sell quantity;
- no negative holdings;
- no unexplained negative cash;
- no D+1 fields may enter D state;
- no future close may be used to decide open execution.

Required state artifacts in smoke/full runs:

orders.parquet
fills.parquet
rejects.parquet
pending_orders_daily.parquet
holdings_daily.parquet
cash_daily.parquet
equity_daily.parquet
trade_reconciliation.parquet
execution_manifest.json

==================================================
PART 3 — EXECUTION-DATE TRADABILITY CONTRACT
==================================================

Separate the tradability contract from the engine.

Required interface:

```text
check_buy(symbol, execution_date, market_row, status_row)
check_sell(symbol, execution_date, market_row, status_row)
```

Required checks where data exists:

- row exists;
- open is finite and > 0;
- dated ST status;
- dated suspension status;
- listing date and minimum listing age;
- delist/inactive status;
- buy-side locked limit-up;
- sell-side locked limit-down;
- board-specific execution rules where required.

Do not infer open tradability from the execution day's close.

Do not calculate `is_limit_up` or `is_limit_down` from D close to decide D open execution.
Use only fields available at the execution decision time under the published database contract.

If a required dated field is unavailable before the DB callback, return an explicit blocker:

WAITING_FOR_DATED_ST_HISTORY
WAITING_FOR_SUSPENSION_HISTORY
WAITING_FOR_EXECUTION_LIMIT_STATUS
WAITING_FOR_LISTING_DELIST_HISTORY

The smoke fixture must include synthetic dated tradability rows so the contract is fully tested
without waiting for the central database.

==================================================
PART 4 — EXACT ACCOUNTING AND RECONCILIATION
==================================================

Implement exact row-level accounting.

For every trade date preserve:

pre_trade_cash
pre_trade_holdings_value
sell_notional
buy_notional
buy_commission
sell_commission
stamp_duty
slippage_cost
post_trade_cash
post_trade_holdings_value
post_trade_total_value
reconciliation_error

Identity:

pre_trade_cash
+ pre_trade_holdings_value
- buy_commission
- sell_commission
- stamp_duty
- slippage_cost
= post_trade_cash + post_trade_holdings_value

within a declared numeric tolerance after accounting for price convention and trade notional.

Requirements:

- charge commission on buys and sells;
- charge stamp duty on sells only;
- use slippage exactly once;
- no `per_stock * 1.1` allowance;
- deterministic lot-size rounding;
- explicit residual cash;
- zero trade means zero cost;
- failed/rejected orders do not change cash or holdings;
- target-weight rebalancing uses incremental net shares;
- same-day sell proceeds may fund buys only after sells execute.

Required smoke acceptance:

maximum absolute reconciliation error <= declared tolerance
minimum cash >= -declared tolerance
minimum holdings quantity >= 0

==================================================
PART 5 — COMPLETE ALL FROZEN HYPOTHESES
==================================================

Define and test:

H1
H2
H3
H4
H5
H6
H7
H8
H11
H12

Keep H9 and H10 blocked until direct evidence arrives.

Requirements:

- exact formula per preregistration;
- exact universe;
- exact bucket rule;
- exact target/inactive regimes;
- exact holding/rebalance period;
- exact guard;
- exact fallback behavior;
- exact cost/execution contract.

Correct bucket behavior:

- apply the preregistered bucket percentage once;
- either signal functions return scores for the full eligible universe and the portfolio builder
  applies the bucket, or signal functions return the frozen selected set and the engine does not
  apply another percentage;
- do not double-apply 20%.

H3 must be behaviorally tested with:

- breadth below threshold -> no signals;
- breadth above threshold -> expected signals.

H8 must be tested with:

- volume shock below threshold -> no signals;
- above threshold -> expected eligible signals.

The fidelity matrix must be generated from actual test results and source references.

==================================================
PART 6 — IMPLEMENT REAL SHARED-CAPITAL ALLOCATORS
==================================================

Implement and commit the following:

A. BEST_SINGLE_CONTINUOUS
B. STATIC_EQUAL_WEIGHT_SLEEVES
C. STATIC_PREREGISTERED_FIXED_WEIGHT_SLEEVES
D. SOFT_PROBABILITY_WEIGHTED_ALLOCATOR
E. HARD_CONFIRMED_STATE_ALLOCATOR
F. LOW_CONFIDENCE_FALLBACK

Common requirements:

- one shared capital account;
- daily sleeve returns or sleeve holdings aligned by date;
- target weights and realized weights;
- incremental sleeve-level trades;
- actual turnover and costs;
- no arithmetic averaging of complete equity arrays as a substitute for allocation;
- no synthetic switch rows;
- no summary table stored under a daily-equity filename.

Soft allocator:

- consumes daily out-of-sample regime probabilities;
- maps probabilities to sleeve target weights;
- applies confidence floor;
- applies sleeve floor/ceiling;
- applies maximum weight change;
- normalizes to the risk budget;
- records target and realized weights daily.

Hard allocator:

- consumes daily confirmed deterministic state;
- uses a preregistered state-to-sleeve map;
- respects confirmation, dwell, hysteresis, and confidence;
- logs every actual switch and reason;
- invokes fallback for low confidence or unavailable specialist.

Required smoke artifacts:

allocator_equity_daily.parquet
allocator_target_weights_daily.parquet
allocator_realized_weights_daily.parquet
allocator_trades.parquet
allocator_switch_log.csv
allocator_cost_reconciliation.csv
allocator_smoke_metrics.csv

The smoke fixture must force at least:

- one soft-weight change;
- one valid hard-state switch;
- one blocked hard switch due to dwell/hysteresis;
- one fallback activation;
- one allocator-level trade with nonzero cost.

==================================================
PART 7 — COMPLETE TRAIN-ONLY DETECTOR PIPELINE
==================================================

Implement:

1. train-only feature selection rule;
2. train-only component-count selection using frozen BIC/AIC or another preregistered rule;
3. train-only scaler fit;
4. train-only model fit;
5. train-only cluster-to-state mapping;
6. frozen application to validation/test;
7. daily OOS probabilities and confidence;
8. serialized or canonicalized scaler/model parameters;
9. scaler hash;
10. model hash;
11. component-selection evidence;
12. feature-order hash;
13. random seed;
14. code commit.

The component-count search must not inspect validation/test outcomes.

Required artifacts:

reports/ds_a_share/remediation_r4_1a/r4_1a_component_selection_train_only_20260713.md
reports/ds_a_share/remediation_r4_1a/r4_1a_probabilistic_detector_manifest_20260713.json
reports/ds_a_share/remediation_r4_1a/r4_1a_model_hashes_20260713.json
reports/runops/ds_a_share_c2r4_1a_20260713/regime_probabilities_smoke.parquet
reports/ds_a_share/remediation_r4_1a/r4_1a_detector_smoke_diagnostics_20260713.csv

The smoke fixture must verify probabilities sum to 1 within tolerance.

==================================================
PART 8 — IMPLEMENT AN EXPLICIT SELECTION LEDGER
==================================================

Every selected configuration must be recorded:

selection_item
selection_stage
allowed_splits
actual_input_artifacts
selected_value
selection_code_ref
test_artifact_accessed
status

Cover at least:

- feature set;
- component count;
- detector mapping;
- regime thresholds;
- strategy formulas;
- allocator state map;
- static weights;
- soft constraints;
- hard dwell/hysteresis;
- packet winner;
- final label.

A static date-order assertion is not sufficient.

Create runtime guards so that test artifacts cannot be passed into selection functions.

Required artifact:

reports/ds_a_share/remediation_r4_1a/r4_1a_selection_ledger_20260713.csv

Any test input in a selection path forces:

TEST_RESULT_SELECTION_DETECTED

==================================================
PART 9 — FAILURE-SENSITIVE UNIT TESTS
==================================================

Create import-safe tests that do not load the full database.

Required test modules:

tests/test_c2r4_1a_import_safety.py
tests/test_c2r4_1a_event_loop.py
tests/test_c2r4_1a_tradability.py
tests/test_c2r4_1a_accounting.py
tests/test_c2r4_1a_hypotheses.py
tests/test_c2r4_1a_soft_allocator.py
tests/test_c2r4_1a_hard_allocator.py
tests/test_c2r4_1a_detector.py
tests/test_c2r4_1a_selection.py
tests/test_c2r4_1a_gates_and_packets.py

Mandatory assertions:

- module imports without DB/file access;
- D signal does not alter D holdings/equity;
- D+1 queued fill executes only on D+1;
- removed targets create sells;
- empty/inactive target invokes frozen liquidation/fallback;
- sells execute before buys;
- NaN open creates an explicit reject;
- dated suspension/ST/limit fixture blocks the correct side;
- no negative cash;
- exact account identity within tolerance;
- sell commission is nonzero in a forced-sell fixture;
- zero trade has zero costs;
- bucket selection count is exact;
- H3 low/high breadth behavior differs;
- H8 low/high shock behavior differs;
- soft weights change with probabilities;
- hard switch obeys dwell/hysteresis;
- fallback activates;
- allocator weights sum to budget;
- switch log matches daily weights;
- BIC/component selection uses train only;
- probability rows sum to 1;
- selection functions reject test artifacts;
- gates fail when a required artifact/test fails;
- packet validator rejects wrong commit/snapshot/hash.

No:

- `pass`-only tests;
- source-text inspection as behavioral proof;
- `>= 0` assertions when positive behavior is required;
- conditional assertions that vacuously pass if no event occurs;
- full-data loading at import time.

Run:

```bash
pytest -q tests/test_c2r4_1a_*.py --junitxml=reports/ds_a_share/remediation_r4_1a/r4_1a_pytest_results.xml
```

Preserve:

reports/ds_a_share/remediation_r4_1a/r4_1a_test_transcript_20260713.txt
reports/ds_a_share/remediation_r4_1a/r4_1a_behavioral_test_matrix_20260713.csv

Generate the matrix from JUnit node results, not from a hard-coded list.

==================================================
PART 10 — BOUNDED END-TO-END SMOKE RUN
==================================================

After unit tests pass, run an end-to-end deterministic smoke workload.

The smoke dataset must be small enough to complete quickly but rich enough to include:

- at least 12 symbols;
- at least 120 trading dates;
- at least 3 deterministic regimes;
- at least one regime transition;
- valid/invalid execution opens;
- dated tradability events;
- target additions/removals;
- at least one sell-before-buy funding event;
- at least one rejected order;
- at least one fallback event;
- train/validation/test partitions.

The smoke run must execute:

- event loop;
- all unblocked hypotheses;
- shared-capital allocators;
- detector;
- selection ledger;
- evidence-derived gates;
- blocked packet templates.

Required smoke outputs:

reports/runops/ds_a_share_c2r4_1a_20260713/smoke/
    orders.parquet
    fills.parquet
    rejects.parquet
    holdings_daily.parquet
    cash_daily.parquet
    equity_daily.parquet
    trade_reconciliation.parquet
    regime_probabilities.parquet
    allocator_equity_daily.parquet
    allocator_target_weights_daily.parquet
    allocator_realized_weights_daily.parquet
    allocator_trades.parquet
    execution_manifest.json

Required smoke summary:

reports/ds_a_share/remediation_r4_1a/r4_1a_smoke_validation_summary_20260713.md
reports/ds_a_share/remediation_r4_1a/r4_1a_smoke_quality_gates_20260713.json

Smoke acceptance requires:

- unit tests pass;
- pipeline completes;
- all required files parse;
- no negative cash;
- reconciliation tolerance passes;
- probabilities sum to 1;
- expected switch/fallback/reject events occur;
- no test-result selection;
- all smoke artifact hashes are recorded.

==================================================
PART 11 — PACKET TEMPLATES AND EVIDENCE-DERIVED GATES
==================================================

Because the central DB callback and full simulation are pending, create schema-complete blocked
packet templates, not positive strategy packets.

Required packet status:

WAITING_FOR_A_SHARE_DB_SNAPSHOT_AND_FULL_REPLAY
SYSTEM_INTAKE_READY=false
PIT_status=PENDING
strategy_candidate_available=false

Packet templates must contain:

- implementation commit;
- code paths;
- exact formula/universe/bucket contract;
- event-loop and cost model;
- smoke evidence URLs/hashes;
- DB callback status;
- central snapshot placeholder;
- known blockers;
- full-run command;
- packet-finalization plan.

Required files:

reports/ds_a_share/remediation_r4_1a/a_share_strategy_packet_static_blocked_20260713.json
reports/ds_a_share/remediation_r4_1a/a_share_strategy_packet_regime_blocked_20260713.json
reports/ds_a_share/remediation_r4_1a/r4_1a_packet_schema_validation_20260713.json

Exit gates must be evidence-derived and include:

SOURCE_COMPLETE
IMPORT_SAFE
UNIT_TESTS_PASS
SMOKE_PIPELINE_PASS
EVENT_LOOP_VALID
TRADABILITY_FIXTURE_VALID
ACCOUNTING_VALID
HYPOTHESIS_FIDELITY_VALID
STATIC_ALLOCATOR_SMOKE_VALID
SOFT_ALLOCATOR_SMOKE_VALID
HARD_ALLOCATOR_SMOKE_VALID
FALLBACK_SMOKE_VALID
GMM_TRAIN_ONLY_SMOKE_VALID
NO_TEST_SELECTION_VALID
PACKET_TEMPLATES_VALID
DB_CALLBACK_AVAILABLE
FULL_REPLAY_COMPLETE
FAMILY_COUNT_GE_4
DRAWDOWN_SANITY

Expected R4.1a state:

- method/smoke gates: may pass;
- DB_CALLBACK_AVAILABLE: false;
- FULL_REPLAY_COMPLETE: false;
- SYSTEM_INTAKE_READY: false.

Required artifact:

reports/ds_a_share/remediation_r4_1a/r4_1a_exit_gate_results_20260713.json

==================================================
PART 12 — FULL RUN DEFERRED UNTIL DB CALLBACK
==================================================

Do not run the 8.7M-row full workload in R4.1a unless the user provides the immutable
A_SHARE_DB_CALLBACK and explicitly asks to continue.

Without the callback, the final status must be:

R4_1A_CODE_COMPLETE_SMOKE_PASS_WAITING_FOR_DB_SNAPSHOT

When the callback arrives later:

1. freeze contract URL, commit, snapshot id, and export hashes;
2. validate the DB callback;
3. run the full pipeline against that exact snapshot;
4. rerun H1/H2/H3/H11;
5. decide whether H9 can be preregistered;
6. generate full-run evidence;
7. perform packet-finalization commit;
8. request external audit.

==================================================
MANDATORY GITHUB COMMIT, PUSH, AND REMOTE VERIFICATION
==================================================

R4.1a completion requires at least two commits.

STEP 1 — CODE COMPLETION COMMIT

Commit:

- import-safe source modules;
- CLI pipeline;
- tests;
- fixture builders;
- smoke runner.

Push and capture:

CODE_COMPLETION_COMMIT_SHA

STEP 2 — SMOKE EVIDENCE COMMIT

After unit tests and smoke pass, commit:

- JUnit XML;
- test transcript;
- smoke artifacts/manifests;
- selection ledger;
- detector manifests/hashes;
- packet templates;
- exit gates;
- callback.

Push and capture:

SMOKE_EVIDENCE_COMMIT_SHA

Required Git flow:

```bash
git status --short --branch
git branch --show-current
git diff --check

git add <R4.1a code and tests>
git diff --cached --check
git commit -m "A-share C2 R4.1a: complete import-safe engine, allocators, detector, and tests"
git push -u origin "$(git branch --show-current)"
CODE_COMPLETION_COMMIT_SHA="$(git rev-parse HEAD)"

# Run tests and smoke, then stage evidence
git add <R4.1a smoke evidence, manifests, blocked packets, callback>
git diff --cached --check
git commit -m "A-share C2 R4.1a: publish smoke validation and evidence-derived gates"
git push
SMOKE_EVIDENCE_COMMIT_SHA="$(git rev-parse HEAD)"

git ls-remote origin "refs/heads/$(git branch --show-current)"
git status --short --branch
```

Remote branch SHA must equal SMOKE_EVIDENCE_COMMIT_SHA.

Do not commit:

- central database files;
- database backups;
- secrets or credentials;
- `.env`;
- tokens;
- private connection strings;
- unbounded raw data;
- virtual environments.

If remote verification fails, return REMOTE_PUSH_FAILED.

==================================================
BOUNDARY
==================================================

Research-only.

No recommendation, ticket, strategy candidate, readiness/product route, daily signal,
broker/order/paper/live/auto activation, secret output, or central-database write.

SYSTEM_INTAKE_READY must remain false.
STRATEGY_CANDIDATE_AVAILABLE must remain false.

==================================================
CALLBACK
==================================================

CALLBACK_ENVELOPE:
BATCH: DS_A_SHARE_C2_REMEDIATION_R4_1A_CODE_COMPLETION_AND_SMOKE_20260713
WORKSTREAM: DS_A_SHARE_RESEARCH_USER_CONTROLLED
REPOSITORY_URL:
BRANCH:
CODE_COMPLETION_COMMIT_SHA:
SMOKE_EVIDENCE_COMMIT_SHA:
TREE_SHA:
IMMUTABLE_CODE_COMMIT_URL:
IMMUTABLE_SMOKE_COMMIT_URL:
REMOTE_BRANCH_URL:
REMOTE_VERIFICATION_OUTPUT:
WORKTREE_STATUS:
PUSH_STATUS:
STATUS:
SOURCE_COMPLETENESS_STATUS:
IMPORT_SAFETY_STATUS:
UNIT_TEST_RESULT:
UNIT_TEST_COUNT:
SMOKE_PIPELINE_STATUS:
EVENT_LOOP_STATUS:
EXECUTION_TRADABILITY_STATUS:
ACCOUNT_RECONCILIATION_STATUS:
HYPOTHESIS_FIDELITY_STATUS:
STATIC_ALLOCATOR_STATUS:
SOFT_ALLOCATOR_STATUS:
HARD_ALLOCATOR_STATUS:
FALLBACK_STATUS:
GMM_TRAIN_ONLY_STATUS:
GMM_MODEL_HASHES:
SELECTION_LEDGER_STATUS:
PACKET_TEMPLATE_COUNT:
PACKET_SCHEMA_STATUS:
A_SHARE_DB_CALLBACK_STATUS: WAITING
CENTRAL_SNAPSHOT_ID: PENDING
FULL_REPLAY_STATUS: NOT_RUN
FAMILY_COUNT_GATE: PENDING_DB_REPLAY
DRAWDOWN_SANITY_GATE: PENDING_FULL_REPLAY
FINAL_METHOD_LABEL:
SYSTEM_INTAKE_READY: false
STRATEGY_CANDIDATE_AVAILABLE: false
ARTIFACT_GITHUB_URLS:
VALIDATION:
BOUNDARY_RESULT:
FIXES_REQUIRED:
NEXT_ACTION:
```
