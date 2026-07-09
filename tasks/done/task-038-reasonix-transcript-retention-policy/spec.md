# TASK-038 Reasonix Transcript Retention Policy

Status: `ASSIGNED`
Target project: `quant-proj`
Agent: `Quant-Dispatcher`
Priority: `P1`
Permission: `L0_RESEARCH_DIAGNOSTIC`

## Goal

Standardize how Reasonix transcripts, normalized reports, and final packet manifests are retained for dispatcher-run batches.

## Must Define

- where Reasonix transcripts are stored;
- how normalized Reasonix outputs are stored;
- when transcript hashes must appear in manifests;
- how to label simulated, draft, normalized, advisory, and accepted outputs;
- what to include in final external-audit packets;
- how fixed sessions and compact behavior interact with durable evidence.

## Expected Outputs

- `runbooks/reasonix_transcript_retention.md`
- update `runbooks/reasonix_sessions.md`
- `reports/workspace_dispatch/task_038_reasonix_transcript_retention_policy_20260704.md`

## Forbidden

No source-project edits, DB write, network ingest, registry/readiness change, recommendation, ticket emission, broker/order/paper/live/auto, `.env` access, key output, or secret handling.
