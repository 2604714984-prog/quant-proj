# Project-Wide Remediation Integrated External Audit — 2026-07-14

## Audit identity

This review reconciles the original repository-wide audit, the first Codex A-share repair, the two
Manager remediation rounds, and the six current ready-for-review implementation PRs.

It does **not** treat findings discovered after the original prompts as proof that the implementers
ignored their instructions. It distinguishes:

1. original prompt-defined findings that are now closed in code;
2. integration and packaging defects in the current PR set;
3. newly exposed full-replay blockers that were outside the first repair scope.

## Exact PR heads reviewed

| Repository / PR | Head commit | Review state |
|---|---|---|
| `quant-proj` PR #27 | `16054c55e8d83757960b10338063397a9f24dfaa` | open, non-draft, mergeable |
| `central-data-ingestion` PR #24 | `94326205df275ebc7490a1084d0849a9000bbdee` | open, non-draft, mergeable |
| `market_data` PR #5 | `47a6c6675fe0be173a5552461921d89ec6d60b09` | open, non-draft, mergeable |
| `quant_research_lab` PR #6 | `4e65fbe5889d6815a8454f80d1ea96ee0802c192` | open, non-draft, mergeable |
| `US_Stock_Monitor` PR #8 | `252fe19be632943389f31d025c2789aca452df74` | open, non-draft, mergeable |
| `A_Share_Monitor` PR #8 | `7951e0669609d7e0bfa8325d47b14f4b954750c9` | open, non-draft, mergeable into repair branch |

All six heads have a successful GitHub Actions run. Green CI is accepted as evidence for the checks
actually executed, not as proof of untested financial or packaging semantics.

## Overall verdict

```text
ORIGINAL_PROMPT_FINDINGS=SUBSTANTIALLY_CLOSED_IN_CODE
CURRENT_PR_SET=CHANGES_REQUIRED_BEFORE_INTEGRATED_ACCEPTANCE
PRODUCTION_DATABASE_CUTOVER=NOT_READY_NOT_AUTHORIZED
A_SHARE_FULL_REPLAY=BLOCKED
US_REAL_DATA_REPLAY=BLOCKED_ON_ACCEPTED_DATA
RESEARCH_RESUME=BLOCKED
SYSTEM_INTAKE_READY=false
STRATEGY_CANDIDATE_AVAILABLE=false
```

The Manager made real progress: the controller was materially simplified, the duplicate
`market_data` writer was removed, the original A-share semantic defects were repaired, and the US
missing-bar policy was substantially hardened. The remaining verdict is not “restart the project.”
It is a narrow request to correct several integration defects and newly exposed engine blockers
before the PRs are represented as project-wide closure.

---

# 1. Original audit findings — reconciled status

## Closed in current code

### R5 same-day regime lookahead

`quant_research_lab/src/a_share_research_r5/allocators.py@4e65fbe:L32-L47,L114-L167`

- close-D state/probability rows are mapped to the next actual session;
- the first dynamic row falls back rather than reading future state;
- decision/effective dates and one-session lag are emitted;
- cost is charged on the effective date;
- alternating-winner and same-day-mutation tests exist.

Status: `CLOSED_FOR_THE_CURRENT_SLEEVE_RETURN_INTERFACE`.

The full replay still has to prove that the return interval is executable; see Finding A3.

### Legacy A-share period returns, PIT fail-open, test selection, and excess-return name

`A_Share_Monitor` repair commits `a82ac7de...` and `7951e066...` contain:

- consecutive period-end monthly/yearly returns;
- missing revisable availability classified fail-closed;
- test counts/results diagnostic-only for selection;
- `excess_total_return` instead of false alpha naming;
- explicit suspension/delisting/unexplained-gap valuation policy.

Status: `CLOSED_ON_THE_SELECTED_REPAIR_LANE`.

Default-branch authority is not closed; see Finding A5.

### R5 package discovery and clean-install CI

`quant_research_lab/pyproject.toml@4e65fbe:L29-L32` includes `a_share_research_r5*`.
The PR CI builds a wheel, installs it in a clean environment, imports the installed package, runs the
focused suite, runs bounded smoke, and verifies artifact hashes.

