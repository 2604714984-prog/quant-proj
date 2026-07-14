# User-Dispatch Prompt — Codex A-Share R5 Critical Semantic Repair

Copy the fenced prompt into the independent user-controlled Codex A-share conversation.

```text
RUN CODEX_A_SHARE_R5_CRITICAL_SEMANTIC_REPAIR_AND_CANONICALIZATION_20260714

WORKSTREAM:
A_SHARE_RESEARCH_CODEX_USER_CONTROLLED_INDEPENDENT

AUTHORITATIVE AUDIT:
https://github.com/2604714984-prog/quant-proj/blob/f816e3c9bd92c274f34ecf901de02e4a914205a8/reports/external_audit/repository_wide_personal_quant_static_code_audit_20260714.md

PRIMARY R5 BASELINE:
repository: https://github.com/2604714984-prog/quant_research_lab
branch: codex/a-share-independent-research-takeover-r5-20260714
commit: d5e902af4beab6826ebc34c9a940b881f25ad750

LEGACY A-SHARE BASELINES TO RECONCILE:
repository: https://github.com/2604714984-prog/A_Share_Monitor
active-preservation baseline: 1a64e70873fc8a3c3d998e509cbcf690010ffef0
reviewed divergent main baseline: ab12cf99331a39a1396c7c7f885072a9f0f68c08

CONTROL
This A-share workstream remains independent and user-controlled. Quant Manager may track refs and
integration status but must not choose strategy winners, thresholds, formulas, or market conclusions.

MISSION
Repair every A-share semantic defect identified by the audit, establish one canonical A-share research
implementation, and prepare—not prematurely run—the full central-database replay.

The authoritative future engine is the existing R5 implementation in `quant_research_lab` after this
repair. Do not create another engine or another repository.

CURRENT BOUNDARY
research_only=true
system_intake_ready=false
strategy_candidate_available=false
full_replay_status=BLOCKED_UNTIL_CODE_FIX_AND_ACCEPTED_DB_CALLBACK

==================================================
ANTI-OVERDESIGN RULES
==================================================

1. Modify the existing R5 code. Do not create R6, a second event engine, a generic backtest framework,
   a plugin system, a DSL, a new registry, or a new report hierarchy.
2. Use one implementation branch per affected repository and one focused PR per repository.
3. Add only tests and code needed to close the listed findings.
4. Do not add a new database schema, writer, provider, or central-data orchestration path.
5. Do not write the production central database.
6. Do not add custom signatures, HG records, packet validators, model-routing controls, or external
   audit wrappers.
7. Limit new evidence to:
   - focused tests/JUnit;
   - one machine-readable quality-gate JSON;
   - one concise closeout Markdown.
8. Prefer deletion/replacement over a compatibility wrapper. No parallel old/new semantic path.
9. A net increase above roughly 500 runtime lines across this task requires stopping for explicit user
   approval. The expected repair should be substantially smaller.
10. Do not inspect held-out test results to choose a formula, parameter, threshold, state map, sleeve,
    or allocator.
11. Do not begin full replay until all code gates pass and an accepted immutable read-only DB callback
    is provided.

==================================================
PHASE 0 — VERIFY REFS AND CREATE REPAIR BRANCHES
==================================================

1. Fetch and verify the remote refs above.
2. If a newer remote commit exists, inspect it and record whether it supersedes any audited line.
   Never silently replace the audit baseline.
3. In `quant_research_lab`, create:
   `codex/a-share-r5-critical-semantic-repair-20260714`
4. In `A_Share_Monitor`, create one narrow branch from the Manager/user-selected canonical branch:
   `codex/a-share-canonical-semantic-repair-20260714`
5. Do not merge the divergent legacy branch automatically. Produce an explicit branch-difference note.

Required output:

```text
REF_STATUS=VERIFIED
R5_REPAIR_BRANCH=<branch>
LEGACY_REPAIR_BRANCH=<branch>
CANONICAL_LEGACY_BASE=<commit>
```

==================================================
PHASE 1 — FIX R5 REGIME-ALLOCATOR LOOKAHEAD
==================================================

AUDIT DEFECT
`src/a_share_research_r5/allocators.py` uses date-D regime state/probability to choose date-D weights
and then multiplies those weights by the date-D sleeve return. Because the state is built from date-D
features, this is same-day lookahead.

REQUIRED SEMANTICS

```text
state/probability observed at D close
 -> target decision dated D
 -> effective portfolio weights on D+1
 -> D return remains controlled by weights fixed no later than D-1
