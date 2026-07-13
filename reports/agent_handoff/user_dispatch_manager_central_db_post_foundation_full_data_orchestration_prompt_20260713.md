# User-Dispatch Prompt — Manager Post-Foundation Central-Database Full Data Orchestration

Copy the complete fenced prompt below into the user-controlled manager conversation.

```text
RUN MANAGER_CENTRAL_DB_POST_FOUNDATION_FULL_DATA_ORCHESTRATION_DB2_20260713

WORKSTREAM:
QUANT_MANAGER_USER_CONTROLLED_DATABASE_ORCHESTRATION

CONTROL

This manager workstream is controlled by the user.
The manager owns orchestration, task decomposition, dependency tracking, callback registration,
acceptance checks, and staged release of central-database work.

A dedicated central-database management conversation performs the database implementation,
ingestion, validation, snapshot publication, and GitHub delivery.

The manager must not:

- select strategy formulas;
- select regime thresholds;
- choose strategy winners;
- alter DS research conclusions;
- promote strategy candidates;
- activate readiness/product routes;
- activate broker/order/paper/live/auto paths;
- expose secrets or credentials.

The manager may:

- create database task packets and GitHub issues;
- assign bounded data-ingestion, schema, quality, backup, and snapshot tasks to the dedicated
  central-database conversation;
- authorize reasonable public/no-secret ingestion required by the frozen task scope;
- require fixes and redispatch failed database subtasks;
- register immutable callbacks and release completed snapshots to the user.

COORDINATION REPOSITORY:
https://github.com/2604714984-prog/quant-proj

PRIMARY DATABASE TASK SOURCE:
https://github.com/2604714984-prog/quant-proj/blob/42c13da1054b09f20b7ff0512642741b0b92ff82/reports/agent_handoff/user_dispatch_central_database_s2_db1_fill_and_snapshot_prompt_20260713.md

A-SHARE METHOD AUDIT SOURCE:
https://github.com/2604714984-prog/quant-proj/blob/29cd6203bcc572bf8fe92a6ecb2d8ef5de052532/reports/agent_handoff/ds_a_share_c2_r4_method_external_audit_result_20260713.md

A-SHARE R4.1 TASK SOURCE:
https://github.com/2604714984-prog/quant-proj/blob/270ec6118112ab6cf02741f697f0fc3c524c2337/reports/agent_handoff/user_dispatch_ds_a_share_c2_r4_1_critical_method_patch_prompt_20260713.md

US DATABASE BLOCKER SOURCE:
https://github.com/2604714984-prog/us_stock_30w/blob/6880e2c8f55e86f678f45bad5a5b149c22222d98/reports/ds_us/C2_REMEDIATION_PROGRESS_REPORT_20260713.md

==================================================
PRIMARY OBJECTIVE
==================================================

After the central-database foundation and governance layer are normalized, create and dispatch
a complete, staged database-ingestion backlog so that all data required by the current A-share,
US, regime-detection, strategy-validation, and future system-validation roadmap are written into
the authoritative central database.

The manager must not merely create a checklist. It must:

1. verify foundation readiness;
2. create task packets and issues;
3. dispatch each task to the dedicated database conversation;
4. track dependencies and callbacks;
5. verify GitHub commits, database quality gates, snapshot ids, and read-only exports;
6. release each accepted staged callback to the user as soon as it is ready;
7. continue until the full frozen backlog is accepted or every remaining item has an explicit
   external-source/auth blocker.

Do not wait for the entire backlog before releasing high-priority snapshots.

==================================================
PHASE 0 — CENTRAL DATABASE FOUNDATION READINESS GATE
==================================================

Do not dispatch full ingestion until the database conversation has completed and returned an
immutable foundation callback covering:

- logical central-database contract;
- physical database topology;
- owner repositories;
- ingestion entrypoints;
- schema-version policy;
- snapshot-id policy;
- dataset catalog;
- backup and rollback procedure;
- single-writer / locking policy;
- read-only export policy;
- PIT policy;
- corporate-action/adjustment policy;
- survivorship policy;
- calendar policy;
- data-quality gate policy;
- secret/credential handling policy;
- GitHub delivery policy;
- snapshot registry.

Required manager status:

CENTRAL_DB_FOUNDATION_READY

If any item is missing, return:

CENTRAL_DB_FOUNDATION_NOT_READY

and redispatch only the missing foundation tasks.

The manager must record the accepted foundation callback at:

reports/central_database/manager/central_db_foundation_acceptance_20260713.md

and create:

reports/central_database/manager/central_db_full_ingestion_dependency_graph_20260713.md
reports/central_database/manager/central_db_full_ingestion_task_matrix_20260713.csv

==================================================
PHASE 1 — CREATE THE MASTER DATABASE BACKLOG
==================================================

Create a canonical task packet:

tasks/in_progress/central-database-full-ingestion-db2-20260713/spec.md

Create a tracking issue in `quant-proj` titled:

`CENTRAL_DATABASE_FULL_INGESTION_DB2_20260713`

Create one database-dialogue prompt per lane under:

reports/agent_handoff/central_database_db2/

The task matrix must contain:

lane_id
priority
market
dataset
physical_table
required_fields
symbol_scope
date_range
source_policy
PIT_requirement
adjustment_requirement
corporate_action_requirement
quality_thresholds
dependencies
owner_repository
implementation_branch
status
callback_path
snapshot_id
blocking_reason
next_action

Freeze task definitions before ingestion. Do not relax quality thresholds after seeing results
without a documented amendment approved by the user.

==================================================
LANE A0 — A-SHARE CORE MARKET AND CALENDAR DATA
==================================================

Ensure the central database contains and governs:

1. `a_share_trade_calendar`
2. `a_share_daily_raw`
3. `a_share_symbol_master_history`

Required daily fields:

ts_code
trade_date
open
high
low
close
pre_close
volume
amount
pct_chg
source
source_timestamp
ingested_at
quality_status

Required symbol-history fields:

ts_code
name
exchange
board
list_date
delist_date
list_status
status_effective_from
status_effective_to
source

Required quality checks:

- zero duplicate primary keys;
- all expected open sessions represented;
- date and ticker normalization;
- finite positive prices where tradable;
- no future-dated rows;
- listing/delisting consistency;
- source lineage and hashes;
- latest completed market date present.

==================================================
LANE A1 — A-SHARE DAILY BASIC, MARKET CAP, AND VALUATION
==================================================

Ensure governed point-in-time tables for:

- `a_share_daily_basic`;
- direct `circ_mv`;
- direct `total_mv`;
- turnover_rate;
- volume_ratio;
- pe / pe_ttm;
- pb;
- ps / ps_ttm if available;
- dividend yield if available.

Critical current requirement:

`circ_mv` must support decision-date universe filtering for H1/H2/H3/H11 and potential H9
SmallCap Quality research.

Required checks:

- PIT availability by signal close;
- units and scaling;
- non-null coverage by date;
- non-null coverage by symbol;
- duplicate-key count;
- raw/basic join coverage before and after key normalization;
- bidirectional anti-join samples;
- outliers and zero values;
- current-universe/survivorship review;
- coverage thresholds frozen before repair.

Recommended initial acceptance thresholds:

- duplicate `(ts_code, trade_date)` keys = 0;
- eligible-date join coverage >= 98%, or an explicit blocker approved by user;
- eligible-symbol `circ_mv` non-null coverage >= 98%, or an explicit blocker;
- unexplained systemic missing-date clusters = 0.

Required staged callback:

A_SHARE_DB_CALLBACK_P0_CIRC_MV

Release it immediately after acceptance; do not wait for US work.

==================================================
LANE A2 — A-SHARE ADJUSTMENT AND CORPORATE ACTIONS
==================================================

Populate and govern:

- `a_share_adj_factor`;
- `a_share_daily_adjusted` or a reproducible adjusted-price materialized view;
- dividends;
- splits/bonus shares;
- rights issues;
- other relevant corporate actions.

Required outputs:

- adjustment formula;
- raw-vs-adjusted reconciliation;
- dividend treatment;
- split/bonus/rights treatment;
- source lineage;
- event timestamps;
- coverage and hashes.

Do not label prices `total_return` unless dividends are included under a documented method.

==================================================
LANE A3 — A-SHARE TRADABILITY AND STATUS HISTORY
==================================================

Populate and govern dated history for:

- ST / *ST status;
- suspensions and resumptions;
- limit-up / limit-down prices and locked status;
- listing age;
- delist status;
- board/market status;
- tradability flags available before execution.

Recommended logical tables:

- `a_share_st_status_history`;
- `a_share_suspension_history`;
- `a_share_limit_price_status`;
- `a_share_tradability_daily`.

The contract must state exact information-availability timing for signal date and execution date.

==================================================
LANE A4 — A-SHARE INDUSTRY, SECTOR, AND BOARD HISTORY
==================================================

Populate dated classification history:

- industry;
- sector;
- board;
- classification provider/version;
- effective date range.

Recommended table:

`a_share_industry_classification_history`

Required purpose:

- sector-neutral strategy research;
- sector dispersion and breadth;
- board-neutral diagnostics;
- historical, not current-only, classification.

Release label:

A_SHARE_INDUSTRY_HISTORY_READY

==================================================
LANE A5 — A-SHARE POINT-IN-TIME FUNDAMENTALS
==================================================

Populate point-in-time financial/fundamental data needed for quality, value, dividend, cash-flow,
and profitability strategies.

Required logical datasets include, where legally and technically available:

- income statement PIT;
- balance sheet PIT;
- cash-flow statement PIT;
- financial indicators PIT;
- earnings announcement dates;
- report period;
- first-publication timestamp;
- restatement/version handling.

Required fields/families:

- revenue and growth;
- net profit and growth;
- ROE/ROA;
- gross/net margin;
- operating cash flow;
- free-cash-flow inputs;
- accruals;
- leverage;
- current ratio;
- dividend history;
- quality and value inputs.

No financial row may become available before its actual publication timestamp.

Release label:

A_SHARE_PIT_FUNDAMENTALS_READY

==================================================
LANE A6 — A-SHARE DIRECT EVENT AND FUND-FLOW DATA
==================================================

Populate only direct row-backed and time-stamped data for:

- financing balance and financing-balance change;
- direct fund-flow fields;
- northbound/southbound flows where historically available;
- block trades;
- lockup releases;
- dividend announcements;
- earnings announcements;
- buybacks;
- major shareholder changes if available;
- other approved event datasets.

Recommended logical tables:

- `a_share_financing_balance_daily`;
- `a_share_fund_flow_direct`;
- `a_share_block_trades`;
- `a_share_lockup_releases`;
- `a_share_dividend_events`;
- `a_share_earnings_events`;
- `a_share_buyback_events`.

Every event requires:

symbol
event_date
publication_timestamp
effective_date
event_type
value/amount
source
revision/version
quality_status

Do not create synthetic direct labels from proxies.
If unavailable, return a source blocker without marking the dataset ready.

==================================================
LANE U0 — US TRADE CALENDAR AND SYMBOL MASTER
==================================================

Populate and govern:

- NYSE/Nasdaq trade calendar;
- completed sessions;
- holidays and half days;
- ETF/equity symbol master;
- inception and delisting dates;
- exchange;
- asset type;
- currency;
- historical sector/industry where applicable.

Recommended tables:

- `us_trade_calendar`;
- `us_symbol_master_history`.

Required date range:

2010-01-01 through at least the current year end for the calendar;
full available history for symbols.

==================================================
LANE U1 — US P0-A: QQQ AND GLD STRICT US46 DATA
==================================================

Priority P0-A.

Populate:

QQQ
GLD

Date range:

2016-01-01 through the latest completed US market session.

Required fields:

symbol
trade_date
open
high
low
close
adjusted_close or total_return_index
volume
dividend_amount
split_factor
source
source_timestamp
ingested_at
quality_status

Required supporting data:

- trade calendar;
- dividend history;
- split history;
- corporate-action reconciliation;
- missing-session checks;
- raw-vs-adjusted comparison;
- immutable snapshot and export hashes.

Required callback:

US_DB_CALLBACK_P0A

Release it immediately once QQQ/GLD are accepted. Do not wait for other US symbols.

==================================================
LANE U2 — US P0-B: REGIME CORE ETF DATA
==================================================

Add:

SPY
TLT
HYG
LQD

Required purposes:

- equity trend;
- rates/duration context;
- credit-risk proxy;
- cross-asset risk regime;
- defensive specialist inputs.

Use the same adjusted/total-return, calendar, corporate-action, quality, and snapshot rules as
U1.

Required callback:

US_DB_CALLBACK_P0B

==================================================
LANE U3 — US P1: SECTOR ETF BREADTH DATA
==================================================

Add:

XLK
XLF
XLE
XLV
XLI
XLP
XLY
XLB
XLU
XLRE
XLC

Required purposes:

- true sector breadth;
- sector participation;
- sector dispersion;
- breadth-conditioned A3 research;
- C3 sector equal-weight strategy.

Do not fabricate pre-inception history.
Document inception-limited coverage explicitly.

Required callback:

US_DB_CALLBACK_P1

==================================================
LANE U4 — US VOLATILITY, RATES, CREDIT, AND MACRO PIT DATA
==================================================

Populate governed market-context datasets needed for regime detection:

- VIX or approved volatility index history;
- Treasury yields and/or rate proxies;
- yield-curve points;
- risk-free/cash proxy;
- credit-spread or HYG/LQD-derived context;
- macro releases used by the project;
- original release timestamp;
- vintage/revision handling where applicable.

Recommended logical tables:

- `us_volatility_daily`;
- `us_rates_daily`;
- `us_credit_context_daily`;
- `us_macro_releases_pit`.

No revised macro value may be backdated as if known at the original release date without
vintage tracking.

==================================================
LANE U5 — US EQUITY DAILY, HISTORICAL MEMBERSHIP, AND SURVIVORSHIP
==================================================

Populate adjusted daily histories for the accepted US research universe, including the
current 270-symbol staging universe and any future accepted broader universe.

Required governance:

- adjusted OHLCV;
- dividends and splits;
- historical symbol master;
- historical index/universe membership;
- delistings;
- mergers/ticker changes;
- survivorship handling;
- source/mirror preservation;
- snapshot hashes.

Recommended tables:

- `us_equity_daily_adjusted`;
- `us_index_membership_history`;
- `us_symbol_change_history`;
- `us_corporate_actions`.

Do not treat a current-universe backfill as survivor-bias-free evidence.

==================================================
LANE U6 — US POINT-IN-TIME FUNDAMENTALS AND EARNINGS
==================================================

Populate PIT data for quality, value, profitability, accrual, leverage, and earnings-drift
research.

Required logical datasets:

- PIT financial statements;
- PIT financial ratios;
- earnings announcement timestamps;
- actual/estimate/surprise where legally available;
- restatements and versions;
- sector/industry history.

Recommended tables:

- `us_fundamentals_pit`;
- `us_earnings_events_pit`;
- `us_estimate_surprise_pit` where available.

No row may become available before its public timestamp.

==================================================
LANE X1 — CROSS-MARKET DERIVED FEATURE STORES
==================================================

After raw/PIT datasets pass, create reproducible derived feature stores or materialized views.

A-share examples:

- returns 1/5/20/60;
- realized/downside volatility;
- amount/turnover features;
- breadth;
- sector dispersion;
- direct market-cap ranks;
- adjusted-return fields.

US examples:

- ETF total returns;
- sector breadth;
- credit/rate context;
- trend/volatility/drawdown features;
- historical-membership-aware equity features.

Every derived field must include:

source_dataset
source_snapshot_id
formula
lookback
minimum_periods
available_time
PIT_status
derivation_commit
hash

Do not store undocumented derived columns.

==================================================
LANE X2 — SOURCE HEALTH, SCHEDULED UPDATE, AND SNAPSHOT AUTOMATION
==================================================

For each accepted dataset, create:

- bounded ingestion command;
- idempotent incremental update;
- retry policy;
- source-health check;
- stale-data alert;
- duplicate-key guard;
- schema-drift guard;
- quality-gate report;
- backup before mutation;
- rollback path;
- immutable snapshot publication;
- read-only export generation;
- hashes;
- GitHub report/manifests.

The manager must ensure that database maintenance becomes repeatable, not a one-time manual
fill.

==================================================
MANAGER DISPATCH RULES
==================================================

For every lane or bounded subtask, the manager must create a database-dialogue packet with:

BATCH_ID
LANE_ID
PRIORITY
TARGET_DATABASE
TARGET_TABLES
OWNER_REPOSITORY
SOURCE_POLICY
SYMBOL_SCOPE
DATE_RANGE
REQUIRED_FIELDS
PRIMARY_KEY
PIT_REQUIREMENTS
ADJUSTMENT_REQUIREMENTS
QUALITY_THRESHOLDS
BACKUP_REQUIREMENTS
ROLLBACK_REQUIREMENTS
TESTS_REQUIRED
ARTIFACTS_REQUIRED
CALLBACK_SCHEMA
GITHUB_BRANCH
STOP_CONDITIONS

The manager must not send vague instructions such as “fill all missing data.”
Each dispatch must be independently testable and auditable.

The database dialogue must push code/tests/reports/manifests before a callback is accepted.
Database binaries and raw unbounded dumps must never be committed to GitHub.

==================================================
STAGED RELEASE ORDER
==================================================

Release and hand back to the user in this order whenever each stage passes:

1. CENTRAL_DB_FOUNDATION_CALLBACK
2. A_SHARE_DB_CALLBACK_P0_CIRC_MV
3. US_DB_CALLBACK_P0A
4. A_SHARE_DB_CALLBACK_P1_ADJUSTMENT_TRADABILITY
5. US_DB_CALLBACK_P0B
6. US_DB_CALLBACK_P1
7. A_SHARE_PIT_FUNDAMENTALS_CALLBACK
8. A_SHARE_EVENT_FUND_FLOW_CALLBACK
9. US_EQUITY_SURVIVORSHIP_CALLBACK
10. US_PIT_FUNDAMENTALS_EARNINGS_CALLBACK
11. CENTRAL_DB_FULL_DATA_CALLBACK

Do not hold A-share callbacks while waiting for US work, or vice versa.

The user controls delivery of callbacks to DS conversations.
The manager must not directly restart or control DS A-share or DS US research.

==================================================
CALLBACK ACCEPTANCE CHECKS
==================================================

Before accepting a database callback, verify:

- immutable full commit SHA resolves;
- remote branch SHA matches callback;
- database change manifest exists;
- backup and rollback reference exists;
- table schema and primary key are declared;
- row count, symbol count, date range are declared;
- duplicate count is zero or explicitly blocked;
- PIT/adjustment/corporate-action semantics are declared;
- quality thresholds pass;
- snapshot id is immutable and unique;
- read-only exports and hashes exist;
- no secret is printed;
- no database binary is committed;
- worktree status is documented;
- GitHub URLs resolve.

Rejected callbacks must be returned to the database dialogue with a bounded remediation packet.

==================================================
MANAGER STATUS BOARD
==================================================

Maintain:

reports/central_database/manager/central_db_db2_status_board_20260713.csv
reports/central_database/manager/central_db_db2_callback_registry_20260713.csv
reports/central_database/manager/central_db_db2_blocker_board_20260713.csv
reports/central_database/manager/central_db_db2_final_summary_20260713.md

Status labels:

NOT_DISPATCHED
DISPATCHED
IN_PROGRESS
CALLBACK_RECEIVED
CALLBACK_REJECTED_FIX_REQUIRED
SNAPSHOT_ACCEPTED
RELEASED_TO_USER
BLOCKED_BY_PUBLIC_SOURCE
BLOCKED_BY_AUTH
BLOCKED_BY_SCHEMA
BLOCKED_BY_QUALITY
COMPLETE

==================================================
MANDATORY GITHUB TASK PUBLICATION
==================================================

Before dispatching the first ingestion task, the manager must commit and push:

- master spec;
- task matrix;
- dependency graph;
- database-dialogue prompts;
- issue link;
- status board.

After every accepted callback, update and push the callback registry and status board.

Required Git procedure:

```bash
git status --short --branch
git diff --check

