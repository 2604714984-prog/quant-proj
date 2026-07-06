# Claude Code Workspace Rules

This controller workspace uses `AGENTS.md` as the authoritative agent rulebook.

Before taking action in this repository, read:

- `AGENTS.md`
- `reports/workspace_dispatch/continuous_closed_loop_goal_20260705.md`
- `runbooks/task_dispatch.md`
- `runbooks/human_gate.md`
- `runbooks/recorded_execution_mode.md`
- `reports/workspace_dispatch/downstream_completion_callback_protocol_20260706.md`

Short rule summary:

- Quant-Dispatcher is controller-only: intake, classify, dispatch, record,
  summarize, commit, and push controller records.
- Do not directly edit downstream source-project implementation files unless
  the user explicitly changes the role boundary.
- Do not read, print, copy, or commit `.env`, key, token, credential, or secret
  values.
- Do not authorize recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket
  emission, eligibility candidates, product-route activation, production
  readiness, broker/order/paper/live/auto behavior, raw-data migration, or
  secret handling.
- User performs GPT Pro / ChatGPT external-audit UI operation. Quant-Dispatcher
  receives pasted task lists, verdicts, and downstream acceptances.
- Current Windows WSL2 dispatcher thread:
  `019f3830-4b44-7a83-944d-247a0d4dc169`.
