# TASK-035 US Eligibility Gate Object Contract

Status: `ASSIGNED`
Target project: `US_Stock_Monitor`
Agent: `Codex-Dev`
Priority: `P1`
Permission: `L0_RESEARCH_DIAGNOSTIC`

## Goal

Create or verify a source-project contract for the US eligibility gate object so the system cannot confuse qualitative metadata, evidence gaps, or partial precheck state with a ticket-eligible recommendation.

## Inputs

- `TASK-031` metadata gap repair plan: US commit `4d4e21f35374fd2aca6c6f756830ab9d1b353593`, tree `a1172367829db0a0545701b7e02e194b0b38cf27`.
- `TASK-032` qualitative feedback schema review: US commit `30a4dffb8d84c61be812dc1d36ede1649e2f60b6`, tree `dfb7efd8642c99cea74b2b1ffbc4f279ff54b60e`.
- `TASK-024` eligibility blocker drilldown: US commit `04e7e6742a7fa87d04ea9a65ebc5cf6f0f55a3a7`.

## Must Prove

- `eligibility_candidate` remains `null` or absent until all source-project preconditions are satisfied.
- Qualitative feedback metadata from `TASK-032` cannot set `actionable_feedback=true`.
- Missing 44-symbol metadata from `TASK-031` continues to block expansion readiness and cannot be bypassed with synthetic defaults.
- `ticket_eligibility_candidate=false` and `ticket_emitted=false` are preserved when evidence or feedback remains incomplete.
- Broker/order/paper/live/auto flags are always false in the eligibility gate contract.

## Expected Outputs

- `reports/codex_dev/task_035_us_eligibility_gate_object_contract.md`
- optional JSON/static contract artifact if useful.
- focused tests committed if changed.

## Validation Expectations

- `python scripts/agent_safety_check.py`
- focused US eligibility / US-10 / US-11 / US-12 tests
- JSON parse validation if a JSON artifact is created
- `python -m usq smoke`
- `git diff --check`

## Forbidden

No runtime ingestion, recommendation, ticket emission, broker/order/paper/live/auto, DB write, network call, registry/readiness change, `actionable_feedback=true`, eligibility candidate creation for live use, `.env` access, key output, or secret handling.
