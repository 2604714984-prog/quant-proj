# User/Manager-Dispatch Prompt — Central Database S2 DB1 Fill and Snapshot Management

Copy the complete fenced prompt below into the dedicated central-database management conversation controlled by the user and manager.

```text
RUN CENTRAL_DATABASE_S2_DB1_FILL_AND_SNAPSHOT_20260713

WORKSTREAM:
CENTRAL_DATABASE_MANAGEMENT_USER_MANAGER_CONTROLLED

CONTROL:
This central-database workstream is jointly controlled by the user and manager.
It has authorization to inspect, back up, repair, populate, validate, version, and publish
central research datasets needed by the A-share and US research workstreams.

It does not have authority to select strategies, formulas, regime thresholds, winners,
candidates, paper/live routes, or trading decisions.

COORDINATION REPOSITORY:
https://github.com/2604714984-prog/quant-proj

IMPLEMENTATION REPOSITORY RULE:
Use the existing repository that owns central-data ingestion and schema code. If ownership is
ambiguous, identify it first and record it in the central-database contract. Do not create a
new repository merely to avoid discovering the existing owner.

CURRENT SOURCE EVIDENCE

A-share R3 implementation:
https://github.com/2604714984-prog/quant_research_lab/commit/808629b72224ac24f080599903a083cc69864682

A-share progress report:
https://github.com/2604714984-prog/quant_research_lab/blob/fae383317c35f807c728078ccddda019eba523bc/reports/ds_a_share/ds_a_share_c2_progress_report_20260713.md

US R3 blocker implementation:
https://github.com/2604714984-prog/us_stock_30w/commit/2e34749f0830e000c5c577200ef3b0f65e2c70b0

US progress report:
https://github.com/2604714984-prog/us_stock_30w/blob/6880e2c8f55e86f678f45bad5a5b149c22222d98/reports/ds_us/C2_REMEDIATION_PROGRESS_REPORT_20260713.md

CURRENT VERIFIED BLOCKERS

A-share:

- a_share_daily_basic.circ_mv exists, but point-in-time semantics and join coverage are not
  proven;
- H1/H2/H3/H11 produced zero fills after the R3 merge;
- ts_code/trade_date normalization and anti-join diagnostics are missing;
- industry/sector data exists or may exist but is not under a published research contract;
- adj_factor may exist but adjusted-price semantics are not published;
- H9 SmallCap Quality must remain blocked until direct decision-date market-cap evidence is
  validated.

US:

- current central database contains no usable QQQ/GLD/SPY/TLT/HYG/LQD ETF history;
- no adjusted/total-return ETF table;
- us_trade_calendar is empty;
- no corporate-action table;
- no sector-ETF breadth history;
- no usable current US regime snapshot can be generated;
- US DS is paused and must not build a parallel provider data chain.

PRIMARY OBJECTIVE

Publish a governed central-database contract and release immutable read-only snapshots in
stages so that:

1. DS A-share can repair circ_mv-dependent strategies and optionally preregister H9.
2. DS US can first validate frozen US46, then resume regime/specialist research.
3. Every project consumes one authoritative snapshot with schema, lineage, PIT, adjustment,
   quality, and hash evidence.

Do not wait for all US datasets before releasing an independently complete A-share snapshot.
Do not wait for all 17 US ETFs before releasing a valid QQQ/GLD static-strategy snapshot.

==================================================
PART 0 — DISCOVER AND PUBLISH THE CENTRAL DATABASE CONTRACT
==================================================

The project currently references at least two physical DuckDB paths:

- `/home/rongyu/workspace/A_Share_Monitor/data/local_market/a_share_market.duckdb`
- `/home/rongyu/workspace/quant_data/quant_research.duckdb`

Determine whether these are:

- one logical central database split into market-specific physical stores;
- a primary database plus legacy/local mirror;
- two independently maintained databases that require governance unification.

Do not assume path names imply authority.

Publish a logical contract that maps markets to physical stores and owning code repositories.

Required artifact in the coordination repository:

reports/central_database/central_database_contract_20260713.json

Required fields:

contract_version
logical_database_name
market
physical_database_path
database_engine
owner_repository
ingestion_entrypoint
schema_version
snapshot_naming_rule
read_only_export_rule
PIT_policy
adjustment_policy
corporate_action_policy
survivorship_policy
calendar_policy
quality_gate_policy
backup_policy
rollback_policy
credential_policy
update_frequency
current_snapshot_id
status

Also produce:

reports/central_database/central_database_topology_20260713.md
reports/central_database/central_database_dataset_catalog_20260713.csv

Before writes:

- create a point-in-time backup or safe copy;
- hash the pre-change database files;
- record table counts and schemas;
- record rollback instructions;
- verify sufficient disk space;
- ensure no active writer conflict.

Do not commit database binaries or backups to GitHub.

==================================================
PART 1 — A-SHARE P0: CIRC_MV PIT AND JOIN-COVERAGE REPAIR
==================================================

Goal:
Publish an immutable A-share snapshot that proves whether circ_mv can support decision-date
universe filtering and SmallCap research.

Inspect:

- a_share_daily_raw;
- a_share_daily_basic;
- a_share_symbol_master;
- a_share_limit_price_status;
- suspension/tradability tables;
- industry/sector classification;
- adj_factor or adjusted-price tables.

Required checks for `a_share_daily_basic.circ_mv`:

1. Schema and units.
2. Source/provider lineage.
3. Raw source timestamp or as-of semantics.
4. Whether values are available by close of the declared signal date.
5. Non-null coverage by date.
6. Non-null coverage by symbol.
7. Duplicate key count.
8. Coverage for the DS research date range.
9. Coverage for all candidate-universe symbols.
10. Outlier and zero-value checks.
11. Join coverage against a_share_daily_raw before normalization.
12. Join coverage after normalization.
13. Anti-join samples from both sides.
14. ts_code normalization rules.
15. trade_date type/format/timezone normalization.
16. Evidence that no current-universe-only filter introduces survivorship bias.

Do not silently use total_mv as a replacement for circ_mv.
If total_mv is published as a fallback, label it separately and document that it changes the
strategy premise.

Required artifacts:

reports/central_database/a_share/a_share_circ_mv_pit_audit_20260713.md
reports/central_database/a_share/a_share_circ_mv_coverage_by_date_20260713.csv
reports/central_database/a_share/a_share_circ_mv_coverage_by_symbol_20260713.csv
reports/central_database/a_share/a_share_raw_basic_join_coverage_20260713.csv
reports/central_database/a_share/a_share_raw_basic_anti_join_samples_20260713.csv
reports/central_database/a_share/a_share_key_normalization_contract_20260713.md

Required remediation:

- fix ingestion/key normalization if the missing join is caused by code or schema mismatch;
- rebuild affected rows or materialized views;
- preserve old snapshot and publish a new snapshot id;
- do not mutate historical values without a correction manifest.

Release criteria for `CIRC_MV_PIT_READY`:

- PIT semantics documented and accepted;
- date/symbol coverage meets declared thresholds;
- join coverage is sufficient for the declared strategies;
- no unexplained systemic gaps;
- anti-join reasons are categorized;
- snapshot and export hashes are published.

If not met, publish:

CIRC_MV_PIT_BLOCKED

with exact reason and required next source action.

==================================================
PART 2 — A-SHARE P1: RESEARCH SUPPORTING FIELDS
==================================================

Validate and publish contracts for:

- industry / sector / board classification;
- ST status;
- suspension status;
- listing date / delist date / list status;
- limit-up / limit-down status;
- open and close execution fields;
- adj_factor / adjusted-price semantics;
- amount and turnover_rate;
- direct event/fund-flow fields if present.

For every field publish:

field
physical_table
source
units
PIT_status
available_time
coverage
missingness
update_frequency
snapshot_id
quality_status

Required artifact:

reports/central_database/a_share/a_share_research_field_contract_20260713.csv

If industry is suitable for sector-neutral research, explicitly release:

A_SHARE_INDUSTRY_FIELD_READY

If adj_factor supports an adjusted return series, publish the transformation formula and
validation against raw prices/corporate actions.

Do not claim event/fund-flow readiness if the fields are not row-backed and time-stamped.

==================================================
PART 3 — PUBLISH THE A-SHARE READ-ONLY SNAPSHOT CALLBACK
==================================================

Once Parts 1-2 are complete, publish a read-only snapshot/export for DS A-share.

Required snapshot contents for immediate replay:

- ts_code;
- trade_date;
- open;
- close;
- pre_close;
- amount;
- turnover_rate;
- circ_mv;
- total_mv;
- pb/pe if available;
- industry/sector if ready;
- ST/suspension/tradability;
- up_limit/down_limit;
- list/delist metadata;
- source/PIT/lineage metadata.

Required callback:

A_SHARE_DB_CALLBACK:
STATUS:
CENTRAL_DATABASE_CONTRACT_URL:
OWNER_REPOSITORY:
OWNER_COMMIT_SHA:
PHYSICAL_DATABASE:
DATASET:
SCHEMA_VERSION:
SNAPSHOT_ID:
AS_OF_MARKET_DATE:
ROW_COUNT:
SYMBOL_COUNT:
DATE_MIN:
DATE_MAX:
CIRC_MV_PIT_STATUS:
CIRC_MV_NON_NULL_COVERAGE:
CIRC_MV_JOIN_COVERAGE:
TS_CODE_NORMALIZATION_STATUS:
TRADE_DATE_NORMALIZATION_STATUS:
ANTI_JOIN_ARTIFACT_URL:
INDUSTRY_FIELD_STATUS:
ADJ_FACTOR_STATUS:
PIT_STATUS:
QUALITY_GATE_STATUS:
READ_ONLY_EXPORT_URLS:
EXPORT_HASHES:
ROLLBACK_REFERENCE:
FIXES_REQUIRED:
NEXT_ACTION:

Return this callback to the user immediately when ready. Do not wait for US ingestion.

==================================================
PART 4 — US P0-A: MINIMUM DATA TO UNBLOCK FROZEN US46
==================================================

Priority goal:
Unblock strict holdings-based validation of the frozen 50% QQQ / 50% GLD strategy.

Required symbols:

QQQ
GLD

Required date range:

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
source_timestamp
source
quality_status

Required supporting data:

- NYSE/Nasdaq completed-session calendar;
- dividends and split history;
- adjustment methodology;
- delisting/corporate-action semantics, even if not applicable to the current ETFs;
- missing-session handling;
- duplicate and outlier checks.

Source selection:

The database manager may use reasonable public/no-secret or already-authorized sources.
Do not expose credentials. Use at least one consistency check against an independent source
or previously preserved raw-close series where feasible.

Do not define adjusted_close ambiguously. State whether it is:

- split-adjusted only;
- dividend and split adjusted;
- a total-return index;
- provider-specific adjusted close.

Required datasets may be named according to the existing schema, but the logical contract
must expose stable names such as:

us_etf_daily_adjusted
us_trade_calendar
us_corporate_actions

Required validation:

- QQQ and GLD each have continuous expected coverage;
- latest completed session is present;
- adjusted/raw relationships are plausible;
- dividend and split events reconcile;
- no duplicate symbol/date rows;
- calendar alignment passes;
- export and table hashes are published.

When ready, publish `US_DB_CALLBACK_P0A` without waiting for all regime datasets.

==================================================
PART 5 — US P0-B: REGIME CORE DATA
==================================================

Add:

SPY
TLT
HYG
LQD

Required purpose:

- equity trend;
- rates/duration context;
- credit-risk proxy;
- cross-asset state detection;
- defensive specialist inputs.

Use the same adjusted/total-return, calendar, corporate-action, quality, and snapshot rules as
P0-A.

Publish a new immutable snapshot rather than mutating the P0-A snapshot identifier.

Release label:

US_REGIME_CORE_DATA_READY

==================================================
PART 6 — US P1: SECTOR ETF BREADTH DATA
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

Required purpose:

- sector breadth;
- sector participation;
- cross-sector dispersion;
- breadth-conditioned A3 strategy;
- C3 sector equal-weight strategy.

Required fields and adjustment rules match the core ETF contract.

Release label:

US_SECTOR_BREADTH_DATA_READY

If one or more ETF histories have inception limitations, document them. Do not silently fill
pre-inception dates.

==================================================
PART 7 — US CORPORATE ACTIONS AND TOTAL-RETURN RECONCILIATION
==================================================

Publish:

- dividend events;
- split events;
- provider/source lineage;
- adjustment factors or return-index methodology;
- reconciliation between raw close, adjusted close, and total return.

Required artifacts:

reports/central_database/us/us_etf_adjusted_data_manifest_20260713.json
reports/central_database/us/us_trade_calendar_validation_20260713.csv
reports/central_database/us/us_corporate_action_reconciliation_20260713.csv
reports/central_database/us/us_adjusted_vs_raw_validation_20260713.csv
reports/central_database/us/us_data_quality_board_20260713.csv

Do not release strict US46 validation data if corporate-action/adjustment semantics remain
unknown.

==================================================
PART 8 — PUBLISH STAGED US CALLBACKS
==================================================

Callback P0-A:

US_DB_CALLBACK_P0A:
STATUS:
CENTRAL_DATABASE_CONTRACT_URL:
OWNER_REPOSITORY:
OWNER_COMMIT_SHA:
PHYSICAL_DATABASE:
DATASET:
SCHEMA_VERSION:
SNAPSHOT_ID:
AS_OF_MARKET_DATE:
SYMBOLS: QQQ,GLD
ROW_COUNT:
DATE_MIN:
DATE_MAX:
ADJUSTED_TOTAL_RETURN_STATUS:
DIVIDEND_STATUS:
SPLIT_STATUS:
TRADE_CALENDAR_STATUS:
CORPORATE_ACTION_STATUS:
QUALITY_GATE_STATUS:
READ_ONLY_EXPORT_URLS:
EXPORT_HASHES:
ROLLBACK_REFERENCE:
FIXES_REQUIRED:
NEXT_ACTION:

Callback P0-B:

US_DB_CALLBACK_P0B:
STATUS:
SNAPSHOT_ID:
SYMBOLS: QQQ,GLD,SPY,TLT,HYG,LQD
REGIME_CORE_STATUS:
QUALITY_GATE_STATUS:
READ_ONLY_EXPORT_URLS:
EXPORT_HASHES:
FIXES_REQUIRED:
NEXT_ACTION:

Callback P1:

US_DB_CALLBACK_P1:
STATUS:
SNAPSHOT_ID:
SECTOR_ETF_SYMBOLS:
SECTOR_BREADTH_STATUS:
QUALITY_GATE_STATUS:
READ_ONLY_EXPORT_URLS:
EXPORT_HASHES:
FIXES_REQUIRED:
NEXT_ACTION:

Return each callback to the user as soon as that stage is ready. Do not wait for the final
stage to report the earlier stages.

==================================================
PART 9 — DATABASE QUALITY GATES AND TESTS
==================================================

Create independent tests for:

A-share:

- circ_mv PIT availability;
- symbol/date key normalization;
- join coverage threshold;
- no duplicate keys;
- anti-join categorization;
- open-price completeness;
- ST/suspension/limit field timing;
- adjusted-price formula if released.

US:

- initial and latest session coverage;
- no duplicate symbol/date rows;
- calendar alignment;
- adjustment continuity;
- dividend/split reconciliation;
- ETF inception handling;
- raw-vs-adjusted sanity;
- export hash reproducibility;
- staged snapshot immutability.

Global:

- read-only export reproducibility;
- snapshot id uniqueness;
- schema-version consistency;
- backup and rollback validation;
- no secret output;
- no database binary staged for Git.

Produce:

reports/central_database/central_database_quality_gate_results_20260713.json
reports/central_database/central_database_snapshot_registry_20260713.csv
reports/central_database/central_database_change_manifest_20260713.json

==================================================
PART 10 — COORDINATION RULES
==================================================

The database manager must not:

- modify DS strategy formulas;
- create a fourth A-share family;
- choose whether US46 or another strategy is best;
- run test-period strategy selection;
- activate system intake, candidate, paper, or live trading;
- send a callback directly into a DS conversation without the user's control.

The database manager must:

- return staged callbacks to the user;
- let the user deliver A-share snapshot data to DS A-share;
- let the user deliver US snapshot data to DS US;
- provide Quant Manager with the same immutable callbacks for registration;
- preserve rollback and prior snapshots.

==================================================
MANDATORY GITHUB COMMIT, PUSH, AND REMOTE VERIFICATION
==================================================

All ingestion code, schema migrations, tests, contracts, reports, manifests, and snapshot
metadata must be committed and pushed to their owning GitHub repositories.

Do not commit:

- DuckDB database files;
- backups;
- raw unbounded data dumps;
- credentials;
- `.env`;
- tokens;
- private connection strings.

Required Git procedure in each changed repository:

```bash
git status --short --branch
git branch --show-current
git rev-parse HEAD

