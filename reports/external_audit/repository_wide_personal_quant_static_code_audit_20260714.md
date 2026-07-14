# Repository-Wide Personal-Quant Static Code and Architecture Audit — 2026-07-14

## Status

`AUDIT_COMPLETE_CRITICAL_FIXES_AND_SIMPLIFICATION_REQUIRED`

## Overall verdicts

- Whole-project architecture: `SIMPLIFY_NOW`
- Central database: `REBUILD_MINIMAL`
- Backtest and validation stack: `CONDITIONALLY_USABLE_AFTER_CRITICAL_FIXES`
- Current strategy-development process: `PROCESS_AND_ENGINE_BOTTLENECK`
- Current strategy promotion: `NOT_AUTHORIZED`
- `strategy_candidate_available=false`

The project is materially over-engineered for one person, one WSL host, one local DuckDB, research-only use, and approximately CNY 400,000 of capital. The excessive process does not merely consume time: it has obscured basic semantic defects in backtest, allocation, data-writing, and evidence-generation code.

Green CI is useful but does not rebut this conclusion. The central-data branch has a successful CI run, and the controller branch has five green jobs, yet risk-based semantic review still found defects that the existing suites do not exercise.

---

# 1. Audit scope and method

## Immutable GitHub refs reviewed

- `quant-proj`: `0e90a2647a84010476470d83ebee017db7f5d20b`
- `central-data-ingestion`: `f2d401e42aa8f7cd17a14d94c039f45ba6546d9d`
- `quant_research_lab` R5: `d5e902af4beab6826ebc34c9a940b881f25ad750`
- `A_Share_Monitor` active preservation branch: `1a64e70873fc8a3c3d998e509cbcf690010ffef0`
- `A_Share_Monitor` divergent main reviewed for regression risk: `ab12cf99331a39a1396c7c7f885072a9f0f68c08`
- `US_Stock_Monitor`: `681d3a54662c79162e0477fda2a2aa8efeff0c47` plus current engine code at `872f54211e56a162e713d987d904b49d2521bd25`
- `market_data` central warehouse merge: `300d4cf902cafc7f8462991e761e658febdc1424`
- `us_stock_30w`: active evidence branch plus forensic strategy evidence
- `strategy_work`: active planning/research role and README contract

## Review method

The audit used four layers:

1. Repository-wide inventory of active project-owned repositories, tracked runtime modules, tests, configurations, workflow files, and authoritative registry declarations.
2. Risk-based line-level semantic review of all high-risk paths:
   - database network acquisition and writes;
   - backup, lock, transaction, idempotency, and rollback;
   - signal timing and execution timing;
   - portfolio accounting and valuation;
   - costs, fills, suspension/limit handling, and settlement;
   - train/validation/test selection;
   - regime detection and strategy allocation;
   - candidate/gate generation;
   - task dispatch and acceptance controls.
3. Review of CI job definitions and committed JUnit/test evidence.
4. Independent dynamic reproductions of three material semantic issues.

This is a repository-wide static audit with risk-based line-level review. All active runtime/config/test surfaces were inventoried. High-risk code was read semantically. Historical report/data-room prose was reviewed for authority and boundary, but the audit does not claim that every line of every legacy Markdown report was manually reread; those files are not executable risk surfaces.

## Execution limitation

The external environment did not contain the local 2.4 GB DuckDB, private provider inputs, or the WSL worktrees. Full production-data runs were therefore not rerun externally. Dynamic reproductions below use deterministic minimal fixtures that isolate the reviewed semantics. Existing GitHub CI and committed JUnit evidence were examined but not treated as proof of untested semantics.

---

# 2. Executive findings

## 2.1 The project is too heavy for its actual scale

The controller and database layers are designed as though the project were a multi-tenant institutional platform. The actual project is one owner, one local host, one local DuckDB, research-only, without customers, SLA, regulated production, or an active live-trading route.

The central ingestion repository alone reports:

