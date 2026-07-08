# WINDOWS_WSL2_MATERIALIZED_FEATURE_STRATEGY_LAB_R22_20260708

## Classification

Ordinary research-only strategy diagnostics batch after R21/C1 closeout.

## Evidence basis

R20_V2 established source review, experiment memory, and failure memory but still had no wide-eligible strategy. R21/C1 materially improved the evidence base by producing row-backed data:

- ETF amount/turnover rows: 32,482.
- ETF NAV/premium evidence: partial; still unresolved/limited.
- pass77 A-share feature rows: 136,767.
- global/news/macro context rows: 100.
- fixed features tested: peg_proxy, funds_flow_proxy_score, hot_money_proxy_score, amount_z20, turnover_z20.
- fixed-feature diagnostics: 5 rows, validation positive for funds/hot-money/amount/turnover but test negative.
- ETF R21 delta rows remained unstable with amount/turnover context.
- Wide research eligibility remains 0.
- Strategy candidate availability remains false.

## Objective

Use the newly materialized ETF amount/turnover rows and pass77 A-share feature rows for focused, limitation-aware strategy diagnostics. This is no longer source-review or rule-cleanup work. Do not revisit controller architecture or gate cleanup unless a concrete blocker appears.

## Boundaries

Research-only. No actionable output, no candidate promotion, no readiness/product-route activation, no daily signal push, no raw-data migration into controller, no active schema/registry activation, no credential output, no full-frame wide3068, no test-result parameter selection.

## Lane 0 - Evidence freeze and import

- R22-0-1: Freeze C1/R21 materialized evidence and limitation board.
- R22-0-2: Import C1/R21 rows and diagnostics into experiment store.
- R22-0-3: Update failure memory with R21 ETF instability and A-share validation/test divergence.

Deliverables:

- reports/workspace_dispatch/r22_c1_r21_evidence_freeze_20260708.md
- reports/workspace_dispatch/r22_c1_r21_evidence_freeze_20260708.json
- reports/workspace_dispatch/r22_experiment_store_import_20260708.md
- reports/workspace_dispatch/r22_failure_memory_update_20260708.md

## Lane 1 - ETF amount/turnover strategy diagnostics

Use the 32,482 ETF amount/turnover rows. Do not rerun earlier ETF grids without new filters.

- ETF-R22-1: Amount/turnover data-quality and liquidity bucket audit.
- ETF-R22-2: Reinterpret R19/R20 44 ETF rows under amount/turnover liquidity constraints.
- ETF-R22-3: Liquidity-aware ETF rotation diagnostics.
- ETF-R22-4: Turnover-throttled ETF rotation diagnostics.
- ETF-R22-5: Defensive-fallback and drawdown-control ETF diagnostics.
- ETF-R22-6: ETF NAV/premium public-source retry plan or explicit field-unavailable record.
- ETF-R22-7: ETF research board v4.

Deliverables:

- reports/workspace_dispatch/etf_r22_amount_turnover_quality_audit_20260708.md
- reports/workspace_dispatch/etf_r22_liquidity_aware_rotation_diagnostics_20260708.md
- reports/workspace_dispatch/etf_r22_turnover_throttled_rotation_diagnostics_20260708.md
- reports/workspace_dispatch/etf_r22_defensive_drawdown_diagnostics_20260708.md
- reports/workspace_dispatch/etf_r22_nav_premium_public_source_status_20260708.md
- reports/workspace_dispatch/etf_r22_research_board_v4_20260708.csv

## Lane 2 - pass77 fixed-feature strategy lab

Use the 136,767 validated pass77 feature rows. Focus on why validation was positive but test was negative.

- A-R22-1: pass77 feature quality and timing audit.
- A-R22-2: Decile/IC/stability diagnostics for the five fixed features.
- A-R22-3: Validation/test divergence attribution.
- A-R22-4: Opposite-signal and neutralized-signal diagnostics.
- A-R22-5: Regime-conditioned fixed-feature diagnostics using global/news/macro context.
- A-R22-6: Pair and small triple combinations using only fixed pre-registered families.
- A-R22-7: Walk-forward and bootstrap stress for top fixed-feature rows.
- A-R22-8: pass77 research board.

Deliverables:

