# Repository-Wide Personal Quant Static/Dynamic Audit — 2026-07-14

## Scope and evidence

This review covers the active personal-quant control, database, and A-share research paths at these immutable review points:

- `central-data-ingestion` PR #22, commit `f2d401e42aa8f7cd17a14d94c039f45ba6546d9d`;
- `quant-proj` PR #22 addendum, commit `0e90a2647a84010476470d83ebee017db7f5d20b`;
- `quant_research_lab` R5 Milestone-A head, commit `d5e902af4beab6826ebc34c9a940b881f25ad750`.

The review method was repository-wide static inventory plus risk-based line-level semantic review of mutation, accounting, execution-timing, model-selection, allocator, packet, and gate code. Dynamic evidence was checked from committed JUnit, smoke outputs, manifests, hashes, and CI metadata. The external execution environment could not clone GitHub repositories because DNS/network access was unavailable, so no independent local pytest rerun is claimed. Committed dynamic evidence is treated as evidence, not as a substitute for source review.

Historical reports and superseded artifacts were classified for retention/archival value but were not treated as active runtime authority.

## Executive verdict

### Whole project

`SIMPLIFY_NOW`

The project is materially over-governed for one person, one WSL host, one DuckDB warehouse, research-only use, and approximately CNY 400,000 of capital. Reliability should remain high, but institutional-style authorization, packet, signature, repeated audit, and publication machinery is increasing defect surface, slowing strategy research, and obscuring the small amount of code that actually changes data or computes returns.

### Central database runtime

`REBUILD_MINIMAL_WITH_COMPATIBILITY_BRIDGE`

Do not continue incremental simplification across all current ingestion paths. Freeze the current database and current accepted writer, build one minimal bulk-ingestion path beside it, prove parity on bounded batches, then archive the old publishers/remediation/signature paths.

### A-share R5 method engine

`ACCEPT_AS_MILESTONE_A_ENGINE_PROTOTYPE_WITH_CRITICAL_ALLOCATOR_TIMING_FIX`

R5 is a large improvement over the rejected DS implementations. The event loop, reconciliation, import safety, detector fitting, and bounded evidence are credible enough to retain. However, the allocator code applies date-D regime probabilities/states and date-D target weights to date-D sleeve returns. If those regime features are formed at D close, this is same-day look-ahead. The full replay must shift allocation decisions to D+1 and introduce an explicit allocator rebalance schedule before any strategy conclusion is accepted.

### Strategy readiness

`NOT_READY_FOR_SYSTEM_INTAKE`

No full central-database snapshot has been accepted, no full-data replay has run, legacy A-share/US backtest paths have known defects, and R5 allocator timing requires correction. `strategy_candidate_available=false` remains correct.

---

## 1. Architecture proportionality

The central database repository itself records 19 production modules, 6,689 production lines, 3,425 test lines, 34 JSON profile/schema/report artifacts, five deployment templates, and 15,355 inserted lines since inception. The largest modules are `publisher.py` (1,237), `routine_append.py` (1,159), `remediation.py` (869), `tushare_replay.py` (617), `a0_route_mechanics.py` (587), and `publish_authorization.py` (576).

This is disproportionate to the actual operating model:

- one owner;
- one machine;
- one local DuckDB;
- no multi-tenancy;
- no live trading;
- no regulated production route;
- daily or bounded research updates.

The first useful append needed two GETs, one backup, one writer lock, one DuckDB transaction, and postchecks. It inserted 5,524 daily rows and 60 partial daily-basic rows. The durable Replay adapter retained zero rows, and the actual import used a temporary bridge outside Git. That is the clearest architecture failure: the durable repository contains more control machinery than operational data flow, while the working bridge was not the durable path.

### Root cause

The project optimized for proving authority boundaries rather than minimizing the correctness-critical path. This led to multiple overlapping concepts:

- SQLite staging;
- Gate-B copy/swap publication;
- routine append;
- one-time remediation;
- Replay qualification;
- signed profiles;
- HG records;
- multiple immutable JSON receipts;
- repeated database copies and hashes;
- external acceptance per routine batch.