- 19 production modules;
- 6,689 production lines;
- 3,425 test lines;
- 34 JSON profile/schema/packet/report artifacts;
- 5 deployment templates;
- 15,355 inserted lines since inception.

The two largest writer modules contain 2,396 lines before tests. The first useful Replay import, by contrast, required two GET requests, one backup, one lock, one DuckDB transaction, and simple post-write checks.

## 2.2 More controls did not produce proportionally more reliability

The project has multiple acceptance layers, signed profiles, task-level records, hashes of context files, fixed callback UUIDs, model routing contracts, independent acceptance, audit, and external audit. Despite this, prior A-share DS engines repeatedly contained basic timing, accounting, allocator, and test-evidence errors.

The conclusion is not that testing or safety should be removed. The conclusion is that controls are aimed at the wrong risks. The project needs fewer workflow controls and stronger executable invariants around:

- no-lookahead;
- account reconciliation;
- real costs;
- point-in-time data;
- split isolation;
- reproducible snapshots;
- one authoritative engine and one authoritative writer.

## 2.3 Green CI is necessary but not sufficient

The central ingestion CI successfully compiles, runs Ruff, executes pytest, and scans secrets. The controller CI has five green jobs, including branch/merge identity and integration-identity checks. These prove that the implemented contracts are internally consistent. They do not prove that the contracts are proportionate, that the accepted runtime path is the path actually used, or that untested financial semantics are correct.

## 2.4 The central database should be rebuilt minimally

This is not a recommendation to delete the current database or interrupt collection. It is a recommendation to preserve the current DB as a rollback source, freeze feature growth, extract the essential controls into one minimal writer, and archive overlapping paths.

## 2.5 Strategy development is slow mainly because of process and engine duplication

The project has repeatedly built new task packets, audit packages, engines, smoke frameworks, and evidence layers before obtaining stable data and one trusted engine. Strategy discovery has consequently become an engineering-governance project instead of a research loop.

The remedy is:

- one engine per market, preferably a shared core plus market adapters;
- one immutable data snapshot per research cycle;
- a small hypothesis queue;
- vectorized screening first;
- event-driven validation only for survivors;
- one frozen test use;
- external audit only when an engine/data contract changes or a strategy reaches system intake.

---

# 3. Critical and high-severity findings

## P0-1 — R5 regime allocators use same-day state information for same-day returns

Repository: `quant_research_lab`

File: `src/a_share_research_r5/allocators.py`

`run_allocator()` calls the weight function on date D, immediately uses those target weights against date-D sleeve returns, and then records date-D equity. The soft allocator merges date-D regime probabilities with date-D returns; the hard allocator merges date-D confirmed state with date-D returns.

The regime inputs are built from date-D market features. Therefore a close-D regime decision is being used to earn the return already realized on D. This is lookahead unless the sleeve-return row explicitly represents D+1 execution-to-close returns and is labelled accordingly. The current interface does not enforce that interpretation.

### Independent dynamic reproduction

Two sleeves were created with alternating returns:

```text
Day:       1      2      3      4
Sleeve A: +10%  -10%   +10%  -10%
Sleeve B: -10%  +10%   -10%  +10%
```

The same-day state always identifies the winning sleeve.

- Current same-day weighting: equity `1.4641`
- One-day-lagged weighting: equity `0.7290`

The unlagged implementation manufactures +10% every day from information unavailable before the day’s return.

### Required fix

- Shift confirmed states and probability rows by one trading session before allocator target generation.
- Date-D portfolio return must use weights fixed no later than D-1 close, or a clearly modelled D-open decision using only pre-open data.
- Add a test proving that changing the D state cannot change the D portfolio return.
- Full database replay must not begin until this is fixed.

## P0-2 — The active and main A-share branches disagree on missing-price valuation

Repository: `A_Share_Monitor`

The active preservation branch carries the last observed mark when a held symbol has no close and exposes a missing-price flag. The divergent main branch values the held position at zero.

