# User-Dispatch Prompt — DS US C2 R3 Central-DB Engine and Allocator Fix

Copy the complete fenced prompt below into the independently controlled DS US conversation.

```text
RUN DS_US_C2_REMEDIATION_R3_CENTRAL_DB_ENGINE_ALLOCATOR_FIX_20260713

WORKSTREAM:
DS_US_RESEARCH_USER_CONTROLLED

TARGET REPOSITORY:
https://github.com/2604714984-prog/us_stock_30w

ACCEPTED R2 SOURCE ANCHOR:
branch: research/c2-remediation-r2-20260713
commit: e47d4155d4e2bace2c15ae22e53f66556d19d832

CREATE AND USE A NEW BRANCH:
research/c2-remediation-r3-20260713

EXTERNAL AUDIT SOURCE:
https://github.com/2604714984-prog/quant-proj/blob/3e0fbde8cc592b5d5044aa2ce5734e84b57bed9d/reports/agent_handoff/ds_c2r_r2_callbacks_external_audit_result_20260713.md

CONTROL AND INDEPENDENCE

The user exclusively controls this DS US research project.
Quant Manager, dispatcher, Codex, DS A-share, and other agents must not choose formulas,
assets, regime states, parameters, preferred winners, or conclusions.
Return the final callback, branch, full commit SHA, tree, artifacts, validation, and GitHub
URLs to the user only.
Do not send the callback directly to Quant Manager or Codex.

R2 AUDIT STATUS

The R2 callback was externally rejected for strategy-system intake:

DS_US_C2R_CALLBACK_REJECTED_PARTIAL_REMEDIATION_INCOMPLETE_AND_ENGINE_INVALID
S2_CONTINUE_REQUIRED

Useful R2 work must be preserved as immutable audit anchors:

- a row-backed daily US regime feature Parquet exists;
- the deterministic detector updates daily with past/current-only hysteresis;
- 11 hypotheses across four active families were preregistered;
- FORWARD_HOLDOUT_CONTAMINATED was correctly preserved;
- R2 disclosed adjusted-data, hard-switching, and probabilistic-detector limitations.

Do not rebuild the entire data foundation unless a reproducible defect is found.
This is a narrow R3 engine, formula-fidelity, allocator, data-contract, and evidence cycle.

==================================================
CENTRAL DATABASE SOURCE-OF-TRUTH
==================================================

A central project database already exists and is the authoritative source of truth for US
and ETF prices, adjusted returns, corporate actions, market calendar, cross-asset features,
and supporting research inputs.

The DS project is a READ-ONLY RESEARCH CONSUMER of the central database.

The DS project must not:

- create another primary database;
- create a competing source of truth;
- modify central database tables;
- run schema migrations;
- overwrite central snapshots;
- migrate raw data into the research repository;
- dump or commit the central database;
- expose database credentials or connection strings;
- bypass the central database by independently fetching Sina, yfinance, OpenBB-provider,
  or other external data unless the user gives separate explicit authorization for a narrowly
  defined data-gap investigation.

All ordinary R3 research data must come from one fixed, versioned central-database snapshot
or an approved read-only export from that snapshot.

The central database is authoritative for:

- QQQ / GLD / SPY / TLT / HYG / LQD prices;
- adjusted close and total-return series;
- dividends and split factors;
- corporate actions;
- volume and dollar volume;
- exchange calendar and completed-session dates;
- sector ETF data and breadth inputs;
- rate, credit, and cross-asset context;
- source and retrieval metadata.

Before any strategy or regime run, resolve and freeze:

central_database_name
dataset_name
snapshot_id
schema_version
as_of_market_date
generated_at
query_or_export_command
query_parameters
row_count
symbol_count
date_min
date_max
field_list
field_lineage
point_in_time_status
adjusted_data_status
corporate_action_status
survivorship_status
missingness
duplicate_status
source_health_status
export_hashes

Do not print credentials, tokens, passwords, or private connection details.

If the repository does not contain a discoverable central-database access contract, return:

CENTRAL_DB_ACCESS_CONTRACT_MISSING

and create a structured database-maintenance request rather than inventing an independent
provider chain.

A local Parquet or CSV may be created only as a bounded derived research export and must be
accompanied by:

- central snapshot id;
- exact query/export command;
- query parameters;
- export timestamp;
- row count;
- symbol count;
- date range;
- schema;
- SHA-256 hash;
- derivation code;
- no-future audit.

The R2 Sina raw-close data may be retained only as:

RAW_CLOSE_FORENSIC_BASELINE

It must not replace central adjusted/total-return evidence.

DATA GAP RULE

If a required field is absent, do not silently substitute another field. Return one of:

CENTRAL_DB_FIELD_UNAVAILABLE
CENTRAL_DB_POINT_IN_TIME_UNAVAILABLE
CENTRAL_DB_ADJUSTED_DATA_UNAVAILABLE
CENTRAL_DB_CORPORATE_ACTION_UNAVAILABLE
CENTRAL_DB_MARKET_CALENDAR_UNAVAILABLE
CENTRAL_DB_BREADTH_UNAVAILABLE
CENTRAL_DB_CREDIT_RATE_UNAVAILABLE
CENTRAL_DB_SNAPSHOT_STALE
CENTRAL_DB_SCHEMA_MISMATCH
CENTRAL_DB_ACCESS_BLOCKED

Create:

reports/ds_us/remediation_r3/central_db_data_gap_request_20260713.json

with:

market
strategy_or_detector
required_dataset
required_field
required_semantics
required_date_range
required_symbol_scope
current_snapshot_id
blocking_reason
acceptable_fallback
fallback_limitations
requested_database_action

Any ingestion, backfill, correction, or schema change must be returned to the user for the
Codex/database-maintenance workstream. DS has no database-write authorization.

If the central database does not provide adjusted total-return or corporate-action-corrected
data, return:

CENTRAL_DB_ADJUSTED_DATA_UNAVAILABLE

Under that blocker:

- US46 remains FROZEN_STATIC_HYPOTHESIS_ONLY;
- raw-close metrics remain forensic-only;
- FROZEN_US46_STATIC_BEST is not allowed as strict evidence;
- SYSTEM_INTAKE_READY must remain false;
- do not build an independent Sina/yfinance replacement chain.

A Strategy Intake Packet cannot be SYSTEM_INTAKE_READY without:

- central snapshot id;
- central dataset name;
- schema version;
- lineage status;
- PIT/no-future status;
- adjusted/corporate-action status;
- export hashes;
- exact research commit;
- exact generator command.

==================================================
PRIMARY OBJECTIVE
==================================================

Correct the holdings engine and cost/cash accounting, use central adjusted total-return data
or a hard blocker, faithfully implement preregistered strategies, implement real static/soft/
hard/fallback allocators, update the regime snapshot from the latest completed central-market
session, and produce two schema-complete Strategy Intake Packets if system intake is requested.

==================================================
PART 0 — FREEZE R2 SOURCE ARTIFACTS
==================================================

Read and preserve:

reports/ds_us/remediation_r2/
reports/ds_us/remediation_r2/us46_holdings_based_engine.py
reports/ds_us/remediation_r2/build_regime_features.py
reports/ds_us/remediation_r2/c2_remediation_pipeline.py

Produce:

reports/ds_us/remediation_r3/r3_r2_source_freeze_20260713.md
reports/ds_us/remediation_r3/r3_failure_memory_import_20260713.json
reports/ds_us/remediation_r3/r3_central_db_r2_snapshot_mapping_20260713.csv

Record:

- R2 source commit;
- R2 rule hash;
- R2 data hashes;
- central snapshot mapping;
- accepted R2 artifacts;
- externally rejected conclusions;
- exact R3 changes.

Do not overwrite R2 artifacts and do not mix R2 raw rows with a newer central snapshot in a
single run.

If the central snapshot differs, produce:

reports/ds_us/remediation_r3/r3_snapshot_drift_report_20260713.md

==================================================
PART 1 — FIX THE US46 HOLDINGS ENGINE
==================================================

The R2 engine remained in cash for the first 63 sessions and did not correctly remove
transaction costs from portfolio value.

Implement a correct holdings-based engine using one frozen central snapshot:

1. Allocate 50% QQQ / 50% GLD on the first eligible execution session.
2. Allow weights to drift between scheduled rebalances.
3. Rebalance every 63 trading sessions after the initial allocation.
4. Execute incremental net trades, not sell-all/buy-all, unless gross-turnover accounting is
   explicitly used and costed consistently.
5. Deduct transaction costs from cash and portfolio value.
6. Cost equals 5 bps one-way on actual absolute traded notional.
7. Preserve shares, cash, prices, weights, notional, fees, and post-trade value.
8. Support fractional shares for research unless another rule is declared.
9. Use one documented execution-price convention consistently.
10. No leverage, no shorting, and no unexplained negative cash.

Required reconciliation on every trade date:

pre_trade_cash
+ pre_trade_holdings_value
- transaction_cost
= post_trade_cash + post_trade_holdings_value

Required artifacts:

reports/runops/ds_us_c2r3_20260713/us46_holdings_daily.parquet
reports/runops/ds_us_c2r3_20260713/us46_rebalance_ledger.csv
reports/runops/ds_us_c2r3_20260713/us46_equity_daily.parquet
reports/ds_us/remediation_r3/us46_engine_reconciliation_20260713.json
reports/ds_us/remediation_r3/us46_rule_and_data_manifest_20260713.json

Required focused tests:

- first eligible session is invested;
- first 63 sessions are not entirely cash;
- rebalance count matches schedule;
- weights drift between rebalances;
- cost leaves the portfolio rather than remaining as cash;
- post-trade accounting identity holds;
- zero target-weight change produces zero trade and zero cost;
- incremental notional matches share changes;
- equity remains positive and dates monotonic;
- frozen parameters cannot change during the run.

No hard-coded passed=True test is allowed.

==================================================
PART 2 — CENTRAL ADJUSTED TOTAL-RETURN AND CORPORATE-ACTION EVIDENCE
==================================================

Query and freeze central-database adjusted/total-return data for QQQ, GLD, SPY, TLT, HYG,
LQD, and required sector ETFs.

Evidence must include:

- adjusted close or total-return series;
- dividend treatment;
- split treatment;
- source metadata;
- retrieval timestamp;
- date range;
- missingness;
- hashes;
- cross-source or internal consistency checks where available.

Do not treat one provider rate limit as proof that adjusted data is unavailable. Provider
maintenance belongs to the central database workstream, not DS.

If unavailable, emit CENTRAL_DB_ADJUSTED_DATA_UNAVAILABLE and the structured gap request.
Do not output a positive strict US46 label from raw-close data.

Required artifacts:

reports/ds_us/remediation_r3/us_adjusted_data_manifest_20260713.json
reports/ds_us/remediation_r3/us_adjusted_vs_raw_diagnostic_20260713.csv
reports/ds_us/remediation_r3/us_corporate_action_audit_20260713.md

==================================================
PART 3 — FAITHFULLY IMPLEMENT PREREGISTERED SPECIALISTS
==================================================

The R2 diagnostic strategies did not match the preregistered formulas.
Implement the frozen R2 hypotheses faithfully:

- A1: frozen holdings-based US46 under the corrected engine.
- A2: dynamic rule based on QQQ versus its 200MA, switching between 70/30 and 30/70;
  not fixed 70/30.
- A3: breadth-conditioned allocation using the declared central breadth field; not fixed
  80/20.
- B1: GLD-heavy + cash under its target selloff regime.
- B2: TLT + GLD barbell under its target selloff regime.
- C1: SPY + QQQ 50/50 under sideways regime.
- C2: SPY + cash buffer under sideways regime.
- C3: equal-weight the declared sector ETF universe; do not replace with SPY/QQQ/GLD.
- D1: true SPY buy-and-hold with initial allocation and no periodic rebalance.
- D2: holdings-based SPY/TLT 60/40 with the declared schedule.
- Blocked PIT-fundamental or earnings families remain blocked unless the central database has
  valid PIT data.

For every strategy preserve:

- exact formula;
- regime condition;
- execution dates;
- weights;
- holdings;
- equity curve;
- turnover;
- costs;
- train/validation/test_diagnostic metrics;
- central snapshot id.

Produce:

reports/ds_us/remediation_r3/r3_hypothesis_implementation_fidelity_20260713.csv
reports/ds_us/remediation_r3/r3_specialist_diagnostics_20260713.csv
reports/runops/ds_us_c2r3_20260713/specialist_equity_curves.parquet

Every active hypothesis must be faithfully implemented or explicitly blocked.

==================================================
PART 4 — INDEPENDENT TRAIN-FROZEN PROBABILISTIC DETECTOR
==================================================

The R2 EMA sidecar is a smoothed copy of deterministic labels and is not independent.

Implement an independent detector using causal central-database regime features, such as:

- Gaussian Mixture Model;
- Hidden Markov Model;
- train-fitted clustering;
- change-point model with train-frozen parameters.

Requirements:

1. Fit scaler/model on train only.
2. Freeze before validation.
3. Test is diagnostic-only.
4. Do not use deterministic states as the training target.
5. Preserve feature list, parameters, random seed, train dates, and model hash.
6. Generate out-of-sample probabilities/confidence.
7. Compare genuinely independent outputs.

If this cannot be implemented, emit PROBABILISTIC_DETECTOR_BLOCKED and keep the regime-aware
packet blocked.

Required artifacts:

reports/ds_us/remediation_r3/r3_probabilistic_detector_manifest_20260713.json
reports/ds_us/remediation_r3/r3_detector_agreement_matrix_20260713.csv
reports/ds_us/remediation_r3/r3_detector_oos_diagnostics_20260713.csv

==================================================
PART 5 — UPDATE THE CURRENT REGIME SNAPSHOT
==================================================

The R2 snapshot was stale and was not a current-market result.

Rebuild from the latest completed US session in the central database.

Requirements:

- as_of_market_date equals the latest actual market row;
- record central snapshot id and retrieval timestamp;
- record staleness in calendar and trading days;
- do not use wall-clock date as market-data date;
- do not claim HIGH fit when required dimensions are missing;
- distinguish deterministic state, independent probabilistic state, confidence, candidate
  persistence, and confirmation lag;
- preserve FORWARD_HOLDOUT_CONTAMINATED for strategy selection.

Required artifact:

reports/ds_us/remediation_r3/us_current_regime_snapshot_20260713.json

Allowed fit labels:

US46_REGIME_FIT_HIGH
US46_REGIME_FIT_MODERATE
US46_REGIME_FIT_LOW
US46_REGIME_FIT_UNCERTAIN

This is research context only, not advice.

==================================================
PART 6 — IMPLEMENT REAL STATIC / SOFT / HARD / FALLBACK ALLOCATORS
==================================================

Build real daily portfolio equity curves under the same engine, central snapshot, dates,
costs, and risk budget.

Required allocators:

A. FROZEN_US46_STATIC
B. BEST_SINGLE_SPECIALIST_CONTINUOUS
C. STATIC_EQUAL_WEIGHT_SPECIALIST_ENSEMBLE
D. STATIC_PREREGISTERED_FIXED_WEIGHT_ENSEMBLE
E. SOFT_REGIME_PROBABILITY_ALLOCATOR
F. HARD_REGIME_SWITCHING_ALLOCATOR
G. DEFENSIVE_OR_CASH_FALLBACK

Soft allocator:

- uses frozen independent regime probabilities;
- applies a confidence threshold;
- maximum weight-change constraint;
- explicit risk budget;
- actual turnover and cost.

Hard allocator:

- uses confirmed state only;
- respects minimum dwell and hysteresis;
- uses a preregistered state-to-specialist map;
- maximum allocation change;
- low-confidence fallback;
- actual turnover and cost.

All allocators must use holdings ledgers, not averages of Sharpe ratios.

Required outputs:

reports/runops/ds_us_c2r3_20260713/allocator_equity_curves.parquet
reports/runops/ds_us_c2r3_20260713/allocator_weights_daily.parquet
reports/ds_us/remediation_r3/r3_allocator_comparison_20260713.csv
reports/ds_us/remediation_r3/r3_allocator_state_attribution_20260713.csv
reports/ds_us/remediation_r3/r3_allocator_switch_log_20260713.csv

Report by train / validation / test_diagnostic_only / pseudo_forward_diagnostic:

- total return;
- CAGR;
- annual volatility;
- Sharpe;
- Sortino;
- maximum drawdown;
- turnover;
- gross traded notional;
- transaction cost;
- switch count;
- average dwell;
- fallback percentage;
- state attribution.

Selection must use train and validation only.
2026 remains contaminated and cannot select parameters or strategies.

==================================================
PART 7 — TWO SCHEMA-COMPLETE STRATEGY INTAKE PACKETS
==================================================

Produce two complete packets only if supported:

1. corrected frozen US46 static packet;
2. regime-aware allocator packet or a schema-complete blocked packet.

Both packets must include:

- strategy id and exact formula;
- asset universe;
- central dataset and snapshot id;
- adjusted/corporate-action status;
- source and hashes;
- execution timing;
- rebalance rule;
- cost model;
- risk/capacity assumptions;
- split policy;
- validation metrics;
- test diagnostic-only metrics;
- target/inactive/failure regimes;
- detector dependency;
- fallback behavior;
- known blockers;
- artifact references;
- final 40-character source commit.

Do not use branch names as code_commit.
Do not call a packet complete when required fields or implementation are absent.

Required outputs:

reports/ds_us/remediation_r3/us_strategy_packet_us46_static_20260713.json
reports/ds_us/remediation_r3/us_strategy_packet_regime_20260713.json
reports/ds_us/remediation_r3/r3_packet_schema_validation_20260713.json

==================================================
PART 8 — FOCUSED TESTS AND REPRODUCIBILITY
==================================================

Create independent focused tests for:

- initial allocation;
- first 63-session exposure;
- weight drift;
- rebalance schedule;
- incremental trade notional;
- cash/cost reconciliation;
- zero-trade zero-cost behavior;
- adjusted-data lineage and central snapshot consistency;
- A2 dynamic 200MA rule;
- A3 breadth rule;
- C3 sector ETF composition;
- D1 true buy-and-hold;
- train-only probabilistic fitting;
- soft allocator risk budget;
- hard allocator dwell/hysteresis;
- no use of 2026 contaminated data for selection;
- packet schema and commit/artifact references.

Required files:

tests/test_c2r3_us46_initial_allocation.py
tests/test_c2r3_us46_cost_cash_reconciliation.py
tests/test_c2r3_us_strategy_formula_fidelity.py
tests/test_c2r3_us_allocator_construction.py
tests/test_c2r3_us_packets_and_forward_boundary.py

Create a reproducible entrypoint:

scripts/run_c2_remediation_r3_pipeline.py

One command must regenerate all R3 artifacts from one frozen central snapshot.

==================================================
FINAL DECISION
==================================================

Allowed labels:

FROZEN_US46_STATIC_BEST
STATIC_SPECIALIST_ENSEMBLE_BEST
SOFT_REGIME_ALLOCATION_VALIDATION_INTERESTING
HARD_SWITCHING_VALIDATION_INTERESTING
NO_REGIME_SWITCHING_EDGE_WITH_CURRENT_EVIDENCE
CENTRAL_DB_ADJUSTED_DATA_UNAVAILABLE
PROBABILISTIC_DETECTOR_BLOCKED
REGIME_ALLOCATOR_INCOMPLETE
SYSTEM_INTAKE_READY
S2_CONTINUE_REQUIRED

FROZEN_US46_STATIC_BEST is allowed only if:

- the corrected engine passes accounting tests;
- central adjusted/total-return evidence is available;
- validation comparison is fair;
- test/2026 are not used for selection.

NO_REGIME_SWITCHING_EDGE_WITH_CURRENT_EVIDENCE is allowed only if real static, soft, hard,
and fallback portfolios were compared under identical execution, cost, and central-snapshot
assumptions.

SYSTEM_INTAKE_READY is not a strategy-candidate label.
STRATEGY_CANDIDATE_AVAILABLE must remain false.

==================================================
BOUNDARY
==================================================

Research-only.

Do not output:

- recommendation/advice;
- ticket;
- strategy candidate;
- readiness/product route;
- daily signal;
- broker/order/paper/live/auto;
- secret/credential output;
- central database files or backups.

==================================================
MANDATORY GITHUB COMMIT, PUSH, AND REMOTE VERIFICATION
==================================================

Completion is invalid until all approved R3 source code, tests, manifests, reports, and
bounded research artifacts are committed and successfully pushed to GitHub.

Do not claim COMPLETE, ALL_PASS, SYSTEM_INTAKE_READY, or CALLBACK_READY before remote
verification succeeds.

Before committing:

1. Run the full focused test suite.
2. Run JSON / CSV / Parquet parse checks.
3. Run no-future and test-result-selection checks.
4. Run `git diff --check`.
5. Confirm no credentials, tokens, private keys, database passwords, connection strings,
   `.env`, central database files, database backups, or unbounded raw caches are staged.
6. Confirm only approved source, tests, reports, manifests, and bounded derived exports are
   included.

Required Git procedure:

```bash
git status --short --branch
git branch --show-current
git rev-parse HEAD