Status: `CLOSED`.

### US unexplained-gap fail-closed semantics

`US_Stock_Monitor` now distinguishes available, confirmed halt, confirmed lifecycle/corporate action,
and unexplained provider gap. Unexplained gaps raise; confirmed gaps produce explicit no-fill or
valuation behavior.

Status: `SUBSTANTIALLY_CLOSED_WITH_ONE_PRECEDENCE_FIX_REQUIRED`; see Finding U1.

### Controller process simplification

`quant-proj` PR #27 genuinely reduces the active routine process to:

```text
one issue -> one branch/PR -> focused CI -> short closeout
```

The five-job controller workflow is reduced to one required job, model routing is marked historical,
and routine packet/UUID/duplicate-acceptance requirements are removed.

Status: `CLOSED_IN_IMPLEMENTATION`, subject to correcting overclaimed status records.

---

# 2. Merge-blocking findings

## D1 — P0 — The new minimal central writer is not packaged or exposed by the installed project

Repository: `central-data-ingestion` PR #24

Evidence:

- `pyproject.toml@943262:L16-L21` still exposes:
  - `central-data-ingestion = central_data_ingestion.cli:main`;
  - `central-data-publisher = central_data_ingestion.publisher_cli:main`;
  - package discovery only for `central_data_ingestion*`.
- The new implementation lives under top-level package `central_data/`.
- `central_data` is absent from package discovery and has no console entry point.
- The installed `central-data-ingestion` command still enters the legacy authorization / collector /
  SQLite-staging path in `central_data_ingestion/cli.py@943262:L13-L16,L40-L101`.
- CI installs editable mode and runs from the repository checkout, so imports of an unpackaged
  top-level directory can pass without proving wheel/install behavior.

Impact:

```text
ONE_MINIMAL_CLI_STATUS=false
MINIMAL_WRITER_INSTALLED_RUNTIME_STATUS=false
LEGACY_ACTIVE_PATH_REMOVED=false
```

The PR currently adds a tested source-tree shadow implementation but does not make it the installed
shadow command. The controller's “one writer / one CLI” statements are therefore premature.

Deterministic reproduction procedure:

```bash
python -m build
python -m venv /tmp/central-clean
/tmp/central-clean/bin/pip install dist/*.whl
cd /tmp
/tmp/central-clean/bin/python -c 'import central_data'
central-data-ingestion --help
```

Under the reviewed package-discovery contract, `central_data` is excluded and the console command
resolves to the legacy CLI.

Required narrow correction:

1. Include `central_data*` in the built distribution.
2. Add a clearly named temporary shadow entry point, or replace the routine entry point only at an
   explicitly approved cutover.
3. Keep the legacy command labelled `LEGACY_ACTIVE_DURING_SHADOW_MIGRATION` until cutover; do not call
   the state “one CLI” yet.
4. Add clean-wheel install/import/CLI tests outside the repository root.
5. At approved cutover, remove the old publisher and staging console entries from active packaging.

Do not create a third package or another orchestration layer.

## D2 — P0 — The central writer is not yet an end-to-end operational provider-to-database command

Repository: `central-data-ingestion` PR #24

`central_data/cli.py@943262:L18-L41` accepts a prebuilt JSON rows file. It does not call the Replay
adapter. The adapter-to-writer test invokes Python functions directly, and the real adapter does not
enrich ordinary provider rows with the `source` / `available_at` metadata commonly required by the
writer config.

Impact:

A human or temporary script is still required between provider response and the CLI rows file. This
recreates the prior “formal route plus uncommitted bridge” risk unless a committed adapter runner is
provided.

Required narrow correction:

- add one `fetch-append` subcommand to the same minimal CLI, or one committed dataset-specific command
  that calls adapter -> metadata enrichment -> normalize -> validate -> append;
- compute `source_sha256` from the actual response/file inside the command rather than trusting a
  caller-supplied unrelated value;