Each layer is individually defensible. Collectively they create more failure modes than they remove for this project scale.

---

## 2. Central database module decisions

| Module/path | Decision | Reason |
|---|---|---|
| `tushare_replay.py` | SIMPLIFY | Keep provider request, secret handling, response caps, retries/timeouts, and source labels. Remove signed profiles/batches, single-use controller grants, aggregate-only receipt layers, and qualification-only dead end. It should return normalized rows to the common writer. |
| `tushare_replay_cli.py` | SIMPLIFY | One CLI subcommand is enough; merge into the main ingestion CLI. |
| `routine_append.py` | REPLACE/ARCHIVE | It combines security hardening, signed profile validation, daily checkpoints, row-by-row key lookups, Python-loop writes, receipts, risk classification, and post-verification. Replace with temporary-table bulk anti-join/upsert under one lock and transaction. |
| `publisher.py` | ARCHIVE | Copy/swap publisher and capability-based publication are unnecessary for one local research DuckDB once the bulk writer is proven. |
| `publisher_cli.py` | DELETE after migration | A second publication CLI creates route ambiguity. |
| `publish_authorization.py` | ARCHIVE | Custom Ed25519 grants, detached HG records, path/descriptor attack defenses, and single-use capabilities are disproportionate. Retain only generic canonical JSON/hash helpers if still useful. |
| `remediation.py` | ARCHIVE | One-time foundation repair must not remain part of normal runtime. Preserve as historical migration tooling. |
| `a0_route_mechanics.py` | ARCHIVE or fold into adapter tests | It is another acquisition/route layer. Keep only provider-specific normalization logic that is still active. |
| old SQLite staging path | DELETE after parity | It duplicates DuckDB staging and creates another schema/source of truth. |
| `contracts.py` | SIMPLIFY | Keep typed dataset specification, natural key, required fields, and date/PIT semantics. Remove packet-oriented authority fields. |
| `quality.py` | KEEP/SIMPLIFY | Keep duplicate, null, range, date, and key checks. Convert to table-driven checks used before/after bulk write. |
| provider adapters | KEEP | One small adapter per provider, each producing the same normalized batch interface. |
| main CLI | KEEP/SIMPLIFY | One CLI with `ingest`, `validate`, `snapshot`, and `status` commands. |
| systemd templates | ARCHIVE | For one user, Task Scheduler/cron/manual CLI is sufficient. Keep one example only if automatic daily refresh is actually used. |
| JSON schemas/profiles | DELETE MOST | Replace dozens of overlapping schemas with one dataset registry and one run-manifest schema. |
| external audit/report artifacts | ARCHIVE | Keep immutable milestone summaries, not per-run packet chains. |

### Minimum safety controls that must remain

1. Secret read from a private file or environment; never logged or committed.
2. Exactly one writer lock.
3. One backup per mutation run, or one per day when multiple append runs occur.
4. One DuckDB transaction with rollback on any failure.
5. Fixed natural key and database uniqueness constraint/index where practical.
6. Bulk idempotency using temporary staging plus anti-join/upsert.
7. Conflict quarantine for same natural key with materially different payload.
8. Post-write duplicate, count, null, date-range, and reopen checks.
9. Source, retrieval timestamp, query/content hash, and PIT/adjustment labels.
10. No database, raw payload, token, key, or backup in Git.

Everything else is optional and should require a concrete threat or recovery scenario.

---

## 3. Minimal central database target

### Repository/runtime structure

```text
central_data_ingestion/
  cli.py                 # ingest / validate / snapshot / status
  registry.py            # dataset definitions only
  adapters/
    tushare.py
    replay.py
    public_us.py
  normalize.py           # provider row -> canonical dataframe/Arrow table
  writer.py              # lock + backup + temp table + transaction
  checks.py              # pre/post quality checks
  snapshots.py           # short run record and export hashes
```

Target runtime: approximately 1,000–1,500 clear lines. Target tests: 500–800 high-value lines. Line count is not a gate, but any excess must correspond to an active operational need.

### One data-flow only

