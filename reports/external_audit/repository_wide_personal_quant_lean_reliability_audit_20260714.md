# Repository-wide Personal Quant Lean Reliability Audit — 2026-07-14

## Verdict

- Whole project: `SIMPLIFY_NOW`
- Central database runtime: `REBUILD_MINIMAL_IN_PLACE`
- Backtest stack: `CONSOLIDATE_AND_REPAIR_BEFORE_PROMOTION`
- A-share R5 event engine: `CONDITIONALLY_KEEP`
- A-share R5 regime allocators: `REJECT_UNTIL_CAUSAL_LAG_FIX`
- `strategy_candidate_available=false`

## Scope

All accessible active first-party repositories were inventoried: `quant-proj`,
`central-data-ingestion`, `quant_research_lab`, `A_Share_Monitor`, `US_Stock_Monitor`,
`market_data`, `strategy_work`, and `us_stock_30w`. Evidence-only repositories were classified,
but generated reports were not treated as executable runtime. Archived `quant`/`qts` and upstream
FinGPT/RD-Agent forks are not current first-party runtime.

Risk-based line review covered code that can write data, determine point-in-time availability,
select strategies, simulate fills, apply costs, change account state, compute metrics, or promote
results. Bounded dynamic reproductions supplemented the static review.

Pinned primary heads:

- `central-data-ingestion@f2d401e42aa8f7cd17a14d94c039f45ba6546d9d`
- `quant-proj@0e90a2647a84010476470d83ebee017db7f5d20b`
- `quant_research_lab@d5e902af4beab6826ebc34c9a940b881f25ad750`

## Major findings

### P0 — Architecture is materially overbuilt

The central database repository has 19 production modules / 6,689 production lines and 3,425
test lines. It contains overlapping collection, staging, copy/swap publication, structural
remediation, routine append, Replay qualification, route mechanics, authorization and receipt
paths. This is disproportionate to one person, one WSL host, one DuckDB file and a research-only
project.

The first useful append needed two provider requests, one backup, one writer lock and one
transaction. The accepted Replay path retained zero rows, while the successful bridge was a
temporary script outside Git. Complexity reduced reproducibility.

Green CI proves that the implemented controls behave as tested. It does not prove that the controls
are needed.

### P0 — Multiple database writers and schema authorities

`central-data-ingestion` and `market_data/central_warehouse.py` both contain writer/migration logic.
SQLite staging, JSON profiles, JSON schemas, provider maps and DuckDB tables all partially define
data shape. The project needs one writer and one schema authority.

### P0 — R5 regime allocation has a one-bar look-ahead risk

The R5 allocator computes target weights from the current row and applies them to the same row's
sleeve returns. Soft allocation merges current-date probabilities with current-date returns; hard
allocation does the same with current-date confirmed state. A D-close state may only control D+1
returns.

A bounded four-observation reproduction produced +46.41% when current-day perfect-state weights were
applied to current-day returns, versus -27.10% when the same weights were lagged one observation.
This is illustrative, not a claim about real strategy performance. It proves the timing defect can
reverse a conclusion.

### P0 — Duplicate A-share engines

`A_Share_Monitor/qta` and `quant_research_lab/R5` both implement T+1 simulation, fills, costs,
tradability, strategies and validation. Maintaining both guarantees drift.

The qta engine is daily-causal, but its periodic rebalance fills only empty slots. It does not rotate
a full portfolio back to the current top-N ranking. That is valid for entry/hold/exit, but not for a
cross-sectional rotation strategy unless made an explicit engine mode.

### P0 — Validation is too permissive in one place and too institutional elsewhere

The A-share evaluator defaults to three trades. That cannot support a meaningful research or paper
observation label. At the opposite extreme, `strategy_work` includes DSR, CSCV-PBO, global lifetime
hash ledgers and frozen-holdout contracts. Those are useful for finalists, not every exploratory idea.

### P1 — Metric semantics need repair

Monthly grouping slices the first six characters of `trade_date`. ISO dates from January through
September collapse into `YYYY-0`; October through December into `YYYY-1`. Use parsed datetime
periods. Raw-close benchmark difference should be named `simple_excess_return`, not `alpha`, and
adjusted total-return benchmark data should be used where available.

## Dynamic reproductions

### Row-by-row versus bulk DuckDB append

Bounded in-memory test:

- 2,500 existing rows;
- 5,000 incoming rows, half already present;
- row-by-row SELECT plus INSERT: 5.3861 seconds;
- one registered incoming relation plus anti-join INSERT: 0.01647 seconds;
- same final row count;
- observed ratio: about 327x.

This is not a universal benchmark. It confirms that normal daily batches should be vectorized.

### Regime-allocation timing

A four-observation two-sleeve fixture produced +46.41% with current-row weights and -27.10% with
causal one-row-lag weights. The current R5 allocator must be shifted and retested.

## Repository disposition

| Repository | Action | Target responsibility |
|---|---|---|
| `quant-proj` | SIMPLIFY | roadmap, decisions, accepted callbacks, architecture records |
| `central-data-ingestion` | REBUILD MINIMAL IN PLACE | only authoritative ingestion and DuckDB writes |
| `quant_research_lab` | KEEP + FIX | sole active research/backtest codebase |
| `A_Share_Monitor` | SIMPLIFY, then archive duplicate research core | compatibility or future execution adapter only |
| `strategy_work` | merge useful statistics, then archive | finalist-only statistics inside research lab |
| `market_data` | merge read-only adapter; archive writer | tiny read-only client/registry |
| `US_Stock_Monitor` | extract PIT/SEC ingestion, then archive | ingestion moves to central data; research moves to lab |
| `us_stock_30w` | ARCHIVE | immutable negative evidence only |
| reports/vault/data-room repos | ARCHIVE EVIDENCE | no active orchestration |