- reports/workspace_dispatch/a_share_r22_pass77_feature_quality_audit_20260708.md
- reports/workspace_dispatch/a_share_r22_fixed_feature_ic_decile_stability_20260708.csv
- reports/workspace_dispatch/a_share_r22_validation_test_divergence_attribution_20260708.md
- reports/workspace_dispatch/a_share_r22_opposite_neutralized_signal_diagnostics_20260708.csv
- reports/workspace_dispatch/a_share_r22_regime_conditioned_fixed_feature_diagnostics_20260708.csv
- reports/workspace_dispatch/a_share_r22_pair_triple_fixed_feature_diagnostics_20260708.csv
- reports/workspace_dispatch/a_share_r22_walk_forward_bootstrap_fixed_feature_20260708.md
- reports/workspace_dispatch/a_share_r22_pass77_research_board_20260708.csv

## Lane 3 - Feature expansion beyond pass77, only if source evidence supports it

Do not treat pass77-only success as market-wide evidence. Try to expand materialized rows to date-gap 121 / overlap 198 / wider 3068 only if source health and lineage are clear.

- A-R22-9: Materialization expansion feasibility report for date-gap 121, overlap 198, and wider 3068.
- A-R22-10: Field-by-field source lineage for proxy vs direct features.
- A-R22-11: Direct public funds-flow validation smoke.

Deliverables:

- reports/workspace_dispatch/a_share_r22_materialization_expansion_feasibility_20260708.md
- reports/workspace_dispatch/a_share_r22_feature_lineage_proxy_vs_direct_20260708.csv
- reports/workspace_dispatch/a_share_r22_public_funds_flow_validation_smoke_20260708.md

## Lane 4 - Global/news/macro regime context

Use existing 100 context rows and 13-symbol global regime support as context only.

- GNM-R22-1: Align global/news/macro context calendar to ETF and pass77 A-share dates.
- GNM-R22-2: Test whether context explains validation/test divergence.
- GNM-R22-3: Produce context-only limitation matrix.

Deliverables:

- reports/workspace_dispatch/gnm_r22_context_calendar_alignment_20260708.csv
- reports/workspace_dispatch/gnm_r22_divergence_explanation_20260708.md
- reports/workspace_dispatch/gnm_r22_context_limitation_matrix_20260708.md

## Lane 5 - Conditional probes

Only after lanes 1-4 complete.

- STRAT-R22-1: Research prequalification board.
- STRAT-R22-2: Conditional local-cache probe or skip.
- STRAT-R22-3: Conditional wider research probe or skip. Full-frame wide3068 remains forbidden.

Allowed labels:

- R22_LOCAL_RESEARCH_PROBE_ELIGIBLE
- R22_WIDE_RESEARCH_PROBE_ELIGIBLE
- BLOCKED_BY_VALIDATION_TEST_DIVERGENCE
- BLOCKED_BY_INSTABILITY
- BLOCKED_BY_COST_OR_TURNOVER
- BLOCKED_BY_DATA_LIMITATION
- NO_R22_RESEARCH_PROBE_ELIGIBLE

Deliverables:

- reports/workspace_dispatch/strategy_r22_prequalification_board_20260708.csv
- reports/workspace_dispatch/strategy_r22_local_probe_or_skip_20260708.md
- reports/workspace_dispatch/strategy_r22_wide_probe_or_skip_20260708.md

## Lane 6 - Support repos

market_data:

- MD-R22-1: Update research contract for materialized-row diagnostics and probe labels.
- MD-R22-2: Overclaim regression for local/wide research probe labels.

strategy_work:

- SW-R22-1: Materialized feature strategy lab memo.
- SW-R22-2: Final sync after accepted callbacks.

quant-proj:

- QP-R22-1: Intake and dispatch.
- QP-R22-2: Result summary and closeout.

## Validation

- JSON parse PASS.
- git diff check PASS.
- focused pytest PASS if code changed.
- overclaim scan PASS.
- experiment store update PASS.
- failure memory update PASS.
- source health PASS before any source-heavy work.
- No duplicate search without new evidence.
- No full-frame wide3068.
- No direct signal use from news/macro.
- No candidate promotion or actionable output.

## Stop conditions

- New strategy diagnostics attempted before C1/R21 evidence import.
- pass77 diagnostics promoted beyond pass77 evidence scope.
- ETF NAV/premium still missing but limitation label omitted.
- validation-positive/test-negative divergence ignored.
- old R19/R20 grids repeated without amount/turnover or other new evidence.
- direct news/macro signal use.
- test-result parameter selection.
- full-frame wide3068 attempted.
- route/readiness/registry/schema/trading path attempted.
- credential/auth/secret required.

## Callback envelope

Return a callback with batch id, repo, branch, commit, tree, tasks completed, artifacts, validation, materialized data status, diagnostics status, eligible count, candidate availability, boundary result, fixes required, and next source action.