- retain `--execute-network` and dry-run-by-default behavior;
- prove the installed CLI path with a mocked transport integration test.

## D3 — P1 / cutover blocker — Backup semantics still perform a full copy per run and do not prove a
closed/checkpointed production DuckDB

Repository: `central-data-ingestion` PR #24

`central_data/backup.py@943262:L61-L78` includes a run-id-derived suffix in each recovery-point name,
and `append_batch()` always supplies `run_id`. Multiple routine dataset appends can therefore hash and
copy the full multi-GB database multiple times per day.

The backup copies the database file descriptor directly. The focused tests use closed temporary DBs;
they do not prove a safe backup when an existing DuckDB writer/WAL is active. The new sidecar lock also
cannot coordinate old writer paths until those paths use the same lock or are stopped.

Required before production cutover:

- choose one reusable first-write-of-day backup for routine increments, with per-run backup reserved
  for elevated work; or document why one run per day is guaranteed;
- stop all legacy writers for cutover;
- run `CHECKPOINT`, close the write connection, copy, then reopen/restore-test the copied DB;
- add an actual DuckDB open/query restore test, not only byte restoration;
- run read-only production preflight against real table/meta schemas and file permissions.

## D4 — P1 — Central metadata writes rely on positional table order

Repository: `central-data-ingestion` PR #24

`central_data/writer.py@943262:L412-L424` inserts into `meta.ingest_runs` using `INSERT ... VALUES`
without an explicit column list, while preflight checks only a subset of required names and not exact
column order/types.

Required correction:

- use an explicit target column list;
- validate required column types or introduce a narrow compatibility mapping;
- require natural-key fields to be non-null in both config schema and existing target data.

## A1 — P0 / full-replay blocker — R5 still values missing held prices at zero

Repository: `quant_research_lab` PR #6

`src/a_share_research_r5/event_loop.py@4e65fbe:L51-L57` computes:

```python
prices.get(symbol, 0.0)
```

for every held symbol. The same method is used for execution-price reconciliation and daily close
valuation. Holdings evidence also uses zero for absent closes at lines 254-259.

Minimal reproduction:

```text
holding = 10,000 shares
last accepted close = CNY 10
current close row absent
current market value = 0
artificial one-day loss = 100%
```

Reconciliation can still pass because both sides use the same incorrect zero mark. The focused R5
tests do not contain a missing-held-price case.

Required narrow correction in the existing engine:

- track last accepted mark and dated status;
- confirmed suspension: carry last accepted mark with stale evidence;
- explicit terminal event: apply a frozen terminal-value rule;
- unexplained gap: fail closed after a very small tolerance;
- no prior mark: fail immediately;
- add failure-sensitive tests for open and close valuation.

Do not build R6 or a generic pricing service.

## A2 — P0 / account-realism blocker — R5 has no maximum holding count and defaults to CNY 1,000,000

Repository: `quant_research_lab` PR #6

Evidence:

- `EngineConfig.initial_cash = 1_000_000` and has no `max_positions` in
  `src/a_share_research_r5/config.py@4e65fbe:L17-L23`.
- Every hypothesis uses a 20% bucket in `signals.py@4e65fbe:L90-L145`.
- `event_loop.py@4e65fbe:L161-L211,L236-L252` equal-weights every selected target without a position
  cap.

For illustration, if 2,400 liquid names survive the universe filter, a 20% bucket is 480 holdings.
At CNY 400,000 this is CNY 833 per theoretical holding before fees, so a 100-share lot is possible only
below CNY 8.33. The backtest then acquires a strong low-price / zero-share bias.

Required correction before real replay:

- treat the top quantile as a candidate pool, not the final portfolio;
- preregister and enforce a realistic 10-20 position cap;
- run with the actual deployable A-share capital allocation, with 400k as the current whole-project
  reference unless the user supplies a different market split;
- preserve 100-share lots and report unfilled theoretical targets;
- add minimum-commission and applicable fee semantics or import the accepted legacy cost spec;
- add capital-sensitivity runs, not a new position-sizing framework.

