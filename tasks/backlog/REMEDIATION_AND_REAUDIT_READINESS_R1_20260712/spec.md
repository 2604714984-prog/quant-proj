# REMEDIATION_AND_REAUDIT_READINESS_R1_20260712

Status: `IN_PROGRESS`

This is a remediation release, not a strategy research or feature release.
The controlling external verdict is `FAIL_REMEDIATION_REQUIRED` with 13
findings: two Critical, four High, six Medium, and one Low.

## Findings

| ID | Severity | Scope |
| --- | --- | --- |
| F-001 | Critical | A-share evidence database identity, real split purge, validation-before-publish |
| F-002 | Critical | A10 test provenance reaching a non-test ticket ledger |
| F-003 | High | Quant Lab positional alignment and final winning-factor evaluation |
| F-004 | High | US30W strict PIT `available_at` enforcement and downgrade |
| F-005 | High | Research-only versus retained HITL/manual-fill capability boundary |
| F-006 | High | `market_data` hardlink/symlink/race-safe atomic output |
| F-007 | Medium | Manifest validation versus executed-command attestation |
| F-008 | Medium | US CSV table/path confinement and conflicting duplicate rows |
| F-009 | Medium | Family 66 data-byte verification bypass classification |
| F-010 | Medium | CI dependency/action pinning and unexpected integration skips |
| F-011 | Medium | Single immutable controller audit root and stale-reference rejection |
| F-012 | Medium | Public binary and row-level data provenance/license governance |
| F-013 | Low | PBO non-divisible sample remainder handling and disclosure |

## Hard boundaries

- No new strategy, parameter search, LLM factor iteration, or frozen-outcome rerun.
- No provider call, network ingestion, database/cache/schema/raw write, or new
  row-level data publication.
- No recommendation, actionable ranking, real ticket emission, candidate or
  readiness promotion, product route, broker, order, paper, live, or auto path.
- Do not read, copy, print, or commit credentials.
- Preserve affected historical artifacts by hash; never overwrite them.
- Critical and High findings require an implementer, a separate semantic
  reviewer, a separate final acceptor, negative tests, and a hash-bound
  dynamic reproduction.

## Completion

Completion requires all original Critical/High findings closed without risk
acceptance, all 13 findings represented in the closure matrix, cross-repository
reproduction from a single immutable controller root, and a clean independent
shadow audit. Engineering-self-check CI alone is insufficient.
