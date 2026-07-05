# Reasonix-Strategy R11 Research Draft

Created: 2026-07-05
Role: Reasonix-Strategy
Model: `deepseek-v4-pro`
Effort: `high`
Transcript: `reports/workspace_dispatch/reasonix_strategy_data_strategy_batch_r11_run_20260705.jsonl`
Status: `RESEARCH_DRAFT`

## Verdict

Reasonix-Strategy recommends holding evidence advancement until A-share forward-holdout validation, robust-candidate recovery diagnostics, peer-control stress expansion, and US signal-versus-evidence diagnostics are complete. No product or readiness promotion is authorized.

## A-Share Strategy Advisory

- `600177.SH` should be treated as an exploratory tracer, not a conviction candidate.
- Forward holdout must use a pure out-of-time period that was not used in R10 config selection.
- The three recovery variants should be pre-registered before execution:
  - `strict_v2`
  - `risk_control_balanced`
  - `liquidity_affordability_balanced`
- Peer-control stress should test sector-neutral reshuffles, volatility regimes, and liquidity dry-up periods to identify fragility.

## US Signal Vs Evidence Advisory

- R10 `0/60` and `0/61` outcomes may reflect weak signal, over-stringent filters, or evidence blockers.
- R11 should separate raw factor distributions and IC time series from evidence readiness.
- Filter relaxation should be diagnostic only, used to identify binding constraints rather than recover candidate lists for promotion.
- No US config promotion should occur until diagnostics show a minimal signal and the evidence blockers are addressed.

## Memo Sync Advisory

`strategy_work` should run final memo sync only after A-share, US, and market_data R11 source acceptances are available. It should document outcomes and open gaps, not signal promotion.

## Risks

- Single-symbol overfitting in A-share.
- Over-relaxing filters to recover noisy candidates.
- Data leakage through repeated round trips.
- US evidence gaps invalidating prior experiments after repair.
- Premature memo sync embedding draft hypotheses as accepted state.

## Codex-Dev Handoff

- Implement A-R11-1 forward-holdout validation.
- Implement A-R11-2 recovery variants with identical train/holdout splits.
- Implement A-R11-3 peer-control stress expansion.
- Implement US-R11-4 signal diagnostic before conservative filters.
- Gate SW-R11-1 memo sync on accepted source results.

## Non-Authorization

This Reasonix-Strategy draft is not buy/sell advice, a recommendation, an eligibility signal, or a production readiness declaration. It does not authorize ticket emission, `PENDING_HUMAN_REVIEW`, product route activation, broker/order/paper/live/auto, DB write, network ingest, schema change, data migration, registry modification, readiness change, or provider persistence.
