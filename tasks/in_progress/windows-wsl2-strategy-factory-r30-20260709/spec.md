# WINDOWS_WSL2_STRATEGY_FACTORY_R30_20260709

## Classification

Large research-only strategy development factory. This batch is designed to continue iterating inside one controlled batch until it either produces at least one verifiable research strategy line or exhausts the accepted strategy surfaces under explicit stop rules.

## Important clarification

This batch cannot guarantee that a viable strategy exists. Its goal is to run an evidence-backed research factory until one of these outcomes occurs:

1. `LOCAL_RESEARCH_PROBE_ELIGIBLE` appears under accepted research rules.
2. All active surfaces are marked `DO_NOT_RETRY_UNTIL_NEW_SOURCE` / `OBSERVATION_ONLY` / `RETIRED_UNDER_CURRENT_EVIDENCE`.
3. A hard blocker appears that requires separate user authorization.

No output from R30 is a strategy candidate, recommendation, ticket, readiness, product route, daily signal, or trading path.

## Evidence basis

Read first:

- R28 source/final-sync artifacts.
- R29 direct market-cap task packet and any R29 closeout if available.
- A_Share_Monitor backtest engine and rules code.
- SmallCap R26/R27/R28 evidence packages.
- R25/R26/R27/R28 external audit results.

## Code inspection findings to preserve

The current A_Share_Monitor code supports serious research but requires evidence discipline:

- `DailyBacktestEngine` schedules orders from signal day to next trade date, preserving T+1 execution semantics.
- `ConservativeDailyFillModel` uses open-price execution with slippage, limit/suspend rejection, amount/volume participation, and lot rounding.
- `Portfolio` applies cash/cost accounting, lot sizing, position state, and close-based mark-to-market.
- `evaluate_rules` now handles empty AND/OR rule semantics correctly.
- `apply_universe_filters` handles ST/suspension/list-days/delist filters and amount filters, but SmallCap direct market-cap membership still requires separate evidence.

## Objective

Run a single large strategy research factory focused on verifiable strategy discovery. Do not spend the batch on process-only reports. Build, test, reject, repair, and retire research strategy lines until the batch reaches a clear research outcome.

## Active strategy surfaces

Surface A: SmallCap Low Turnover.

- Primary blocker: direct market-cap membership evidence.
- If R29 has completed and direct market-cap membership is available, use it.
- If R29 is incomplete, run the R29 direct market-cap evidence task first.
- If direct market-cap evidence remains unavailable, mark SmallCap `DO_NOT_RETRY_UNTIL_NEW_SOURCE` and move on.

Surface B: US30W-R22-002 adaptive_quality / baseline.

- Primary blocker: local-only evidence and limited robustness.
- Only use as research observation unless remote/mirror preservation is complete.

Surface C: pass77 direct/proxy feature line.

- Primary blocker: direct/proxy source evidence absent.
- Do not rerun pass77 strategies unless new accepted source evidence appears.

Surface D: ETF amount/turnover rotation.

- Current status: retired under accepted R25/R27 evidence.
- Do not reopen unless new accepted evidence changes the instability premise.

Surface E: New strategy families, allowed only after active surfaces are blocked.

Allowed new families:

- A-share low-turnover quality / value / dividend quality.
- A-share liquidity-constrained reversal.
- A-share small-cap stability / quality overlay.
- ETF defensive benchmark strategies only if old rotation remains retired.
- US30W quality/momentum variants only if remote/mirror preservation is solved.

## Factory phases

### Phase 0 - R29 gate and evidence freeze

- Import the latest R29 result if present.
- If R29 is not complete, run the R29 direct market-cap evidence task first.
- Update failure memory.
- Produce active surface board.

Deliverables:

- reports/workspace_dispatch/r30_active_surface_freeze_20260709.md
- reports/workspace_dispatch/r30_active_surface_board_20260709.csv
- reports/workspace_dispatch/r30_failure_memory_update_20260709.json

### Phase 1 - SmallCap decisive path

If direct market-cap evidence is available:

- Rebuild SmallCap matrix with direct market-cap membership.
- Run leakage/timing audit.
- Run walk-forward, cost/capacity, universe sensitivity, bootstrap/permutation.
- Decide local research probe eligibility.

If direct market-cap evidence is unavailable:

- Stop SmallCap local-probe reconsideration.
- Mark `DO_NOT_RETRY_UNTIL_NEW_SOURCE`.

Deliverables:

- reports/workspace_dispatch/r30_smallcap_direct_mcap_or_stop_20260709.md
- reports/workspace_dispatch/r30_smallcap_decisive_diagnostics_20260709.csv
- reports/workspace_dispatch/r30_smallcap_probe_decision_20260709.csv

