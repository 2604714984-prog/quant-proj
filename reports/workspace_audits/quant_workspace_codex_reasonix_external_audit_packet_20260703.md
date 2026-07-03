# Quant Workspace Codex + Reasonix Collaboration / Migration External Audit Packet

Date: 2026-07-03
Prepared from workspace: `/Users/rongyuxu/Desktop/quant proj`
Status: READY_FOR_EXTERNAL_REVIEW / PLANNING_ONLY / LOCAL_GIT_CHECKPOINT_READY

## External Reviewer Request

Please review this as a workspace architecture, agent-collaboration, and migration-readiness packet.

This is not a trading-system approval, not a recommendation-runtime approval, not a broker/order/live-trading approval, and not a final third-party verdict by Codex.

Requested external audit questions:

1. Is the proposed "controller workspace first, no physical merge yet" decision appropriate?
2. Are the migration blockers correctly identified?
3. Is the Codex CLI / Reasonix CLI role split safe and operationally useful?
4. Are audit boundaries, data boundaries, and no-trading boundaries explicit enough?
5. What must be fixed before any physical migration into `/Users/rongyuxu/Desktop/quant proj`?

## Scope Reviewed

In scope:

- The new controller workspace under `/Users/rongyuxu/Desktop/quant proj`.
- Existing local project roots:
  - `/Users/rongyuxu/Desktop/A_Share_Monitor`
  - `/Users/rongyuxu/Desktop/US_Stock_Monitor`
  - `/Users/rongyuxu/Desktop/market_data`
  - `/Users/rongyuxu/Desktop/strategy_work`
- Current Git states, current latest commits/trees, and dirty-file risk.
- Current local DuckDB row-count/readiness facts from read-only inspection.
- Proposed Codex CLI + Reasonix CLI collaboration model.
- Proposed staged migration plan.

Out of scope:

- Strategy alpha validation.
- Recommendation quality.
- Any buy/sell decision.
- Broker integration.
- Order routing.
- Manual-fill runtime activation.
- Paper trading or live trading.
- Full source-code audit of every project.
- Full data-quality audit of all raw rows.

## Packet Evidence Files

Workspace-local files created for review:

- `README.md`
- `AGENTS.md`
- `QUANT_WORKSPACE_CODEX_REASONIX_PLAN.md`
- `registry/projects.yaml`
- `prompts/reasonix_advisory_review.md`
- `prompts/reasonix_db_maintainer.md`
- `prompts/reasonix_strategy_researcher.md`
- `runbooks/migration.md`
- `runbooks/task_dispatch.md`
- `reports/workspace_audits/quant_workspace_codex_reasonix_external_audit_packet_20260703.md`
- `reports/workspace_audits/multi_agent_architecture_prior_plan_review_20260703.md`
- `reports/workspace_audits/dispatcher_agent_addendum_20260703.md`
- `reports/workspace_audits/reasonix_role_split_addendum_20260704.md`
- `reports/workspace_audits/quant_workspace_file_audit_20260703.md`
- `reports/workspace_audits/quant_workspace_file_audit_findings_20260703.json`
- `.gitignore`

Prior reference reviewed but not adopted directly:

- `/Users/rongyuxu/Desktop/multi_agent_architecture_plan.md`

No raw DuckDB, parquet, SQLite, `.env`, zip, or API-key artifact was copied into this workspace.

## Source Audit Point

This workspace is being checkpointed as a local Git repository for reproducibility. It is still not a GitHub-published packet unless a remote is later configured and pushed.

Workspace Git audit point:

- local repo: `/Users/rongyuxu/Desktop/quant proj`
- branch: `main`
- tag: `quant-workspace-controller-audit-20260703`
- packet entry path: `reports/workspace_audits/quant_workspace_codex_reasonix_external_audit_packet_20260703.md`
- handoff path: `reports/agent_handoff/quant_workspace_external_audit_handoff_20260703.md`

The external reviewer should still treat the source project states as local evidence that should be rechecked before any formal migration or publication step.

Existing repo audit points observed:

