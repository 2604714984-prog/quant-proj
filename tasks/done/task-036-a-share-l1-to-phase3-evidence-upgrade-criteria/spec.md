# TASK-036 A-share L1 To Phase3 Evidence Upgrade Criteria

Status: `ASSIGNED`
Target project: `A_Share_Monitor`
Agents: `Reasonix-DB` first, then `Codex-Dev` review if implementation or source-project contract is needed
Priority: `P1`
Permission: `L0_RESEARCH_DIAGNOSTIC`

## Goal

Define the criteria for when the A-share L1 local 1000-symbol snapshot can be considered ready to enter a future Phase3 evidence stage, without performing DB writes, network ingest, readiness upgrades, or ticket/recommendation work.

## Inputs

- `TASK-030` DuckDB diagnosis: A-share commit `ce26b391e0eebf5eca35aae974052a236cdf5bca`, tree `f2819654363f116f45d9dd171492c4cb9d227c6d`.
- `TASK-029` A11 unblock plan from the same commit.
- `TASK-007` L1 snapshot `a_expand_20260704_l1_local1000_0317`.
- `TASK-008` market_data readiness stayed Level 1 / product-read blocked.

## Must Define

- minimum suspension capability evidence before Phase3 can start;
- minimum limit-price coverage evidence before Phase3 can start;
- lineage requirements between L1 repaired snapshot, A11 candidates, and market_data route;
- required manifests, hashes, row counts, and warning handling;
- stop conditions that keep Phase3 blocked;
- which future actions require unique pre-execution `HG-EXEC-TASK-*` records;
- Codex-Dev validation required before any source-project promotion.

## Expected Outputs

- Reasonix-DB draft: `reports/deepseek_db/task_036_a_share_l1_to_phase3_upgrade_criteria.md`
- Reasonix-DB JSON: `reports/deepseek_db/task_036_a_share_l1_to_phase3_upgrade_criteria.json`
- transcript: `reports/workspace_dispatch/reasonix_db_task_036_20260704.jsonl`
- optional Codex-Dev source-project review if dispatched after the Reasonix draft.

## Forbidden

No DB write, migration, canonicalization write, network ingest, registry activation, readiness upgrade, Phase3 execution, recommendation, ticket emission, broker/order/paper/live/auto, `.env` access, key output, or secret handling.
