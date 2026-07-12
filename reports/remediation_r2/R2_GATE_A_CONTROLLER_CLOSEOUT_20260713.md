# Remediation R2 Gate A and controller closeout

Status: `READY_FOR_TARGETED_EXTERNAL_REAUDIT`

RW-001 through RW-006 have implementation evidence, dynamic negative tests, green automated gates and independent read-only acceptance. EA-001 has a fresh ten-asset download receipt, verified publisher source history and independent Parquet recomputation with `mismatch_rows=0`. The current-tree artifact inventory has zero forbidden or unclassified payloads.

Gate A passes. The private `central-data-ingestion` repository implements only DB-603 through DB-607 and passed its independent acceptance and GitHub CI. Its collector timer remains inert; no token or provider call occurred. The central publisher is absent and disabled, and the 1 GB central DuckDB remains byte-identical to its recorded baseline and backup.

The controller now derives sensitive runtime binding from exact source AST, requires exact active import edges and function/return/conditional-call semantics, consumes that evidence in closure validation, separates exact branch-head CI from a two-direct-parent merge ref, and validates local and remote registry identities.

This closes the internal remediation findings but does not self-issue a new external audit verdict. The prior `NOT_PASSED_REWORK_REQUIRED` remains authoritative until the targeted external reviewer examines the new GitHub refs and receipts. `strategy_candidate_available=false`.