| Project | Branch | Commit | Tree | Working tree |
|---|---|---|---|---|
| A_Share_Monitor | `codex/harden-a-share-research-pipeline` | `02346fda47baee7eeefcfcb1fb8449862629f018` | `d4138ad3d8a5ad8a55ec2353212231f1a4fb733e` | dirty |
| US_Stock_Monitor | `codex/duckdb-provider` | `88c0834184c2552a98c263e7e01b03f13164b448` | `758e9e436a729eb4be0f93ab5b00e11d93ce4c84` | dirty |
| market_data | `main` | `4483fda1ac17678735b2f8721449f347f206e9a6` | `4cd9416a8f2c426180955011b98ec520a0d04bd8` | dirty |
| strategy_work | `main` | `0ae165063020662c0f428579aa6470896dba23c2` | `26e6fe6107209fa93dcf4dd6e3addc34b616916b` | dirty |

## Current Workspace Decision

Recommended decision:

Use `/Users/rongyuxu/Desktop/quant proj` as a controller workspace first. Do not physically move or merge the existing repos yet.

The prior desktop proposal `multi_agent_architecture_plan.md` is useful as an architecture reference, but it is not the current implementation plan. It is broader, more automation-heavy, and contains stale assumptions about project stages, model/tool names, and ChatGPT browser automation. The current packet intentionally chooses a smaller controller-workspace path first.

Rationale:

- Three core repos have dirty working trees.
- `strategy_work` has a new untracked config file, now recorded as a migration deferral rather than a clean first-migration candidate.
- Existing stage packets rely on repo-specific branches, tags, commits, tree hashes, and reports.
- Several registry/report files still use absolute paths under `/Users/rongyuxu/Desktop/...`.
- Physical DuckDB/parquet/cache files are intentionally ignored and should not be copied into a planning workspace.
- `market_data/catalog/market_data_registry.yaml` currently states `physical_db_migration_allowed: false`.
- Current DB facts have drifted from older documentation, so registry refresh must precede migration.

## Tooling State

Observed local tools:

- Codex CLI: `/Applications/Codex.app/Contents/Resources/codex`, version `codex-cli 0.142.5`.
- Reasonix CLI: `/Users/rongyuxu/.local/bin/reasonix`, version `reasonix 0.53.2`.

Proposed role split:

| Tool / Role | Allowed use | Not allowed |
|---|---|---|
| Codex-Dev | Implementation, integration, tests, delivery reports, fix responses, controlled Git work | Secret leakage, trading enablement, deleting tests to pass |
| Reasonix-DB | DS-backed database diagnostics, schema/readiness review, manifest planning, SQL/migration drafts | Writing physical DBs by default, changing readiness/registry activation, secret access, trading authorization |
| Reasonix-Strategy | DS-backed strategy hypotheses, config drafts, evidence-gap planning, backtest diagnosis | Buy/sell advice, recommendation tickets, promotion into source repos without Codex-Dev |
| Reasonix-Advisory | Read-only second review, test-gap review, report-overclaim review, boundary-leak review | Editing files, final verdict, replacing Codex-Audit |
| Codex-Audit | Separate read-only process review with findings JSON | Code edits, commits, final third-party verdict |
| ChatGPT external audit | Final external audit of prepared packet | Runtime execution or implicit trading approval |

## Project Inventory

### A_Share_Monitor

- Path: `/Users/rongyuxu/Desktop/A_Share_Monitor`
- Approximate size: 1.7G
- Package / CLI: `qta`, `python -m qta`
- Current branch: `codex/harden-a-share-research-pipeline`
- Working tree: dirty
- Latest commit: `02346fd A-STRAT-1: zero-candidate diagnosis + 5 research hypotheses + A11 experiment plan`

Dirty files observed:

- Modified: `qta/cli.py`, `qta/ops/__init__.py`
- Untracked local data/tooling additions under `qta/data/local_market_db/`, `qta/ops/auto_update.py`, and multiple `scripts/*` data/update helpers and logs.

Migration decision:

- Defer physical migration.
- First package or discard current local-data expansion work.
- Preserve A-share stage boundaries and data-readiness warnings.

