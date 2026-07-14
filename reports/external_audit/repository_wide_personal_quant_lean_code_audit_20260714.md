# Repository-Wide Personal Quant Code and Architecture Audit — 2026-07-14

## Audit status

`COMPLETED_RISK_BASED_REPOSITORY_WIDE_AUDIT`

Overall verdict:

```text
PROJECT_ARCHITECTURE: SIMPLIFY_NOW
CENTRAL_DATABASE: REBUILD_MINIMAL
BACKTEST_TRUST: NOT_YET_READY_FOR_STRATEGY_SELECTION
A_SHARE_R5_METHOD: STRONG_REBUILD_WITH_CRITICAL_FIXES_REQUIRED
US_PIT_CORE: KEEP
STRATEGY_RESEARCH_PROCESS: REPLACE_PROCESS_HEAVY_LOOP
SYSTEM_INTAKE_READY: false
STRATEGY_CANDIDATE_AVAILABLE: false
```

This project is one person's research system, running on one WSL host with approximately CNY 400,000 of intended capital. It should be judged against personal-research requirements: correctness, recoverability, legibility, fast iteration, and bounded operational risk. It should not reproduce the governance surface of a multi-tenant institutional platform.

## Question assumptions and reframing

The request correctly suspects over-engineering, but it also assumes that reducing process necessarily reduces reliability. That assumption is false.

The useful distinction is:

- **Reliability controls** protect data identity, event chronology, cash accounting, point-in-time availability, and recoverability.
- **Process controls** create extra roles, packets, signatures, approval layers, duplicate evidence files, and repeated external acceptance without directly improving model correctness.

The correct question is therefore:

> What is the smallest architecture that preserves causal data, correct portfolio accounting, deterministic reproduction, one recoverable database, and honest validation—while deleting controls that do not reduce a material risk for one user and CNY 400,000?

## Scope and method

The audit used GitHub source and immutable refs. Every accessible first-party repository was inventory-classified. Runtime, validation, database-write, research-selection, and execution-related modules received risk-based line-level semantic review. Evidence-only repositories and external forks were classified but not treated as runtime code.

Deep-review refs:

- `central-data-ingestion` Draft PR #22, head `f2d401e42aa8f7cd17a14d94c039f45ba6546d9d`
- `quant-proj` Draft PR #22, head `0e90a2647a84010476470d83ebee017db7f5d20b`
- `quant_research_lab` A-share R5 evidence commit `d5e902af4beab6826ebc34c9a940b881f25ad750`
- `A_Share_Monitor` main `ab12cf99331a39a1396c7c7f885072a9f0f68c08`
- `US_Stock_Monitor` main `872f54211e56a162e713d987d904b49d2521bd25`
- `market_data` main `300d4cf902cafc7f8462991e761e658febdc1424`
- `strategy_work` main `a050e20ba50ada3f8bb052585c667770dac2c2c4`
- `us_stock_30w` master `62abe5ba0213e9e7a8ade69db423fc71a3746357`

Review method:

1. repository and role inventory;
2. current architecture and PR-history reconstruction;
3. static review of risk-bearing source and tests;
4. cross-repository ownership and duplication review;
5. deterministic micro-reproductions of high-risk semantics;
6. target architecture and migration design.

This is not a claim that every prose report line was manually read. All tracked repositories and file classes were inventoried; every identified risk-bearing executable surface was reviewed, and the highest-risk modules were inspected line by line.

## Repository disposition

| Repository | Disposition | Active role |
|---|---|---|
| `quant-proj` | SIMPLIFY | status, decisions, audit entry |
| `central-data-ingestion` | REBUILD_MINIMAL | one database writer |
| `market_data` | SIMPLIFY/ARCHIVE | read-only client, migration history |
| `quant_research_lab` | KEEP_AND_FIX | canonical A-share research |
| `A_Share_Monitor` | SHRINK | monitor/legacy compatibility |
| `US_Stock_Monitor` | KEEP_AND_SIMPLIFY | US PIT and research |
| `strategy_work` | KEEP_SMALL | shared statistics/failure memory |
| `us_stock_30w` | ARCHIVE_EVIDENCE | fixed ETF negative evidence |
| `STRATEGY_VAULT` | ARCHIVE | historical strategy records |
| shared reports/data room | ARCHIVE | evidence only |
| `quant`, `qts` | KEEP_ARCHIVED | legacy references |
| `FinGPT`, `RD-Agent` | EXTERNAL_REFERENCE | no canonical runtime |

