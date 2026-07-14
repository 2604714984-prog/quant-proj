# User-Dispatch Prompt — Manager Project-Wide Remediation

Copy the fenced prompt into the user-controlled Quant Manager conversation.

```text
RUN MANAGER_PROJECT_WIDE_REMEDIATION_AND_MINIMALIZATION_20260714

AUTHORITATIVE AUDIT:
https://github.com/2604714984-prog/quant-proj/blob/f816e3c9bd92c274f34ecf901de02e4a914205a8/reports/external_audit/repository_wide_personal_quant_static_code_audit_20260714.md

EXISTING DB MINIMALIZATION TASK:
https://github.com/2604714984-prog/quant-proj/blob/a1482e71b13554d53906f4205c4825d2a85fcd5c/reports/agent_handoff/user_dispatch_manager_part1_central_db_minimalization_shadow_migration_prompt_20260714.md

This prompt AMENDS the existing database task. Do not restart or duplicate it.

MISSION
Resolve every material issue in the audit while making the project smaller and faster to maintain.
Judge all architecture against the real scope: one user, one WSL host, one DuckDB, research-only, and
approximately CNY 400,000 capital.

FROZEN VERDICTS
WHOLE_PROJECT_ARCHITECTURE=SIMPLIFY_NOW
CENTRAL_DATABASE=REBUILD_MINIMAL
BACKTEST_VALIDATION=CONDITIONALLY_USABLE_AFTER_CRITICAL_FIXES
STRATEGY_DEVELOPMENT=PROCESS_AND_ENGINE_BOTTLENECK
STRATEGY_CANDIDATE_AVAILABLE=false

TARGET OWNERSHIP
quant-proj              lightweight roadmap, status, decisions, audits
central-data-ingestion  only central-database writer and provider adapters
market_data             read-only catalog/client only
quant_research_lab      authoritative A-share research engine
US_Stock_Monitor        authoritative US research engine
A_Share_Monitor         temporary adapters and historical evidence, then reduced
us_stock_30w            archived forensic evidence
strategy_work           archived research knowledge/failure memory

ANTI-OVERDESIGN RULES
1. No new repository, writer, backtest engine, registry authority, signature format, receipt hierarchy,
   agent role, dispatcher layer, or acceptance layer.
2. One active writer repository and one active research engine per market.
3. Ordinary work uses one issue, one branch/PR, focused CI, and one short closeout.
4. Maximum two required PR jobs per runtime repository unless a reproduced defect requires another.
5. No new abstraction or framework without two existing active use cases.
6. No speculative data lane. Add data only for a current maintenance need or preregistered hypothesis.
7. Do not run a programme to fill every A0-A6/U0-U6 lane.
8. A central-data PR adding more than about 250 net runtime lines must delete comparable obsolete code
   or stop for explicit user approval.
9. A research fix must modify the selected authoritative engine, not create another engine.
10. Preserve history, but remove superseded paths from active imports, CLI, CI, and current docs.
11. External review is reserved for engine semantics, data/PIT/schema changes, destructive DB work,
    strategy intake, and any future execution-stage opening—not every routine task.
12. Any proposed scope expansion returns SCOPE_EXPANSION_REQUIRES_USER_APPROVAL.

CONTROLLER ARTIFACT LIMIT
Create or reuse one umbrella issue:
PROJECT_WIDE_REMEDIATION_AND_MINIMALIZATION_20260714

Create only:
reports/workspace_dispatch/project_wide_remediation_status_20260714.md
reports/workspace_dispatch/project_wide_remediation_board_20260714.csv
reports/architecture/project_ownership_and_deprecation_20260714.md

Do not create one task folder per finding.

PHASE 0 — PIN AND FREEZE
1. Verify current remote refs for every active repo. Keep audit refs immutable.
2. Pin exact implementation branches/commits.
3. Freeze new DB modules/schemas, engines, workflow layers, and speculative providers.
4. Select one canonical A_Share_Monitor branch; preserve other branches as evidence only.
5. Confirm the existing DB minimalization task continues unchanged except for the amendments below.

PHASE 1 — CLOSE SEMANTIC FINDINGS

A-SHARE
Dispatch the independent Codex A-share conversation with:
reports/agent_handoff/user_dispatch_codex_a_share_r5_critical_semantic_repair_prompt_20260714.md

It must close:
P0-1 R5 same-day regime state/probability applied to same-day sleeve returns
P0-2 divergent missing-price valuation behavior
P0-3 incorrect monthly/yearly return calculation
P0-4 missing PIT availability treated as PASS
P1-1 R5 omitted from package discovery
P1-2 no clean-install independent R5 CI
P1-4 test trade count affecting selection status
P1-5 excess total return mislabeled as alpha

Do not run R5 full central-DB replay until allocator timing and focused CI pass.

US
Create one narrow PR in US_Stock_Monitor:
- explicit policy for confirmed halt, confirmed delisting/action, and unexplained provider gap;
- deterministic tests for all three;
- reconfirm close-D signal to D+1 open;
- reconfirm train/validation-only selection;
- retain adjusted/total-return requirement for accepted real-data research;
- no new US engine or candidate framework.

CONTROLLER
Reduce ordinary flow to:
one issue -> one implementation PR -> focused CI -> short closeout

For routine work remove mandatory prompt inbox copies, per-task packet folders, fixed callback UUIDs,
model-route bindings, duplicate acceptance layers, and five separate identity-oriented CI jobs.
Keep elevated controls only for material data, engine, DB, strategy-intake, and execution-boundary work.
Do not delete historical audit evidence.

PHASE 2 — MINIMAL CENTRAL DATABASE AND ONE WRITER
Continue the active database task with these amendments:

central-data-ingestion = only writer
market_data = read-only client/catalog

Required runtime path:
provider adapter -> normalize -> validate -> one lock -> one backup when needed -> one set-based
DuckDB transaction -> postchecks -> one short run record

Required changes:
- extract useful bulk-ingest/audit logic from market_data/central_warehouse.py;
- archive that file as an active writer after parity;
- retain a small read-only central-store client;
- archive SQLite staging, copy/swap publisher, custom signatures, one-time remediation runtime,
  qualification-only Replay path, duplicate CLIs, duplicate receipt schemas, and unused deployment
  templates after parity;
- use set-based SQL, not per-row SELECT/INSERT;
- one logical snapshot identity, not a full DB copy per dataset/profile.

IMMEDIATE DATA SCOPE ONLY
A-share:
daily
daily_basic including circ_mv where available
adj_factor
dated ST/suspension/limit/listing/delisting status
trade calendar
industry history

US:
QQQ, GLD, SPY, TLT, HYG, LQD
adjusted/total-return daily data
corporate actions
trade calendar

PAUSE UNTIL AN ACTIVE HYPOTHESIS NEEDS THEM
sector ETF expansion
full PIT fundamentals
macro-vintage expansion
full event/fund-flow lanes
speculative completion of all historical data lanes

PHASE 3 — CANONICAL OWNERSHIP AND DEPRECATION
After semantic fixes and DB parity:
1. quant_research_lab is the A-share authority.
2. US_Stock_Monitor is the US authority.
3. A_Share_Monitor keeps only unmigrated adapters, required market-specific rules, and history.
4. market_data becomes read-only.
5. us_stock_30w becomes archived forensic evidence after any needed frozen specs/tests are copied.
6. strategy_work becomes an archived knowledge/failure-memory repository.
7. Data-room/shared-report repos are excluded from routine CI and dispatch.

Every deprecation record must state replacement owner, last active commit/tag, rollback/reference
location, and removed active imports/CLI/CI entries.

PHASE 4 — RESUME LIGHTWEIGHT RESEARCH
Research resumes only after all P0 findings are closed and the central snapshot contract is accepted
read-only.

Use:
maximum 10 active hypotheses
-> maximum 24 frozen variants per family for train/validation screen
-> only top 1-2 survivors enter the event engine
-> cost/capacity/walk-forward/benchmark checks
-> one frozen test use
-> one strategy-intake review only for a survivor

Archive a family after two independent negative validation cycles, repeated cost failure, or repeated
parameter-neighbourhood instability. Reopen only with materially new data or a new economic premise.

ACCEPTANCE GATES

SEMANTICS
- changing date-D regime state cannot change date-D allocator return;
- decision date and effective return date are explicit;
- missing-price tests cover halt, delisting/action, and unexplained gap;
- monthly/yearly returns use period-end boundaries;
- missing PIT availability cannot produce a positive PASS for revisable data;
- held-out test does not select thresholds, variants, family, or winner;
- simple excess return is not labelled alpha.

PACKAGING/CI
- R5 builds and installs in a clean environment;
- installed import and focused tests pass;
- no more than two required CI jobs;
- no new engine.

DATABASE
- one writer repository and one routine CLI;
- set-based writes;
- shadow row/key/value parity;
- rollback and backup restore pass;
- no temporary uncommitted bridge;
- no database, backup, raw payload, cache, or credential committed.

ARCHITECTURE
- ownership matrix published;
- duplicate writer/engine paths removed from active surface;
- ordinary controller flow reduced to issue/PR/CI/closeout;
- active modules/CLIs/CI jobs decrease, rather than being wrapped by another layer;
- no speculative data lanes.

STOP CONDITIONS
Stop and report a blocker if a task proposes a new repository, engine, writer, registry, signature,
orchestration layer, unsupported provider, test-based parameter choice, destructive DB action without
user approval, or complexity growth without equivalent deletion/deprecation.

GITHUB
Push all code, tests, concise evidence, and status changes. Verify each branch with:
git diff --check
git status --short --branch
git rev-parse HEAD
git push -u origin "$(git branch --show-current)"
git ls-remote origin "refs/heads/$(git branch --show-current)"

CALLBACK 1 — PROJECT_FREEZE
STATUS:
UMBRELLA_ISSUE_URL:
STATUS_BOARD_URL:
PINNED_REFS:
OWNERSHIP_DRAFT_URL:
DB_TASK_CONTINUED:
BLOCKERS:
NEXT_ACTION:

CALLBACK 2 — P0_CLOSED
STATUS:
A_SHARE_R5_COMMIT:
A_SHARE_R5_CI_URL:
ALLOCATOR_LAG_STATUS:
A_SHARE_METRICS_STATUS:
PIT_STATUS:
A_SHARE_CANONICAL_BRANCH:
US_MISSING_PRICE_STATUS:
OPEN_P0_FINDINGS:
NEXT_ACTION:

CALLBACK 3 — DATABASE_PARITY
STATUS:
CENTRAL_WRITER_COMMIT:
SHADOW_PARITY_URL:
ONE_WRITER_STATUS:
ONE_CLI_STATUS:
MARKET_DATA_READ_ONLY_STATUS:
ARCHIVED_ACTIVE_PATHS:
BACKUP_RESTORE_STATUS:
NEXT_ACTION:

CALLBACK 4 — PROJECT_CONSOLIDATED
STATUS:
FINAL_OWNERSHIP_URL:
ACTIVE_WRITER:
ACTIVE_A_SHARE_ENGINE:
ACTIVE_US_ENGINE:
ROUTINE_CONTROLLER_FLOW:
REQUIRED_CI_JOB_COUNTS:
ACTIVE_MODULE_REDUCTION:
MINIMUM_DATA_SCOPE_STATUS:
RESEARCH_RESUME_STATUS:
STRATEGY_CANDIDATE_AVAILABLE: false
FIXES_REQUIRED:
NEXT_ACTION:
```