git add <manager task files, prompts, status boards, callback registry only>
git diff --cached --check
git commit -m "Manager DB2: dispatch and track full central-database ingestion backlog"
git push -u origin "$(git branch --show-current)"

git rev-parse HEAD
git ls-remote origin "refs/heads/$(git branch --show-current)"
```

Do not commit database files, backups, raw dumps, credentials, `.env`, tokens, or private
connection strings.

==================================================
BOUNDARY
==================================================

Authorized:

- database orchestration;
- task creation and issue tracking;
- bounded public/no-secret data-ingestion authorization;
- central database writes performed by the dedicated database conversation;
- backup, repair, schema, validation, snapshot, and export tasks;
- GitHub code/tests/reports/manifests publication.

Not authorized:

- strategy selection;
- recommendation/advice;
- strategy candidate;
- readiness/product route;
- daily signal;
- broker/order/paper/live/auto;
- secret output;
- committing database binaries or raw unbounded data.

==================================================
FINAL MANAGER CALLBACK
==================================================

CALLBACK_ENVELOPE:
BATCH: MANAGER_CENTRAL_DB_POST_FOUNDATION_FULL_DATA_ORCHESTRATION_DB2_20260713
WORKSTREAM: QUANT_MANAGER_USER_CONTROLLED_DATABASE_ORCHESTRATION
STATUS:
REPOSITORY_URL:
BRANCH:
FULL_COMMIT_SHA:
TREE_SHA:
IMMUTABLE_COMMIT_URL:
REMOTE_VERIFICATION_OUTPUT:
FOUNDATION_READY_STATUS:
MASTER_SPEC_URL:
TRACKING_ISSUE_URL:
TASK_MATRIX_URL:
DEPENDENCY_GRAPH_URL:
DATABASE_DIALOGUE_PROMPT_URLS:
DISPATCHED_LANES:
ACCEPTED_SNAPSHOTS:
RELEASED_CALLBACKS:
A_SHARE_P0_STATUS:
A_SHARE_P1_STATUS:
A_SHARE_PIT_FUNDAMENTALS_STATUS:
A_SHARE_EVENT_DATA_STATUS:
US_P0A_STATUS:
US_P0B_STATUS:
US_P1_STATUS:
US_EQUITY_SURVIVORSHIP_STATUS:
US_PIT_FUNDAMENTALS_STATUS:
DERIVED_FEATURE_STORE_STATUS:
UPDATE_AUTOMATION_STATUS:
QUALITY_GATE_STATUS:
BLOCKED_ITEMS:
CENTRAL_DB_FULL_DATA_STATUS:
FIXES_REQUIRED:
NEXT_ACTION:
BOUNDARY_RESULT:
```