### Independent dynamic reproduction of the main-branch behavior

- Holding: 10,000 shares
- Last price: CNY 10
- Prior equity: CNY 100,000
- One missing daily bar
- Main-branch valuation: CNY 0
- Artificial daily return: `-100%`

The active preservation branch fixes this specific issue. The unresolved risk is branch divergence: merging or running the wrong branch can reintroduce a severe error.

### Required fix

- Select one canonical branch and merge the safe valuation policy into it.
- For confirmed suspensions, carry the last valid mark and flag it stale.
- For confirmed delisting/default, apply a separate explicit terminal-price policy.
- For unexplained provider gaps, fail the research run after a small tolerance rather than silently marking zero or indefinitely carrying.

## P0-3 — A-share monthly and yearly returns are calculated from the first observation inside the period

Repository: `A_Share_Monitor`

File: `qta/backtest/metrics.py`

Monthly and yearly returns are calculated as the last equity divided by the first equity within each month/year. This omits the return between the prior period’s last observation and the first observation of the current period.

### Independent dynamic reproduction

```text
2023-12-29 equity = 100
2024-01-02 equity = 110
2024-01-31 equity = 121
```

- Current January calculation: `121 / 110 - 1 = 10%`
- Correct boundary-to-boundary January return: `121 / 100 - 1 = 21%`

This affects monthly win rate, worst month, yearly returns, single-year dependency checks, and reports.

### Required fix

Resample the full equity series and use period-end percentage changes, retaining the preceding period-end observation:

```python
monthly = equity.set_index(date).resample("ME").last().pct_change()
yearly = equity.set_index(date).resample("YE").last().pct_change()
```

## P0-4 — Chunked no-future checking returns PASS when the required PIT timestamp is absent

Repository: `A_Share_Monitor`

File: `qta/research/strategy_search.py`

If `available_date` is missing, `_no_future_leak_status_chunked()` returns PASS. Absence of a point-in-time availability field is not proof of no leakage. It is `UNKNOWN` or `BLOCKED` for any feature whose value can be revised or published after the observation date.

### Required fix

- Return `WARNING` for purely price-derived features when lineage proves causal rolling construction.
- Return `FAIL/BLOCKED` for fundamentals, events, membership, or classifications without dated availability.
- Do not permit a positive strategy label from an unknown PIT state.

## P0-5 — The durable central-data runtime is not the path that completed the first useful write

Repository: `central-data-ingestion`

The accepted Replay module qualifies routes and deliberately retains zero rows. The useful append used a temporary bridge outside Git. This is a reproducibility failure: the repository contains more control code than the operation needs, while the successful path is not the durable path.

### Required fix

Stop adding controls around the current split pipeline. Implement one durable end-to-end command:

```text
provider adapter
  -> normalize DataFrame
  -> validate
  -> one writer lock
  -> one backup
  -> one bulk DuckDB transaction
  -> postchecks
  -> one short run record
```

## P0-6 — There are multiple central-writer ownership paths

Repositories: `central-data-ingestion`, `market_data`

`central-data-ingestion` contains collector, SQLite staging, copy/swap publisher, routine append, remediation, Replay, and authorization paths. `market_data/central_warehouse.py` independently implements schema initialization, A-share physical migration, provider ingestion, locking, snapshots, auditing, and compatibility views.

Two repositories must not own central writes. This creates divergence in schema, snapshot semantics, tests, operational commands, and incident recovery.

### Required fix

- One repository owns the writer.
- `market_data` becomes read-only catalog/access adapters.
- Extract any useful bulk-ingest and audit logic from `central_warehouse.py`, then archive the duplicate writer.

## P1-1 — R5 package is not included by the current packaging configuration

Repository: `quant_research_lab`

The `pyproject.toml` package discovery includes only `quant_lab*` and `paper_trader*`. The new `src/a_share_research_r5` package is not included. Local source-tree imports can pass while an installed wheel omits the new engine.

