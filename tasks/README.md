# Task Queue

This directory stores task packets created by Quant-Dispatcher.

Directory roles:

- `inbox/`: raw task lists copied from ChatGPT.
- `backlog/`: accepted task packets not yet assigned for execution.
- `in_progress/`: tasks currently being worked by a downstream agent.
- `done/`: completed task reports and closeout notes.
- `blocked/`: tasks requiring human approval, missing inputs, or external state changes.

No raw databases, parquet caches, `.env`, API keys, or generated outputs belong here.