## A3 — P0 for strategy-switching claims — The repaired sleeve allocator still lacks executable
return-interval proof and stock-level shared-capital accounting

Repository: `quant_research_lab` PR #6

The one-session lag correctly removes the audited same-day state leak. However:

- each hypothesis first runs an independent full-capital stock account;
- `specialists.py@4e65fbe:L8-L16` converts independent equity curves to returns and averages them by
  family;
- the allocator then trades those family return series, rather than netting underlying stock targets
  in one account.

A close-D decision applied to a D+1 close-to-close sleeve return also includes the overnight move from
D close to D+1 open, which was not executable after the close-D signal.

Consequences:

- overlapping holdings are not netted;
- lot rounding and minimum commissions are not applied at combined-account level;
- stock concentration is not measured at combined level;
- sleeve-level costs can be added on top of costs already paid inside independent strategy engines;
- the first overnight segment can be credited before the D+1-open rebalance.

Required resolution before a switching strategy can become evidence:

1. preferred: aggregate sleeve stock target weights and execute net orders in one EventLoopEngine
   account; or
2. bounded alternative: keep the current allocator as `DIAGNOSTIC_FUND_OF_FUNDS_APPROXIMATION`, exclude
   it from system-intake gates, and validate only the static stock-level strategy until a holdings-level
   allocator exists.

Do not add a second engine.

## A4 — P1 — R5 metric labelled Sharpe is CAGR divided by volatility

Repository: `quant_research_lab` PR #6

`src/a_share_research_r5/metrics.py@4e65fbe:L9-L23` computes annualized CAGR and divides it by annualized
volatility. That is not the usual annualized mean excess return divided by return volatility.

Required correction:

- calculate standard daily-return Sharpe (with an explicitly frozen risk-free convention), or
- rename the field `cagr_to_volatility`.

Cross-engine Sharpe comparisons are invalid until this is corrected.

## A5 — P0 integration blocker — Legacy A-share PR #8 does not update the default branch

Repository: `A_Share_Monitor` PR #8

The PIT repair itself is narrow and valid, but the PR base is
`codex/a-share-canonical-semantic-repair-20260714`, not default `main`. Default
`main@ab12cf99331a39a1396c7c7f885072a9f0f68c08` remains divergent.

Merging PR #8 closes the repair lane only. It does not make the default execution path safe or
canonical.

Required Manager decision:

- merge PR #8 into the repair lane;
- then either create one explicit repair-lane-to-main reconciliation PR, change the default branch to
  the accepted repair line, or disable all research execution from legacy main while QRL takes over;
- tag the displaced branch and verify no safety fix is lost.

The project board must not report canonical A-share closure before this happens.

## U1 — P1 — Confirmed halt has execution precedence but not valuation precedence when a valid price is
present

Repository: `US_Stock_Monitor` PR #8

`fill_model.py` correctly checks `trading_halt` before accepting a valid execution price. In contrast,
`gap_policy.classify_bar()` returns `AVAILABLE` whenever the price is positive before checking action
types. `resolve_held_valuation()` delegates to that order.

Therefore a provider's stale or indicative positive price on a confirmed halt day can revalue a held
position instead of carrying the last accepted adjusted close, contradicting the PR's stated policy.

Existing tests cover:

- valid execution price plus halt -> no fill;
- missing price plus halt -> prior mark valuation.

They do not cover valid price plus halt for held valuation.

Required narrow correction:

- in `resolve_held_valuation`, give explicit `trading_halt` identity precedence over current price;
- add a held-position test with a changed positive bar plus confirmed halt and assert the previous
  accepted adjusted mark is retained;
- decide explicitly whether terminal lifecycle identity also takes precedence over a positive but
  non-action-complete mark.

## C1 — P0 reporting/integration blocker — Controller status overclaims closure and contains stale refs

Repository: `quant-proj` PR #27

The simplification code is good, but the status/ownership records currently state:

- one installed central writer/CLI;
- old publisher/SQLite paths removed from active surface;
- zero open P0 code findings;
- PR #27 head `14dcee...` in several files.