Recommended steady-state active repositories:

1. `quant-proj`: one short project status and decision log;
2. `central-data-ingestion`: minimal authoritative warehouse writer;
3. `quant_research_lab`: canonical A-share research;
4. `US_Stock_Monitor`: canonical US research and PIT fundamentals;
5. optional small `strategy_work`: shared statistics only.

`market_data` should cease being a second warehouse owner. `A_Share_Monitor` should cease being a second A-share research engine after R5 is accepted. `us_stock_30w` should remain evidence-only.

# 1. Architecture and audit process

## Finding A-001 — The controller architecture is too heavy

`quant-proj/AGENTS.md` defines separate Quant-Manager, Quant-Dispatcher, Codex-Dev, Strategy-Work, Codex-Advisory, Codex-Audit, ChatGPT external audit, and Human-Gate roles. That separation is understandable for regulated production systems but disproportionate for one user and research-only operation.

Routine work should use:

```text
user/manager chooses objective
    -> one owner implements
    -> automated tests run
    -> short callback
```

Only high-risk changes should add independent review:

- destructive database rewrite;
- schema migration;
- new provider or credential path;
- historical PIT reconstruction;
- backtest execution/accounting changes;
- strategy promotion;
- broker/paper/live activation.

Routine data increments, ordinary feature experiments, failed strategy runs, report updates, and same-schema refreshes should not require task packets, controller signatures, independent model acceptance, and external audit.

Recommended audit levels:

| Level | Trigger | Required control |
|---|---|---|
| L0 | routine research/data refresh | tests + short run record |
| L1 | code/data contract change | owner review + CI |
| L2 | destructive/PIT/execution/promotion | independent audit |

Expected process reduction: approximately 60–80% fewer handoff documents and approval steps without weakening causal or accounting correctness.

## Finding A-002 — Historical artifacts obscure the active system

The workspace contains many task-batch scripts, superseded reports, old callbacks, rejected experiments, and archived strategy paths. Some historical scripts still contain forward-shift operations or older research conventions. They are valuable evidence but should not remain visually adjacent to active runtime modules.

Recommended structure in each active repository:

```text
src/                 active library only
scripts/             current entrypoints only
tests/               current tests only
reports/current/     latest concise evidence
archive/             old task batches and reports
```

Old R16–R33 scripts, R2–R4 A-share remediation implementations, and prior strategy-batch generators should be moved to an archive branch or release tag rather than retained as apparent active surfaces.

## Finding A-003 — Green CI is being confused with architecture correctness

The central database reports 164 passing tests; quant-proj reports 166. R5 reports 39 focused tests. These prove the tested assertions passed. They do not prove that:

- the architecture is appropriate;
- all tests are failure-sensitive;
- the full repository is coherent;
- full-data behavior matches smoke behavior;
- critical temporal assumptions are correct.

The current R5 branch demonstrates this distinction: its focused suite is substantially better than previous DS tests, yet static review still finds an allocator timing leak and a deterministic-detector initialization defect.

# 2. Central database architecture

## Verdict

`REBUILD_MINIMAL`

The current central database is not merely somewhat complex. It has overlapping ingestion/publication models whose control code is larger than the operation they protect.

At the reviewed identity the repository records:

- 88 tracked files;
- 19 production modules and 6,689 runtime lines;
- 9 test files and 3,425 test lines;
- 34 JSON profile/schema/packet/report artifacts;
- 5 deployment templates.

The largest modules are `publisher.py` (1,237 lines), `routine_append.py` (1,159), `remediation.py` (869), `tushare_replay.py` (617), `a0_route_mechanics.py` (587), and `publish_authorization.py` (576).

The first useful Replay import required two provider requests, one backup, one writer lock, and one DuckDB transaction, but the accepted Replay adapter writes zero rows and the actual bridge was outside Git. This is the clearest possible signal that the durable architecture is misaligned with the useful operation.

