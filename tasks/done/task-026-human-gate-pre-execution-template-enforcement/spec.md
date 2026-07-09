# TASK-026 Human-Gate Pre-Execution Template Enforcement

## Status

QUEUED_P1

## Target Project

`quant-proj`

## Recommended Agent

`Codex-Dev`

## Goal

Make future L1-L4 tasks require `HG-EXEC-TASK-*` before execution.

## Deliverables

- template under `reports/human_gate/templates/`;
- dispatcher checklist update;
- task packet validation rule;
- sample `HOLD` record.

## Expected Output

`CODEX_ACCEPTANCE_TASK_026_HG_EXEC_TEMPLATE`

## Boundary

Controller policy hardening only. No source-project execution, no DB write, no network ingest, no readiness change, no recommendation, no ticket, no broker/order/paper/live/auto.