### US_Stock_Monitor

- Path: `/Users/rongyuxu/Desktop/US_Stock_Monitor`
- Approximate size: 261M
- Package / CLI: `usq`, `python -m usq`
- Current branch: `codex/duckdb-provider`
- Working tree: dirty
- Latest commit: `88c0834 W1: add DuckDB provider for US real data + fix _metric_at for Series safety`

Dirty files observed:

- Modified: `config/data/data_sources.yaml`
- Untracked: `scripts/db_ops/`, `scripts/expand_us_300.py`

Migration decision:

- Defer physical migration.
- First close the DuckDB-provider route and reconcile with US-13 state.

### market_data

- Path: `/Users/rongyuxu/Desktop/market_data`
- Approximate size: 2.4M
- Current branch: `main`
- Working tree: dirty
- Latest commit: `4483fda Finalize DB-2 current-state audit packet`

Dirty files observed:

- Untracked reference/schema scripts and many handoff/audit/deepseek DB reports, including unified local DB acceptance packet files and offline bundle files.

Migration decision:

- Defer until registry refresh and untracked audit artifacts are intentionally committed or archived.
- This is the best candidate to become the workspace registry/access-gate layer, but only after current facts are reconciled.

### strategy_work

- Path: `/Users/rongyuxu/Desktop/strategy_work`
- Approximate size: 432K
- Current branch: `main`
- Working tree: dirty
- Latest commit: `0ae1650 consolidated data requirements: A-share + US stock combined spec`

Dirty files observed:

- Untracked: `configs/a_share_300_fast.yaml`

Migration decision:

- Still the safest first migration candidate after deciding whether to include or ignore the new config.

## Current Local Data Facts

Read-only DuckDB inspection was performed. No `.env` was read and no key values were printed.

### A-share DuckDB

- Path: `/Users/rongyuxu/Desktop/A_Share_Monitor/data/local_market/a_share_market.duckdb`
- Tables: 15
- Target table: `a_share_canonical_daily_bars`
- Current rows: 659,478
- Current symbols: 310
- Current date range: `20180102` to `20260701`
- Readiness rows: 2

Latest readiness rows include:

- `local_17b656b7acaebc19963a32d8`: `PASS`, `Level 2`, with `recommendation_runtime_enabled=false`, `broker_api_allowed=false`, `live_trading_allowed=false`.
- `a_db_2_core_297_20260702_193900`: `WARNING`, `Level 2 draft-only`, warnings include `ST_status_from_empty_table`, `ST_like_activation_guard_required`, and `draft_only_do_not_activate_before_audit`.

Interpretation:

- A-share data is useful for local research/evidence work.
- The newer expanded DB state is not a production recommendation or trading unlock.
- Current registry/docs should be refreshed before any migration or external claim.

### US DuckDB

- Path: `/Users/rongyuxu/Desktop/US_Stock_Monitor/data/local_market/us_stock_market.duckdb`
- Tables: 13
- Target table: `canonical_daily_bars`
- Current rows: 689,626
- Current symbols: 326
- Current date range: `2020-01-02` to `2026-07-02`
- Readiness rows: 1

Readiness row:

- snapshot: `us_data_4_level2_4e259f7aa0fa`
- status in JSON: `PASS_LEVEL_2`
- warnings include missing adjusted close for some rows and primary-source history shorter than 3 years
- `recommendation_runtime_enabled=false`
- `broker_api_allowed=false`
- `live_trading_allowed=false`

Interpretation:

- US local data is now materially populated.
- It still does not authorize recommendation runtime, broker usage, orders, paper trading, or live trading.

## Boundary Verdicts

| Boundary | Packet status |
|---|---|
| Recommendation runtime | Not enabled |
| Buy/sell recommendations | Out of scope / forbidden |
| Broker API | Not enabled / forbidden |
| Order routing | Not enabled / forbidden |
| Auto execution | Not enabled / forbidden |
| Manual-fill runtime activation | Out of scope |
| Paper trading | Not enabled |
| Live trading | Not enabled / forbidden |
| Secret handling | No `.env` read; no key values printed |
| Raw DB/parquet migration | Not performed |
| Git mutation | Not performed |

