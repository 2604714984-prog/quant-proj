# CENTRAL_DATABASE_FULL_INGESTION_DB2_20260713

Status: READY_TO_DISPATCH_AFTER_GITHUB_PRESERVATION

Tracking issue: https://github.com/2604714984-prog/quant-proj/issues/19

Foundation acceptance: `reports/central_database/manager/central_db_foundation_acceptance_20260713.md`

Task matrix: `reports/central_database/manager/central_db_full_ingestion_task_matrix_20260713.csv`

Queue order: A0 -> A1 -> A2 -> A3 -> U0 -> U1 -> U2 -> U3 -> A4 -> A5 -> A6 -> U4 -> U5 -> U6 -> X1 -> X2

The dedicated database thread owns all physical database implementation and writes. The manager
owns orchestration, dependency tracking, callback acceptance, status publication, and external
audit assembly. Routine append is one-command and receipt-driven after a signed profile has been
accepted. Heavy gates apply only to elevated categories documented in the foundation acceptance.

Every lane prompt is independently testable and cannot itself authorize network or database
mutation. Each elevated lane uses a single-use acquisition authority, isolated staging, fresh
independent result acceptance, and a separate locked central-append authority. The routine fast
lane is limited to an already-qualified source/profile with unchanged schema, natural key, and
append semantics. Callbacks must declare commit/tree, backup, rollback, schema, primary key,
row/symbol/date coverage, duplicate count, PIT/adjustment/corporate-action semantics, snapshot ID,
export hashes, worktree state, and GitHub URLs.

Boundary: research data only; strategy_candidate_available=false; no recommendation, readiness,
signal, broker/order/paper/live/auto, secret output, database binary commit, or unbounded raw dump.