## Central database runtime disposition

| Module/path | Action |
|---|---|
| `collector.py` | simplify to provider call + normalization handoff |
| `contracts.py` | keep one dataset contract; remove duplicate schema truth |
| `quality.py` | keep compact invariants |
| `storage.py` | archive SQLite staging path |
| `cli.py` | rewrite as one CLI: plan, ingest, verify, status |
| `routine_append.py` | replace row loops with one bulk MERGE/anti-join |
| `publisher.py` | archive copy/swap publisher |
| `publish_authorization.py` | remove custom local signature/HG runtime |
| `remediation.py` | archive one-time repair code |
| `tushare_replay.py` | merge useful adapter/normalizer into the one writer |
| A0 route/manifest tools | archive after migration evidence is pinned |
| systemd templates | archive until routine operation is stable |

## Lightweight central database design

```text
one DuckDB file
one writer lock
one Python package
one YAML dataset contract
one CLI
one ingest_runs table
one conflicts table
```

Schemas:

```text
meta     schema version, ingest runs, snapshots, conflicts
ref      calendars, instrument history, classification history
raw      bars, daily-basic, corporate actions, PIT fundamentals, events
feature  only durable reused features; most research features remain reproducible views/exports
```

Routine flow:

```text
provider -> DataFrame/Arrow -> normalize -> validate
-> writer lock -> one backup per run/day -> BEGIN
-> register incoming relation -> quarantine conflicting keys
-> bulk INSERT/MERGE -> one ingest_runs row -> COMMIT
-> count/date/null/duplicate/reopen checks -> short JSON result
```

Keep: mode-0600 secrets, one writer lock, transaction/rollback, natural-key idempotency,
conflict quarantine, PIT/lineage labels and post-write checks.

Do not use for ordinary appends: custom cryptography, per-batch grants, copy/swap publication,
multiple JSON receipts, model acceptance or independent external audit.

Escalate review only for a new source, schema/natural-key change, historical replacement,
destructive operation, database migration, or paper/live activation.

## Proportionate validation for approximately CNY 400,000

### Engine gate

Required after engine changes: causal D-close/D+1 timing, T+1 availability, lot rounding, fees,
price limits, suspension/ST/list/delist, adjusted data and exact account reconciliation.

### Fast research screen

Per family: preregister no more than 12 fixed variants, use train/validation, realistic costs,
and require at least 20 independent rebalance episodes or 30 closed trades. Do not use test for
selection. Do not run DSR/PBO here.

### Finalist validation

For at most two frozen variants: 3–5 walk-forward windows, 1.5x/2x cost stress, universe and
rebalance perturbation, block bootstrap/permutation appropriate to the horizon, and one untouched
diagnostic period. DSR/PBO is optional and only justified when many variants were actually tried.

Preregister practical personal-account constraints rather than optimize them: 8–20 positions,
5–12.5% per position, no more than 1% of average daily amount, and no leverage initially.

### Observation

Run 8–12 weeks of frozen shadow/paper observation. Parameter changes restart the observation clock.
Broker/paper/live integration requires a separate user authorization.

## Required code fixes

### R5

1. Shift soft/hard allocation decisions one session forward.
2. Add a test that D probabilities/states cannot earn D sleeve returns.
3. Document whether family sleeves are virtual independent portfolios or one stock-level account.
4. Rerun all smoke evidence after the timing fix.
5. Keep full replay blocked until the accepted database snapshot arrives.

### qta

1. Add explicit `ENTRY_HOLD_UNTIL_EXIT` and `PERIODIC_TARGET_REBALANCE` modes.
2. In target-rebalance mode, sell removed names and resize retained names.
3. Raise default validation sample requirements above three trades.
4. Parse dates before monthly grouping.
5. Rename simple benchmark difference and use adjusted benchmark data.
6. After R5 parity, keep only one active A-share engine.

### strategy_work

Keep DSR/PBO/HAC code, but move it behind a finalist-only command. It must not block ordinary
hypothesis development.

## Faster strategy workflow

```text
1. one hypothesis family
2. no more than 12 preregistered variants
3. vectorized train screen
4. at most 2 validation survivors
5. exact event-engine replay
6. cost + walk-forward + one robustness suite
7. continue / retire / blocked
8. external audit only before system intake or observation
```

One cycle produces one spec, one result table, one failure-memory row and one commit. Stop a family
after two failed cycles unless new direct data changes its premise.

## Migration sequence

1. Freeze new architecture layers.
2. Fix R5 allocator timing and rerun smoke.
3. Build a minimal bulk writer in shadow mode.
4. Compare old/new writer rows, keys and conflicts for bounded batches.
5. Move useful market-data and SEC/PIT code into the lean central writer.
6. Move advanced statistics into research lab.
7. Archive duplicate writers, CLIs, grants and evidence-only runtimes.
8. Resume one A-share and one US strategy family at a time.

## Complexity budget

- one active writer;
- one active research engine per execution model;
- no custom crypto for local routine work;
- no new repository without a real deployment boundary;
- no routine external audit;
- one spec and one result per research cycle;
- any new runtime path must replace an old one;
- central-ingestion runtime target: roughly 1,000–1,500 lines;
- focused central-ingestion tests target: roughly 400–600 lines;
- test count is not a success metric.

## Final judgment

The strongest minority view is that one operator needs more automation because no colleague will
catch mistakes. That is correct. The right controls are automatic and simple: lock, backup,
transaction, idempotency, lineage, postchecks and a frozen holdout.

The current project passed that optimum. Overlapping writers, an untracked bridge and repeated false
completion claims show that complexity itself is now a reliability risk.

Final decision: `SIMPLIFY_NOW`.