## Proposed Migration Plan To Audit

### M0: Freeze Map

Create and maintain a repeatable inventory:

- project path;
- branch;
- latest commit/tree;
- dirty state;
- current DB paths;
- current readiness flags;
- raw-data exclusion status.

Current implementation start:

- `registry/projects.yaml`

### M1: Clean Checkpoints

For each repo:

1. Classify dirty files as active work, generated output, stale artifact, or migration candidate.
2. Commit intentional source/report changes.
3. Keep raw generated data ignored.
4. Refresh stage reports and audit handoffs where appropriate.

### M2: Controller Workspace

Keep repos in place. Add only:

- workspace README;
- workspace AGENTS;
- prompt library;
- migration runbooks;
- inventory scripts and registry files.

### M3: Optional Consolidation

Preferred options, in order:

1. Git submodules under `projects/`.
2. External path references plus scripts.
3. Physical moved repos with path rewrite and retest.
4. Monorepo merge only after explicit approval.

## Required Fixes Before Physical Migration

1. Refresh `market_data` registry from current DuckDB facts.
2. Resolve or document dirty files in all four repos.
3. Add a repeatable workspace inventory script.
4. Decide whether `strategy_work/configs/a_share_300_fast.yaml` is intended.
5. Create a Git repo or other immutable audit point for `/Users/rongyuxu/Desktop/quant proj` if this workspace itself will be externally audited as a source artifact.
6. Convert absolute paths in registry/report files to either documented local paths or repo-relative paths where possible.
7. Add a workspace-level raw-artifact exclusion policy before any copy/move operation.

## Validation Performed

Commands/checks performed:

- Listed workspace files.
- Parsed `registry/projects.yaml` successfully.
- Verified this workspace currently contains no `.duckdb`, `.parquet`, `.sqlite`, `.env`, or `.zip` files.
- Checked Git branch/commit/tree/dirty status for all four source projects.
- Read-only inspected A-share and US DuckDB tables/readiness rows.

Not performed:

- No full `pytest` across source repos.
- No Reasonix-DB / Reasonix-Strategy / Reasonix-Advisory run yet.
- No Codex-Audit read-only process review yet.
- Local Git checkpoint/tag prepared for this workspace.
- No external ChatGPT verdict.

## Known Risks

1. This packet has a local Git checkpoint and checksum manifest, but it is not GitHub-published unless a remote is later configured and pushed.
2. Dirty project worktrees make a physical migration unsafe today.
3. Current data facts have drifted from older docs, especially US and A-share DB counts.
4. Physical DB migration is currently blocked by policy and should remain blocked until a separate audited stage.
5. Reasonix-DB and Reasonix-Strategy are draft/diagnostic roles; allowing them to write DBs, promote strategy configs, or declare final verdict would weaken current audit separation.
6. The controller workspace now has a raw-artifact `.gitignore`; keep it in place before any broad copy operation.
7. The older desktop multi-agent plan may be confused with the current implementation plan unless clearly marked as reference-only.

## Recommended External Audit Outcome Options

The external reviewer should choose one:

- `ACCEPT_CONTROLLER_WORKSPACE_PLAN`: The plan is safe to proceed to M0/M1 with no physical migration.
- `ACCEPT_WITH_FIXES`: The plan is directionally safe, but the reviewer requires listed fixes before implementation.
- `REJECT_MIGRATION_APPROACH`: The proposed controller/submodule strategy is insufficient; reviewer should state an alternative.

This preparer recommends:

`ACCEPT_WITH_FIXES`

Reason:

- The controller-first strategy is appropriate.
- The current packet is useful but not immutable.
- Dirty worktrees and stale registry facts must be fixed before any physical migration.

## Explicit Non-Authorization

This report does not authorize:

- recommendation generation;
- system buy/sell advice;
- broker API usage;
- order routing;
- order submission;
- auto execution;
- paper trading;
- live trading;
- raw database migration;
- raw API payload packaging;
- secret handling changes.
