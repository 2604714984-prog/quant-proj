# Migration Runbook

## Goal

Move toward a durable `quant proj` controller workspace without breaking existing repo history, audit tags, or data boundaries.

## M0: Inventory Only

Keep all source repos in place. Refresh:

- `registry/projects.yaml`
- DB row counts and readiness rows from read-only queries
- Git branch, latest commit, dirty state

## M1: Clean Checkpoints

For each repo:

1. Inspect dirty files.
2. Decide whether each dirty change is active work, generated output, or stale artifact.
3. Commit intentional code/docs/test changes.
4. Leave generated data ignored.
5. Update stage report and audit handoff if the work is a formal stage.

## M2: Controller Workspace

Add workspace-level prompts, runbooks, and registry files.

Do not move physical DBs.

## M3: Optional Project Consolidation

Preferred order:

1. Git submodules under `projects/`.
2. External path references plus scripts.
3. Physical moved repos after path rewrite and retest.
4. Monorepo merge only after explicit approval.

## Pre-Move Checklist

- working tree clean or intentionally documented;
- latest commit recorded;
- tags needed for external audit preserved;
- absolute paths identified;
- `.gitignore` reviewed;
- raw data excluded;
- safety tests pass;
- registry refreshed after move in a dedicated commit.

