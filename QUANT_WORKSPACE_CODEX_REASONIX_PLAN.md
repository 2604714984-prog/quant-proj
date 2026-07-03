# Quant Workspace: Codex CLI + Reasonix CLI Collaboration Plan

Date: 2026-07-03
Workspace root: `/Users/rongyuxu/Desktop/quant proj`

## Executive Decision

Use this folder as a workspace controller first, not as a merged monorepo yet.

The existing quant system is already split into separate source-of-truth repositories:

- `/Users/rongyuxu/Desktop/A_Share_Monitor`
- `/Users/rongyuxu/Desktop/US_Stock_Monitor`
- `/Users/rongyuxu/Desktop/market_data`
- `/Users/rongyuxu/Desktop/strategy_work`

Do not physically merge everything today. The repos contain dirty working trees, absolute-path manifests, Git tags/branches used for audits, and ignored local data files. A direct move into this folder would break audit references and some registry paths before the source-of-truth files are reconciled.

Recommended first step: keep the repos where they are, add this folder as the top-level orchestration layer, and migrate only after each repo has a clean checkpoint and path references have been made portable.

## Current Inventory

| Area | Current state | Size | Git state | Migration note |
|---|---:|---:|---|---|
| A_Share_Monitor | A-share research, local data, HITL/manual review stages, A10/P3.x evidence | ~1.7G | dirty | Do not move until current uncommitted data-expansion work is packaged or intentionally abandoned. |
| US_Stock_Monitor | US research/HITL pipeline, current US-13 blocker-resolution route | ~261M | dirty | Do not move until US-13 / DuckDB-provider work is committed or reviewed. |
| market_data | Registry/access gate plus DB acceptance packets | ~2.4M | dirty | Can become workspace registry, but current files are uncommitted and some registry facts are stale. |
| strategy_work | Strategy notes/config drafts | ~436K | dirty | Defer until `configs/a_share_300_fast.yaml` is reviewed, committed, or intentionally ignored. |

Installed local CLIs:

- Codex CLI: `codex-cli 0.142.5`
- Reasonix CLI: `reasonix 0.53.2`

## Current Data Facts

A-share DuckDB:

- Path: `/Users/rongyuxu/Desktop/A_Share_Monitor/data/local_market/a_share_market.duckdb`
- Size: ~1.25GB
- Tables: 15
- Current `a_share_canonical_daily_bars`: 659,478 rows, 310 symbols, date range `20180102` to `20260701`
- Current readiness includes a newer `WARNING / Level 2 draft-only` row for DB-2-style expansion work.

US DuckDB:

- Path: `/Users/rongyuxu/Desktop/US_Stock_Monitor/data/local_market/us_stock_market.duckdb`
- Size: ~70MB
- Tables: 13
- Current `canonical_daily_bars`: 689,626 rows, 326 symbols, date range `2020-01-02` to `2026-07-02`
- Current readiness row: `PASS_LEVEL_2`, but with `recommendation_runtime_enabled=false`, `broker_api_allowed=false`, and `live_trading_allowed=false`.

Important: older docs in `market_data/LLM_REFERENCE.md` and `market_data/catalog/market_data_registry.yaml` are not fully current. Future workspace work should refresh registry manifests from live read-only DB inspection.

## Migration Feasibility

### Safe To Migrate Now

- New workspace-level docs/prompts/runbooks in this folder.
- Generated workspace inventory files that reference existing repos by absolute path.

### Safe After Checkpoint

- `market_data/` can be moved under this folder after committing or explicitly preserving its untracked reports, then updating paths in registry/report files.
- `strategy_work/` can be moved after the untracked `configs/a_share_300_fast.yaml` file is committed, ignored, or explicitly documented.
- A lightweight `projects/` directory can hold Git submodules or worktree references after each repo is clean.

### Do Not Directly Migrate Yet

- A-share and US physical DuckDB files.
- `data/`, `outputs/`, `logs/`, cache directories, raw API payloads, `.env`, API keys, or the Desktop Reasonix offline zip that is labeled as containing an API key.
- Existing repo roots before their dirty changes are resolved.

### Why Not A Direct Move Today

- A-share, US, and market_data have uncommitted files.
- Many audit packets use immutable branch/tag/commit/tree references; moving without checkpointing makes review harder.
- Several manifests and registry files contain absolute paths under `/Users/rongyuxu/Desktop/...`.
- `.gitignore` intentionally excludes real data and generated outputs. A naive copy could accidentally include files that should remain local-only.
- `market_data/catalog/market_data_registry.yaml` explicitly says `physical_db_migration_allowed: false`.

## Recommended Workspace Layout

Create the workspace as a controller:

```text
quant proj/
  QUANT_WORKSPACE_CODEX_REASONIX_PLAN.md
  README.md
  AGENTS.md
  registry/
    projects.yaml
    data_sources.yaml
  prompts/
    codex_dev.md
    codex_audit_handoff.md
    reasonix_advisory_review.md
    reasonix_test_gap.md
  runbooks/
    daily_use.md
    stage_delivery.md
    migration.md
    external_audit_packet.md
  reports/
    workspace_inventory/
    workspace_audits/
```

Optional later:

```text
quant proj/projects/
  A_Share_Monitor/      # submodule, subtree, or moved repo after checkpoint
  US_Stock_Monitor/
  market_data/
  strategy_work/
```

## Agent Roles

### Codex-Dev

Primary implementation and integration agent.

Use for:

- editing code/config/tests/docs;
- running safety checks and pytest;
- writing delivery reports and fix responses;
- committing/tagging only after explicit stage closeout;
- maintaining stage boundaries.

### Reasonix-Advisory

DeepSeek-backed secondary reviewer and research helper.

