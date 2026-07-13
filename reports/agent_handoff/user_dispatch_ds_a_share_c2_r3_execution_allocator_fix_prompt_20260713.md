# User-Dispatch Prompt — DS A-Share C2 R3 Execution and Allocator Fix

Copy the complete fenced prompt below into the independently controlled DS A-share conversation.

```text
RUN DS_A_SHARE_C2_REMEDIATION_R3_EXECUTION_ALLOCATOR_FIX_20260713

WORKSTREAM:
DS_A_SHARE_RESEARCH_USER_CONTROLLED

TARGET REPOSITORY:
https://github.com/2604714984-prog/quant_research_lab

ACCEPTED R2 SOURCE ANCHOR:
branch: research/c2-remediation-r2-20260713
commit: 8c57e3f34e15c8a744423323c9461b40928e0894

CREATE AND USE A NEW BRANCH:
research/c2-remediation-r3-20260713

EXTERNAL AUDIT SOURCE:
https://github.com/2604714984-prog/quant-proj/blob/3e0fbde8cc592b5d5044aa2ce5734e84b57bed9d/reports/agent_handoff/ds_c2r_r2_callbacks_external_audit_result_20260713.md

CONTROL AND INDEPENDENCE

The user exclusively controls this DS A-share research project.
Quant Manager, dispatcher, Codex, DS US, and other agents must not choose formulas,
features, thresholds, regime states, parameters, preferred winners, or conclusions.
Return the final callback, branch, full commit SHA, tree, artifacts, and validation to the user only.
Do not send the callback directly to Quant Manager or Codex.

R2 AUDIT STATUS

The R2 callback was externally rejected for strategy-system intake:

DS_A_SHARE_C2R_CALLBACK_REJECTED_STRATEGY_EVIDENCE_INVALID
S2_CONTINUE_REQUIRED

The R2 data foundation is useful and must be preserved:

- all 35 sorted feature partitions were inventoried and hashed;
- the canonical snapshot covers approximately 5.4M rows and 3068 symbols;
- the row-backed daily regime feature table exists;
- the deterministic hysteresis no longer reads future confirmation rows;
- hypothesis Markdown/CSV counts are aligned.

Do not rebuild the data foundation unless a reproducible defect is found.
This is a narrow R3 methodology and execution remediation cycle.

PRIMARY OBJECTIVE

Correct the strategy simulator, faithfully implement the preregistered hypotheses,
construct genuine static/soft/hard/fallback portfolio equity curves, and produce valid
Strategy Intake Packets. End with an evidence-based conclusion about whether regime
allocation has an edge.

R3 must not close on summary-only, average-Sharpe comparison, or manually edited packets.

==================================================
PART 0 — FREEZE R2 SOURCE ARTIFACTS
==================================================

Read and preserve the R2 artifacts under:

reports/ds_a_share/remediation_r2/
reports/runops/c2_a_share_remediation_r2_20260713/
scripts/c2_remediation_r2_pipeline.py

Produce:

reports/ds_a_share/remediation_r3/r3_r2_source_freeze_20260713.md
reports/ds_a_share/remediation_r3/r3_failure_memory_import_20260713.json

The freeze must record:

- source commit;
- snapshot id;
- data hashes;
- accepted data artifacts;
- rejected strategy conclusions;
- exact R3 changes.

Do not overwrite R2 artifacts.

==================================================
PART 1 — REPLACE THE STRATEGY SIMULATOR
==================================================

The R2 simulator selected positions from date-D rows and immediately booked date-D
`daily_return`. This violates the packet claim of close-D signal and open-D+1 execution.

Implement a causal portfolio simulator with:

1. Signal formation on close of trading date D.
2. Orders scheduled for the next valid trading session D+1.
3. Execution at D+1 open if open data exists.
4. If valid open data is unavailable, return `BLOCKED_BY_EXECUTION_PRICE_DATA`; do not
   silently use same-day return.
5. Positions earn returns only after execution.
6. No signal may consume D+1 return, close, high, low, volume, or membership information.
7. ST, suspension, limit-up/limit-down, listing-age, delist, and tradability filters must be
   evaluated using information available before execution.
8. Holdings, cash, orders, fills, rejects, and portfolio value must be preserved daily.

Required row-level outputs:

reports/runops/ds_a_share_c2r3_20260713/orders.parquet
reports/runops/ds_a_share_c2r3_20260713/fills.parquet
reports/runops/ds_a_share_c2r3_20260713/holdings_daily.parquet
reports/runops/ds_a_share_c2r3_20260713/equity_daily.parquet
reports/runops/ds_a_share_c2r3_20260713/execution_manifest.json

Required tests:

- signal D cannot earn date-D return;
- order execution date is strictly later than signal date;
- unavailable D+1 prices create a reject or explicit blocker;
- positions begin earning only after fill;
- split boundaries do not leak positions or future fields.

==================================================
PART 2 — ACTUAL TURNOVER AND TRANSACTION COSTS
==================================================

Replace fixed cost subtraction with actual traded-notional accounting.

At every rebalance preserve:

- pre-trade shares;
- pre-trade weights;
- target shares;
- buy notional;
- sell notional;
- gross traded notional;
- one-way fees;
- stamp duty on sells where applicable;
- slippage;
- post-trade cash;
- post-trade holdings;
- post-trade portfolio value.

Required reconciliation:

pre_trade_value
- fees
- stamp_duty
- slippage_cost
= post_trade_cash + post_trade_holdings_market_value

Do not deduct cost when positions do not change.
Do not use a constant cost merely because a prior switch occurred.

Required artifacts:

reports/ds_a_share/remediation_r3/r3_cost_model_contract_20260713.md
reports/ds_a_share/remediation_r3/r3_cost_turnover_reconciliation_20260713.csv
reports/ds_a_share/remediation_r3/r3_cost_capacity_stress_20260713.csv

==================================================
PART 3 — FAITHFULLY IMPLEMENT THE PREREGISTERED HYPOTHESES
==================================================

Use the R2 preregistration as the frozen source. Do not collapse hypotheses into generic
single-column configurations.

Required implementation audit for each hypothesis:

- exact formula;
- exact universe;
- exact target/inactive regimes;
- exact holding and rebalance schedule;
- exact bucket direction and size;
- exact filters and guards;
- exact cost/capacity assumptions;
- exact fallback behavior.

The following R2 mismatches must be corrected:

- H1 must implement the preregistered composite formula, not momentum_60 alone.
- H3 must implement the breadth guard.
- H5 must implement the low-volatility + PB composite.
- H8 must implement its direct liquidity/volume shock condition.
- top-80% circ_mv universes must actually be enforced where declared.
- sector-neutral variants must actually neutralize sector/board exposure where declared.
- liquidity floors and tradability filters must actually be enforced.
- top/bottom 20% declarations must not be replaced by generic top-10 unless explicitly
  preregistered before validation.
- H9 and H10 remain blocked unless new direct evidence materially changes their premise.

Produce a formula-fidelity board:

reports/ds_a_share/remediation_r3/r3_hypothesis_implementation_fidelity_20260713.csv

Required columns:

hypothesis_id
formula_fidelity
universe_fidelity
regime_fidelity
holding_fidelity
cost_fidelity
implemented
blocked_reason
source_code_ref

Every active hypothesis must be either faithfully implemented or explicitly blocked.

==================================================
PART 4 — INDEPENDENT TRAIN-FROZEN PROBABILISTIC DETECTOR
==================================================

The R2 sidecar used all dates and deterministic labels from the same full sample.
That is not accepted as an independent probabilistic detector.

Implement one independent sidecar using only causal regime features, for example:

- Gaussian Mixture Model;
- Hidden Markov Model;
- train-fitted clustering plus frozen mapping;
- change-point detector with train-frozen thresholds.

Requirements:

1. Fit scaler/model on train only.
2. Freeze parameters before validation.
3. Validation may evaluate the frozen detector.
4. Test is diagnostic-only.
5. Do not train on deterministic confirmed-state labels as the prediction target.
6. Preserve model parameters, feature list, train dates, random seed, and model hash.
7. Produce probabilities/confidence for all dates by out-of-sample transform/predict.
8. Detector agreement must compare genuinely independent outputs.

If a valid independent sidecar cannot be implemented, use:

PROBABILISTIC_DETECTOR_BLOCKED

and do not claim a passed probabilistic gate.

Required artifacts:

reports/ds_a_share/remediation_r3/r3_probabilistic_detector_manifest_20260713.json
reports/ds_a_share/remediation_r3/r3_detector_agreement_matrix_20260713.csv
reports/ds_a_share/remediation_r3/r3_detector_oos_diagnostics_20260713.csv

==================================================
PART 5 — BUILD REAL ALLOCATOR PORTFOLIOS
==================================================

The R2 comparison averaged independent strategy Sharpe and drawdown values.
That is not a portfolio allocator comparison.

Construct actual daily portfolio equity curves using the same specialists, dates, capital,
execution model, risk budget, costs, and rebalance calendar.

Required allocators:

A. BEST_SINGLE_CONTINUOUS
B. STATIC_EQUAL_WEIGHT_SPECIALIST_ENSEMBLE
C. STATIC_PREREGISTERED_FIXED_WEIGHT_ENSEMBLE
D. SOFT_REGIME_PROBABILITY_ALLOCATOR
E. HARD_REGIME_SWITCHING_ALLOCATOR
F. DEFENSIVE_OR_NO_TRADE_FALLBACK

Soft allocator requirements:

- weights derived from frozen regime probabilities;
- maximum weight change per rebalance;
- confidence floor;
- minimum allocation floor/ceiling;
- actual turnover and switching costs.

Hard allocator requirements:

- confirmed state only;
- minimum dwell;
- hysteresis;
- confidence threshold;
- explicit specialist mapping;
- maximum allocation change;
- fallback on low confidence.

Static ensemble requirements:

- one shared portfolio equity curve;
- strategy sleeves with explicit capital weights;
- no averaging of Sharpe ratios.

Required outputs:

reports/runops/ds_a_share_c2r3_20260713/allocator_equity_curves.parquet
reports/runops/ds_a_share_c2r3_20260713/allocator_weights_daily.parquet
reports/ds_a_share/remediation_r3/r3_allocator_comparison_20260713.csv
reports/ds_a_share/remediation_r3/r3_allocator_state_attribution_20260713.csv
reports/ds_a_share/remediation_r3/r3_allocator_switch_log_20260713.csv

Report by train / validation / test_diagnostic_only:

- total return;
- CAGR;
- annualized volatility;
- Sharpe;
- Sortino;
- maximum drawdown;
- turnover;
- gross traded notional;
- transaction cost;
- switch count;
- average dwell;
- fallback percentage;
- performance by regime.

Selection must use train and validation only.
Test must remain diagnostic-only.

==================================================
PART 6 — FIX GATES AND PLAUSIBILITY CHECKS
==================================================

The R2 gate named family_count_ge_4 incorrectly checked >=3.
The R2 drawdown sanity test also used the wrong sign.

Requirements:

- `family_count_ge_4` must require at least four genuinely distinct active families, or fail.
- If only three valid active families remain, record `FAMILY_COUNT_GATE_FAILED`.
- Maximum drawdown must use one documented sign convention.
- A drawdown worse than 50% must trigger review; worse than 70% must block a positive label
  unless explicitly justified and accepted.
- No gate may be hard-coded true.
- All gate results must be derived from generated artifacts.

Required artifact:

reports/ds_a_share/remediation_r3/r3_exit_gate_results_20260713.json

==================================================
PART 7 — COMPLETE AND CONSISTENT STRATEGY INTAKE PACKETS
==================================================

Produce at least two schema-complete packets only if their evidence is valid:

1. strongest static/all-weather packet;
2. strongest regime-aware allocator or a complete blocked packet.

Required corrections:

- `target_regimes` must be a list, never boolean true;
- formula must reference the exact implemented formula;
- packet execution timing must match code;
- cost model must match code;
- universe must match code;
- source commit must be the final 40-character SHA, not `pending` or a branch name;
- artifact paths and hashes must be present;
- validation metrics must come from validation only;
- test metrics must be clearly diagnostic-only;
- blocked packets must include every schema field plus concrete blockers.

Required outputs:

reports/ds_a_share/remediation_r3/a_share_strategy_packet_static_20260713.json
reports/ds_a_share/remediation_r3/a_share_strategy_packet_regime_20260713.json
reports/ds_a_share/remediation_r3/r3_packet_schema_validation_20260713.json

==================================================
PART 8 — FOCUSED TEST SUITE AND REPRODUCIBILITY
==================================================

Create focused tests covering:

- T+1 signal/execution timing;
- no same-day return leakage;
- traded-notional cost reconciliation;
- no-cost-on-no-trade;
- universe/filter fidelity;
- formula fidelity;
- soft allocator weights sum to allowed risk budget;
- hard switching respects dwell/hysteresis;
- static ensemble uses a shared portfolio curve;
- family-count gate semantics;
- drawdown sanity semantics;
- packet schema and code/artifact references;
- train-only fitting for probabilistic detector;
- no test-result parameter selection.

Required files:

tests/test_c2r3_execution_timing.py
tests/test_c2r3_cost_reconciliation.py
tests/test_c2r3_hypothesis_fidelity.py
tests/test_c2r3_allocator_construction.py
tests/test_c2r3_exit_gates_and_packets.py

Create a single reproducible entrypoint:

scripts/run_c2_remediation_r3_pipeline.py

One command must regenerate all R3 artifacts from the frozen R2 data foundation.

==================================================
FINAL DECISION
==================================================

Allowed final labels:

STATIC_SINGLE_STRATEGY_BEST
STATIC_ENSEMBLE_BEST
SOFT_REGIME_ALLOCATION_VALIDATION_INTERESTING
HARD_SWITCHING_VALIDATION_INTERESTING
NO_REGIME_SWITCHING_EDGE_WITH_CURRENT_EVIDENCE
REGIME_SWITCHING_COMPARISON_BLOCKED
PROBABILISTIC_DETECTOR_BLOCKED
FAMILY_COUNT_GATE_FAILED
SYSTEM_INTAKE_READY
S2_CONTINUE_REQUIRED

`NO_REGIME_SWITCHING_EDGE_WITH_CURRENT_EVIDENCE` is allowed only if genuine static, soft,
hard, and fallback portfolio equity curves were compared under the same execution and cost model.

`SYSTEM_INTAKE_READY` is allowed only if all required gates and tests pass and packets are
schema-complete. It is not a strategy-candidate label.

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

STRATEGY_CANDIDATE_AVAILABLE must remain false.

==================================================
CALLBACK
==================================================

CALLBACK_ENVELOPE:
BATCH: DS_A_SHARE_C2_REMEDIATION_R3_EXECUTION_ALLOCATOR_FIX_20260713
WORKSTREAM: DS_A_SHARE_RESEARCH_USER_CONTROLLED
TARGET_REPO:
BRANCH:
COMMIT:
TREE:
STATUS:
R2_SOURCE_FREEZE_STATUS:
T1_EXECUTION_AUDIT_STATUS:
COST_RECONCILIATION_STATUS:
HYPOTHESIS_FIDELITY_STATUS:
ACTIVE_HYPOTHESIS_COUNT:
ACTIVE_FAMILY_COUNT:
PROBABILISTIC_DETECTOR_STATUS:
STATIC_PORTFOLIO_STATUS:
SOFT_ALLOCATOR_STATUS:
HARD_ALLOCATOR_STATUS:
FALLBACK_STATUS:
PACKET_COUNT:
PACKET_SCHEMA_STATUS:
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
