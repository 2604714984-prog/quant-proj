# Task Queue

This directory stores task packets created by Quant-Dispatcher.

Directory roles:

- `inbox/`: raw task lists copied from ChatGPT.
- `backlog/`: accepted task packets not yet assigned for execution.
- `in_progress/`: tasks currently being worked by a downstream agent.
- `done/`: completed task reports and closeout notes.
- `blocked/`: tasks requiring human approval, missing inputs, or external state changes.

No raw databases, parquet caches, `.env`, API keys, or generated outputs belong here.

Before dispatch, validate each packet with `runbooks/task_packet_validation.md`.

Future L1-L4 execution tasks require a unique pre-execution `HG-EXEC-TASK-*` record before the command runs. If the record is missing, keep the task in `blocked/` or mark it `HOLD_FOR_MISSING_HG_EXEC_TASK_RECORD`; do not send it as executable work.