Use for:

- low-cost read-only second review;
- test-gap review;
- report overclaim review;
- codebase Q&A after `reasonix index`;
- drafting commit messages from staged diffs;
- research planning that does not emit buy/sell advice.

Reasonix output is advisory only. It does not replace Codex-Audit or ChatGPT external audit.

### Codex-Audit

Separate read-only process-review thread.

Use only after Codex-Dev has produced a delivery report, validation results, and ideally Reasonix/DeepSeek advisory output. Codex-Audit writes process review plus findings JSON and may mark a stage ready for ChatGPT external audit, but it must not claim final third-party PASS.

### Human / ChatGPT External Audit

The human remains the approval gate. ChatGPT external audit consumes immutable tags or offline bundles and decides whether the staged packet is externally acceptable.

## Standard Stage Workflow

1. Codex-Dev opens a stage branch or verifies the active branch.
2. Codex-Dev writes or refreshes the stage goal, forbidden actions, and evidence target.
3. Codex-Dev implements narrowly.
4. Codex-Dev runs safety, focused tests, full pytest when feasible, smoke commands, `git diff --check`, and gitignore checks.
5. Reasonix runs a read-only advisory review with transcript saved under `reports/deepseek_audit/` or workspace `reports/workspace_audits/`.
6. Codex-Dev fixes BLOCKER/HIGH/MEDIUM findings or writes explicit waivers where allowed.
7. Codex-Dev prepares delivery report and handoff.
8. Codex-Audit performs read-only process review and findings JSON.
9. Codex-Dev fixes any audit findings, then requests narrow re-review.
10. Final packet is prepared for ChatGPT external audit with branch/tag/commit/tree or an offline bundle when no Git audit point exists.

## CLI Patterns

Codex main development:

```bash
codex -C /Users/rongyuxu/Desktop/US_Stock_Monitor
codex -C /Users/rongyuxu/Desktop/A_Share_Monitor
codex -C /Users/rongyuxu/Desktop/market_data
```

Codex non-interactive review:

```bash
codex review -C /Users/rongyuxu/Desktop/US_Stock_Monitor
```

Reasonix interactive code review:

```bash
reasonix code /Users/rongyuxu/Desktop/US_Stock_Monitor \
  --budget 1 \
  --transcript reports/deepseek_audit/reasonix_stage_review.jsonl
```

Reasonix one-shot advisory:

```bash
reasonix run --effort high --budget 0.50 \
  --transcript reports/deepseek_audit/reasonix_stage_review.jsonl \
  "Read-only review: inspect the current stage delivery, hard-rule boundaries, tests, and report overclaims. Do not edit files. Do not read .env. Do not output buy/sell advice."
```

Reasonix semantic index:

```bash
reasonix index --dir /Users/rongyuxu/Desktop/US_Stock_Monitor
reasonix index --dir /Users/rongyuxu/Desktop/A_Share_Monitor
reasonix index --dir /Users/rongyuxu/Desktop/market_data
```

## Daily Operating Modes

### A-share

Use only as a research/evidence system unless a later audited stage explicitly opens more.

Current boundary:

- P3.6 closeout is `WARNING`, dry-comparison-only.
- A10-style artifacts remain no-recommendation / no-broker / no-live.
- A-share DB expansion is useful, but current draft rows must not be overclaimed as production recommendation readiness.

### US

Use as research and human-review pipeline.

Current boundary:

- US-13 current real-state result is `NO_RECOMMENDATION_AVAILABLE`.
- Prior AAPL/HOLD ticket remains `PENDING_HUMAN_REVIEW`.
- No recommendation runtime, broker API, order routing, manual-fill runtime, paper trading, or live trading is enabled.

### market_data

Use as registry/access-gate and acceptance-packet hub.

Current boundary:

- Physical DBs live in their source repos.
- Registry facts need refresh before being treated as current.
- Do not migrate physical DBs into `market_data` until a future audited migration stage explicitly allows it.

### strategy_work

Use as research scratchpad and report workspace.

Promotion rule:

- Strategy configs mature here first.
- Only promote into A-share or US repos through a staged Codex-Dev implementation plus tests and audit.

## Migration Plan

### Phase M0: Freeze Map

- Generate `registry/projects.yaml` with repo paths, branches, dirty state, latest commit, data DB paths, and boundary flags.
- Do not move files.

### Phase M1: Clean Checkpoints

- For each repo, decide whether dirty changes are intentional.
- Commit, stash, or explicitly document uncommitted work.
- Refresh `market_data` registry from live DB facts.

### Phase M2: Controller Workspace

- Add workspace `README.md`, `AGENTS.md`, prompts, runbooks, and inventory scripts.
- Keep projects as external paths.

### Phase M3: Optional Physical Consolidation

Choose one:

- Submodules: best for preserving independent histories and audit tags.
- Git worktrees: best for local operational convenience, weaker as a durable repo structure.
- Move repos as subfolders: simplest locally, but requires path rewrites and careful audit retagging.
- Monorepo merge: not recommended now.

Recommended choice: submodules or external-path controller first.

## Non-Negotiable Boundaries

- No `.env` reads or secret printing.
- No raw DB/parquet/API payload packaging into audit bundles.
- No broker API, order routing, auto execution, or live trading.
- No buy/sell advice from Codex or Reasonix.
- No claim that `PASS`, `WARNING`, or `Level 2` means recommendation or trading readiness.
- Empty/blocked states such as `NO_RECOMMENDATION_AVAILABLE`, `NO_FILLS_TO_REVIEW`, `NO_REAL_FEEDBACK_YET`, and `PENDING_HUMAN_REVIEW` are valid states when supported by evidence.