### Required fix

Adopt a single `src` layout or add the R5 package explicitly. Add a CI test that builds a wheel, installs it into a clean environment, imports the package, and runs the focused tests.

## P1-2 — R5 has good local JUnit evidence but no independent branch CI run

The committed JUnit shows 39 passing tests, including event-loop, accounting, detector, allocator, selection, tradability, and packet/gate tests. No GitHub Actions run was found for the R5 smoke commit.

### Required fix

Add one focused PR job:

```text
build/install package
ruff/compile
39 focused tests
bounded smoke
artifact schema/hash checks
```

Do not add multiple identity jobs.

## P1-3 — US engine is safer but operationally brittle on missing execution prices

Repository: `US_Stock_Monitor`

The US portfolio refuses stale-price valuation, which is safer than silently using zero. However, the engine values holdings at open before execution. A missing open for a held symbol can abort the backtest before the fill model records a blocked fill.

### Required fix

Use an explicit policy:

- confirmed suspension: carry the last close with a stale flag;
- confirmed delisting/corporate action: terminal-value policy;
- unexplained missing execution price: reject order and fail after a small provider-gap tolerance.

## P1-4 — Walk-forward summaries allow test trade counts to influence status

Repository: `A_Share_Monitor`

The walk-forward summary status requires both minimum validation and minimum test trade counts. Test performance should not affect selection eligibility. Test sample size can be reported as diagnostic, but it should not choose or reject the model after the research design is frozen.

### Required fix

- Selection status: train + validation only.
- Test status: diagnostic adequacy only, never fed into strategy selection or parameter choice.

## P1-5 — “Alpha” is mislabelled

`alpha_vs_benchmark` is simply strategy total return minus benchmark total return. This is excess return, not regression alpha.

### Required fix

Rename to `excess_total_return`. Calculate alpha only if a regression with aligned periodic returns, beta, and risk-free rate is actually performed.

---

# 4. Repository disposition

## `quant-proj`

Decision: `SIMPLIFY`

Keep:

- one project roadmap;
- one authoritative repository registry;
- short architecture decisions;
- external-audit reports;
- explicit trading-boundary approvals.

Remove from routine work:

- mandatory raw-prompt preservation;
- one folder with spec/handoff/human-gate/context-delta/gate-manifest for every ordinary task;
- fixed callback UUIDs and model-role bindings;
- duplicate acceptance plus audit plus external audit for non-boundary changes;
- merge-ref, branch-head, integration-identity, and controlled-fixture jobs as five separate mandatory CI jobs.

Target routine flow:

```text
one GitHub issue
  -> one branch/PR
  -> focused CI
  -> one short result note
```

External audit should be reserved for:

- backtest-engine semantic changes;
- new data source/schema/PIT semantics;
- destructive database changes;
- a strategy reaching system intake;
- paper/live activation.

## `central-data-ingestion`

Decision: `REBUILD_MINIMAL`

Keep the risk invariants, not the current architecture.

## `market_data`

Decision: `SIMPLIFY_TO_READ_ONLY`

Keep:

- read-only central-store adapter;
- dataset catalog;
- small registry contracts.

Archive after extracting useful code:

- `central_warehouse.py` as a second writer;
- one-off A-share physical migration;
- provider-specific one-off warehouse logic.

## `quant_research_lab`

Decision: `KEEP_AND_HARDEN`

Make this the authoritative A-share research engine after:

- allocator state lag fix;
- packaging/clean-install CI;
- full snapshot replay;
- explicit missing-price policy.

Do not build another A-share engine.

## `A_Share_Monitor`

Decision: `SIMPLIFY_AND_DEPRECATE_DUPLICATE_RESEARCH`

Keep temporarily:

- verified market-specific adapters not yet moved to the central database;
- stable A-share fill/cost/tradability semantics;
- historical failure evidence.

Move or archive:

