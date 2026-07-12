# Remediation R1 Re-audit Brief

## Status

`TARGETED_REAUDIT_PENDING / EXTERNAL_REAUDIT_NOT_PASSED / CHANGES_REQUESTED`

The external re-audit in `EXTERNAL_REAUDIT_VERDICT_20260712.md` returned `NOT_PASSED`, one new High (RA-001), one Medium (RA-002), and one external-evidence blocker (EA-001). This package records the targeted rework; it does not overwrite or self-upgrade that verdict. `strategy_candidate_available=false` remains fixed.

No new strategy family, parameter search, LLM factor search, provider ingestion, frozen-outcome rerun, recommendation, candidate promotion, broker/order/paper/live/auto path, or strategy result was executed during remediation. US31/US36/US41/US46, Family66 and the old Family68 packet were not reopened.

## What changed

The finding-by-finding evidence is in `FINDING_CLOSURE_MATRIX.json`. The principal closures are:

- F-001: the database actually opened is descriptor/inode/hash bound; the full label is purged across splits before validation; publication is validated and atomic with rollback.
- F-002: test provenance is rejected at both the A10 runner and sink; no test input can write a non-test ticket or ledger.
- F-003: factor results bind by position, experiment/data/code/winner identities are fail closed, and the one frozen test evaluates the selected winners. Three adversarial review rounds were required before acceptance.
- F-004: missing, naive, future or revision-unsafe `available_at` cannot enter strict PIT.
- F-005: default research interfaces expose no actionable HITL/manual-fill command; retained disabled code is explicitly classified.
- F-006: schema collectors reject hardlinks, symlinks and root-to-leaf races, and publish only through a validated atomic replacement.
- F-007: `MANIFEST_VALID` and `EXECUTION_ATTESTED` are distinct; a separate acceptance task replayed 39 tests/commands and verified all logs and identities.
- F-008/RA-001/RA-002: the active CSV factory, qualification and readiness paths now use one `CsvImporterProvider`; caller-controlled `real_data` state is removed; runtime config and provenance bytes are controller-pinned; empty, malformed, escaping and conflicting inputs fail closed. Exact paths, Git blobs, test node IDs and factory bindings are recorded in the closure matrix.
- F-009: the closure path is corrected to `analysis/a_share_breakout60_lowvol_volume_event_methodology_recompute.py` and bound to audited/fixed blobs and exact test nodes. F-013 still rejects silent PBO remainder loss.
- F-010: all seven repositories pin Actions and hash-locked dependencies, expose three separate required jobs, and report zero unexpected skips at their exact commits.
- F-012: all 22 unresolved historical binaries are enumerated and absent from the final remediation refs; licensed controlled fixtures are content-addressed.
- F-011: the final step creates one checksum-bound controller root whose executable validator lives at a separate immutable controller code root, avoiding a false self-referential commit claim.

## Invalidated evidence and non-reopening rule

`ARTIFACT_INVALIDATION_AND_SUPERSESSION_LEDGER.json` preserves old paths and SHA-256 identities as invalidated evidence. Old A-share R21 descendants, affected QRL factor-miner outputs, test-derived A10 tickets, unsafe market-data schema publications and the Family66 verification-ambiguous summary are not overwritten and cannot be used to reopen a strategy.

The A-share repair was exercised twice in isolated private temporary roots against the same read-only local database: 136,767 rows, 77 symbols, 2,779 cross-boundary rows, zero non-null crossing labels, identical Parquet/report/normalized-manifest hashes, and zero retained temporary data. The owner subsequently issued a single-use authorization for publication to a controlled data room. `DATA_ROOM_EXTERNAL_ACCESS_INDEX_20260712.json` binds a read-only inventory, complete checksum chain, verification commands, publisher Git bundle and source archive. All ten assets are also published in private repository `2604714984-prog/a-share-canonical-evidence-data-room`, release `a-share-canonical-evidence-20260712`; GitHub-reported SHA-256 digests match the local manifest. Row-level data remains outside public Git and does not constitute strategy evidence. EA-001 remains open until the external reviewer obtains private access and returns an independent byte-verification receipt.

## Capability boundary