## Finding DB-001 — Four overlapping pipelines

Current or historical paths include:

1. SQLite staging through `storage.py` and the original CLI;
2. Gate-B copy/swap publication through `publisher.py`;
3. daily append through `routine_append.py`;
4. signed Replay qualification through `tushare_replay.py`;
5. a separate central warehouse implementation in `market_data/central_warehouse.py`.

One project should have one writer path.

## Finding DB-002 — Routine append is row-by-row

`routine_append.py` performs one `SELECT` per incoming row, classifies inserts/noops/conflicts in Python, then executes one `INSERT` per inserted row. For daily market data this creates unnecessary Python/SQL round trips and makes the largest routine path harder to reason about.

Replace it with:

```sql
CREATE TEMP TABLE incoming AS SELECT * FROM incoming_arrow;

INSERT INTO target
SELECT i.*
FROM incoming i
ANTI JOIN target t USING (natural_key...);
```

Conflicts should be produced by one join query and written in bulk.

## Finding DB-003 — Backups and hashes are duplicated by profile

The routine checkpoint is organized by profile and calendar date. Multiple profiles can therefore copy and hash the same multi-gigabyte database separately. For one local database, one pre-write recovery point per day or per run is enough.

Recommended retention:

- one pre-first-write daily backup;
- seven daily backups;
- four weekly backups;
- explicit backup before schema/destructive work.

Do not hash the full multi-gigabyte database after every routine dataset append. Record table-level row counts, max dates, source hashes, and one daily database backup hash.

## Finding DB-004 — High-water rules block legitimate idempotent correction paths

The routine path escalates any batch at or behind accepted/current high water before row-level idempotence is evaluated. This turns same-day partial completion, late rows, and corrected source rows into elevated processes.

A personal warehouse should permit bounded same-key replay:

- identical row: no-op;
- absent key: insert;
- differing key: quarantine or explicit correction mode.

## Finding DB-005 — Security controls exceed the actual threat model

Useful controls:

- secret file mode 0600;
- one writer lock;
- path containment;
- atomic transaction;
- rollback;
- natural keys;
- no secrets/database in Git.

Disproportionate routine controls:

- custom Ed25519 controller grants;
- one-use HG receipts;
- signed profile lifetimes;
- multiple immutable JSON layers;
- descriptor/path adversarial defenses on every routine run;
- independent model acceptance for ordinary append;
- copy/swap publication for normal inserts.

The operating-system user account is the trust boundary for this personal project. Cryptographic authorization should not be the routine data-write boundary.

## Finding DB-006 — Schema ownership is duplicated

Schema truth currently exists in:

- provider field maps;
- signed profiles;
- JSON schemas;
- DuckDB tables;
- `market_data/central_warehouse.py`;
- central-data ingestion contracts.

DuckDB DDL plus one small dataset registry should be authoritative. Provider adapters map into that contract.

## Central database module disposition

| Module | Action | Destination |
|---|---|---|
| `contracts.py` | SIMPLIFY | dataset definitions |
| `collector.py` | SIMPLIFY | `providers/` adapters |
| `quality.py` | KEEP | focused checks |
| `cli.py` | REWRITE | one CLI |
| `storage.py` | DELETE | remove SQLite staging |
| `authorization.py` | DELETE | no routine HG |
| `publisher.py` | ARCHIVE | no normal copy/swap |
| `publisher_cli.py` | ARCHIVE | merged CLI |
| `publish_authorization.py` | ARCHIVE/DELETE | no custom routine grants |
| `mock_canary.py` | ARCHIVE | migration evidence |
| `remediation.py` | ARCHIVE | one-time migration only |
| `remediation_cli.py` | ARCHIVE | one-time migration only |
| `routine_append.py` | REPLACE | bulk writer |
| `routine_append_cli.py` | DELETE | merged CLI |
| `a0_local_manifest.py` | SIMPLIFY | `status` command |
| `a0_local_manifest_cli.py` | DELETE | merged CLI |
| `a0_route_mechanics.py` | ARCHIVE | provider experiment history |
| `a0_route_mechanics_cli.py` | ARCHIVE | provider experiment history |
| `tushare_replay.py` | REWRITE | simple provider adapter |
| `tushare_replay_cli.py` | DELETE | merged CLI |
| `market_data/central_warehouse.py` | ARCHIVE | migration history |
| `market_data/adapters/central_store.py` | KEEP | read-only client |