- duplicate strategy-search orchestration;
- candidate registry/report machinery superseded by R5;
- legacy data caches after central snapshot parity;
- divergent branch-only fixes after merging into one canonical branch.

## `US_Stock_Monitor`

Decision: `KEEP_AS_US_AUTHORITY`

This is the strongest current market-specific stack. Keep one US backtest/research engine here. Add real adjusted/total-return data and the missing-price policy. Do not create a second active US engine.

## `us_stock_30w`

Decision: `ARCHIVE_READ_ONLY`

Preserve forensic US31/US36/US41/US46 evidence. Do not maintain it as a second runtime or data source. Move frozen strategy specifications/tests into the authoritative US repository if needed.

## `strategy_work`

Decision: `ARCHIVE_AS_KNOWLEDGE_BASE`

Use as historical research memos/failure memory only. It should not be an execution engine, mandatory callback layer, or separate source of strategy truth.

## Data-room and shared-report repositories

Decision: `ARCHIVE_READ_ONLY`

Keep immutable evidence, but exclude them from routine code review, CI, and workflow dispatch.

---

# 5. Central database module decisions

## KEEP — after extraction into the minimal path

- natural-key definitions;
- schema/type/null/date/OHLC validation from `quality.py`;
- one writer lock;
- one atomic DuckDB transaction;
- idempotent natural-key insert/merge;
- conflict quarantine;
- source/retrieval/PIT metadata;
- post-write reopen, row-count, duplicate, null, date-range checks;
- credential file permissions and no-secret logging;
- read-only client from `market_data/adapters/central_store.py`.

## SIMPLIFY / REWRITE

- `collector.py`: provider request + normalization only; no SQLite control plane.
- `contracts.py`: typed table specs/natural keys, not multiple JSON authorities.
- `routine_append.py`: replace 1,159 lines with a bulk writer using a temporary DuckDB table and anti-join/merge.
- `routine_append_cli.py`: replace with the single central CLI.
- `tushare_replay.py`: reduce to a provider adapter returning normalized rows plus source metadata.
- `cli.py`: one command surface for ingest, validate, snapshot, and audit.
- schema initialization: one versioned migration module.

## ARCHIVE

- `publisher.py` and `publisher_cli.py` copy/swap path;
- `remediation.py` one-time foundation repair after its migration record is frozen;
- `a0_route_mechanics.py` after provider reachability has a simple integration test;
- `authorization.py` and `publish_authorization.py` custom one-use authorization system;
- old SQLite staging/control database code;
- systemd/environment deployment templates not used on the single WSL host;
- per-lane signed profiles, batches, HG records, and receipts;
- duplicated central writer in `market_data/central_warehouse.py` after useful logic is extracted.

## DELETE after one release of compatibility

- dead JSON schema variants;
- temporary bridge scripts after their logic is in the minimal writer;
- obsolete publisher manifests;
- duplicate CLIs;
- one-time converter drafts and test fixtures that are not on the accepted path.

---

# 6. Minimal central database architecture

## Physical design

One database:

```text
~/quant_data/quant.duckdb
```

Four schemas are sufficient:

```text
meta
raw_a
raw_us
feature
```

Alternative names are acceptable, but additional schemas require a concrete query-isolation or lifecycle reason.

## Minimal metadata tables

```text
meta.dataset
meta.ingest_run
meta.snapshot
meta.schema_version
```

`meta.ingest_run` should contain one row per command:

```text
run_id
source
dataset
started_at
finished_at
status
requested_range
fetched_rows
inserted_rows
noop_rows
rejected_rows
duplicate_count
null_count
min_date
max_date
snapshot_id
source_hash
error_summary
```

No chain of five JSON receipts is required.

## A-share tables

Only populate datasets needed by current research:

```text
raw_a.daily
raw_a.daily_basic
raw_a.adj_factor
raw_a.symbol_status
raw_a.trade_calendar
raw_a.industry_history
raw_a.fundamental_pit        # only when a live hypothesis needs it
raw_a.event_pit              # only when a live hypothesis needs it
```

