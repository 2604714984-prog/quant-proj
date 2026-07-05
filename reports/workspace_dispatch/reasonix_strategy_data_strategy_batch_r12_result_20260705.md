# Reasonix-Strategy R12 Research Draft

Created: 2026-07-05
Role: Reasonix-Strategy
Model: `deepseek-v4-pro`
Effort: `high`
Transcript: `reports/workspace_dispatch/reasonix_strategy_data_strategy_batch_r12_run_20260705.jsonl`
Status: `RESEARCH_DRAFT`

## Verdict

Reasonix-Strategy treats R12 as diagnostic-only strategy research. It supports the R12 direction: separate in-snapshot temporal stress from true forward-holdout evidence, decompose amount-scale artifact risk, classify recovered-symbol fragility without ranking, and attribute US evidence-readiness bottlenecks without creating repair authorization or eligibility.

## A-Share Strategy Advisory

- `IN_SAMPLE_TEMPORAL_STRESS_NOT_FORWARD_HOLDOUT` must be used for all in-snapshot temporal splits.
- In-snapshot temporal stress can reject obvious overfit but cannot confirm future performance.
- Amount-scale decomposition must avoid future-range or post-hoc aggregate statistics.
- Bin edges and linearization parameters should be frozen before evaluation to avoid new leakage.
- Fragility taxonomy must remain diagnostic and must not become a ranking/filtering mechanism.

## US Strategy Advisory

- US evidence-readiness bottleneck attribution should separate stale frequency, look-ahead construction, survivorship contamination, and noise dominance.
- US outputs should be blocker/evidence maps only, not repair approval or candidate quality promotion.
- Any suggestion that signal strength can substitute for metadata/crosscheck evidence should be rejected.

## strategy_work Advisory

`SW-R12-1` should remain dependency-gated. Final memo sync should happen only after A-share, US, and market_data R12 source acceptances are available. If source results are not accepted, strategy_work should stop at a draft-only note.

## Risks

- Temporal splits may look strong while still being in-sample.
- Amount-scale decomposition can create a new leakage path if blinding is not verified.
- Fragility taxonomy can drift into a ranking if thresholds are selected after seeing performance.
- US bottleneck attribution is an evidence-gap map, not a repair plan.

## Codex-Dev Handoff

- Implement A-R12-2 as stress-test evidence, not holdout validation.
- Implement A-R12-3 with pre-frozen scale/liquidity/size controls using existing fields only.
- Implement A-R12-4 as a non-ranked taxonomy.
- Implement US-R12-4 as a bottleneck attribution report with no ticket or eligibility output.
- Gate SW-R12-1 on accepted source results.

## Non-Authorization

This Reasonix-Strategy draft is not buy/sell advice, a recommendation, an eligibility signal, or a production readiness declaration. It does not authorize ticket emission, `PENDING_HUMAN_REVIEW`, product route activation, broker/order/paper/live/auto, DB write, network ingest, schema change, data migration, registry modification, readiness change, or provider persistence.