git add <approved ingestion code, migrations, tests, contracts, reports, manifests only>
git diff --cached --check
git commit -m "Central DB S2 DB1: publish contracts, repair A-share PIT joins, and ingest US ETF data"
git push -u origin "$(git branch --show-current)"

git rev-parse HEAD
git ls-remote origin "refs/heads/$(git branch --show-current)"
git status --short --branch
```

Remote verification requires matching full 40-character SHAs and resolvable immutable commit
URLs. If push fails, return REMOTE_PUSH_FAILED.

==================================================
BOUNDARY
==================================================

Authorized:

- central research database maintenance;
- bounded public/no-secret data ingestion;
- schema and data-quality repair;
- backup, rollback, snapshot, and read-only export publication;
- code/tests/report commits and pushes.

Not authorized:

- strategy selection;
- recommendation/advice;
- ticket or strategy candidate;
- readiness/product route;
- daily signal;
- broker/order/paper/live/auto;
- secret output;
- committing database binaries or raw unbounded data.

==================================================
FINAL CALLBACK
==================================================

CALLBACK_ENVELOPE:
BATCH: CENTRAL_DATABASE_S2_DB1_FILL_AND_SNAPSHOT_20260713
WORKSTREAM: CENTRAL_DATABASE_MANAGEMENT_USER_MANAGER_CONTROLLED
STATUS:
COORDINATION_REPOSITORY:
IMPLEMENTATION_REPOSITORIES:
BRANCHES:
FULL_COMMIT_SHAS:
TREE_SHAS:
IMMUTABLE_COMMIT_URLS:
REMOTE_VERIFICATION_OUTPUTS:
WORKTREE_STATUSES:
PUSH_STATUSES:
CENTRAL_DATABASE_CONTRACT_STATUS:
LOGICAL_DATABASE_NAME:
PHYSICAL_DATABASES:
SNAPSHOT_REGISTRY_STATUS:
A_SHARE_CIRC_MV_PIT_STATUS:
A_SHARE_JOIN_COVERAGE_STATUS:
A_SHARE_SNAPSHOT_ID:
A_SHARE_DB_CALLBACK_URL:
US_P0A_STATUS:
US_P0A_SNAPSHOT_ID:
US_P0A_CALLBACK_URL:
US_P0B_STATUS:
US_P0B_SNAPSHOT_ID:
US_P0B_CALLBACK_URL:
US_P1_STATUS:
US_P1_SNAPSHOT_ID:
US_P1_CALLBACK_URL:
BACKUP_STATUS:
ROLLBACK_STATUS:
QUALITY_GATE_STATUS:
ARTIFACT_GITHUB_URLS:
FIXES_REQUIRED:
NEXT_ACTION:
BOUNDARY_RESULT:
```
