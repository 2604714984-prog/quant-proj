# User-Dispatch Prompt — DS US C2 R3 Engine and Allocator Fix

Copy the complete fenced prompt below into the independently controlled DS US conversation.

```text
RUN DS_US_C2_REMEDIATION_R3_ENGINE_ALLOCATOR_FIX_20260713

WORKSTREAM:
DS_US_RESEARCH_USER_CONTROLLED

TARGET REPOSITORY:
https://github.com/2604714984-prog/us_stock_30w

ACCEPTED R2 SOURCE ANCHOR:
branch: research/c2-remediation-r2-20260713
commit: e47d4155d4e2bace2c15ae22e53f66556d19d832

CREATE AND USE A NEW BRANCH:
research/c2-remediation-r3-20260713

EXTERNAL AUDIT SOURCE:
https://github.com/2604714984-prog/quant-proj/blob/3e0fbde8cc592b5d5044aa2ce5734e84b57bed9d/reports/agent_handoff/ds_c2r_r2_callbacks_external_audit_result_20260713.md

CONTROL AND INDEPENDENCE

The user exclusively controls this DS US research project.
Quant Manager, dispatcher, Codex, DS A-share, and other agents must not choose formulas,
assets, regime states, parameters, preferred winners, or conclusions.
Return the final callback, branch, full commit SHA, tree, artifacts, and validation to the user only.
Do not send the callback directly to Quant Manager or Codex.

R2 AUDIT STATUS

The R2 callback was externally rejected for strategy-system intake:

DS_US_C2R_CALLBACK_REJECTED_PARTIAL_REMEDIATION_INCOMPLETE_AND_ENGINE_INVALID
S2_CONTINUE_REQUIRED

Useful R2 work must be preserved:

- a row-backed daily US regime feature Parquet exists;
- the deterministic detector updates daily with past/current-only hysteresis;
- 11 hypotheses across four active families were preregistered;
- FORWARD_HOLDOUT_CONTAMINATED was correctly preserved;
- R2 disclosed adjusted-data, hard-switching, and probabilistic-detector limitations.

Do not rebuild the entire data foundation unless a reproducible defect is found.
This is a narrow R3 engine, formula-fidelity, allocator, and evidence remediation cycle.

PRIMARY OBJECTIVE

Correct the holdings engine and cost/cash accounting, use adjusted total-return data or a
hard blocker, faithfully implement the preregistered strategies, implement real static/soft/
hard/fallback allocators, update the regime snapshot from the latest completed market session,
and produce two schema-complete Strategy Intake Packets if system intake is requested.

==================================================
PART 0 — FREEZE R2 SOURCE ARTIFACTS
==================================================

Read and preserve:

reports/ds_us/remediation_r2/
reports/ds_us/remediation_r2/us46_holdings_based_engine.py
reports/ds_us/remediation_r2/build_regime_features.py
reports/ds_us/remediation_r2/c2_remediation_pipeline.py

Produce:

reports/ds_us/remediation_r3/r3_r2_source_freeze_20260713.md
reports/ds_us/remediation_r3/r3_failure_memory_import_20260713.json

Record:

- source commit;
- rule hash;
- data hashes;
- accepted R2 artifacts;
- externally rejected conclusions;
- exact R3 changes.

Do not overwrite R2 artifacts.

==================================================
PART 1 — FIX THE US46 HOLDINGS ENGINE
==================================================

The R2 engine remained in cash for the first 63 sessions and did not correctly remove
transaction costs from portfolio value.

Implement a correct holdings-based engine:

1. Allocate 50% QQQ / 50% GLD on the first eligible execution session.
2. Allow weights to drift between scheduled rebalances.
3. Rebalance every 63 trading sessions after the initial allocation.
4. Execute incremental net trades, not sell-all/buy-all, unless gross-turnover accounting is
   explicitly used and costed consistently.
5. Deduct transaction costs from cash and portfolio value.
6. Cost must equal 5 bps one-way on actual absolute traded notional.
7. Preserve shares, cash, prices, weights, notional, fees, and post-trade value.
8. Support fractional shares for research unless a separate lot-size rule is declared.
9. Use one documented execution price convention consistently.
10. No leverage, no shorting, no negative cash unless explicitly rejected.

Required reconciliation on every trade date:

pre_trade_cash
+ pre_trade_holdings_value
- transaction_cost
= post_trade_cash + post_trade_holdings_value

Required artifacts:

reports/runops/ds_us_c2r3_20260713/us46_holdings_daily.parquet
reports/runops/ds_us_c2r3_20260713/us46_rebalance_ledger.csv
reports/runops/ds_us_c2r3_20260713/us46_equity_daily.parquet
reports/ds_us/remediation_r3/us46_engine_reconciliation_20260713.json
reports/ds_us/remediation_r3/us46_rule_and_data_manifest_20260713.json

Required focused tests:

- first eligible session is invested;
- first 63 sessions are not left entirely in cash;
- rebalance count matches schedule;
- weights drift between rebalances;
- cost leaves the portfolio rather than remaining as cash;
- post-trade accounting identity holds;
- zero target-weight change produces zero trade and zero cost;
- incremental notional matches share changes;
- equity remains positive and dates monotonic;
- frozen parameters cannot change during the run.

No hard-coded `passed=True` test is allowed.

==================================================
PART 2 — ADJUSTED TOTAL-RETURN / CORPORATE-ACTION DATA
==================================================

Strict US46 validation requires adjusted total-return or corporate-action-corrected evidence.
Sina raw close may remain only as a forensic comparison.

Attempt bounded public/no-secret sources for QQQ, GLD, SPY, TLT, HYG, LQD, and required
sector ETFs. Acceptable evidence must include:

- adjusted close or total-return series;
- dividend treatment;
- split treatment;
- source metadata;
- retrieval timestamp;
- date range;
- missingness;
- hashes;
- cross-source smoke check where possible.

Do not treat one provider's rate limit as proof that adjusted data is unavailable.
Try a second accepted public/no-secret source or an already-local verified cache.

If adjusted total-return data still cannot be obtained, return:

BLOCKED_BY_ADJUSTED_TOTAL_RETURN_DATA

Under that blocker:

- US46 may remain `FROZEN_STATIC_HYPOTHESIS_ONLY`;
- do not output `FROZEN_US46_STATIC_BEST` as strict evidence;
- raw-close metrics must be labelled forensic-only;
- system intake readiness must be false.

Required artifacts:

reports/ds_us/remediation_r3/us_adjusted_data_manifest_20260713.json
reports/ds_us/remediation_r3/us_adjusted_vs_raw_diagnostic_20260713.csv
reports/ds_us/remediation_r3/us_corporate_action_audit_20260713.md

==================================================
PART 3 — FAITHFULLY IMPLEMENT PREREGISTERED SPECIALISTS
==================================================

The R2 diagnostic strategies did not match the preregistered formulas.
Implement the frozen R2 hypotheses faithfully.

Mandatory corrections:

- A1: frozen holdings-based US46 under the corrected engine.
- A2: dynamic rule based on QQQ versus its 200MA, switching between the preregistered
  70/30 and 30/70 allocations; not fixed 70/30.
- A3: breadth-conditioned allocation using the declared sector breadth rule; not fixed 80/20.
- B1: GLD-heavy + cash under its target selloff regime.
- B2: TLT + GLD barbell under its target selloff regime.
- C1: SPY + QQQ 50/50 under sideways regime.
- C2: SPY + cash buffer under sideways regime.
- C3: equal-weight the declared sector ETF universe; do not replace it with SPY/QQQ/GLD.
- D1: true SPY buy-and-hold with initial allocation and no periodic rebalance.
- D2: holdings-based SPY/TLT 60/40 with the declared rebalance schedule.
- Blocked PIT-fundamental or earnings families must remain blocked unless new PIT data exists.

For every strategy preserve:

- exact formula;
- regime condition;
- execution dates;
- weights;
- holdings;
- equity curve;
- turnover;
- costs;
- train/validation/test_diagnostic metrics.

Produce:

reports/ds_us/remediation_r3/r3_hypothesis_implementation_fidelity_20260713.csv
reports/ds_us/remediation_r3/r3_specialist_diagnostics_20260713.csv
reports/runops/ds_us_c2r3_20260713/specialist_equity_curves.parquet

Every active hypothesis must be faithfully implemented or explicitly blocked.

==================================================
PART 4 — INDEPENDENT TRAIN-FROZEN PROBABILISTIC DETECTOR
==================================================

The R2 EMA sidecar is a smoothed copy of deterministic labels and is not independent.
Do not report its agreement as independent-detector agreement.

Implement an independent detector using causal regime features, for example:

- Gaussian Mixture Model;
- Hidden Markov Model;
- train-fitted clustering;
- change-point model with train-frozen parameters.

Requirements:

1. Fit scaler/model on train only.
2. Freeze before validation.
3. Test is diagnostic-only.
4. Do not use deterministic states as the training target.
5. Preserve feature list, parameters, random seed, train dates, and model hash.
6. Generate out-of-sample probabilities/confidence.
7. Compare genuinely independent outputs.

If this cannot be implemented, emit:

PROBABILISTIC_DETECTOR_BLOCKED

and keep the regime-aware packet blocked.

Required artifacts:

reports/ds_us/remediation_r3/r3_probabilistic_detector_manifest_20260713.json
reports/ds_us/remediation_r3/r3_detector_agreement_matrix_20260713.csv
reports/ds_us/remediation_r3/r3_detector_oos_diagnostics_20260713.csv

==================================================
PART 5 — UPDATE THE CURRENT REGIME SNAPSHOT
==================================================

The R2 snapshot was as of 2025-12-31 and 194 days stale. It was not a current-market result.

Rebuild the snapshot from the latest completed US market session available at execution time.

Requirements:

- `as_of_market_date` equals latest actual market row;
- record retrieval timestamp;
- record staleness in calendar and trading days;
- do not use wall-clock date as market-data date;
- do not claim HIGH fit when required data dimensions are missing;
- distinguish current deterministic state, independent probabilistic state, confidence,
  candidate persistence, and confirmation lag;
- preserve FORWARD_HOLDOUT_CONTAMINATED for strategy selection.

Required artifact:

reports/ds_us/remediation_r3/us_current_regime_snapshot_20260713.json

Allowed fit labels:

US46_REGIME_FIT_HIGH
US46_REGIME_FIT_MODERATE
US46_REGIME_FIT_LOW
US46_REGIME_FIT_UNCERTAIN

This fit label is research context only, not advice.

==================================================
PART 6 — IMPLEMENT REAL STATIC / SOFT / HARD / FALLBACK ALLOCATORS
==================================================

The R2 hard switching and fallback rows were zero-valued placeholders, and no soft allocator
was implemented.

Build real daily portfolio equity curves under the same engine, data, dates, costs, and risk
budget.

Required allocators:

A. FROZEN_US46_STATIC
B. BEST_SINGLE_SPECIALIST_CONTINUOUS
C. STATIC_EQUAL_WEIGHT_SPECIALIST_ENSEMBLE
D. STATIC_PREREGISTERED_FIXED_WEIGHT_ENSEMBLE
E. SOFT_REGIME_PROBABILITY_ALLOCATOR
F. HARD_REGIME_SWITCHING_ALLOCATOR
G. DEFENSIVE_OR_CASH_FALLBACK

Soft allocator:

- uses frozen independent regime probabilities;
- applies confidence threshold;
- maximum weight-change constraint;
- explicit risk budget;
- actual turnover and cost.

Hard allocator:

- uses confirmed state only;
- respects minimum dwell and hysteresis;
- uses a preregistered state-to-specialist map;
- applies maximum allocation change;
- low-confidence fallback;
- actual turnover and cost.

All allocators must use a holdings ledger, not averages of Sharpe ratios.

Required outputs:

reports/runops/ds_us_c2r3_20260713/allocator_equity_curves.parquet
reports/runops/ds_us_c2r3_20260713/allocator_weights_daily.parquet
reports/ds_us/remediation_r3/r3_allocator_comparison_20260713.csv
reports/ds_us/remediation_r3/r3_allocator_state_attribution_20260713.csv
reports/ds_us/remediation_r3/r3_allocator_switch_log_20260713.csv

Report by train / validation / test_diagnostic_only / pseudo_forward_diagnostic:

- total return;
- CAGR;
- annual volatility;
- Sharpe;
- Sortino;
- maximum drawdown;
- turnover;
- gross traded notional;
- transaction cost;
- switch count;
- average dwell;
- fallback percentage;
- state attribution.

Selection must use train and validation only.
2026 remains contaminated and cannot select parameters or strategies.

==================================================
PART 7 — TWO SCHEMA-COMPLETE STRATEGY INTAKE PACKETS
==================================================

Produce two complete packets only if supported:

1. corrected frozen US46 static packet;
2. regime-aware allocator packet or a schema-complete blocked packet.

Both packets must include:

- strategy id and exact formula;
- asset universe;
- data snapshot id;
- adjusted/corporate-action status;
- source and hashes;
- execution timing;
- rebalance rule;
- cost model;
- risk/capacity assumptions;
- split policy;
- validation metrics;
- test diagnostic-only metrics;
- target/inactive/failure regimes;
- detector dependency;
- fallback behavior;
- known blockers;
- artifact references;
- final 40-character source commit.

Do not use branch names as `code_commit`.
Do not call a packet complete when required fields or implementation are absent.

Required outputs:

reports/ds_us/remediation_r3/us_strategy_packet_us46_static_20260713.json
reports/ds_us/remediation_r3/us_strategy_packet_regime_20260713.json
reports/ds_us/remediation_r3/r3_packet_schema_validation_20260713.json

==================================================
PART 8 — FOCUSED TESTS AND REPRODUCIBILITY
==================================================

Create independent focused tests for:

- initial allocation;
- first 63-session exposure;
- weight drift;
- rebalance schedule;
- incremental trade notional;
- cash/cost reconciliation;
- zero-trade zero-cost behavior;
- adjusted-data lineage;
- A2 dynamic 200MA rule;
- A3 breadth rule;
- C3 sector ETF composition;
- D1 true buy-and-hold;
- train-only probabilistic fitting;
- soft allocator risk budget;
- hard allocator dwell/hysteresis;
- no use of 2026 contaminated data for selection;
- packet schema and commit/artifact references.

Required files:

tests/test_c2r3_us46_initial_allocation.py
tests/test_c2r3_us46_cost_cash_reconciliation.py
tests/test_c2r3_us_strategy_formula_fidelity.py
tests/test_c2r3_us_allocator_construction.py
tests/test_c2r3_us_packets_and_forward_boundary.py

Create a reproducible entrypoint:

scripts/run_c2_remediation_r3_pipeline.py

One command must regenerate all R3 artifacts from the frozen R2 data foundation and newly
accepted market data.

==================================================
FINAL DECISION
==================================================

Allowed labels:

FROZEN_US46_STATIC_BEST
STATIC_SPECIALIST_ENSEMBLE_BEST
SOFT_REGIME_ALLOCATION_VALIDATION_INTERESTING
HARD_SWITCHING_VALIDATION_INTERESTING
NO_REGIME_SWITCHING_EDGE_WITH_CURRENT_EVIDENCE
BLOCKED_BY_ADJUSTED_TOTAL_RETURN_DATA
PROBABILISTIC_DETECTOR_BLOCKED
REGIME_ALLOCATOR_INCOMPLETE
SYSTEM_INTAKE_READY
S2_CONTINUE_REQUIRED

`FROZEN_US46_STATIC_BEST` is allowed only if:

- the corrected engine passes accounting tests;
- adjusted/total-return evidence is available;
- validation comparison is fair;
- test/2026 are not used for selection.

`NO_REGIME_SWITCHING_EDGE_WITH_CURRENT_EVIDENCE` is allowed only if real static, soft, hard,
and fallback portfolios were compared under identical execution and cost assumptions.

`SYSTEM_INTAKE_READY` is not a strategy-candidate label.
STRATEGY_CANDIDATE_AVAILABLE must remain false.

==================================================
BOUNDARY
==================================================

Research-only.

Do not output:

- recommendation/advice;
- ticket;
- strategy candidate;
- readiness/product route;
- daily signal;
- broker/order/paper/live/auto;
- secret/credential output.

==================================================
CALLBACK
==================================================

CALLBACK_ENVELOPE:
BATCH: DS_US_C2_REMEDIATION_R3_ENGINE_ALLOCATOR_FIX_20260713
WORKSTREAM: DS_US_RESEARCH_USER_CONTROLLED
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
R2_SOURCE_FREEZE_STATUS:
US46_INITIAL_ALLOCATION_STATUS:
US46_COST_CASH_RECONCILIATION:
ADJUSTED_TOTAL_RETURN_STATUS:
HYPOTHESIS_FIDELITY_STATUS:
ACTIVE_HYPOTHESIS_COUNT:
ACTIVE_FAMILY_COUNT:
PROBABILISTIC_DETECTOR_STATUS:
CURRENT_REGIME_AS_OF_MARKET_DATE:
CURRENT_CONFIRMED_REGIME:
US46_CURRENT_REGIME_FIT:
STATIC_PORTFOLIO_STATUS:
SOFT_ALLOCATOR_STATUS:
HARD_ALLOCATOR_STATUS:
FALLBACK_STATUS:
PACKET_COUNT:
PACKET_SCHEMA_STATUS:
FORWARD_HOLDOUT_STATUS: FORWARD_HOLDOUT_CONTAMINATED
FOCUSED_TEST_RESULT:
FINAL_REGIME_EDGE_LABEL:
SYSTEM_INTAKE_READY:
LOCAL_RESEARCH_PROBE_ELIGIBLE_COUNT:
STRATEGY_CANDIDATE_AVAILABLE: false
ARTIFACTS:
VALIDATION:
BOUNDARY_RESULT:
FIXES_REQUIRED:
NEXT_ACTION:
```
