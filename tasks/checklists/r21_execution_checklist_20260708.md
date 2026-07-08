# R21 Execution Checklist

Batch: `WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708`

## Preconditions

- [ ] Read R21 spec.
- [ ] Read R20_V2 external audit result.
- [ ] Freeze R20 evidence and limitations.
- [ ] Import R20 outputs into experiment store and failure memory.
- [ ] Run source-health before fetch-heavy work.

## ETF Lane

- [ ] Attempt bounded public/no-secret ETF amount/NAV/premium materialization.
- [ ] If unavailable, preserve explicit limitation labels.
- [ ] Do not rerun R19 grid v2 or R20 delta search without new field evidence.
- [ ] Run only bounded delta diagnostics or emit skip.

## A-share Feature Lane

- [ ] Materialize PEG rows only after source-health PASS.
- [ ] Materialize event/funds/hot-money rows only after source-health PASS.
- [ ] Write `features_daily_v2_research` manifest.
- [ ] Audit local rows for dates, symbols, duplicate keys, missingness, and provenance.
- [ ] Skip strategy diagnostics if no validated local feature rows exist.

## Global / News / Macro

- [ ] Create date-indexed global regime rows if source-health passes.
- [ ] Create date-indexed news/macro context rows if source-health passes.
- [ ] Preserve `direct_signal_use=false`.

## Boundary

- [ ] No recommendation/advice.
- [ ] No ticket or eligibility candidate.
- [ ] No strategy candidate promotion.
- [ ] No readiness or product-route activation.
- [ ] No market_data activation.
- [ ] No broker/order/paper/live/auto.
- [ ] No daily signal push.
- [ ] No raw-data migration into `quant-proj`.
- [ ] No active schema/registry change.
- [ ] No credential or secret output.

## Validation

- [ ] JSON parse PASS.
- [ ] `git diff --check` PASS.
- [ ] Focused pytest PASS if code/tests changed.
- [ ] `agent_safety_check.py` PASS where applicable.
- [ ] Forbidden overclaim scan PASS.
- [ ] Manifest/count/hash evidence recorded for fetched/written artifacts.
- [ ] Callback envelope generated.