```

IMPLEMENTATION REQUIREMENTS

1. Make timing explicit. Dynamic allocator outputs must carry or be derivable from:
   - `decision_date`;
   - `effective_date`;
   - `state_lag_sessions=1`.
2. Use the previous trading session's confirmed state/probabilities for the current return row.
   Do not use an unqualified calendar-day shift.
3. The first dynamic-allocation return row must use the preregistered fallback, normally cash, unless a
   pre-sample state is explicitly supplied.
4. Static allocators may retain preregistered initial weights; dynamic allocators may not infer the
   first return from same-day state.
5. Costs and turnover must be charged when the effective weights change, not on the state observation
   date if that is a different date.
6. Preserve shared-capital accounting and realized-weight drift.
7. Do not change detector thresholds, GMM component candidates, hypothesis formulas, or state-to-sleeve
   mapping as part of this fix.

MANDATORY FAILING-BEFORE/PASSING-AFTER TESTS

A. SAME-DAY STATE MUTATION
Changing the date-D state/probabilities while keeping all prior information fixed must not change the
portfolio return recorded for D.

B. ALTERNATING-WINNER REPRODUCTION
Use two sleeves with alternating +10%/-10% returns and same-day states identifying the winner.
Prove:
- old/unlagged logic produces the artificial high path;
- repaired logic does not earn the same-day winner;
- expected lagged path matches the hand calculation.

C. EFFECTIVE-DATE TEST
Every dynamic allocation decision is effective strictly after its decision date.

D. COST-DATE TEST
Turnover/cost is charged on the effective allocation date.

E. MISSING-STATE TEST
A missing prior state activates the frozen fallback and does not forward-fill future information.

==================================================
PHASE 2 — PACKAGE AND CLEAN-INSTALL PROOF
==================================================

AUDIT DEFECT
`quant_research_lab/pyproject.toml` currently discovers `quant_lab*` and `paper_trader*`, not the new
R5 package under `src/a_share_research_r5`.

REQUIRED FIX

1. Adopt the smallest correct package-discovery change. Do not reorganize unrelated packages.
2. Build a wheel or sdist in a clean temporary environment.
3. Install the built artifact without relying on the repository working directory.
4. Prove:
   - `import a_share_research_r5` or the selected installed import path succeeds;
   - public R5 API imports succeed;
   - focused tests run against the installed package;
   - the CLI does not depend on accidental `src.` imports from the repository root.
5. Add one focused GitHub Actions job or integrate into one existing job:

```text
compile / Ruff
build package
clean install
focused R5 tests
bounded smoke
artifact schema/hash checks
```

Do not add branch-head, merge-ref, acceptance, or duplicate identity jobs.

==================================================
PHASE 3 — RECONCILE LEGACY A-SHARE SEMANTICS
==================================================

The future strategy engine remains R5. Apply only narrow semantic repairs to `A_Share_Monitor` so the
legacy repository cannot reintroduce false evidence while it is being reduced.

--------------------------------------------------
3A. MISSING-PRICE POLICY
--------------------------------------------------

The active preservation branch carries a prior mark; the reviewed divergent main branch values a held
symbol at zero. Establish one explicit policy:

1. Confirmed suspension/temporary halt:
   - carry the last valid close;
   - mark `price_stale=true` and record stale age;
   - do not treat the day as a -100% return.
2. Confirmed delisting or terminal corporate event:
   - apply an explicit terminal-value rule;
   - never confuse this with an ordinary provider gap.
3. Unexplained provider gap:
   - carry the last mark only within a small configured tolerance;
   - fail the research run when tolerance is exceeded;
   - expose the affected symbols/dates.
4. A held symbol with no prior valid mark must fail closed.

Add deterministic tests for all paths. Do not create a generic pricing service.

--------------------------------------------------
3B. MONTHLY/YEARLY RETURN METRICS
--------------------------------------------------

Replace first-observation-to-last-observation period returns with period-end boundary returns.

Required proof fixture:

```text
2023-12-29 equity 100
2024-01-02 equity 110
2024-01-31 equity 121
```

January return must be 21%, not 10%.

Apply the same rule to yearly returns. Verify monthly win rate, worst month, worst year, and
single-year-dependency inputs.

--------------------------------------------------
3C. EXCESS RETURN LABEL
--------------------------------------------------

Rename simple strategy-return minus benchmark-return output to `excess_total_return`.
Do not call it alpha. Preserve a deprecated alias only if an active consumer proves it is required;
otherwise remove it.

--------------------------------------------------
3D. PIT FAIL-OPEN
--------------------------------------------------

The chunked path must not return no-future PASS merely because `available_date` is absent.

Required classification:

- price-only rolling features with proven causal lineage: PASS or explicit bounded WARNING;
- fundamental/event/industry/membership/revisable data without availability time: BLOCKED/FAIL;
- unknown PIT status cannot produce a positive candidate or observation label.

Add tests for price-only, valid PIT, missing PIT, and future-dated availability.

--------------------------------------------------
3E. TEST SPLIT MUST NOT SELECT
--------------------------------------------------

Walk-forward/selection status must use train and validation only.
Test trade count and test performance may be reported as diagnostics but must not affect selection,
parameter stability, candidate labels, or winner ordering.

Add a mutation test: changing only test-period trades/returns must not change selection status or the
selected configuration.

==================================================
PHASE 4 — MINIMAL CENTRAL-DB INTAKE CONTRACT
==================================================

Do not access or write the production database during code repair.

Strengthen the R5 full-mode callback validator so it accepts only an immutable read-only A-share
snapshot contract containing at least:

```text
accepted=true
owner_repository
owner_commit
snapshot_id or dataset snapshot ids
database_path or read-only export path
database/source hash identities
schema version
required dataset list
row counts and date ranges
natural-key duplicate count=0
quality gate status=PASS
PIT/availability qualification per non-price dataset
export hashes where exports are used
read_only=true
```

Required datasets for the first full replay:

```text
daily
daily_basic/circ_mv
adj_factor
dated ST/suspension/limit/listing/delisting status
trade calendar
industry history where the frozen hypothesis requires it
```

Rules:

- open the database read-only;
- verify exact registered snapshot identities and required fields;
- do not require unrelated future datasets;
- do not hash the full multi-GB DB repeatedly if dataset-level immutable identities are sufficient;
- reject unknown or contradictory PIT labels;
- no central DB writes, repairs, migrations, or cache publication from this conversation.

Full mode remains blocked until the user/Manager supplies the accepted callback.

==================================================
PHASE 5 — FULL REPLAY AFTER ACCEPTED DB CALLBACK
==================================================

Execute this phase only after all prior gates pass and an accepted immutable DB callback is supplied.

1. Pin code commit, data snapshot, config, formulas, thresholds, state map, and split boundaries before
   reading held-out test results.
2. Run the frozen R5 hypotheses H1-H8/H11-H12 only. H9/H10 remain blocked unless the accepted snapshot
   contains the exact required direct evidence.
3. Use repaired D-to-D+1 timing for:
   - stock event loop;
   - regime allocators;
   - switching costs.
4. Use one shared-capital account.
5. Report train and validation first.
6. Freeze the survivor set and configuration.
7. Use the held-out test once.
8. Compare:
   - best frozen static strategy;
   - static sleeve allocation;
   - repaired soft allocation;
   - repaired hard allocation;
   - cash fallback.
9. Report costs, capacity, missing-price events, stale marks, turnover, drawdown, trade count, regime
   episode coverage, and failure attribution.
10. A valid outcome may be `NO_VALIDATED_A_SHARE_STRATEGY`. Do not force a positive result.

No recommendation or system-intake promotion is permitted by this prompt.

==================================================
FOCUSED TEST MATRIX
==================================================

Required test groups:

R5 TIMING
- D state mutation cannot alter D return;
- decision date < effective date;
- first dynamic row fallback;
- cost charged on effective date;
- no future state forward-fill.

EVENT LOOP/ACCOUNTING
- D signal does not alter D account;
- D+1 open fill;
- sells before buys;
- retained resize;
- cash/holdings reconciliation;
- no negative cash/holdings;
- rejection paths remain active.

LEGACY SEMANTICS
- suspension stale mark;
- terminal/delisting rule;
- unexplained gap tolerance and failure;
- monthly/yearly boundary returns;
- excess-return naming;
- PIT missing blocks;
- test-only mutation does not change selection.

PACKAGE
- wheel/sdist build;
- clean install;
- installed import;
- focused tests outside repo-root import path.

DB CONTRACT
- valid callback accepted;
- missing snapshot/hash/required dataset rejected;
- duplicate or PIT failure rejected;
- full mode remains blocked without callback;
- read-only access proven.

==================================================
ACCEPTANCE GATES
==================================================

CODE_ACCEPTANCE:
- old allocator reproduction is recorded;
- repaired allocator passes all lag tests;
- no formula/threshold/state-map selection change;
- R5 clean install passes;
- A-share legacy semantic tests pass;
- no test-period selection influence;
- no new engine or framework.

SCOPE_ACCEPTANCE:
- runtime net growth remains within the stated limit;
- no DB writer/provider/schema added;
- no new report/task hierarchy;
- obsolete conflicting code is removed or clearly deprecated.

FULL_REPLAY_ACCEPTANCE:
- accepted immutable callback verified;
- DB opened read-only;
- all required datasets present;
- code/config/data identities pinned;
- test read only after freeze;
- no recommendation or promotion claim.

==================================================
OUTPUTS
==================================================

In `quant_research_lab`, publish only:

```text
reports/codex_a_share_r5_repair/r5_critical_semantic_repair_closeout_20260714.md
reports/codex_a_share_r5_repair/r5_critical_semantic_repair_gate_20260714.json
reports/codex_a_share_r5_repair/r5_critical_semantic_repair_pytest_20260714.xml
```

In `A_Share_Monitor`, publish only one concise semantic-repair closeout and focused test evidence.
Do not commit generated market data, DB files, Parquet outputs, raw payloads, caches, or credentials.

Push both implementation branches and verify remote refs.

==================================================
CALLBACK 1 — CODE_REPAIR_COMPLETE
==================================================

BATCH: CODEX_A_SHARE_R5_CRITICAL_SEMANTIC_REPAIR_AND_CANONICALIZATION_20260714
STAGE: CODE_REPAIR_COMPLETE
STATUS:
R5_BRANCH:
R5_COMMIT:
R5_IMMUTABLE_COMMIT_URL:
LEGACY_BRANCH:
LEGACY_COMMIT:
LEGACY_IMMUTABLE_COMMIT_URL:
ALLOCATOR_LOOKAHEAD_REPRO_BEFORE_FIX:
ALLOCATOR_LAG_TEST_STATUS:
MONTHLY_YEARLY_METRICS_STATUS:
PIT_STATUS:
TEST_SELECTION_STATUS:
MISSING_PRICE_POLICY_STATUS:
PACKAGE_BUILD_STATUS:
CLEAN_INSTALL_STATUS:
FOCUSED_CI_URL:
RUNTIME_NET_LINE_DELTA:
FULL_REPLAY_STATUS: BLOCKED_WAITING_FOR_ACCEPTED_DB_CALLBACK
SYSTEM_INTAKE_READY: false
STRATEGY_CANDIDATE_AVAILABLE: false
FIXES_REQUIRED:
NEXT_ACTION:

==================================================
CALLBACK 2 — DB_CALLBACK_VERIFIED
==================================================

BATCH: CODEX_A_SHARE_R5_CRITICAL_SEMANTIC_REPAIR_AND_CANONICALIZATION_20260714
STAGE: DB_CALLBACK_VERIFIED
STATUS:
CALLBACK_PATH_OR_URL:
OWNER_COMMIT:
SNAPSHOT_IDS:
REQUIRED_DATASETS_PRESENT:
DUPLICATE_STATUS:
PIT_STATUS:
READ_ONLY_VERIFICATION:
FULL_REPLAY_AUTHORIZED_BY_CALLBACK:
FIXES_REQUIRED:
NEXT_ACTION:

==================================================
CALLBACK 3 — FULL_REPLAY_COMPLETE
==================================================

BATCH: CODEX_A_SHARE_R5_CRITICAL_SEMANTIC_REPAIR_AND_CANONICALIZATION_20260714
STAGE: FULL_REPLAY_COMPLETE
STATUS:
CODE_COMMIT:
DATA_SNAPSHOT_IDS:
CONFIG_HASH:
TRAIN_VALIDATION_FREEZE_STATUS:
TEST_SINGLE_USE_STATUS:
STATIC_RESULT:
SOFT_ALLOCATOR_RESULT:
HARD_ALLOCATOR_RESULT:
COST_CAPACITY_STATUS:
MISSING_PRICE_EVENT_COUNT:
VALIDATED_STRATEGY_COUNT:
SYSTEM_INTAKE_READY:
STRATEGY_CANDIDATE_AVAILABLE:
BOUNDARY_RESULT: RESEARCH_ONLY
FIXES_REQUIRED:
NEXT_ACTION:
```