The actual reviewed PR head is `16054c55...`. The central packaging facts and the R5/default-branch
findings above contradict the stronger closure claims.

Required correction:

- distinguish `ORIGINAL_AUDIT_FINDINGS_CLOSED_IN_REPAIR_BRANCHES` from
  `FULL_REPLAY_AND_CUTOVER_BLOCKERS_OPEN`;
- change central status to `MINIMAL_SOURCE_PATH_IMPLEMENTED_SHADOW_ENTRYPOINT_NOT_YET_ACCEPTED` until
  D1/D2 are fixed;
- update every exact PR head;
- list A1-A5 and U1 in the board;
- retain `RESEARCH_RESUME=BLOCKED` and `strategy_candidate_available=false`.

## C2 — P2 — Historical agent registry still looks operational

Repository: `quant-proj` PR #27

`registry/model_routing.yaml` is correctly marked historical/advisory. `registry/agents.yaml` still
contains a large active-looking role graph and permission model.

Required small cleanup:

- add an unmistakable top-level `status: HISTORICAL_REFERENCE_ONLY`, or move the file under a historical
  registry directory;
- make the lightweight `AGENTS.md` and issue/PR runbook the sole active routine authority.

## R1 — P2 — Generated smoke Parquet/CSV outputs remain committed in the canonical A-share PR

Repository: `quant_research_lab` PR #6

The PR includes a large `reports/runops/a_share_r5` output set, and `.gitignore` intentionally allows
those generated outputs. This conflicts with the newly adopted rule against committing generated
outputs and makes future code review noisy.

Required cleanup:

- keep concise closeout, JSON gate, JUnit, and a small manifest;
- publish bulk Parquet/large CSV smoke artifacts as GitHub Actions artifacts or a tagged evidence
  release, not normal source history;
- do not delete immutable historical evidence already relied on without recording its replacement.

---

# 3. PR-specific verdicts

## `quant-proj` PR #27

```text
VERDICT=REQUEST_CHANGES
```

Reason: real simplification is accepted, but exact refs and closure states are inaccurate and depend on
unaccepted source PRs.

## `central-data-ingestion` PR #24

```text
VERDICT=REQUEST_CHANGES
```

Reason: the new writer is source-tree tested but not packaged or exposed; the installed commands still
point to the legacy runtime; provider-to-write CLI and production-safe backup/preflight evidence are
incomplete.

## `market_data` PR #5

```text
VERDICT=ACCEPT_WITH_MERGE_SEQUENCE
```

Reason: the duplicate writer is genuinely removed and the retained client is read-only. Merge after a
fixed/installable central shadow writer is accepted, so the workspace does not temporarily lose the
intended replacement path.

No new framework is requested. The remaining large legacy catalog may be frozen and simplified later
only when a current reader needs it.

## `quant_research_lab` PR #6

```text
VERDICT=REQUEST_CHANGES_BEFORE_CANONICAL_ENGINE_MERGE
```

Reason: the original instructed repairs are valid, but zero-price held valuation and unbounded 20%
portfolio construction are critical for the intended sole A-share engine. The sleeve allocator must be
bounded to diagnostic-only or converted to stock-level execution before any switching claim.

## `US_Stock_Monitor` PR #8

```text
VERDICT=REQUEST_ONE_BOUNDED_SEMANTIC_FIX
```

Reason: strong implementation, but confirmed-halt valuation precedence is missing for a positive
stale/indicative bar.

## `A_Share_Monitor` PR #8

```text
VERDICT=ACCEPT_SCOPED_REPAIR_LANE_ONLY
```

Reason: the PIT follow-up is valid for its base branch. It does not close default-branch authority.
A separate canonicalization/deactivation decision is required.

---

# 4. Corrected project state