git add <only approved R3 source, tests, reports, manifests, and bounded artifacts>
git diff --cached --check

git commit -m "US C2 R3: fix holdings, allocators, central DB snapshot, and evidence"

git push -u origin "$(git branch --show-current)"

git rev-parse HEAD
git ls-remote origin "refs/heads/$(git branch --show-current)"
git status --short --branch
```

Remote verification passes only if:

- git rev-parse HEAD returns a full 40-character SHA;
- git ls-remote returns the same SHA for the branch;
- the remote branch is visible on GitHub;
- the immutable commit URL resolves;
- the worktree is clean or remaining files are documented.

If push or remote verification fails, return REMOTE_PUSH_FAILED and do not claim completion.

Do not commit:

- central database files;
- database backups;
- full raw-data migrations;
- credentials or `.env`;
- provider tokens;
- private connection strings;
- unbounded cache directories;
- virtual environments;
- unrelated worktree changes.

==================================================
CALLBACK
==================================================

CALLBACK_ENVELOPE:
BATCH: DS_US_C2_REMEDIATION_R3_CENTRAL_DB_ENGINE_ALLOCATOR_FIX_20260713
WORKSTREAM: DS_US_RESEARCH_USER_CONTROLLED
TARGET_REPO:
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
R2_SOURCE_FREEZE_STATUS:
CENTRAL_DATABASE_STATUS:
CENTRAL_DATASET:
CENTRAL_SNAPSHOT_ID:
CENTRAL_SCHEMA_VERSION:
CENTRAL_EXPORT_HASHES:
SNAPSHOT_DRIFT_STATUS:
US46_INITIAL_ALLOCATION_STATUS:
US46_COST_CASH_RECONCILIATION:
ADJUSTED_TOTAL_RETURN_STATUS:
HYPOTHESIS_FIDELITY_STATUS:
ACTIVE_HYPOTHESIS_COUNT:
ACTIVE_FAMILY_COUNT:
PROBABILISTIC_DETECTOR_STATUS:
CURRENT_REGIME_AS_OF_MARKET_DATE:
CURRENT_CONFIRMED_REGIME:
US46_CURRENT_REGIME_FIT:
STATIC_PORTFOLIO_STATUS:
SOFT_ALLOCATOR_STATUS:
HARD_ALLOCATOR_STATUS:
FALLBACK_STATUS:
PACKET_COUNT:
PACKET_SCHEMA_STATUS:
FORWARD_HOLDOUT_STATUS: FORWARD_HOLDOUT_CONTAMINATED
FOCUSED_TEST_RESULT:
FINAL_REGIME_EDGE_LABEL:
SYSTEM_INTAKE_READY:
LOCAL_RESEARCH_PROBE_ELIGIBLE_COUNT:
STRATEGY_CANDIDATE_AVAILABLE: false
ARTIFACTS:
ARTIFACT_GITHUB_URLS:
VALIDATION:
BOUNDARY_RESULT:
FIXES_REQUIRED:
NEXT_ACTION:
```