`CAPABILITY_MATRIX.json` and `CAPABILITY_BOUNDARY_ADR.md` are machine-checked against the code. The current boundary is research/evidence only. Disabled source code is not described as absent; it is described as retained, non-default and non-authorizing. Automatic broker, order, paper, live and auto execution remain disabled.

## Data and software supply chain

- `BINARY_ARTIFACT_PROVENANCE_LICENSE_MANIFEST.json` records the 22 historical files, removal from current refs, and the explicit no-history-rewrite decision pending separate governance authority.
- `DEPENDENCY_SBOM_INDEX.json` binds seven strict CycloneDX 1.6 SBOMs to exact repository commits and lockfiles.
- `SECRET_SCAN_INDEX.json` is redacted by construction. It discloses one historical credential candidate in QRL without exposing its value. `CREDENTIAL_REVOCATION_ATTESTATION.json` records the account owner's official-console deletion; the revoked bytes remain in Git history and are not operationally usable.
- `CI_REQUIRED_RUNS.json` binds 21 required job results to exact commits.

## Highest-value reproductions for the external reviewer

1. Supply database A while the global path points at B; verify only A's opened FD identity is recorded and read.
2. Swap the database path during query; verify failure before publication.
3. Inject a post-rename failure; verify the accepted path is removed or quarantined by identity.
4. Send test A10 candidates directly to the emitter; verify rejection and an unchanged real ledger.
5. Use a non-contiguous factor index; compare positional output and verify the frozen test receives every selected winner.
6. Replace an ancestor directory, data file or winner after validation; verify the QRL identity ledger rejects it.
7. Provide null, naive, future and revised corporate-action availability; verify strict PIT is unavailable.
8. Point a schema output at a database hardlink/symlink and race an ancestor; verify the database and unrelated victim remain unchanged.
9. Forge test counts, reuse stale logs or drift the interpreter/lock/commit; verify Luna acceptance fails.
10. Add an unregistered binary or remove a controlled-fixture license/hash; verify CI fails.
11. Change capability documentation without code/matrix agreement; verify CI fails.
12. Change any checksummed final artifact or immutable branch ref; verify the final-root/checksum validator fails.
13. Reproduce the four RA-001 attacks through `usq.data.factory.get_provider("csv")`; verify all fail closed and readiness remains development-only without both config and provenance pins.
14. Obtain read-only data-room access, run the supplied EA-001 commands, and compare the returned receipt with `DATA_ROOM_EXTERNAL_ACCESS_INDEX_20260712.json`.

## Authoritative entrypoint and transport model

`FINAL_CONTROLLER_ROOT.json` is the only authoritative semantic root. `CHECKSUMS.sha256` binds it and every supporting artifact. The root binds targeted-rework controller code to immutable branch `agent/remediation-targeted-reaudit-code-root-r2-20260712` at commit `4df14a054871dba2517bf9d4d426820d4cf3ea50`, PR 13, exact-head CI `29198065747` (3/3 success). The later package commit is only the transport that contains the root and checksum chain. This separation is deliberate because a file cannot truthfully contain the Git commit hash that contains that same file.

## Post-shadow integration reconciliation

`us_stock_30w` PR 7 was reconciled with `master` after the first shadow audit. The resulting head `73222d965f3785f457cecb73e9a2392554521e66` is `CLEAN / MERGEABLE`, passed 180 full and 175 focused tests with zero skips, two independent reviews, and exact-head CI `29191481613` with 3/3 jobs. It did not reopen any strategy outcome.

## Targeted re-audit state

The account owner revoked the historical DeepSeek credential; this remains an owner attestation, not provider-independent confirmation. Optional Git-history rewriting remains a separate governance choice.

RA-001 and RA-002 are internally closed by US Monitor commit `44557c39001c90201a4ab51ce7dcff1595b10642`, PR 6, full 656/656 and focused 54/54 tests, and exact-head CI `29197919583` (3/3 success). The previous shadow-audit F-008 conclusion is historical evidence and is superseded by the external finding plus targeted rework.

EA-001 is prepared but not closed: the external reviewer must receive the controlled bytes and return an independent verification receipt. The correct controller state is `TARGETED_REAUDIT_PENDING`, and `FINAL_EXTERNAL_AUDIT_VERDICT=NOT_PASSED` remains in force until the targeted reviewer returns a new verdict.
