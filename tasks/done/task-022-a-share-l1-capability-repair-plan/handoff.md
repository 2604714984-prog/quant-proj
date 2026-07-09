# TASK-022 Handoff

To: `Reasonix-DB`
Fixed session: `quant-reasonix-db`
Model: `deepseek-v4-pro`
Effort: `high`
Task: `A-share L1 snapshot capability repair plan`

## Evidence

- TASK-007 source commit: `7c168999b6a583ca20a325098cc2111de311a1a1`
- TASK-007 source tree: `93af3e1f2df82c80a00598a35ae3e602130a45bd`
- snapshot: `a_expand_20260704_l1_local1000_0317`
- symbols: `1000`
- canonical rows: `2,059,000`
- date range: `20180102..20260701`
- readiness: `WARNING`, `Level 1`
- suspension status: `WARNING_EVENT_TABLE_EMPTY`
- limit price status: `WARNING_LOW_COVERAGE`
- `phase3_evidence_ready=false`
- `micro_recommendation_data_ready_with_warnings=false`

## Expected Output

Reasonix-DB should return a repair plan and JSON summary suitable for Codex-Dev conversion into a later implementation task.

## Boundary

Read-only plan only. No source edits, no DB writes, no network ingest, no readiness claim, no recommendation, no ticket.
