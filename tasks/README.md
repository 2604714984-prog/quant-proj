# Task Records

Routine work is tracked in one GitHub issue and one branch/PR. Do not create an
inbox copy or a per-task folder for ordinary implementation, tests, or docs.

The existing `inbox/`, `backlog/`, `in_progress/`, `done/`, and `blocked/`
trees are retained as historical evidence. New files under `tasks/` are only
needed when an elevated data, PIT, schema, destructive DB, strategy-intake, or
execution-boundary authorization requires a durable record.

Never store databases, raw payloads, caches, generated outputs, `.env` files,
or credential values here.
