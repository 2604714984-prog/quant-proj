# WINDOWS_WSL2_SMALLCAP_DIRECT_MARKETCAP_R29_20260709 Intake

Classification: ordinary research-only direct market-cap evidence resolution batch.

## Trigger

R28 closed research-only evidence-incomplete/no-probe-eligible. The only remaining SmallCap local-probe blocker is missing direct market-cap membership snapshots.

## Baseline

- R28 row-level pre-trade signal matrix preserved.
- R28 universe membership snapshot uses amount/amount_ma20 proxy.
- Direct market-cap coverage is 0.0.
- local_research_probe_eligible_count=0.
- wide_research_probe_eligible_count=0.
- strategy_candidate_available=false.

## Required reads

- `tasks/in_progress/windows-wsl2-smallcap-direct-marketcap-r29-20260709/spec.md`
- `reports/agent_handoff/windows_wsl2_smallcap_direct_marketcap_r29_dispatcher_prompt_20260709.md`
- R28 result summary and closeout.
- R28 signal matrix manifest and leakage/timing audit.

## Boundary

Research-only. No actionable output, no candidate promotion, no readiness/product-route activation, no daily signal, no raw-data migration into controller, no active schema/registry activation, and no credential output.
