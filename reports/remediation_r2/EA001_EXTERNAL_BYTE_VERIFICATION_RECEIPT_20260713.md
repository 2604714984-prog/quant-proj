# EA-001 independent byte-verification receipt

Verdict: `EA001_EXTERNAL_BYTE_VERIFICATION_PASS`

At `2026-07-13T02:51:14+08:00`, an independent read-only reviewer used a fresh WSL2 temporary root to download all ten assets from the private GitHub release. Ten of ten sizes and SHA-256 digests matched; all nine packaged checksum entries passed and the checksum file's own digest matched the controller index.

`git bundle verify` reported complete history. A fresh clone was clean, passed `git fsck --full --strict`, and resolved to commit `3903977d2480a5ad9be67c4c267cd2a5c5a4bdb8`, tree `40de1564d87c71e3b7695b631fef13d668637ac2`. Builder, embedded commit, archive stream and fresh `git archive` identities matched.

Independent DuckDB in-memory recomputation returned 136,767 rows, 77 symbols, dates 2018-01-02 through 2026-07-03, zero duplicate keys, 2,779 crossing rows, all 2,779 purged, zero non-null crossing labels, and zero label/split/purge-flag/purge-reason mismatches. Aggregate `mismatch_rows=0`. Source database, universe CSV and authorization/receipt/manifest cross-binding checks passed.

All temporary downloads and clones were deleted. No repository edit, commit, push, database write or strategy execution occurred. This receipt closes only EA-001 evidence accessibility and byte verification; it does not itself declare the overall external audit passed. `strategy_candidate_available=false`.
