# Reasonix-DB R12 Data Draft

Created: 2026-07-05
Role: Reasonix-DB
Model: `deepseek-v4-pro`
Effort: `high`
Primary transcript: `reports/workspace_dispatch/reasonix_db_data_strategy_batch_r12_retry_20260705.jsonl`
Exploratory transcript: `reports/workspace_dispatch/reasonix_db_data_strategy_batch_r12_run_20260705.jsonl`
Status: `WARNING_ADVISORY_ONLY`

## Verdict

Reasonix-DB produced an advisory draft for R12 data work, but with important dispatcher corrections:

- The first run did not produce a usable draft and attempted to hand off to an unavailable explore subagent. It is retained as transcript evidence only.
- The retry produced useful validation ideas, but over-stated several items as Human-Gate decisions and suggested implementation shapes involving new columns/tables. R12 remains ordinary read-only/dry-run research work unless a future task-level `HG-EXEC` authorizes writes or schema changes.

## Useful Advisory Points

- A-share snapshot reporting must distinguish baseline rows from true post-freeze forward-holdout evidence.
- A-share R12 should report failure classes for every available snapshot instead of relying on "holdout rows" wording.
- US metadata repair packets must remain import-blocked unless controlled provenance, source hash, snapshot id, freshness, and active-equity eligibility are all present.
- Synthetic crosscheck fixtures must remain logic-test-only and must not count as research evidence.
- US-300A should map each data-clear criterion to an explicit evidence status; no missing evidence can implicitly pass.
- Negative tests should reject criteria passing without an auditable evidence artifact.

## Dispatcher Corrections

The following Reasonix-DB suggestions are advisory only and must not be executed in R12 without a separate gated task:

- Adding physical columns or tables.
- Creating a repair workspace that writes data.
- Using Parquet as a new second-source input if that would import or persist raw data.
- Treating `SYNTHETIC_ONLY_INVALID` as the fallback for all no-second-source rows; Codex-Dev should preserve the requested `NO_CONTROLLED_SECOND_SOURCE_AVAILABLE` outcome when no controlled file exists.
- Requiring Human-Gate merely to define research-only classification labels or dry-run validators.

## Codex-Dev Handoff

- Implement A-share snapshot semantics as read-only reports/tests where possible.
- Keep US metadata repair packet import-blocked and dry-run only.
- Make second-source file contract explicit; if no valid local file exists, return `NO_CONTROLLED_SECOND_SOURCE_AVAILABLE`.
- Extend US-300A evidence-status bridge tests so all seven criteria plus clean evidence are required.
- Preserve all research-only labels and blocked states honestly.

## Non-Authorization

This Reasonix-DB draft does not authorize recommendation/advice, ticket or `PENDING_HUMAN_REVIEW`, eligibility candidate creation, product route, production readiness, broker/order/paper/live/auto, DB write, network ingest, schema migration, bulk ingest, readiness change, registry activation, provider persistence, or raw-data migration. Any persistent execution requires separate task-level `HG-EXEC`.
