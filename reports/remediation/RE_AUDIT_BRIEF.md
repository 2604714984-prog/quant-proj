# Remediation R1 Re-audit Brief

## Status

`REMEDIATION_IMPLEMENTED / SHADOW_AUDIT_ACCEPTED / FINAL_EXTERNAL_AUDIT_NOT_PASSED`

This package does not claim that the external audit passed. It records the remediation of the 13 findings from the `REJECT_AS_FINAL_AUDIT_VERDICT / ACCEPT_AS_AUDIT_INPUT` review and keeps `strategy_candidate_available=false`.

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
- F-008/F-009/F-013: CSV traversal/conflicts, the Family66 canonical verification bypass, and silent PBO remainder loss now fail closed.
- F-010: all seven repositories pin Actions and hash-locked dependencies, expose three separate required jobs, and report zero unexpected skips at their exact commits.
- F-012: all 22 unresolved historical binaries are enumerated and absent from the final remediation refs; licensed controlled fixtures are content-addressed.
- F-011: the final step creates one checksum-bound controller root whose executable validator lives at a separate immutable controller code root, avoiding a false self-referential commit claim.

## Invalidated evidence and non-reopening rule

`ARTIFACT_INVALIDATION_AND_SUPERSESSION_LEDGER.json` preserves old paths and SHA-256 identities as invalidated evidence. Old A-share R21 descendants, affected QRL factor-miner outputs, test-derived A10 tickets, unsafe market-data schema publications and the Family66 verification-ambiguous summary are not overwritten and cannot be used to reopen a strategy.

The A-share repair was exercised twice in isolated private temporary roots against the same read-only local database: 136,767 rows, 77 symbols, 2,779 cross-boundary rows, zero non-null crossing labels, identical Parquet/report/normalized-manifest hashes, and zero retained temporary data. This is classified only as `ENGINEERING_SELF_CHECK`; canonical/public row-level evidence publication remains disabled.

## Capability boundary

`CAPABILITY_MATRIX.json` and `CAPABILITY_BOUNDARY_ADR.md` are machine-checked against the code. The current boundary is research/evidence only. Disabled source code is not described as absent; it is described as retained, non-default and non-authorizing. Automatic broker, order, paper, live and auto execution remain disabled.

## Data and software supply chain

- `BINARY_ARTIFACT_PROVENANCE_LICENSE_MANIFEST.json` records the 22 historical files, removal from current refs, and the explicit no-history-rewrite decision pending separate governance authority.
- `DEPENDENCY_SBOM_INDEX.json` binds seven strict CycloneDX 1.6 SBOMs to exact repository commits and lockfiles.
- `SECRET_SCAN_INDEX.json` is redacted by construction. It discloses one unresolved historical credential candidate in QRL without exposing its value.
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

## Authoritative entrypoint and transport model

`FINAL_CONTROLLER_ROOT.json` is the only authoritative semantic root. `CHECKSUMS.sha256` binds it and every supporting artifact. The root binds executable controller code to immutable branch `agent/remediation-reaudit-code-root-r1-20260712` at commit `8247e619398a235911edeeaaaa3785dade4f9fe4`; the later package commit is only the transport that contains the root and checksum chain. This separation is deliberate because a file cannot truthfully contain the Git commit hash that contains that same file.

## Disclosed blockers before launching another external audit

1. The one redacted QRL historical credential candidate must be revoked/rotated by its owner. Any optional history rewrite requires separate governance authority and a coordinated clone/PR invalidation plan.
2. Canonical/public A-share row-level evidence remains disabled. The private deterministic engineering reproduction proves the repaired mechanics but does not itself authorize publication or create canonical strategy evidence.
3. `us_stock_30w` PR 7 has an integration conflict with `master`. The exact audited head is independently accepted and CI-green, but any conflict resolution creates a new head that must be revalidated.

The independent code/dynamic and package/governance shadow audits both finished with zero new Critical or High findings. The package audit first rejected two stale representation claims; those were repaired at `5f9bde1498f614890aecadb7dac6be07314194d5` and independently reaccepted.

Until the three disclosed blockers are resolved, the correct state is not `REAUDIT_READY`; it is `REMEDIATION_IMPLEMENTED_BLOCKED`, and `FINAL_EXTERNAL_AUDIT_VERDICT=NOT_YET_PASSED`.
