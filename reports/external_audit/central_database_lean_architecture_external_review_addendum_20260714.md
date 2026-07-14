# External re-audit addendum: personal-quant central database architecture

## Status

`READY_FOR_INDEPENDENT_EXTERNAL_ARCHITECTURE_REVIEW`

This addendum extends, but does not modify or supersede, the hash-frozen consolidated package:

- consolidated review SHA-256: `18731af60d8d3727491edf40afd9781da07fb60b34fe5b621220e9cd90ebb0d0`;
- consolidated manifest SHA-256: `b77c6365a963ec0d49c8bdd3d32b4393f119d4edba8cbe56ef9c9816493513ca`.

The earlier package established that the database foundation existed. This addendum asks a different
question: **is that foundation and its operating process too complex for a personal quant project?**

## Actual project scale

- one owner and operator;
- one local WSL host;
- one local DuckDB warehouse;
- research-only use;
- no customers, service-level agreement, multi-tenancy, regulated production environment, or live
  trading route.

The reviewer must not assume institutional requirements that do not exist.

## Code under review

- repository: [`2604714984-prog/central-data-ingestion`](https://github.com/2604714984-prog/central-data-ingestion);
- visibility: private; an external reviewer needs authenticated collaborator access;
- draft PR: [central-data-ingestion #22](https://github.com/2604714984-prog/central-data-ingestion/pull/22);
- branch: `agent/central-db-lean-architecture-audit-20260714`;
- commit: `f2d401e42aa8f7cd17a14d94c039f45ba6546d9d`;
- tree: `6f9692d9efafe2ee0f3521d774635e45121aefde`;
- architecture request: [`PERSONAL_QUANT_LEAN_ARCHITECTURE_REVIEW_20260714.md`](https://github.com/2604714984-prog/central-data-ingestion/blob/f2d401e42aa8f7cd17a14d94c039f45ba6546d9d/docs/PERSONAL_QUANT_LEAN_ARCHITECTURE_REVIEW_20260714.md);
- machine evidence: [`central_database_personal_project_evidence_20260714.json`](https://github.com/2604714984-prog/central-data-ingestion/blob/f2d401e42aa8f7cd17a14d94c039f45ba6546d9d/reports/external_audit/central_database_personal_project_evidence_20260714.json).

No database, backup, raw provider payload, token, private key, private grant, or lock file is in the
review branch.

## Why this review is necessary

The current review branch contains:

- 19 production Python modules and 6,689 lines;
- 9 test files and 3,425 lines;
- 34 JSON profile/schema/packet/report artifacts;
- 5 deployment templates;
- 15,355 inserted lines since the initial repository commit.

The system has overlapping SQLite staging, Gate-B copy/swap publication, routine append, remediation,
authorization, and Replay qualification paths. The largest two writers total 2,396 lines before their
tests.

By contrast, the first successful Replay append on 2026-07-14 needed two GET requests, one backup,
one writer lock, one transaction, and simple postchecks. It inserted 5,524 daily rows and 60 partial
daily-basic rows for `20260713`, with zero duplicate natural keys. The post-write database SHA-256 is
`936e1ee5230207b1ca59e1fd6245ad5a3c1dd957ae030441e8420c83e57a3869`.

The durable Replay adapter currently qualifies routes but retains zero rows. The successful append
used a bounded temporary bridge outside Git. This mismatch is evidence for review, not something the
package conceals.

## Questions for the external reviewer

1. Should the current system be `KEEP_AS_IS`, `SIMPLIFY_NOW`, or `REBUILD_MINIMAL`?
2. For each runtime module, classify it as `KEEP`, `SIMPLIFY`, `ARCHIVE`, or `DELETE`.
3. Are custom Ed25519 authorization, per-batch HG records, repeated independent acceptance, full-DB
   copies per profile/day, descriptor/path attack defenses, and multiple publisher paths justified
   for this single-user local project?
4. Can routine writes use this path instead?

   ```text
   provider adapter
       -> normalize/validate
       -> one writer lock and one backup
       -> one bulk DuckDB transaction
       -> duplicate/count/null/date checks
       -> one short run record
   ```

5. Which checks protect real risks, and which primarily create delay or duplicate context?
6. What is the smallest CI suite that catches material defects without generating repeated all-jobs-
   failed email noise?
7. Can the old SQLite collector, copy/swap publisher, one-time remediation code, inactive systemd
   templates, per-lane runtime reports, and duplicated authorization layers be archived or deleted?

## Expected response

Return:

- one overall architecture verdict;
- one module-level decision table;
- the minimum non-negotiable safety controls;
- a no-more-than-three-phase simplification plan;
- expected code/test/process reductions;
- concrete migration risks and rollback steps;
- a judgment on whether the current architecture is proportionate for one person.

Do not evaluate strategy quality or promote any strategy. This is an infrastructure maintainability
review. `strategy_candidate_available=false`.