```text
provider adapter
  -> normalize to Arrow/Pandas batch
  -> validate schema/key/date/PIT labels
  -> acquire one writer lock
  -> create one backup if none exists for run/day
  -> register batch as temp DuckDB table
  -> bulk INSERT anti-join / MERGE in one transaction
  -> quarantine conflicts
  -> postchecks and reopen
  -> one row in meta.ingestion_runs
```

### Core metadata tables

```text
meta.dataset_registry
meta.ingestion_runs
meta.snapshots
meta.conflicts
```

No per-batch authorization schema, no signed profile schema, and no multiple JSON receipt layers.

### Research tables

Keep tables aligned with actual research, not every possible future source:

```text
a_share.calendar
a_share.symbol_history
a_share.daily
a_share.daily_basic
a_share.adj_factor
a_share.tradability_daily
a_share.industry_history
a_share.fundamentals_pit
a_share.events_pit

us.calendar
us.symbol_history
us.daily_adjusted
us.corporate_actions
us.membership_history
us.fundamentals_pit
us.events_pit

macro.releases_pit
```

Derived features should be reproducible views or versioned feature tables only when they are reused. Do not materialize a new layer for each research batch.

### Daily process

```text
python -m central_data_ingestion ingest a_share.daily --from last_success
```

Output should be one short record:

```text
run_id, dataset, started_at, finished_at, source, query_hash,
rows_received, rows_inserted, rows_noop, rows_conflict,
min_date, max_date, backup_path, status, error
```

### Elevated operations only

Require manual confirmation and a separate backup for:

- new source;
- schema change;
- natural-key change;
- destructive overwrite/delete;
- historical correction/backfill larger than a configured threshold.

Routine same-source, same-schema increments do not need task packets, signatures, external acceptance, or independent model review.

---

## 4. Backtest and validation standards for approximately CNY 400,000

The current project repeatedly applied institution-style evidence gates while still missing basic accounting and timing correctness. For this capital level, the priorities should be reversed.

### Non-negotiable correctness

1. Signal timestamps and execution timestamps are explicit.
2. Close-D signals execute no earlier than D+1.
3. PIT universe membership, ST/suspension/list/delist, limits, and corporate actions are dated.
4. Adjusted prices/returns are documented and reproducible.
5. Natural survivorship and delisting effects are represented.
6. Cash, holdings, commissions, stamp duty, slippage, and lot rounding reconcile row by row.
7. Benchmark and cash return conventions are explicit.
8. Parameter/model selection never uses the final test period.
9. Full replay uses an immutable data snapshot.

### Proportionate validation

For each strategy family:

- one train period;
- one validation period;
- one untouched diagnostic holdout;
- two or three walk-forward folds if history is long enough;
- realistic base cost plus one harsher cost stress;
- parameter-neighborhood/plateau check;
- universe sensitivity;
- bootstrap or permutation only when it answers a specific fragility question;
- benchmark-relative after-cost return and drawdown;
- minimum trade count appropriate to holding period.

Do not require every research hypothesis to pass dozens of custom gates. Do not use CSCV/PBO, nested cross-validation, complex capacity models, or multiple independent audit rounds unless the strategy search space and capital justify them.

### Simple acceptance board

A strategy is `VALIDATION_INTERESTING`, not “validated,” when:

- causal and accounting tests pass;
- validation after-cost performance is positive versus the declared benchmark or materially improves risk;
- result is not dominated by one short episode;
- neighboring parameters do not collapse;
- harsher costs do not erase the entire premise;
- drawdown is tolerable for the user;
- holdout remains diagnostic-only.

It becomes eligible for system dry-run only after independent code/data replay, not after more governance documents.

---

## 5. R5 A-share engine review

### Strong improvements

The R5 event loop is materially better than prior DS code:

- queued orders execute at the start of the scheduled date;
- sells are sorted before buys;
- retained targets are resized;
- removed targets are liquidated;
- invalid opens are rejected;
- buy/sell costs are separately represented;
- account reconciliation is computed at execution prices;
- smoke artifacts are nonempty;
- detector fit and component selection are train-only;
- package imports are separated from database I/O.

