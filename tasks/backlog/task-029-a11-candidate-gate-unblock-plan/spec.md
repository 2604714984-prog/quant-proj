# TASK-029 A11 Candidate Gate Unblock Plan

Status: `ASSIGNED`
Target project: `A_Share_Monitor`
Agent: `Codex-Dev`
Priority: `P0`
Permission: `L0_RESEARCH_DIAGNOSTIC`

## Goal

Break the 83 A11 research candidates into an executable unblock plan that separates data-fixable gates from evidence-stage, audit, and strategy blockers.

## Inputs

- `TASK-021` result.
- `TASK-009` result.
- A11 gate report.
- `TASK-007` A-share L1 snapshot.
- `TASK-008` market_data registry/readiness result.

## Must Report

- 83 candidates by experiment.
- blocker set for each candidate.
- blocker groups:
  1. research-only/ticket-disabled blocker;
  2. snapshot mismatch blocker;
  3. Phase3 evidence blocker;
  4. micro recommendation data blocker;
  5. suspension capability blocker;
  6. limit-price coverage blocker;
  7. market_data product-read blocker;
  8. production recommendation readiness blocker.
- blockers needing only data repair.
- blockers needing a new evidence stage.
- blockers requiring external audit.
- whether fixing data blockers alone still leaves `expected eligible_ticket_candidate=0`.

## Output

- `reports/codex_dev/task_029_a11_candidate_gate_unblock_plan.md`
- `reports/codex_dev/task_029_a11_candidate_gate_unblock_plan.json`

## Forbidden

No ticket emission, recommendation, buy/sell advice, broker/order/paper/live/auto, DB write, network ingest, registry activation, readiness upgrade, `.env` access, or secret handling.
