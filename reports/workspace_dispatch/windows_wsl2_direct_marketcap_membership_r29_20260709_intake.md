# WINDOWS_WSL2_DIRECT_MARKETCAP_MEMBERSHIP_R29_20260709 Intake

Classification: ordinary research-only evidence completion batch.

## Trigger

R28 completed row-level SmallCap evidence but remained `EVIDENCE_INCOMPLETE` because direct market-cap membership was unavailable. The next task must materialize direct market-cap membership snapshots or explicitly confirm that direct public/no-secret evidence is unavailable.

## Baseline

- R28 row-level pre-trade signal matrix rows: 732,793.
- R28 universe membership proxy snapshot rows: 732,793.
- R28 leakage/timing audit: PASS_WITH_MARKET_CAP_PROXY_LIMITATION.
- local_research_probe_eligible_count=0.
- strategy_candidate_available=false.

## Required reads

- `tasks/in_progress/windows-wsl2-direct-marketcap-membership-r29-20260709/spec.md`
- `reports/agent_handoff/windows_wsl2_direct_marketcap_membership_r29_dispatcher_prompt_20260709.md`
- R28 source/final-sync artifacts.

## Boundary

Research-only. No actionable output, no candidate promotion, no readiness/product-route activation, no daily signal, no raw-data migration into controller, no active schema/registry activation, and no credential output.