These are worth keeping.

### Critical issue: allocator same-day look-ahead

`run_allocator` calls the weight function using date-D probability/state fields, calculates date-D target weights, charges turnover, and immediately applies those weights to date-D sleeve returns.

For close-derived regime features, D information cannot control exposure to the already-realized D return. The correct sequence is:

```text
D close regime/state/probability
  -> D+1 target allocation
  -> D+1 sleeve return
```

Required fix:

- lag target weights one trading session;
- store `signal_date` and `effective_date` in allocator weights/trades;
- calculate return from prior effective weights;
- add a test where a large D return cannot be captured by a state first observed on D.

This applies to both soft and hard allocators. Static allocators also need an explicit rebalance cadence; the current implementation rebalances to fixed targets every day because it compares fixed target weights with daily drifted realized weights on every row. Daily rebalancing may be valid if preregistered, but it is unlikely to be the intended low-friction static benchmark.

### Other R5 cautions

1. Smoke is method evidence, not strategy evidence. Synthetic regimes can prove mechanics but not economic validity.
2. The selection ledger is an explicit API guard, but manual ledger entries alone cannot prove no hidden test access. Full-mode selectors should accept split-scoped objects rather than arbitrary frames.
3. Family sleeve returns average strategies within a family. This is acceptable as a preregistered family sleeve but must not silently dilute or select strategies after validation.
4. Full mode is correctly blocked pending a database callback. Keep that fail-closed behavior.
5. The legacy repository test suite timing out means superseded code still imposes maintenance cost. Archive legacy modules/tests once R5 parity is established.

### R5 verdict

```text
MILESTONE_A_ENGINE:
CONDITIONALLY_ACCEPT_AFTER_ALLOCATOR_LAG_AND_REBALANCE_FIX

FULL_REPLAY:
BLOCKED_PENDING_DATABASE_SNAPSHOT

SYSTEM_INTAKE_READY:
false
```

---

## 6. Whole-project reliability findings

### High-risk patterns found historically

The project history contains repeated examples of:

- same-day signal/return use;
- future execution state applied early;
- cost calculated but not removed from equity;
- initial cash periods that changed strategy exposure;
- preregistered formulas replaced by simplified proxies;
- static/soft/hard comparisons implemented as averages of Sharpe or equity arrays;
- hard-coded or vacuous tests;
- test-period rows entering validation selection through expression errors;
- packet fields claiming evidence not present in code.

This means CI green status is not enough. Tests must be failure-sensitive and must assert economic semantics, not merely file existence or nonnegative row counts.

### Required repository-wide backtest invariant suite

Create one small shared package, no more than approximately 300–500 lines, with reusable tests for every engine:

- signal D cannot earn D return;
- effective allocation date > information date;
- removed holdings sell;
- retained holdings resize;
- sells fund buys in deterministic order;
- zero trade means zero cost;
- account identity holds;
- adjusted data and corporate actions are explicit;
- test split cannot enter selectors;
- benchmark alignment and date calendars match;
- strategy packet references exact code and snapshot.

A-share and US engines should import this invariant suite instead of independently recreating audit frameworks.

---

## 7. Why strategy development has been slow

The bottleneck is not only data or lack of alpha. It is process architecture:

1. Each research step creates packets, gates, callbacks, manifests, hashes, and external-review cycles.
2. Method defects are discovered late because smoke tests assert claims instead of economic behavior.
3. Data ingestion, research, validation, and system intake are mixed conceptually.
4. Too many strategy variants are documented before a trustworthy shared engine/data snapshot exists.
5. Repeated “repair rounds” preserve defective designs instead of replacing them cleanly.

### New strategy-development loop

Use a six-step loop:

```text
1. One-page preregistration
2. Implement on shared tested engine
3. Fast bounded smoke
4. Full immutable-snapshot replay
5. One validation board
6. Retire / continue / dry-run
```

Maximum artifacts per strategy family:

- one preregistration;
- one machine-readable result table;
- one short failure/decision memo;
- one packet only if dry-run eligible.

No external audit is needed for ordinary rejected research. Audit only:

