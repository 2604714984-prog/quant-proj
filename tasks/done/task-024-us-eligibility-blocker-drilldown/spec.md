# TASK-024 US Eligibility Candidate Blocker Drilldown

## Status

BACKLOG_READY_FOR_DISPATCH

## Target Project

`US_Stock_Monitor`

## Recommended Agent

`Codex-Dev`

## Permission Level

`L0_RESEARCH_DIAGNOSTIC`

## Input

`TASK-010` result:

- `NO_TICKET_ELIGIBLE_CANDIDATE`
- evidence gap
- insufficient feedback
- eligibility candidate: false
- `ticket_emitted=false`

## Goal

Explain exactly what evidence, feedback, and eligibility fields are missing, and what data or strategy task would unblock them.

## Expected Outputs

- `reports/codex_dev/task_024_us_eligibility_blocker_drilldown.md`
- `reports/codex_dev/task_024_us_eligibility_blocker_drilldown.json`

## Validation Expectations

- safety check;
- focused tests or script-level validation for diagnostic output;
- JSON parse validation;
- `git diff --check`;
- commit and push scoped changes if files are changed.

## Forbidden

No ticket emission, no recommendation, no broker/order/paper/live/auto, no readiness upgrade, no DB write, no network ingest, no `.env`, no secrets.