## Minimal central database target

### Filesystem

```text
~/quant_data/
    quant.duckdb
    backups/
    raw/<provider>/<dataset>/<date>.parquet
    exports/<snapshot_id>/
    logs/ingestion.jsonl
```

### DuckDB schemas and tables

Keep four schemas at most:

```text
meta
ref
raw
derived
```

Minimum tables:

| Table | Purpose |
|---|---|
| `meta.dataset_registry` | key/source/PIT contract |
| `meta.ingestion_run` | one row per run |
| `meta.snapshot` | accepted snapshot identity |
| `meta.quality_result` | concise checks |
| `ref.security_history` | symbol/listing/classification |
| `ref.trade_calendar` | market sessions |
| `raw.daily_bar` | A/US OHLCV and adjusted fields |
| `raw.daily_basic` | market cap/turnover/valuation |
| `raw.security_status` | ST/suspension/limits |
| `raw.corporate_action` | distributions/splits/actions |
| `raw.fundamental_pit` | filed/available facts |
| `raw.event_pit` | timestamped events |
| `derived.feature_catalog` | feature artifact registry |
| `derived.regime_daily` | market-level state features |

Large wide feature matrices should normally remain versioned Parquet and be registered in DuckDB rather than expanding the database schema for every experiment.

### Minimal runtime package

```text
central_data_ingestion/
    config.py
    contracts.py
    providers/
    normalize.py
    writer.py
    quality.py
    cli.py
```

Target size:

- 1,000–1,500 runtime lines;
- 400–700 failure-sensitive test lines;
- one CI workflow;
- one CLI.

### Writer algorithm

```text
fetch
  -> normalize Arrow/DataFrame
  -> validate schema and keys
  -> acquire one writer lock
  -> create daily backup if absent
  -> begin transaction
  -> bulk anti-join / merge
  -> write conflicts in bulk
  -> postchecks
  -> commit
  -> append one run record
```

Manual escalation only for:

- new provider;
- schema change;
- destructive delete/overwrite;
- historical correction/backfill above a declared threshold;
- restore;
- credential changes.

# 3. Backtest and validation correctness

## Overall trust verdict

`NOT_YET_READY_FOR_STRATEGY_SELECTION`

The project contains several strong components, particularly the US SEC point-in-time module and the rebuilt A-share R5 event engine. However, unresolved high-severity temporal and valuation defects mean current results cannot yet be treated as strategy-valid.

## Finding BT-001 — R5 allocator has same-day lookahead

In `quant_research_lab/src/a_share_research_r5/allocators.py`, date-D target weights are computed from date-D state/probability and immediately multiplied by date-D sleeve returns.

The state/probability is derived from date-D market features. A D-close detector cannot earn the D close-to-close return. D weights must become effective on D+1.

Deterministic reproduction:

```text
Day 2 sleeve A return: +10%
Day 2 probability selects A: 100%
Current implementation equity: 1.10
Correct one-day-lag equity: 1.00
```

Required fix:

```text
state/probability observed on D
    -> allocator target scheduled for D+1
    -> D+1 sleeve return earned
```

This is a critical blocker for any regime-switching conclusion.

## Finding BT-002 — R5 deterministic detector can remain neutral forever

The detector initializes `state=LOW_CONFIDENCE_NEUTRAL` and `dwell=0`. If the first observations are a non-neutral state, `dwell` never increases because only matching current-state observations increment it. The transition condition therefore never becomes true.

Deterministic reproduction:

```text
Input: 10 consecutive TREND_UP_LIQUIDITY_EXPANDING observations
Output after day 10: LOW_CONFIDENCE_NEUTRAL
Final dwell: 0
```

Initialize from the first classified state, or increment time-in-current-state independently while a candidate is pending.

## Finding BT-003 — Missing held prices are marked to zero