- shared engine changes;
- database schema/source changes;
- a strategy moving into system dry-run;
- paper/live execution changes.

### Research prioritization

For CNY 400,000, focus on strategies where small capital is an advantage:

- medium-frequency ETF or broad-universe allocation with low operational burden;
- A-share small/mid-cap quality or liquidity effects only after PIT/tradability evidence;
- defensive/quality/dividend strategies;
- simple cross-sectional momentum or reversal with realistic limits and costs;
- regime detection as a risk overlay, not a complex strategy-switching business.

Avoid building a large multi-agent discretionary-news platform, reinforcement-learning execution stack, or institution-style capacity system before one or two simple strategies survive full replay.

---

## 8. Three-phase simplification plan

### Phase 1 — Freeze and establish one golden path (1–2 weeks)

- Freeze new database framework modules.
- Keep current accepted database read-only except routine ingestion.
- Build minimal adapter -> normalize -> bulk writer -> postcheck path.
- Add allocator D+1 lag and static rebalance cadence to R5.
- Create shared backtest invariant tests.
- Stop producing per-run task packets and independent routine audits.

Exit criteria:

- one A-share daily dataset ingested through minimal path;
- idempotent replay and conflict quarantine pass;
- backup/rollback tested;
- R5 smoke passes with allocator lag.

### Phase 2 — Parity and migration (1–2 weeks)

- Run old and new writers on bounded shadow copies.
- Compare natural keys, payload hashes, row counts, and postchecks.
- Migrate active datasets one by one.
- Publish one compact dataset registry and snapshot registry.
- Archive old SQLite, publisher, authorization, remediation, and duplicate CLI paths.

Exit criteria:

- all active routine datasets use the new writer;
- no operational dependency on temporary bridges;
- runtime code reduced materially;
- one fast CI workflow.

### Phase 3 — Research acceleration (ongoing)

- Accept central snapshot.
- Run R5 full replay after timing fix.
- Run US engine only after the same invariant suite passes.
- Limit active strategy families to a small prioritized queue.
- Audit only promotion events.

---

## 9. Minimal CI

One required workflow, preferably under five minutes:

1. Ruff/format/static import check.
2. Unit tests for writer, natural keys, transaction rollback, and postchecks using temporary DuckDB.
3. Shared backtest invariant suite.
4. One bounded end-to-end ingestion smoke.
5. One bounded A-share/US engine smoke.
6. Secret/risky-extension scan.

Optional local/nightly suite:

- full repository historical tests;
- long full-data replay;
- performance benchmark;
- backup/restore drill.

Do not run five overlapping required workflows that send duplicate failure emails. Do not keep superseded legacy tests in the required path after their code is archived.

---

## 10. Final decisions

```text
WHOLE_PROJECT_ARCHITECTURE:
SIMPLIFY_NOW

CENTRAL_DATABASE_RUNTIME:
REBUILD_MINIMAL_WITH_COMPATIBILITY_BRIDGE

CENTRAL_DATABASE_CURRENT_DESIGN_PROPORTIONATE:
false

R5_A_SHARE_METHOD_ENGINE:
CONDITIONAL_ACCEPT_AFTER_ALLOCATOR_TIMING_FIX

BACKTEST_RELIABILITY:
NOT_YET_PROJECT_WIDE

STRATEGY_DEVELOPMENT_PROCESS:
TOO_SLOW_AND_DOCUMENT_HEAVY

SYSTEM_INTAKE_READY:
false

STRATEGY_CANDIDATE_AVAILABLE:
false
```

## Immediate next actions

1. Manager stops expanding central-database architecture and converts the current full-ingestion plan into tasks against the minimal writer.
2. Database thread implements the minimal writer before adding more source-specific control layers.
3. A-share Codex fixes allocator information/effective-date lag and static rebalance cadence, then republishes Milestone-A evidence.
4. Create the shared backtest invariant package and apply it to A-share and US engines.
5. Archive legacy runtime paths after parity; do not continue repairing every historical branch.
6. Resume strategy research only after one immutable snapshot and one trusted shared engine are available.