## US tables

```text
raw_us.daily_adjusted
raw_us.corporate_action
raw_us.trade_calendar
raw_us.symbol_history
raw_us.membership_history
raw_us.fundamental_pit       # just-in-time
raw_us.macro_pit             # just-in-time
```

For the current roadmap, ingest in this order:

1. QQQ, GLD, SPY, TLT, HYG, LQD adjusted/total-return data and actions.
2. Sector ETFs only when breadth research reaches validation.
3. Equity fundamentals only when a preregistered strategy needs them.

Do not attempt to populate every imaginable A0–A6/U0–U6 dataset before research asks for it.

## Derived features

`feature` contains reproducible materialized features only. Each feature definition must have:

```text
source dataset snapshot
formula
lookback
minimum periods
available-at rule
code commit
```

Do not store undocumented columns.

## Minimal code structure

```text
central_data/
  db.py          # connection, lock, backup, transaction
  specs.py       # table specs and natural keys
  validate.py    # schema/null/date/duplicate/PIT checks
  cli.py         # one CLI
  ingest/
    tushare.py
    us_prices.py
    fundamentals.py   # only when required
```

Target size:

- 1,000–1,500 runtime lines;
- 400–700 focused test lines;
- one active writer API;
- one CLI.

The line target is a guardrail, not a quality substitute.

## Routine ingest algorithm

```text
fetch
  -> normalize to DataFrame/Arrow
  -> validate types, dates, natural keys and PIT labels
  -> acquire writer lock
  -> create the first backup of the day
  -> BEGIN
  -> register incoming rows in a temporary DuckDB table
  -> bulk anti-join INSERT or explicit revision MERGE
  -> postchecks
  -> COMMIT
  -> reopen read-only
  -> write one short run record
```

Do not:

- check each natural key in Python;
- insert each row in a Python loop;
- copy/hash the entire multi-GB DB for each profile;
- use SQLite as an intermediate control plane;
- require signatures for same-source/same-schema routine appends.

## Backup policy

- Always backup before schema changes, backfills, overwrites, or deletes.
- For routine append, make one backup on the first write of the day.
- Retain seven daily and four weekly backups.
- Verify at least one periodic restore.

## Snapshot policy

A snapshot is a logical dataset identity, not necessarily a full database copy:

```text
dataset + max available_at + row count + partition/content checksum + schema version
```

## When elevated review is required

Only for:

- new provider or credential path;
- natural-key/schema change;
- backfill, overwrite, or delete;
- revision/PIT/corporate-action semantics change;
- trading activation.

Routine same-source/same-schema append needs no independent model acceptance or external audit.

---

# 7. Anti-overdesign constraints

The following constraints should be adopted as an architecture decision:

1. One active central writer repository.
2. One active backtest engine per market; new engines require deprecating an old one.
3. One routine database CLI.
4. One run record per database command.
5. No custom cryptographic signing for local routine work.
6. No mandatory multi-agent acceptance for ordinary research/code changes.
7. No new process layer without a documented incident or concrete threat it mitigates.
8. No new module that duplicates an existing writer, engine, allocator, gate, or snapshot concept.
9. A central-DB PR adding more than roughly 250 net runtime lines must either delete comparable obsolete code or receive explicit user approval.
10. One provider/data source is added only when a current hypothesis or required maintenance task needs it.
11. CI is capped at two required PR jobs per runtime repository unless a demonstrated defect requires another.
12. One external audit at an actual decision boundary, not after every research batch.

---

# 8. Backtest and validation standard for approximately CNY 400,000

The project needs retail-professional reliability, not institutional bureaucracy.

## Non-negotiable correctness

