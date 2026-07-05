# Reasonix-DB R8 Draft Result

Project: quant-proj
Batch: DATA_STRATEGY_BATCH_R8_20260705
Role: Reasonix-DB persistent sidecar
Session policy: persistent CLI-like session, keep open and reuse
Model policy: deepseek-v4-pro, effort high
Transcript: `reports/workspace_dispatch/reasonix_db_data_strategy_batch_r8_20260705.jsonl`

## Status

`REASONIX_DRAFT_READY`

Verdict: `PASS_DRAFT_ONLY`

This is an advisory draft only. It does not authorize execution, DB writes, network/provider calls, schema migration, bulk ingest, registry activation, readiness changes, recommendations, tickets, product routes, or broker/order/paper/live/auto paths.

## Scope Covered

| R8 task | Result |
|---|---|
| Task 7, US data-limited eight repair checklist | Drafted a symbol-class taxonomy, missing-field repair lane matrix, per-symbol checklist template, and expected Codex-Dev output paths. |
| Task 8, 44-symbol metadata bootstrap dry-run spec | Drafted group partitioning, active-equity exclusion rule, CSV/JSON dry-run schemas, expected Codex-Dev work, and Human-Gate triggers. |
| Task 10, market_data research route drift check | Drafted assertion set and checks for product-read, production-readiness, broker/live/auto/paper, eligibility, and R7 baseline drift. |

## Key Handoff Points

- The eight data-limited symbols must be populated from real R7/R8 source artifacts by Codex-Dev before any repair checklist is treated as evidence.
- The 44-symbol bootstrap remains dry-run only until a separate task-level HG-EXEC authorizes network/provider fetch or DB write.
- The drift check should fail closed if any route is found with `product_read_allowed=true`, `production_recommendation_data_ready=true`, broker/live/auto/paper enabled, or eligibility tags.
- Suggested follow-up after Codex-Dev produces dry-run outputs: Reasonix-Advisory can spot-check two or three symbols for lane and priority correctness.

## Required Codex-Dev Work From Draft

1. Retrieve the actual R7/R8 data-limited eight-symbol list and query local tables for a real null/gap map.
2. Produce `reports/data_repair/r8_data_limited_eight_checklist.{csv,md}` in the US source repo.
3. Pull the actual 44-symbol list, apply active-equity exclusion, and generate dry-run metadata bootstrap artifacts with no provider calls.
4. Produce `reports/metadata_bootstrap/r8_dry_run_44_metadata_bootstrap.{csv,json,md}` in the US source repo.
5. Run route drift assertions and produce `reports/drift_check/r8_research_route_drift_check.md` in the market_data source repo.

## Human-Gate Notes

The draft names future gates only:

- `HG-R8-01`: DB write for eight-symbol repair after Codex-Dev produces the actual null map.
- `HG-R8-02`: network/provider fetch for 44-symbol metadata bootstrap after dry-run review.
- `HG-R8-03`: readiness or registry status change if drift check reveals needed corrections.

None of these gates are requested or executed by this Reasonix sidecar result.

## Boundary Check

- Recommendation/ticket: not present
- Eligibility candidate: not present
- Product route activation: not present
- Production readiness: not present
- Broker/order/paper/live/auto: not present
- Ungated DB write/network/schema/bulk/readiness/registry change: not present

