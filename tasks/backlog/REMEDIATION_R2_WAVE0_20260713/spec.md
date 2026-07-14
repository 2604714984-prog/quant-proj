# REMEDIATION_R2_WAVE0_20260713

Freeze the Repository-wide R2 baseline and create one byte-identical, lock-coordinated backup of the current central DuckDB before any implementation or provider work.

Allowed: controller artifacts, registry refresh, read-only DB schema/hash/count inspection, one backup under the exact private backup path, validators, tests, commit and push.

Forbidden: token access, provider/network calls, schema/data mutation, collector/publisher activation, readiness or registry activation, strategy execution, recommendation, candidate promotion, broker/order/paper/live/auto paths.

The exact backup execution is governed by `HG-EXEC-TASK-REMEDIATION-R2-DB-BASELINE-BACKUP-20260713` and must fail if the source hash/bytes/mode drift, the destination exists, or the writer lock cannot be acquired.