Both the R5 event engine and `A_Share_Monitor` portfolio use zero when a held symbol is absent from the current price map. In A-shares, suspensions and provider gaps are ordinary. Zero-marking creates an artificial 100% loss and can dominate drawdown and strategy rejection.

Deterministic reproduction:

```text
Position: 1,000 shares
Last valid close: CNY 10
No current bar
Current mark: CNY 0
Implied one-day return: -100%
```

Correct policy:

- suspension/known missing bar: carry last valid close and mark stale;
- delisting/default: explicit write-off policy;
- unexplained data gap: fail the run or quarantine the date;
- never silently zero a normal suspended holding.

## Finding BT-004 — Chunked A-share backtest can silently drop due orders

The chunk runner removes orders due on a warmup date from `pending_orders` before skipping execution on warmup dates.

Deterministic reproduction:

```text
one due order on warmup date
pending after filtering: 0
executed orders: 0
```

Orders should remain pending until the first executable non-warmup date, or warmup boundaries must be placed so no live order can fall inside them.

## Finding BT-005 — Monthly and yearly returns omit period boundaries

`A_Share_Monitor/qta/backtest/metrics.py` groups each month/year and calculates `last / first - 1`. This omits the move from the previous period end to the first observation of the period.

Deterministic reproduction:

```text
Prior month end equity: 100
January first equity: 110
January last equity: 121
Correct January return: 21%
Current reported return: 10%
```

Compute period returns from daily equity percentage changes or use resampled period-end equity and `pct_change()`.

## Finding BT-006 — `alpha_vs_benchmark` is not alpha

The metric is cumulative strategy return minus cumulative benchmark return. It should be called `excess_cumulative_return`. Alpha requires a return regression or another explicit model.

The benchmark also uses raw `close`; research comparison should use an accepted total-return or adjusted benchmark.

## Finding BT-007 — A-share candidate thresholds are too weak and too production-shaped

The default evaluator permits as few as three combined/validation trades and includes a `paper_trading_candidate` label. Three trades do not establish reliability, while paper/live vocabulary adds process pressure before research evidence exists.

Use only:

```text
REJECTED
RESEARCH_INTERESTING
VALIDATION_INTERESTING
FORWARD_OBSERVATION
```

Paper/live status belongs to a separate future execution project.

## Finding BT-008 — R5 static benchmark may be unfairly rebalanced daily

The allocator recomputes static target weights every date and charges turnover caused by daily sleeve drift. Static and regime allocators should use an explicit common allocator-rebalance schedule, or daily and weekly variants should be compared separately.

## Finding BT-009 — R5 model hash is incomplete

The GMM hash captures selected arrays but not all relevant sklearn state, library version, convergence state, precisions/cholesky values, or complete constructor parameters. Record the library version and a serialized/canonical model state hash.

## Finding BT-010 — R5 smoke does not prove detector-to-strategy integration

Strategy engines consume the fixture's preassigned `regime` column, while detectors are run separately. Add an integration test where detector outputs become the strategy/allocator inputs.

## Finding BT-011 — PBO drops observations

`strategy_work/analysis/research_statistics.py` divides periods by block count using integer division and constructs equal blocks, silently ignoring the remainder.

Deterministic reproduction:

```text
periods: 103
blocks: 10
used: 100
dropped: 3
```

Draft PR #11 addresses this but is not merged into main. The main result must remain blocked until remainder-safe semantics are merged and tested.

## Finding BT-012 — Newey-West can overstate significance on nonpositive variance estimates

The implementation clamps a negative long-run variance estimate to zero, then returns an infinite statistic and p-value zero when the sample mean is nonzero. A nonpositive estimate should be reported as invalid/unstable inference, not perfect significance.

## Strong components to retain

### US SEC PIT fundamentals

`US_Stock_Monitor/usq/data/sec_edgar_fundamentals.py` preserves raw response bytes, source hashes, accession, period, unit, filed date, and append-only revisions. It selects facts by filing availability and disables network access unless explicitly opted in. Keep this design.

### US backtest event model

The US engine has explicit D-close signal/D+1-open execution, adjusted prices, sell-first target rebalancing, settlement handling, blocked dates, and test-segment exclusion from selection. Keep it, but continue to require accepted adjusted/corporate-action data.