### Phase 2 - US30W preservation and robustness

Only continue if US30W evidence can be remote-preserved or mirrored sufficiently.

- Configure or document mirror preservation.
- Re-run pipeline with `synthetic_data=false`.
- Stress adaptive_quality and baseline with alternate splits, cost/slippage, symbol subset, and bootstrap.
- Keep as observation-only unless evidence preservation and robustness are adequate.

Deliverables:

- reports/workspace_dispatch/r30_us30w_preservation_status_20260709.md
- reports/workspace_dispatch/r30_us30w_robustness_diagnostics_20260709.csv
- reports/workspace_dispatch/r30_us30w_strategy_board_20260709.csv

### Phase 3 - pass77 source-evidence gate

Do not rerun strategies unless source evidence changes.

- Try bounded public/no-secret direct field validation for funds_flow, hot_money, valuation, amount, turnover.
- If no accepted direct evidence appears, keep `REPAIR_ON_NEW_EVIDENCE_ONLY`.
- If accepted direct evidence appears, run only pre-registered repaired diagnostics.

Deliverables:

- reports/workspace_dispatch/r30_pass77_source_evidence_gate_20260709.md
- reports/workspace_dispatch/r30_pass77_repaired_diagnostics_or_skip_20260709.csv
- reports/workspace_dispatch/r30_pass77_decision_board_20260709.csv

### Phase 4 - New strategy-family expansion, only after A-D are blocked or exhausted

Run new families only if active surfaces do not produce local research probe eligibility.

Rules:

- All new families must be pre-registered before diagnostics.
- No test-result parameter selection.
- Start on local/pass77/accepted universe only, then wider only if prequalification passes.
- Use existing engine with T+1 execution, conservative fill, cost, slippage, limit/suspend handling, and capacity constraints.

Families:

1. Low-turnover quality composite.
2. Dividend/value quality defensive composite.
3. Liquidity-constrained reversal.
4. Small-cap stability overlay.
5. Volatility-controlled hold-period extension.
6. Sector/board neutral small-cap low-turnover variant.
7. US30W adaptive quality robustness variant if preservation is adequate.

Deliverables:

- reports/workspace_dispatch/r30_new_family_preregistration_20260709.md
- reports/workspace_dispatch/r30_new_family_diagnostics_20260709.csv
- reports/workspace_dispatch/r30_new_family_prequalification_board_20260709.csv

### Phase 5 - Final strategy decision

The batch must end with one of these outcomes:

- `LOCAL_RESEARCH_PROBE_ELIGIBLE` for one or more research lines.
- `NO_VERIFIABLE_STRATEGY_UNDER_CURRENT_EVIDENCE`.
- `BLOCKED_BY_AUTH_OR_SOURCE_LIMIT`.

Allowed labels:

- LOCAL_RESEARCH_PROBE_ELIGIBLE
- CONTINUE_RESEARCH
- OBSERVATION_ONLY
- BENCHMARK_ONLY
- REPAIR_ON_NEW_EVIDENCE_ONLY
- DO_NOT_RETRY_UNTIL_NEW_SOURCE
- RETIRED_UNDER_CURRENT_EVIDENCE
- NO_VERIFIABLE_STRATEGY_UNDER_CURRENT_EVIDENCE
- BLOCKED_BY_AUTH_OR_SOURCE_LIMIT

Deliverables:

- reports/workspace_dispatch/r30_final_strategy_factory_board_20260709.csv
- reports/workspace_dispatch/r30_final_strategy_factory_memo_20260709.md

## Support repos

market_data:

- Contract for R30 research labels and overclaim regression.

strategy_work:

- R30 strategy factory memo.
- Final sync after accepted callbacks.

quant-proj:

- Intake, dispatch, result summary, closeout.

## Validation

- JSON parse PASS.
- CSV/parquet read PASS.
- git diff check PASS.
- focused tests PASS if code changed.
- agent_safety_check PASS where applicable.
- source-health PASS before source-heavy work.
- no full-frame wide3068.
- no test-result parameter selection.
- no actionable output.
- no candidate promotion.

## Stop conditions

- Any output becomes recommendation, ticket, candidate, readiness, product route, daily signal, or trading path.
- Secret/auth/non-public provider is required without separate authorization.
- Full-frame wide3068 is attempted.
- Old retired ETF/pass77 surfaces are rerun without changed accepted evidence.
- Local probe label is created without source evidence and timing/leakage support.
- Test result is used to select parameters.

## Callback envelope

Return callback with batch id, repo, branch, commit, tree, tasks completed, artifacts, validation, active surface status, strategy family results, final board counts, local research probe eligible count, strategy candidate availability, boundary result, fixes required, and next source action.
