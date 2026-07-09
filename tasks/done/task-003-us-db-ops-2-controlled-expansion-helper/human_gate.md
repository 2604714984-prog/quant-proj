# Human-Gate Note

Task ID: `TASK-003`
Human-Gate required for assignment: no
Human-Gate required for code rewrite only: no
Human-Gate required before real network or DB write execution: yes

Standing authorization exists:

- `HG-STANDING-20260704`

This means real network or DB-write execution may proceed without asking the user again, but only after creating a task-level `HG-EXEC-*` record with the exact command, target DB path, allowed write scope, stop conditions, and validation plan.

If the task expands into live network fetch, DuckDB/SQLite writes, bulk ingest, schema changes, registry activation, readiness changes, product route activation, or recommendation/HITL behavior, create a separate Human-Gate record before execution.
