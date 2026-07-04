# TASK-033 Final Metadata Packet Standard

Status: `IN_PROGRESS`
Target project: `quant-proj`
Agent: `Quant-Dispatcher / Codex-Dev`
Priority: `P0`
Permission: `L0_RESEARCH_DIAGNOSTIC`

## Goal

Fix the low-risk process issue where final publication metadata was not included in the packet tag/manifest by standardizing final-publication metadata handling.

## Deliverables

- `runbooks/final_publication_metadata.md`
- metadata template under `reports/agent_handoff/`
- dispatcher checklist update
- manifest inclusion rule
- `reports/workspace_dispatch/task_033_final_metadata_standard_20260704.md`

## Must Require

- final tag;
- tag object;
- commit;
- tree;
- tag URL;
- packet path;
- manifest path;
- source-of-truth statement;
- inclusion in packet manifest.

## Forbidden

No source repo edits, product change, recommendation, ticket, broker/order/paper/live/auto, DB write, network ingest, registry activation, readiness change, raw-data migration, `.env` access, or secret handling.
