# TASK-021 A11 Research Candidate Root-Cause Drilldown

## Status

BACKLOG_READY_FOR_DISPATCH

## Source

ChatGPT external audit accepted the recorded-execution packet and requested this P0 follow-up.

## Target Project

`A_Share_Monitor`

## Recommended Agent

`Codex-Dev`

## Permission Level

`L0_RESEARCH_DIAGNOSTIC`

No DB write, network ingest, registry activation, readiness change, or ticket emission is authorized.

## Input

`TASK-009` produced:

- `candidate_count=83`
- `eligible_ticket_candidate_count=0`
- `ticket_emitted=false`

## Goal

Break down the 83 A11 research candidates by gate failure.

## Must Report

- candidate count by experiment;
- failure count by blocker;
- how many candidates are blocked only by `A11_RESEARCH_ONLY_NOT_TICKET_ENABLED`;
- how many are blocked by `PHASE3_EVIDENCE_NOT_READY`;
- how many are blocked by `MICRO_RECOMMENDATION_DATA_NOT_READY`;
- how many are blocked by `SUSPENSION_CAPABILITY_INCOMPLETE`;
- how many are blocked by `LIMIT_PRICE_COVERAGE_LOW`;
- whether any candidate would become eligible if only data-readiness gaps were fixed.

## Expected Outputs

- `reports/codex_dev/task_021_a11_candidate_root_cause_drilldown.md`
- `reports/codex_dev/task_021_a11_candidate_root_cause_drilldown.json`

## Validation Expectations

- safety check;
- focused tests or script-level validation for the blocker aggregation;
- JSON parse validation for the new output;
- `git diff --check`;
- commit and push scoped changes if files are changed.

## Forbidden

No ticket emission, no recommendation, no buy/sell advice, no broker/order/paper/live/auto execution, no trade plan, no entry price, no target weight, no position sizing, no allocation, no `.env` read, no key output.
