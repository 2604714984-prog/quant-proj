# Registry Refresh Runbook

Use this before batch dispatch, migration planning, DB-write planning, registry activation, readiness-status changes, or external audit publication.

The registry is a point-in-time controller snapshot. It is not a live source of truth after source projects move.

## Required Checks

For each registered source project:

- project path exists;
- current branch;
- latest commit and tree;
- working tree status;
- nearest tag or last audit tag;
- known dirty or untracked files;
- current stage/report handle when available;
- current DB-readiness or HITL/runops summary source when available.

Do not read `.env`, API keys, raw API payloads, broker credentials, or key-containing archives.

Do not copy DuckDB, SQLite, parquet, cache, output, or log artifacts into this workspace.

## Source Of Truth Order

Use this order when facts disagree:

1. Immutable Git tag or exact commit in the source project.
2. Fresh registry refresh snapshot.
3. Source-project report, closeout, or handoff file.
4. Chat transcript or operator memory.

If an older registry snapshot conflicts with a live source-project check, mark the registry stale and refresh before dispatch.

## Refresh Steps

1. Inspect each source project read-only.
2. Record branch, commit, tree, nearest tag, and working tree status.
3. Record dirty files as paths only, not file contents, unless the task explicitly requires a scoped review.
4. Record whether the project is clean, dirty, or blocked for migration.
5. Record the data-readiness source as a report or registry path. Only run DB queries when the task explicitly asks for a read-only data refresh.
6. Update `registry/projects.yaml`.
7. Add a short entry under `reports/workspace_status/` when the refresh is part of a dispatch or external audit packet.
8. Re-run YAML validation and forbidden-artifact scan.

## Minimum Validation

```text
registry/projects.yaml parses as YAML
registry/agents.yaml parses as YAML
no .env files in this workspace
no .duckdb, .sqlite, .parquet, .zip, or .tar.gz files in this workspace
```

## Dispatch Rule

Quant-Dispatcher may classify tasks using a stale registry, but it must not assign work that depends on current project state until a fresh registry refresh is completed.

