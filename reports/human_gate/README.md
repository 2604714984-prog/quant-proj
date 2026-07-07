# Human-Gate Records

This directory stores durable Human-Gate decision records for the controller workspace.

`decisions.jsonl` is append-only. A missing approval record means boundary-changing work is not approved. Ordinary research-data fast-path work does not need a per-task HG-EXEC record when it stays within `reports/human_gate/windows_wsl2_research_data_fast_path_policy_20260707.md`.

Do not store secrets, `.env` values, raw data, raw database files, or broker credentials here.

Templates live in:

- `reports/human_gate/templates/hg_exec_task_record_template.json`
- `reports/human_gate/templates/hg_exec_task_hold_example.json`

Future boundary-changing L1-L4 execution requires a unique pre-execution `HG-EXEC-TASK-*` record. Standing authorization alone is not enough for boundary-changing execution.

Recorded execution mode:

- L0 research/diagnostics can run by default when it stays non-actionable.
- Research-data fast path covers bounded public/no-secret network fetch and source-local research cache/staging/report/test writes without per-task HG-EXEC; transcript, manifest/count/hash evidence, validation, and callback are still required.
- L1/L2 outside research-data fast path require Human-Gate.
- L3 active registry/readiness/product route changes require Human-Gate, old/new diff, rollback path, command transcript, and Codex acceptance.
- L4 `PENDING_HUMAN_REVIEW` ticket emission requires Human-Gate and all gates passing. It is not an order, recommendation, trade plan, fill, broker action, or execution instruction.

See `runbooks/recorded_execution_mode.md` and `runbooks/human_gate.md`.