### R5 event/accounting rebuild

The new R5 engine is materially better than the prior DS implementations: import-safe modules, queued execution, sell-first processing, incremental resize, explicit reconciliation, train-only probabilistic fitting, and real smoke artifacts. Fix the temporal/valuation defects above rather than rewriting it again.

# 4. Lean reliability standard for CNY 400,000

## Required, not optional

### Data

- immutable snapshot id per research run;
- adjusted/corporate-action-aware prices;
- PIT availability for fundamentals/events;
- historical universe or explicit current-universe limitation;
- dated ST/suspension/listing/delisting/limit status;
- deterministic missing-data policy.

### Execution

- signal at D close, fill at D+1 open;
- A-share T+1 and lot-size rules;
- actual broker fee configuration, minimum fee, sell tax, slippage;
- sell-first funding and cash/holdings reconciliation;
- no silent zero valuation;
- no negative cash/holdings;
- liquidity filter and simple capacity limit.

For CNY 400,000, an institutional market-impact simulator is unnecessary. A practical default is:

- 5–15 positions;
- configurable maximum position weight;
- order size below a small fraction of recent median daily amount;
- base and stressed transaction costs;
- no leverage or shorting unless explicitly designed.

### Validation

Use one lean sequence:

1. frozen train;
2. frozen validation;
3. one diagnostic test;
4. 3–5 walk-forward folds;
5. base and 2x cost stress;
6. adjacent parameter sensitivity;
7. subperiod/regime attribution;
8. short forward observation.

For ordinary stock strategies, require a meaningful validation sample—normally dozens of completed trades, not three. For slow ETF allocations, use longer history and multiple independent regimes rather than forcing a stock-strategy trade count.

Advanced DSR/PBO/permutation/bootstrap should be conditional:

- use DSR/PBO when a family has many tried variants;
- use bootstrap when trade count supports it;
- do not run 500 permutations and multiple audits for every early hypothesis.

### Promotion

A research result should become `VALIDATION_INTERESTING` only if:

- positive after costs in validation;
- not dependent on one year or one state;
- parameter neighbors are not catastrophic;
- drawdown is within the user's declared tolerance;
- data and execution gates pass;
- test was not used for selection.

Forward observation should precede any paper/live work.

# 5. Why strategy development is slow

## Root causes

1. process work repeatedly displaces research work;
2. the backtest engine has been rewritten instead of frozen and repaired once;
3. data and strategy tasks are coupled, so one missing dataset blocks unrelated families;
4. multiple repositories own overlapping data and research responsibilities;
5. each batch creates new prompts, callbacks, manifests, summaries, and audit packets;
6. failed families are repeatedly replayed;
7. the search loop runs expensive robustness before cheap screening;
8. no small canonical experiment registry controls the actual trial count;
9. full repository test suites are too slow, so targeted tests and legacy tests diverge.

## Replacement research loop

### Stage 0 — Data contract

Confirm only fields needed by the family. Do not wait for the entire database backlog.

### Stage 1 — Fast screen

- vectorized returns/factor diagnostics;
- maximum 24 preregistered variants per family;
- train only;
- minutes, not days.

### Stage 2 — Realistic validation

Move only the best 3–5 fixed hypotheses into the event engine:

- D+1 execution;
- costs;
- tradability;
- validation split;
- capacity.

### Stage 3 — Robustness

Move only the best 1–3 hypotheses into:

- walk-forward;
- parameter neighbors;
- 2x costs;
- regime/subperiod attribution;
- bootstrap/DSR/PBO if justified.

### Stage 4 — Forward observation

Freeze one strategy or static ensemble. Do not tune during observation.

## Research operating rules

- freeze the backtest engine for one development cycle;
- one owner per market;
- one experiment table, not multiple callback chains;
- no more than two repair cycles per family without new data or premise;
- negative results update failure memory and stop;
- external audit only at method-engine, data-snapshot, strategy-packet, and trading-activation milestones;
- database maintenance proceeds independently and releases staged snapshots.

# 6. Minimal experiment registry

Use one small DuckDB table or SQLite file:

