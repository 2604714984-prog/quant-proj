# TASK-001: CODEX_ACCEPTANCE_A11_RESEARCH_RUNNER

Task ID: `TASK-001`
Status: `ASSIGNED_READY_TO_SEND`
Priority: `P0`
Primary assignee: `Codex-Dev`
Target project: `A_Share_Monitor`
Target root: `/Users/rongyuxu/Desktop/A_Share_Monitor`
Dispatcher: `Quant-Dispatcher`
Created at: 2026-07-04T01:25:34+08:00

## Goal

Lightly accept the committed A11 research runner as research-only strategy experiment code.

Current refreshed source state:

- branch: `codex/harden-a-share-research-pipeline`
- commit: `1537e9958fdd11a36f6392314228abd02a26507a`
- tree: `c30fa5401789005ff27ca7658fbe5ddf382f4df5`
- working tree: clean

## Assignment

Send to `Codex-Dev` in a Codex thread rooted at `/Users/rongyuxu/Desktop/A_Share_Monitor`.

Do not send to Reasonix as the primary executor. This is code/test acceptance work.

## Expected Validation For Executor

The executor should run:

```bash
python scripts/agent_safety_check.py
pytest -q tests/test_a11_strategy_research_modules.py
python -m qta research a11-experiments
git diff --check
```

## Acceptance Checks

Confirm the output preserves:

- `research_only=true`
- `non_actionable=true`
- `not_a_recommendation=true`
- `ticket_emitted=false`
- `ticket_emission_allowed=false`
- `recommendation_runtime_enabled=false`
- `broker_api_allowed=false`
- `order_routing_allowed=false`
- `paper_trading_allowed=false`
- `live_trading_allowed=false`

## Required Executor Output

```text
CODEX_ACCEPTANCE_A11_RESEARCH_RUNNER

status:
ACCEPTED / ACCEPTED_WITH_WARNINGS / REJECTED

accepted_level:
L2_STRATEGY_RESEARCH_CODE

candidate_count:
...

blocked_reason_counts:
...

usable_for_future_ticket_gate:
false unless separately audited

external_audit_required_now:
false
```

## Dispatcher Boundary

Quant-Dispatcher only created this packet. No source-project files were edited.

