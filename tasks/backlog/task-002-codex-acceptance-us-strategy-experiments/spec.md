# TASK-002: CODEX_ACCEPTANCE_US_STRATEGY_EXPERIMENTS

Task ID: `TASK-002`
Status: `ASSIGNED_READY_TO_SEND`
Priority: `P0`
Primary assignee: `Codex-Dev`
Target project: `US_Stock_Monitor`
Target root: `/Users/rongyuxu/Desktop/US_Stock_Monitor`
Dispatcher: `Quant-Dispatcher`
Created at: 2026-07-04T01:25:34+08:00

## Goal

Lightly accept `usq/research/us_strategy_experiments/` as research-only diagnostics for the US strategy blockers.

Current refreshed source state:

- branch: `codex/duckdb-provider`
- commit: `36aff30da581d01d24ffba89c6bb1e0515337bec`
- tree: `0fcf4a464116e748e5514ab9c2dbcc899ecc2f74`
- working tree: clean

## Assignment

Send to `Codex-Dev` in a Codex thread rooted at `/Users/rongyuxu/Desktop/US_Stock_Monitor`.

Do not send to RunOps. Do not ask RunOps to approve/reject anything.

## Expected Validation For Executor

The executor should run:

```bash
python scripts/agent_safety_check.py
pytest -q tests/test_us_strategy_experiments.py
pytest -q
python -m usq smoke
git diff --check
```

## Acceptance Checks

Confirm the work:

- only diagnoses evidence, feedback, and eligibility blockers;
- does not emit tickets;
- does not emit recommendations;
- does not connect broker/order/live/paper paths;
- only outputs research diagnostics.

## Required Executor Output

```text
CODEX_ACCEPTANCE_US_STRATEGY_EXPERIMENTS

status:
ACCEPTED / ACCEPTED_WITH_WARNINGS / REJECTED

accepted_level:
L2_STRATEGY_RESEARCH_CODE

remaining_blockers:
- evidence_gap
- insufficient_feedback
- no_eligibility_candidate

external_audit_required_now:
false
```

## Dispatcher Boundary

Quant-Dispatcher only created this packet. No source-project files were edited.