1. Point-in-time signal, universe, fundamentals, membership, and event data.
2. Close-D signal executes at D+1 open or the next explicitly tradable bar.
3. No same-day regime allocation from close-D features to date-D returns.
4. A-share costs:
   - commission, including minimum commission if the broker contract has one;
   - sell stamp duty;
   - transfer fee where applicable;
   - 100-share lot size;
   - slippage;
   - suspension and locked limit rules.
5. US data uses adjusted/total-return semantics with dividends and splits documented.
6. Survivorship-aware universe or an explicit current-universe limitation.
7. Missing-price policy is explicit and tested.
8. Account identity and cash/holdings reconciliation pass every trade date.
9. Test data never selects formula, threshold, state map, or strategy winner.
10. Snapshot, config, code commit, and result are reproducible.

## Proportionate validation

### Cross-sectional stock strategies

- Aim for at least 50 closed trades overall.
- Aim for at least 20 validation-period closed trades.
- Use at least three rolling/expanding validation windows where history permits.
- Reject a result dominated by one year or one trade.

### Low-frequency ETF allocation

Trade counts alone are misleading. Require:

- at least 8–10 independent rebalance episodes;
- multiple market regimes, including at least one adverse episode;
- a frozen static benchmark;
- turnover and tax/cost reconciliation.

### Costs and capacity

For CNY 400,000, capacity is rarely the primary blocker in liquid A-shares, but it must be bounded:

- 10–20 positions;
- 5–10% target per symbol;
- trade size below a conservative fraction of 20-day median daily amount;
- base cost plus 2x cost stress;
- 5, 10, and 20 bps slippage scenarios where appropriate.

### Split discipline

```text
train: research and fitting
validation: choose/freeze
frozen test: use once after design freeze
forward observation: new data only
```

Repeatedly inspecting the same test period converts it into validation. Label it contaminated and establish a new forward start date.

## Useful robustness tests

Run these only for finalists, not every grid row:

- cost/slippage stress;
- parameter neighbourhood stability;
- universe sensitivity;
- 3–5 walk-forward windows;
- block bootstrap/permutation where statistically meaningful;
- benchmark and cash comparison;
- single-year and single-trade dependency.

## Unnecessary controls

The validation standard does not require:

- task-level Ed25519 authorization;
- model-routing UUIDs;
- signed packet chains;
- independent external audit for every rejected research batch;
- hundreds of variants or 500 resamples for every idea;
- production readiness terminology before a strategy survives validation.

---

# 9. How to accelerate strategy development

## Root causes of drag

1. Repeatedly rebuilding bespoke backtest engines.
2. Multiple repositories claiming strategy/data authority.
3. Database architecture work expanding ahead of actual hypothesis needs.
4. Repeated parameter replay in already-failed families.
5. Every batch producing extensive reports, callbacks, gates, and external audits.
6. Strategy research, engine validation, data maintenance, and workflow governance being mixed in the same cycle.

## New research loop

### Stage 1 — Hypothesis queue

Maintain at most 10 active hypotheses.

Each hypothesis has one page:

```text
premise
required fields
target market regime
formula
holding/rebalance rule
cost assumption
failure condition
frozen split
```

No task packet hierarchy.

### Stage 2 — Fast screen

- Vectorized or simplified causal screen.
- Maximum 24 fixed variants per family in one cycle.
- Train/validation only.
- Kill clearly negative, unstable, or cost-limited ideas.

### Stage 3 — Event-driven validation

Only the top one or two survivors enter the authoritative event engine.

Run:

- actual execution/costs;
- walk-forward;
- cost stress;
- capacity;
- benchmark;
- failure attribution.

### Stage 4 — Frozen test

Use the test period once after freezing.

### Stage 5 — Intake review

Only a strategy that survives enters a Strategy Intake Packet and one external audit.

## Research stopping rules

Stop a family when:

- two independent validation cycles are negative;
- cost stress destroys it;
- the same failure repeats under neighbouring parameters;
- the required data premise is absent;
- the edge depends on one episode or one trade.

Reopen only with materially new data or a new economic premise.

