# Human gate

PERMISSION_CLASS: L0_CODE_ONLY_MOCK_TMP
TASK_LEVEL_HG_REQUIRED_FOR_THIS_PACKET: false
CENTRAL_DATABASE_WRITE: forbidden
PROVIDER_NETWORK: forbidden
TOKEN_OR_ENV_READ: forbidden
SYSTEMD_DEPLOYMENT_OR_ACTIVATION: forbidden
REGISTRY_OR_READINESS_ACTIVATION: forbidden
STRATEGY_OR_OUTCOME_EXECUTION: forbidden
CANDIDATE_RECOMMENDATION_PRODUCT_TRADING: forbidden

This packet authorizes implementation and tests only. Every test must use
test-owned temporary directories and temporary DuckDB files. The exact central
database path and any path outside the test root must fail closed.

A future real canary is a separate `L1_CONTROLLED_DB_WRITE` task. It requires
a fresh registry refresh, descriptor-bound database identity, new byte-identical
backup, exact source commit/tree/script/config hashes, a unique single-use
`HG-EXEC-TASK-*` record, explicit command, rollback, transcript, manifest,
consumer reconciliation and fresh independent acceptance. The consumed Wave 0
record is not reusable.

`strategy_candidate_available=false`.
