# Consolidated workspace external re-audit package

## Review status

`READY_FOR_INDEPENDENT_EXTERNAL_REAUDIT_WITH_DATA_LANES_BLOCKED`

This package does not claim that an external auditor has passed the workspace. It consolidates the previously reviewed remediation, the targeted re-audit repair, the R2/Gate-B controller work, and the completed central-database orchestration into one GitHub-reviewable branch.

`strategy_candidate_available=false`; no recommendation, readiness, product route, daily signal, paper/live/auto or broker path is enabled.

## Previous audit remediation

- The R1 closure matrix contains 13 findings: 12 `CLOSED_ACCEPTED` and 1 `CLOSED_AFTER_TARGETED_REWORK`.
- The R2 closure matrix contains 7 findings: 6 `VERIFIED_IMPLEMENTATION_ACCEPTED` and 1 `VERIFIED_EXTERNAL_RECEIPT`.
- The previously open RA-001 CSV authority/runtime split is represented by the targeted re-audit bindings merged into this branch; this package asks an external reviewer to verify the fix rather than self-declaring the old verdict passed.
- CI is hash-locked and separates static/unit, integration identity, controlled fixture reproduction, exact branch-head identity and pull-request merge identity.
- Historical PRs #10 and #12 are superseded by the incorporated R1/R2 chain. PR #13 is incorporated as the targeted re-audit increment. PRs #16 and #18 are incorporated as the R2/Gate-B chain.

## Central database foundation and orchestration

- The central-data-ingestion foundation and routine append fast lane are merged and independently accepted.
- A0-A6, U0-U6, X1 and X2 were adjudicated in order and preserved through central-data-ingestion PRs #6-#21.
- A0 is design-only. A1-A6, U0-U6 and X1 are `ACCEPTED_BLOCKED`. X2 is `ACCEPTED_BLOCKED_NO_ACCEPTED_DATASET`.
- Accepted source datasets: 0. No raw/PIT source was promoted, no derived feature store was materialized, and no production schedule/profile was fabricated.
- Current DuckDB identity is SHA-256 `d356add782758746ea05666af38dd0f64918ae675ec3a7cd5e645588e44309d4`, 2,399,678,464 bytes, mode 0600, 54 relations. The database was unchanged by X1/X2 and by this consolidation.
- Generic same-source/schema append capability includes signed profile/batch, one writer lock, forward high-water, insert-only transaction, idempotent replay, duplicate/schema guards, daily checkpoint, immutable receipt, quarantine and rollback.
- Production source health checks, stale alerts, generic read-only export and schedules are not instantiated because no dataset is accepted. New source/schema/key, backfill, overwrite/delete and promotion remain elevated work.

## Decisive unresolved data blockers

- A-share: canonical calendar and bars are empty; `total_mv`/`circ_mv` are absent; historical ST/name/suspension, industry membership, primary-tied fundamentals, events and fund flows are not qualified.
- US: official/PIT calendar, survivor-complete symbol history, corporate actions/delisting returns, total-return identities, regime/macro PIT inputs and SEC/XBRL fundamentals are incomplete or unqualified.
- Existing retrospective assets with null/unknown `available_at`, current-only membership, cross-snapshot identity or missing primary-document lineage remain noncanonical.

These blockers are data-source qualification outcomes, not defects hidden by the package. They prevent strategy execution or promotion but do not prevent review of the repaired controller and database foundation.

## External reviewer entry points

1. `reports/remediation/FINDING_CLOSURE_MATRIX.json`
2. `reports/remediation/EXTERNAL_REAUDIT_VERDICT_20260712.md`
3. `reports/remediation_r2/R2_FINDING_CLOSURE_MATRIX_20260713.json`
4. `tasks/backlog/REMEDIATION_R2_GATE_B_CODE_MOCK_20260713/`
5. `reports/workspace_status/registry_refresh_external_audit_20260714.md`
6. `registry/projects.yaml`
7. central-data-ingestion PR #21 artifact `reports/central_database/x2_automation_readiness_20260714.json`, SHA-256 `0f31979d90fa01e286c0398afd483c906e466dadc78f715ce4a93c5376cd2178`

## Repository boundary

Git contains reports, schemas, fixtures, tests and code only. It excludes DuckDB/SQLite/Parquet databases, raw provider payloads, caches, logs, archives and credential values. The final pull request must pass all `research-validation` jobs before it is offered for external review.
