# TASK-034 A11 Candidate Safety Regression Tests

Status: `ASSIGNED`
Target project: `A_Share_Monitor`
Agent: `Codex-Dev`
Priority: `P1`
Permission: `L0_RESEARCH_DIAGNOSTIC`

## Goal

Add or verify focused regression coverage proving that A11 research candidates cannot become HITL ticket candidates or recommendation outputs while the known gates remain closed.

## Inputs

- `TASK-029` A11 unblock plan: A-share commit `ce26b391e0eebf5eca35aae974052a236cdf5bca`, tree `f2819654363f116f45d9dd171492c4cb9d227c6d`.
- `TASK-021` candidate root-cause drilldown: A-share commit `025f773d42fa16916e31da8d153382d67c02ebe1`.
- `TASK-009` A11 gated ticket attempt: A-share commit `a2c8b825942a59d7c03429f41336ca1b9145a875`.

## Must Prove

- The `83` A11 candidates remain research-only and non-actionable.
- `eligible_ticket_candidate_count` remains `0`.
- `ticket_emitted=false`.
- Data-repair-only modeling for suspension and limit-price does not by itself create ticket eligibility.
- A11 research-only/ticket-disabled, snapshot mismatch, Phase3 evidence, market_data product-read, and production readiness blockers continue to fail closed.
- No output can include buy/sell advice, entry price, target weight, position sizing, allocation, broker/order fields, paper/live/auto flags, or HITL ticket payload fields.

## Expected Outputs

- `reports/codex_dev/task_034_a11_candidate_safety_regression_tests.md`
- optional JSON report if useful.
- focused source-project tests or static artifact tests, committed if changed.

## Validation Expectations

- `python scripts/agent_safety_check.py`
- focused A11/HITL/ticket-gate regression tests
- JSON parse validation if a JSON artifact is created
- synthetic-only smoke if appropriate
- `git diff --check`

## Forbidden

No ticket emission, recommendation, buy/sell advice, broker/order/paper/live/auto, DB write, network ingest, registry activation, readiness upgrade, `.env` access, key output, or secret handling.