## Timebox

A normal research cycle should target:

- hypothesis and data check: hours, not days;
- fast screen: same day;
- full validation: one compute run;
- review: one pass;
- archive or advance.

The target is not to force a strategy to pass. The target is to reach a reliable yes/no quickly.

---

# 10. Three-phase implementation plan

## Phase 1 — Stop semantic leakage and freeze architecture growth

Before full strategy replay:

1. Fix R5 regime allocator one-session lag.
2. Fix A-share monthly/yearly metrics and alpha naming.
3. Make no-future/PIT missing state block positive labels.
4. Choose and merge one canonical A-share branch.
5. Fix R5 packaging and add one focused CI job.
6. Freeze new central-database modules, schemas, and all-lane ingestion expansion.

Exit condition:

```text
one trusted A-share engine
one trusted US engine
one canonical branch each
focused CI green
no open P0 semantic defects
```

## Phase 2 — Replace the central writer without interrupting data collection

1. Preserve the current DuckDB and backups read-only.
2. Implement the minimal writer beside the old system.
3. Prove parity on one A-share daily append and one US ETF append.
4. Run old and new paths in shadow for several updates.
5. Switch routine writes to the minimal path.
6. Archive publisher, SQLite, authorization, remediation, Replay qualification, duplicate warehouse writer, and unused deployment templates.

Exit condition:

```text
one command performs routine append end-to-end
one writer repo
one run record
rollback tested
```

## Phase 3 — Resume high-throughput research

1. Deliver only the minimum snapshots needed now:
   - A-share daily/basic/adjustment/status/industry;
   - US six core ETFs with adjusted/total-return semantics.
2. Run R5 full replay after the allocator fix.
3. Run the authoritative US engine.
4. Maintain a 10-hypothesis queue and one research PR per cycle.
5. Add data just in time when a preregistered idea requires it.

---

# 11. Immediate decisions

1. Amend the Manager’s “fill every dataset” backlog. Complete the safe foundation, but do not populate all A0–A6/U0–U6 lanes by default.
2. Prioritize only:
   - A-share `daily`, `daily_basic`, `adj_factor`, dated status/tradability, industry;
   - US QQQ/GLD/SPY/TLT/HYG/LQD adjusted data, calendar, and corporate actions.
3. Pause sector ETF, PIT fundamental, macro vintage, and event/fund-flow expansion until an active hypothesis needs them.
4. Do not deliver the central snapshot to R5 full replay until the regime allocator lag is fixed.
5. Do not promote any current strategy from this audit.

---

# 12. Final judgments

## Is the architecture too heavy?

Yes. It is disproportionate to the actual threat model and capital scale. The complexity is now a reliability risk because it hides the small number of controls that materially affect P&L correctness.

## Is the backtest standard appropriate?

Parts are strong, especially the US engine and the new R5 event-loop/accounting work. The overall stack is not yet trustworthy for strategy intake because of the R5 allocator lookahead, A-share metric defects, PIT fail-open behavior, branch divergence, and incomplete clean-install/CI proof.

## Is the strategy-development problem mainly a lack of strategies?

No. It is primarily a throughput and evidence-quality problem caused by duplicated engines, unstable data contracts, repeated audit/process loops, and overly broad database work.

## Should the central database be kept as-is?

No. Preserve the data and proven invariants, but rebuild the runtime minimally.

## Recommended final state

```text
quant-proj              lightweight roadmap/audit controller
central-data-ingestion  one minimal writer and provider adapters
market_data             read-only catalog/client only
quant_research_lab      authoritative A-share research engine
US_Stock_Monitor        authoritative US research engine
A_Share_Monitor         temporary adapters/legacy evidence, then reduced
us_stock_30w            archived forensic evidence
strategy_work           archived research knowledge/failure memory
```

`strategy_candidate_available=false`

No recommendation, ticket, broker/order/paper/live/auto activation, or product-route readiness is authorized by this audit.