```text
PROJECT_FREEZE=PASS
CONTROLLER_SIMPLIFICATION=PASS_CODE_PENDING_STATUS_CORRECTION
ORIGINAL_R5_ALLOCATOR_LAG_FIX=PASS
ORIGINAL_LEGACY_A_SHARE_SEMANTIC_FIXES=PASS_ON_REPAIR_LANE
US_GAP_POLICY=PASS_AFTER_ONE_PRECEDENCE_FIX
MARKET_DATA_READ_ONLY=PASS_PENDING_SEQUENCE
CENTRAL_MINIMAL_WRITER_SOURCE=PASS
CENTRAL_MINIMAL_WRITER_INSTALLED_RUNTIME=FAIL
CENTRAL_PRODUCTION_CUTOVER=NOT_READY_NOT_AUTHORIZED
A_SHARE_CANONICAL_ENGINE=NOT_READY
A_SHARE_DEFAULT_BRANCH_CANONICALIZATION=OPEN
R5_FULL_REPLAY=BLOCKED
RESEARCH_RESUME=BLOCKED
STRATEGY_CANDIDATE_AVAILABLE=false
```

---

# 5. Minimum rework plan — no space for another redesign

## Patch Set 1 — central writer activation

Allowed files only unless a reproduced test proves otherwise:

```text
pyproject.toml
central_data/cli.py
central_data/adapters/tushare.py
central_data/backup.py
central_data/writer.py
central_data/postcheck.py
tests/test_minimal_writer.py
CI workflow
```

Deliver:

- installable `central_data` package;
- one installed shadow CLI;
- mocked provider-to-writer CLI test;
- explicit metadata provenance;
- reusable daily routine backup or elevated per-run policy;
- checkpoint/closed-copy restore proof;
- explicit metadata insert columns;
- production read-only preflight command.

Forbidden:

- new repository;
- new writer package;
- another config/receipt/HG/signature system;
- production cutover.

## Patch Set 2 — R5 full-replay readiness

Allowed existing R5 files only:

```text
config.py
event_loop.py
accounting.py
metrics.py
signals.py
specialists.py
allocators.py
scripts/run_a_share_research_r5.py
focused R5 tests
```

Deliver:

- explicit missing-mark policy;
- 400k/account-allocation config input;
- 10-20 position cap and lot-aware candidate-to-portfolio conversion;
- accepted A-share fee semantics including minimum commission where applicable;
- standard Sharpe or corrected metric name;
- allocator labelled diagnostic-only unless stock-level net execution is implemented;
- no full replay yet.

Forbidden:

- R6;
- new generic engine;
- parameter/formula/state-map changes;
- test-result selection;
- new strategy family.

## Patch Set 3 — US halt precedence

Allowed scope:

```text
usq/backtest/gap_policy.py
tests/test_execution_gap_policy.py
```

Deliver one precedence fix and one regression test. No broader US refactor.

## Patch Set 4 — canonical legacy and controller truth

Manager performs:

- merge repair-lane PIT PR;
- one explicit default-branch reconciliation or deactivation decision;
- update controller board/status/ownership refs and findings;
- mark agent registry historical;
- remove generated R5 bulk artifacts from the source PR or relocate them to CI artifacts;
- request one final external re-review of exact new heads.

---

# 6. Merge and cutover sequence

After the bounded fixes pass:

```text
1. external re-review exact fixed heads
2. merge fixed central-data-ingestion PR #24
3. merge market_data read-only PR #5
4. merge fixed US_Stock_Monitor PR #8
5. merge fixed quant_research_lab PR #6
6. merge A_Share repair-lane PR #8
7. complete explicit A_Share default-branch reconciliation/deactivation
8. update and merge quant-proj PR #27 last
9. perform production DB preflight and shadow runs
10. request separate owner approval for production writer cutover
11. externally audit immutable DB callback
12. issue a fresh R5 full-replay prompt
```

Production cutover must not be combined with these code merges.

---

# 7. Boundary result

```text
BOUNDARY_RESULT=PASS_RESEARCH_ONLY
RECOMMENDATION_ALLOWED=false
STRATEGY_PROMOTION_ALLOWED=false
BROKER_ORDER_PAPER_LIVE_AUTO=false
```

A valid next outcome is still `NO_VALIDATED_STRATEGY`. The purpose of the remaining work is to make
that answer trustworthy, not to force a positive strategy result.