```text
experiment_id
market
family
hypothesis
config_json
code_commit
data_snapshot_id
train_metrics_json
validation_metrics_json
test_metrics_json
status
created_at
parent_experiment_id
```

This is sufficient to count trials for DSR/PBO, prevent accidental test reuse, and reproduce results. It does not require controller-signed ledgers, multiple manifests, or external acceptance per run.

# 7. Three-phase migration

## Phase 1 — Stop adding complexity

Duration: immediate.

- freeze new central DB schemas, signatures, task-packet layers, and publisher paths;
- keep current writer running for essential updates only;
- fix critical backtest bugs before interpreting new strategies;
- mark one canonical owner per domain;
- archive old task-batch scripts from active paths.

Exit criteria:

- no new overlapping writer;
- R5 allocator lag fixed;
- R5 detector initialization fixed;
- missing-price policy fixed;
- A-share chunk warmup order bug fixed;
- monthly/yearly metrics fixed.

## Phase 2 — Build minimal writer alongside current path

- implement provider -> normalize -> bulk writer -> postcheck;
- use one writer lock and one daily backup;
- use one run record;
- test with a temporary DuckDB and one real bounded append;
- compare row counts/hashes against current writer;
- keep old path available for rollback.

Exit criteria:

- same accepted rows and conflicts;
- idempotent replay;
- rollback test;
- runtime materially faster;
- approximately 30–50 high-value tests.

## Phase 3 — Cut over and archive

- switch routine ingestion to minimal writer;
- retain old writer branch/tag for rollback history;
- archive publisher/remediation/SQLite/route/signature modules;
- move read-only client into a small shared package;
- reduce quant-proj to current status, decisions, and milestone audits;
- merge only corrected R5 engine and archive old A-share research implementations.

# 8. Minimal CI

One workflow per active code repository:

```text
ruff
py_compile/import smoke
focused unit tests
one temporary-DuckDB integration test
artifact/secret scan
```

Run:

- pull request;
- push to default branch;
- not both push and PR for the same feature branch.

Do not run:

- full historical data;
- provider network;
- full database copy;
- every archived report/hash test;
- duplicate external-audit validation.

Target central database CI:

- 30–50 tests;
- under 2 minutes;
- one synthetic integration DB;
- no test emails except default-branch failure.

# 9. Immediate priority list

## P0 — correctness

1. lag R5 allocator state/probability weights by one session;
2. fix R5 deterministic initial-state transition;
3. replace zero valuation with stale-price/fail/write-off policy;
4. preserve chunk warmup due orders;
5. fix monthly/yearly metrics;
6. merge remainder-safe PBO or disable PBO on main;
7. add detector-to-strategy integration test.

## P1 — architecture

1. approve `REBUILD_MINIMAL` for central database;
2. choose `central-data-ingestion` as sole writer owner;
3. archive `market_data/central_warehouse.py` after migration;
4. reduce quant-proj routine workflow to one manager/owner/test loop;
5. archive R2–R4 and old strategy-batch scripts from active A-share paths.

## P2 — research speed

1. establish simple experiment registry;
2. create fast-screen -> event-validation -> robustness funnel;
3. cap variants and repair cycles;
4. resume A-share full replay only after P0 fixes and accepted DB snapshot;
5. resume US strict validation when adjusted/corporate-action data is available.

# Final conclusion

The project does not need less rigor. It needs rigor concentrated at the correct boundaries.

Keep:

- causal timestamps;
- PIT data;
- D+1 execution;
- real cash accounting;
- one writer lock;
- one backup;
- one transaction;
- natural-key idempotence;
- missing-data and corporate-action policies;
- train/validation/test isolation;
- concise experiment history.

Remove or archive:

- routine signatures/HG;
- copy/swap publisher;
- SQLite staging;
- overlapping warehouse owners;
- per-batch independent acceptance;
- multiple packet/receipt layers;
- old task-batch code in active paths;
- production-like candidate terminology during research.

The correct project direction is:

```text
small trustworthy database
+ one trustworthy engine per market
+ fast bounded research funnel
+ milestone-only audit
```

Not:

```text
institutional governance simulation
+ repeated engine rewrites
+ audit packets as the primary deliverable
```
