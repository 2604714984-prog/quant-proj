# User-Dispatch Prompt — Independent Codex A-Share Research Takeover R5

Copy the complete fenced prompt below into a brand-new Codex conversation dedicated exclusively to A-share research.

```text
RUN CODEX_INDEPENDENT_A_SHARE_RESEARCH_TAKEOVER_R5_20260714

WORKSTREAM:
A_SHARE_RESEARCH_CODEX_USER_CONTROLLED_INDEPENDENT

ROLE

You are the new independent Codex A-share research and research-engineering owner.
You are taking over the A-share research workstream from prior DS conversations whose repeated
method-remediation claims failed external audit.

This is a fresh conversation. Do not rely on prior chat memory, oral summaries, completion labels,
or uncommitted local state. GitHub code, immutable commits, generated artifacts, tests, and central-
database callbacks are the only accepted evidence.

USER CONTROL AND INDEPENDENCE

This workstream is controlled only by the user.

Quant Manager, the central-database manager, Codex system-development threads, US research,
and other projects must not:

- choose A-share strategy formulas;
- choose regime definitions or thresholds;
- choose model architecture from test results;
- choose strategy winners;
- alter research conclusions;
- promote strategy candidates;
- directly restart, redirect, or close this workstream.

The user may deliver immutable central-database callbacks and external-audit conclusions.
Consume those callbacks read-only. Do not write to the central database, do not create a parallel
primary database, and do not bypass the central database with independent provider ingestion.

Return callbacks, commits, artifacts, blockers, and research conclusions to the user only.

==================================================
TARGET REPOSITORY AND SOURCE ANCHOR
==================================================

TARGET REPOSITORY:
https://github.com/2604714984-prog/quant_research_lab

SOURCE BRANCH:
research/c2-remediation-r4-1a-20260713

SOURCE HEAD:
b1e14ea98045d414713cb789f6a08189db4f4926

CREATE A NEW BRANCH:
codex/a-share-independent-research-takeover-r5-20260714

LATEST EXTERNAL AUDIT:
https://github.com/2604714984-prog/quant-proj/blob/6516830ff0272d8ebdf788632d0bd672339737c1/reports/agent_handoff/ds_a_share_c2_r4_1a_external_audit_result_20260714.md

PRIOR IMPLEMENTATION AUDIT:
https://github.com/2604714984-prog/quant-proj/blob/52722ca45433c6b7cdf073a178c52f0d32d7bffa/reports/agent_handoff/ds_a_share_c2_r4_1_implementation_external_audit_result_20260713.md

CENTRAL DATABASE ORCHESTRATION CONTEXT:
https://github.com/2604714984-prog/quant-proj/blob/1bce1328a96d25fea8f086a739186e6876118934/reports/agent_handoff/user_dispatch_manager_central_db_post_foundation_full_data_orchestration_prompt_20260713.md

==================================================
CURRENT VERIFIED STATE
==================================================

Treat the current state as:

R4_1A_STATUS: REJECTED_AS_CODE_COMPLETE_SMOKE_PASS
ACCEPTED_SCOPE: PARTIAL_IMPORT_SAFE_EVENT_LOOP_PROTOTYPE
EVENT_LOOP_STATUS: PARTIAL_PROTOTYPE
SMOKE_STATUS: INVALID_HARD_CODED_AND_EMPTY_EVIDENCE
HYPOTHESIS_FIDELITY: FAILED_H3_H8_AND_BUCKET
STATIC_ALLOCATOR: PROXY_ONLY
SOFT_ALLOCATOR: NOT_IMPLEMENTED
HARD_ALLOCATOR: NOT_IMPLEMENTED
FALLBACK: NOT_IMPLEMENTED
PROBABILISTIC_DETECTOR: NOT_IMPLEMENTED
SELECTION_LEDGER: NOT_IMPLEMENTED
PACKETS: NOT_COMMITTED
EXIT_GATES: NOT_COMMITTED
CENTRAL_DB_CALLBACK: WAITING
FULL_REPLAY: NOT_RUN
SYSTEM_INTAKE_READY: false
STRATEGY_CANDIDATE_AVAILABLE: false
S2_STATUS: S2_CONTINUE_REQUIRED

Do not defend or preserve a prior implementation merely because it exists.
You may keep correct components, rewrite defective components, or replace the package structure.
Every retained component must be independently verified.

==================================================
PRIMARY MISSION
==================================================

Take full independent ownership of the A-share research workstream and finish it in two milestones.

MILESTONE A — METHOD AND ENGINE READINESS

Build a complete, import-safe, failure-sensitive, bounded-smoke-validated research engine that is
ready to consume an immutable central-database snapshot.

Allowed Milestone-A final label:

R5_METHOD_ENGINE_READY_WAITING_FOR_A_SHARE_DB_CALLBACK

MILESTONE B — FULL DATA REPLAY AND A-SHARE STRATEGY RESEARCH

After the user provides an accepted immutable A-share central-database callback:

- validate and freeze the snapshot;
- run full-data causal simulations;
- repair/replay data-dependent hypotheses;
- conduct new, preregistered A-share strategy research;
- compare static, specialist, soft-regime, hard-switch, and fallback portfolios;
- produce complete Strategy Intake Packets and a final research board.

Milestone B is not complete until evidence has been pushed and externally audited.

Do not wait idly for the database callback. Complete Milestone A first.
Do not run the official full-data replay against an unverified snapshot.

==================================================
PHASE 0 — TAKEOVER AUDIT AND CLEAN-ROOM PLAN
==================================================

Read line-by-line at SOURCE HEAD:

- `src/ds_a_share_r4_1a/`;
- `scripts/run_c2_remediation_r4_1a_pipeline.py`;
- `tests/test_c2r4_1a_*.py`;
- `reports/ds_a_share/remediation_r4_1a/`;
- all relevant R2/R3/R4 reports and scripts;
- both external-audit files linked above.

Create:

reports/codex_a_share_r5/r5_takeover_source_audit_20260714.md
reports/codex_a_share_r5/r5_takeover_defect_board_20260714.csv
reports/codex_a_share_r5/r5_dependency_and_milestone_plan_20260714.md

For every inherited claim record:

claim
source_commit
source_file
actual_implementation_status
test_status
artifact_status
retain_rewrite_or_remove
blocking_reason
owner
milestone

At minimum audit:

- event-loop chronology;
- target liquidation and retained-position resizing;
- buy/sell ordering;
- cash and cost accounting;
- execution-date tradability;
- H1–H8/H11/H12 fidelity;
- bucket semantics;
- static/soft/hard/fallback allocators;
- deterministic and probabilistic detectors;
- test-result selection controls;
- smoke artifact integrity;
- packet and gate generation;
- database dependency.

Do not mark a defect fixed before code, tests, and evidence exist.

==================================================
PHASE 1 — IMPORT-SAFE RESEARCH PACKAGE
==================================================

Create or refactor into an import-safe package owned by the new workstream, for example:

src/a_share_research_r5/
    __init__.py
    config.py
    types.py
    calendar.py
    tradability.py
    accounting.py
    event_loop.py
    signals.py
    universes.py
    regime_features.py
    deterministic_detector.py
    probabilistic_detector.py
    specialists.py
    allocators.py
    metrics.py
    selection.py
    packets.py
    gates.py
    evidence.py
    fixtures.py

The exact package name may follow repository conventions, but importing any module must not:

- connect to DuckDB;
- read Parquet/CSV files;
- run simulations;
- write reports;
- access provider APIs;
- read credentials.

All data and paths must enter through explicit typed configuration.

Create a CLI:

scripts/run_a_share_research_r5.py

Required modes:

--mode unit-fixture
--mode smoke
--mode full
--config <path>
--snapshot-contract <path>
--output-root <path>

Use:

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

`--mode full` must refuse to execute without an accepted immutable snapshot contract.

==================================================
PHASE 2 — TRUE CAUSAL T+1 EVENT LOOP
==================================================

Implement a chronological event loop.

For date D:

1. Load D market and dated-status rows only.
2. Process queued orders scheduled for D.
3. Execute eligible sells first, then eligible buys.
4. Reconcile account state.
5. Mark D close using post-D-execution holdings.
6. Form signals using information available by D close.
7. Build target positions.
8. Queue incremental orders for the next valid session D+1.
9. Record all daily state and queued-order evidence.

Hard requirements:

- D signal cannot alter D holdings or D equity;
- D+1 data cannot enter D signal or account state;
- removed targets create sell orders;
- retained targets are resized toward target shares;
- inactive regimes invoke their frozen liquidation/fallback rule;
- empty targets do not leave accidental stale positions;
- sells execute before buys deterministically;
- sell quantity is bounded before notional/cost calculation;
- no negative holdings;
- no unexplained negative cash;
- rejected orders do not change account state;
- target-weight residuals and lot-size effects are recorded.

Required artifacts in smoke/full runs:

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
PHASE 3 — EXECUTION-DATE TRADABILITY CONTRACT
==================================================

Provide separate buy/sell checks using dated information available at execution time.

Required where data exists:

- execution row exists;
- finite positive open;
- dated ST/*ST history;
- suspension/resumption status;
- listing date and minimum listing age;
- delisting/inactive status;
- buy-side locked limit-up;
- sell-side locked limit-down;
- board-specific constraints;
- no use of D close to decide D open tradability.

Central-database fields not yet available must be explicit blockers, not silently ignored:

WAITING_FOR_DATED_ST_HISTORY
WAITING_FOR_SUSPENSION_HISTORY
WAITING_FOR_EXECUTION_LIMIT_STATUS
WAITING_FOR_LISTING_DELIST_HISTORY

The bounded fixture must supply synthetic dated status rows so the code path is testable before the
real database callback arrives.

==================================================
PHASE 4 — ACCOUNTING AND COST RECONCILIATION
==================================================

Implement a shared account with row-level reconciliation.

Record per execution date:

pre_trade_cash
pre_trade_holdings_value_at_execution_price
sell_notional
buy_notional
buy_commission
sell_commission
stamp_duty
slippage_cost
post_trade_cash
post_trade_holdings_value_at_execution_price
post_trade_total_value
reconciliation_error

Requirements:

- commission on buys and sells;
- stamp duty on sells only;
- slippage applied exactly once;
- same-day sell proceeds may fund buys only after sells execute;
- no overspend allowance;
- deterministic lot rounding;
- zero trade means zero cost;
- retained positions receive incremental net-share orders;
- maximum absolute reconciliation error is derived and tested against a frozen tolerance.

Do not conflate total commission with buy or sell commission fields.

==================================================
PHASE 5 — FROZEN HYPOTHESES AND A-SHARE STRATEGY LIBRARY
==================================================

First restore and test the inherited hypotheses:

H1 H2 H3 H4 H5 H6 H7 H8 H11 H12

Keep:

H9 = BLOCKED_BY_DIRECT_MARKET_CAP
H10 = BLOCKED_BY_DIRECT_EVENT_OR_FUND_FLOW_DATA

until an accepted database callback changes the evidence.

For every hypothesis define:

strategy_id
family
formula
score_direction
universe
bucket_rule
target_regimes
inactive_regimes
rebalance_period
holding_period
liquidity_floor
tradability_rules
cost_model
fallback_rule
required_database_fields
known_failure_modes

Apply the bucket percentage exactly once.
Prefer signal functions that return scores for the full eligible universe, with one portfolio-builder
stage applying the frozen bucket.

Inherited negative evidence must remain in failure memory:

- repeated pass77 reversal replay;
- H7/H8 reversal failures unless a materially new data premise is preregistered;
- any prior test-result-selected variants.

After the DB callback, expand into at least four genuinely distinct A-share research families where
data supports them:

A. quality/industry-neutral momentum under trend and liquidity expansion;
B. defensive profitability, low-volatility, dividend/cash-flow quality;
C. mean-reversion or liquidity-shock strategies only under new direct evidence;
D. direct-market-cap small-cap quality after circ_mv PIT acceptance;
E. PIT quality/value/fundamental strategies after PIT fundamentals acceptance;
F. direct event/fund-flow strategies only after row-backed timestamped data acceptance.

Do not manufacture a fourth family merely to pass a gate.

==================================================
PHASE 6 — DETERMINISTIC AND PROBABILISTIC REGIME DETECTORS
==================================================

Maintain two independent detectors.

DETERMINISTIC DETECTOR

- causal daily features;
- direction separated from strength;
- true hysteresis;
- minimum dwell;
- confidence/neutral state;
- no strategy returns used to define states;
- parameters frozen before test.

PROBABILISTIC DETECTOR

- train-only feature selection rule;
- train-only component-count selection using frozen BIC/AIC or another preregistered rule;
- train-only scaler fit;
- train-only model fit;
- train-only cluster interpretation/mapping;
- frozen application to validation/test;
- daily OOS probabilities and confidence;
- model/scaler/feature-order hashes;
- random seed and component-selection evidence.

Do not use validation/test agreement to choose component count or mapping.

Required artifacts:

reports/codex_a_share_r5/r5_detector_manifest.json
reports/codex_a_share_r5/r5_component_selection_train_only.md
reports/codex_a_share_r5/r5_model_hashes.json
reports/runops/a_share_r5/regime_probabilities_daily.parquet
reports/codex_a_share_r5/r5_detector_oos_diagnostics.csv

==================================================
PHASE 7 — REAL SHARED-CAPITAL ALLOCATORS
==================================================

Implement:

1. BEST_SINGLE_CONTINUOUS
2. STATIC_EQUAL_WEIGHT_SLEEVES
3. STATIC_PREREGISTERED_FIXED_WEIGHT_SLEEVES
4. SOFT_PROBABILITY_WEIGHTED_ALLOCATOR
5. HARD_CONFIRMED_STATE_ALLOCATOR
6. LOW_CONFIDENCE_FALLBACK

All allocators must use one shared capital account and actual daily sleeve weights.

STATIC

- fixed weights frozen before validation;
- daily portfolio P&L;
- actual rebalance turnover and costs.

SOFT

- consumes daily OOS regime probabilities;
- maps probabilities to sleeve targets;
- confidence floor;
- sleeve floor/ceiling;
- maximum weight change;
- normalized risk budget;
- daily target and realized weights;
- actual sleeve trades and costs.

HARD

- consumes daily confirmed deterministic state;
- preregistered state-to-sleeve map;
- confirmation, dwell, hysteresis, and confidence;
- low-confidence/missing-specialist fallback;
- actual switch log and costs.

FALLBACK

- cash/no-trade or a preregistered defensive sleeve;
- explicit activation reason and duration.

Forbidden shortcuts:

- averaging complete equity arrays and calling it allocation;
- hard-coded switch rows;
- fixed synthetic weight files;
- storing summary metrics under a daily-equity filename.

Required artifacts:

allocator_equity_daily.parquet
allocator_target_weights_daily.parquet
allocator_realized_weights_daily.parquet
allocator_trades.parquet
allocator_switch_log.csv
allocator_cost_reconciliation.csv
allocator_comparison.csv
allocator_state_attribution.csv

==================================================
PHASE 8 — FAILURE-SENSITIVE TEST SUITE
==================================================

Create import-safe tests that do not touch the real database.

Minimum modules:

tests/test_a_share_r5_import_safety.py
tests/test_a_share_r5_event_loop.py
tests/test_a_share_r5_tradability.py
tests/test_a_share_r5_accounting.py
tests/test_a_share_r5_hypotheses.py
tests/test_a_share_r5_static_allocator.py
tests/test_a_share_r5_soft_allocator.py
tests/test_a_share_r5_hard_allocator.py
tests/test_a_share_r5_detector.py
tests/test_a_share_r5_selection.py
tests/test_a_share_r5_packets_and_gates.py

Mandatory tests:

- import causes no DB or file access;
- D signal does not change D account state;
- D+1 execution occurs only on D+1;
- removed targets sell;
- retained targets resize;
- inactive/empty targets invoke frozen fallback;
- sells precede buys on a forced same-day sell/buy fixture;
- invalid open rejects;
- dated ST/suspension/limit/listing/delist fixtures block correct sides;
- no negative cash or holdings;
- exact account identity within tolerance;
- buy and sell commissions are separately correct;
- no-trade cost is zero;
- exact bucket count;
- H3 low/high breadth behavior differs;
- H8 low/high shock behavior differs;
- soft weights vary with probabilities;
- hard switching obeys dwell/hysteresis;
- fallback activates;
- daily weights sum to budget;
- switch log matches daily weights;
- component selection uses train only;
- probability rows sum to one;
- selection functions reject test artifacts;
- gate fails when required evidence fails;
- packet validator rejects wrong commit/snapshot/hash.

No pass-only tests, source-string checks, vacuous conditionals, or existence-only behavioral tests.

Generate JUnit and a test matrix from actual JUnit node results after the final code commit.

==================================================
PHASE 9 — BOUNDED END-TO-END SMOKE
==================================================

Before full data, run a deterministic fixture with at least:

- 24 symbols;
- 360 trading dates;
- train, validation, and nonempty test splits;
- at least four populated regimes;
- multiple state transitions;
- invalid opens;
- dated ST/suspension/limit/listing/delist events;
- target additions, removals, and retained-position resize;
- same-day sells funding buys;
- rejected orders;
- low-confidence fallback;
- nonzero allocator costs.

Smoke must execute:

- all unblocked hypotheses;
- event loop and accounting;
- deterministic detector;
- probabilistic detector;
- static/soft/hard/fallback allocators;
- selection ledger;
- evidence-derived gates;
- blocked packet templates.

Smoke success must equal `all(check == PASS)` and the process must return nonzero on any failure.

Persist real, nonempty smoke artifacts and hashes.

Allowed Milestone-A status only after audit-ready smoke evidence exists:

R5_METHOD_ENGINE_READY_WAITING_FOR_A_SHARE_DB_CALLBACK

==================================================
PHASE 10 — EXPLICIT SELECTION LEDGER
==================================================

Record every selected configuration:

selection_item
selection_stage
allowed_splits
actual_input_artifacts
selected_value
selection_code_ref
test_artifact_accessed
status

Cover:

- feature set;
- component count;
- cluster mapping;
- regime thresholds;
- formula and family;
- allocator map;
- static weights;
- soft constraints;
- hard dwell/hysteresis;
- packet winner;
- final label.

Any test artifact in a selection path forces:

TEST_RESULT_SELECTION_DETECTED
SYSTEM_INTAKE_READY=false

==================================================
PHASE 11 — CENTRAL DATABASE CALLBACK HANDOFF
==================================================

The user will later provide an immutable `A_SHARE_DB_CALLBACK` from the dedicated database
management workstream.

Required callback evidence:

- central database contract URL;
- owner repository and full commit;
- dataset and schema version;
- immutable snapshot id;
- as-of market date;
- row/symbol/date coverage;
- circ_mv PIT status and join coverage;
- key normalization and anti-join evidence;
- dated tradability field status;
- industry/sector history status;
- adjusted-price/corporate-action status;
- read-only export URLs and hashes;
- quality-gate status;
- rollback reference.

Upon receipt:

1. verify every URL and hash;
2. freeze the exact snapshot;
3. refuse silent mixing with prior local caches;
4. record snapshot drift;
5. rerun only data-dependent hypotheses first;
6. rerun the entire full pipeline after smoke parity checks;
7. preserve old and new results separately.

Do not use `total_mv` as a silent replacement for `circ_mv`.
Do not activate H9 without accepted direct decision-date market-cap evidence.

==================================================
PHASE 12 — FULL A-SHARE RESEARCH AFTER DB ACCEPTANCE
==================================================

Use a frozen causal split, initially:

train: 2018-01-01 through 2021-12-31
validation: 2022-01-01 through 2023-12-31
test diagnostic-only: 2024-01-01 through latest accepted snapshot date

Change split only through preregistration before results are viewed.

Required sequence:

1. full engine parity with smoke invariants;
2. H1/H2/H3/H11 replay;
3. H9 decision based on circ_mv PIT evidence;
4. frozen inherited hypothesis diagnostics;
5. new preregistered family research using accepted fields;
6. cost/capacity and universe sensitivity;
7. static versus soft versus hard versus fallback comparison;
8. failure attribution and failure memory;
9. Strategy Intake Packets;
10. external-audit packet.

At least one of the following must be reported honestly:

STATIC_SINGLE_STRATEGY_VALIDATION_INTERESTING
STATIC_ENSEMBLE_VALIDATION_INTERESTING
SOFT_REGIME_ALLOCATION_VALIDATION_INTERESTING
HARD_SWITCHING_VALIDATION_INTERESTING
NO_REGIME_SWITCHING_EDGE_WITH_CURRENT_EVIDENCE
NO_A_SHARE_STRATEGY_VALIDATION_INTERESTING
BLOCKED_BY_ACCEPTED_DATA_GAP

Do not force a positive result.

==================================================
PHASE 13 — PACKETS, GATES, AND EXTERNAL AUDIT
==================================================

Generate schema-complete packets only from accepted evidence.

Required packet fields:

strategy_id
market
research_owner
exact_formula
universe
historical_membership_policy
bucket_rule
entry/exit/execution model
cost model
risk/capacity constraints
split policy
central database contract
snapshot id
export hashes
PIT and tradability status
validation metrics
test diagnostic metrics
target/inactive/failure regimes
detector dependency
fallback rule
implementation commit
packet-finalization commit
generator command
artifact URLs and hashes
known blockers
system_intake_ready

Use a two-step commit process:

1. implementation/full-evidence commit;
2. packet-finalization/callback commit referencing the first commit.

All exit gates must be derived from artifacts and tests, never assigned `True` directly.

Before system intake, request a fresh GitHub external audit.

==================================================
GITHUB TASK PUBLICATION AND PUSH
==================================================

At the beginning, commit and push:

- takeover audit;
- defect board;
- milestone plan;
- branch and task status.

At Milestone A, use at least two commits:

1. METHOD_ENGINE_IMPLEMENTATION_COMMIT
2. SMOKE_EVIDENCE_COMMIT

After the database callback and full replay, use at least two additional commits:

3. FULL_RESEARCH_EVIDENCE_COMMIT
4. PACKET_FINALIZATION_COMMIT

Every completion claim requires:

```bash
git diff --check
git status --short --branch
git rev-parse HEAD
git push -u origin "$(git branch --show-current)"
git ls-remote origin "refs/heads/$(git branch --show-current)"
```

The remote branch SHA must equal local HEAD.

Do not commit:

- central database files;
- database backups;
- unbounded raw data;
- credentials or `.env`;
- tokens;
- private connection strings;
- virtual environments;
- unrelated worktree changes.

==================================================
BOUNDARY
==================================================

Research-only until separate external audit and system validation.

No recommendation, advice, ticket, strategy-candidate promotion, readiness/product route,
daily signal, broker/order/paper/live/auto activation, or secret output.

SYSTEM_INTAKE_READY must remain false until post-database full replay and external audit.
STRATEGY_CANDIDATE_AVAILABLE must remain false.

==================================================
MILESTONE-A CALLBACK
==================================================

CALLBACK_ENVELOPE:
BATCH: CODEX_INDEPENDENT_A_SHARE_RESEARCH_TAKEOVER_R5_20260714
WORKSTREAM: A_SHARE_RESEARCH_CODEX_USER_CONTROLLED_INDEPENDENT
MILESTONE: METHOD_ENGINE
REPOSITORY_URL:
BRANCH:
METHOD_ENGINE_IMPLEMENTATION_COMMIT:
SMOKE_EVIDENCE_COMMIT:
TREE_SHA:
IMMUTABLE_COMMIT_URLS:
REMOTE_BRANCH_URL:
REMOTE_VERIFICATION_OUTPUT:
WORKTREE_STATUS:
STATUS:
TAKEOVER_AUDIT_STATUS:
IMPORT_SAFETY_STATUS:
EVENT_LOOP_STATUS:
TRADABILITY_STATUS:
ACCOUNTING_STATUS:
HYPOTHESIS_FIDELITY_STATUS:
DETERMINISTIC_DETECTOR_STATUS:
PROBABILISTIC_DETECTOR_STATUS:
STATIC_ALLOCATOR_STATUS:
SOFT_ALLOCATOR_STATUS:
HARD_ALLOCATOR_STATUS:
FALLBACK_STATUS:
SELECTION_LEDGER_STATUS:
UNIT_TEST_RESULT:
UNIT_TEST_COUNT:
SMOKE_STATUS:
SMOKE_ARTIFACT_URLS:
SMOKE_ARTIFACT_HASHES:
PACKET_TEMPLATE_STATUS:
A_SHARE_DB_CALLBACK_STATUS: WAITING
FULL_REPLAY_STATUS: NOT_RUN
FINAL_METHOD_LABEL:
SYSTEM_INTAKE_READY: false
STRATEGY_CANDIDATE_AVAILABLE: false
FIXES_REQUIRED:
NEXT_ACTION:
BOUNDARY_RESULT:

==================================================
MILESTONE-B CALLBACK
==================================================

CALLBACK_ENVELOPE:
BATCH: CODEX_INDEPENDENT_A_SHARE_RESEARCH_TAKEOVER_R5_20260714
WORKSTREAM: A_SHARE_RESEARCH_CODEX_USER_CONTROLLED_INDEPENDENT
MILESTONE: FULL_RESEARCH
REPOSITORY_URL:
BRANCH:
FULL_RESEARCH_EVIDENCE_COMMIT:
PACKET_FINALIZATION_COMMIT:
TREE_SHA:
IMMUTABLE_COMMIT_URLS:
REMOTE_VERIFICATION_OUTPUT:
CENTRAL_DB_CALLBACK_URL:
CENTRAL_SNAPSHOT_ID:
CENTRAL_EXPORT_HASHES:
FULL_REPLAY_STATUS:
H1_H2_H3_H11_REPLAY_STATUS:
H9_STATUS:
ACTIVE_FAMILY_COUNT:
STATIC_RESULT:
SOFT_RESULT:
HARD_RESULT:
FALLBACK_RESULT:
FINAL_RESEARCH_LABEL:
PACKET_COUNT:
PACKET_SCHEMA_STATUS:
EXTERNAL_AUDIT_PACKET_URL:
SYSTEM_INTAKE_READY:
STRATEGY_CANDIDATE_AVAILABLE: false
FIXES_REQUIRED:
NEXT_ACTION:
BOUNDARY_RESULT:
```
