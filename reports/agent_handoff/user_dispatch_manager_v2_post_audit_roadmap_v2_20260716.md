# V2 Manager Roadmap

Date: 2026-07-18 | Repository: `2604714984-prog/quant-proj` | Default branch: `v2-main` | Status: `CURRENT_MANAGER_HANDOFF`

## Scope and baseline

This is the only active Manager roadmap. It is an operating summary, not a
constitution, registry, dispatcher, task framework, or second research system.

```text
precedence=latest user instruction > merged AGENTS.md > this roadmap > accepted task artifact
architecture_rebuild_required=false
one_repository=true
one_python_package=true
one_CLI=true
one_DuckDB_access_layer=true
one_event_loop_and_portfolio_core=true
one_CI_workflow=true
active_code_writing_family=none
validated_specialists=0
strategy_candidate_available=false
```

Keep the lightweight architecture. During the three-cycle freeze, do not add a
CLI, database layer, event loop, manifest framework, registry, agent platform,
automatic source fusion, or parallel backtester.

## Closed lineage memory

Closed families cannot be rerun, retuned, filtered, regime-relabeled, or rescued
by new infrastructure.

| Lineage | Terminal status | Controlling evidence |
|---|---|---|
| Relative Strength | `HISTORICAL_SCREENING_FAIL` (16/48) | `reports/validation/a_share_relative_strength_historical_secondary_screen_v3.json` |
| Defensive Low Volatility | `HISTORICAL_GATED_FAIL` (48/64) | PR #63; `reports/validation/a_share_defensive_low_volatility_v1_result.json` |
| Cycle 3 liquidity-shock reversal | `CLOSED_PREFLIGHT_STRUCTURAL_INFEASIBLE_NO_OUTCOME` | PR #67; `reports/agent_handoff/cycle_3_liquidity_shock_preflight_terminal_closure_20260717.md` |
| Cycle 4 fixed three-ETF trend | `SOURCE_QUALIFICATION_INCOMPLETE_CLOSE_CYCLE4` | PR #70; `reports/validation/cycle4_three_etf_source_qualification_v1.json` |
| Chronological ordering | `INPUT_BLOCKED_NO_OUTCOME` | `reports/validation/a_share_chronological_return_ordering_preflight_v1_20260718.json` |
| Post-IPO lucky-code avoidance | `INPUT_BLOCKED_NO_OUTCOME` | `reports/validation/a_share_post_ipo_numerology_preflight_v1_20260718.json` |
| Upper-limit delay | `INPUT_BLOCKED_NO_OUTCOME` | `reports/validation/a_share_upper_limit_delay_preflight_v1_20260718.json` |
| Salient return | `STRUCTURAL_FAIL_NO_OUTCOME` | `reports/validation/a_share_salient_return_preflight_v1_20260718.json` |
| Swing Count | `HISTORICAL_SCREENING_FAIL_CLOSED_EXECUTION_ERROR` | PR #74/#75; `reports/validation/a_share_swing_structure_participation_confirmed_trend_v1_result.json` |
| Post-IPO age | `VALIDATION_FAIL` | PR #83; `reports/validation/a_share_post_ipo_age_validation_v1_20260718.json` |
| China price-volume trend replication | `FEASIBILITY_BLOCKED_CLOSE_NO_ADAPTER_NO_OUTCOME` | `reports/validation/a_share_china_price_volume_trend_replication_feasibility_v1_20260718.json` |

PR #58 is closed, unmerged historical material. Shared semantic state is
`H3_STRICT_PREOPEN=CLOSED_ACCEPTED`; `M1_CROSS_TYPE_CORPORATE_ACTION_ID=DEFERRED`.

## Parked external-review increment

```text
research_id=A_SHARE_RELATIVE_VARIANCE_MANAGED_LIQUID_EQUITY_V1_20260718
PR=https://github.com/2604714984-prog/quant-proj/pull/84
PR_HEAD=44199bc4ec9f825750283c62b0242f7981f30fd6
state=DRAFT_PARKED_PENDING_EXTERNAL_REVIEW
scope=outcome_blind_PR_A_plus_aggregate_feasibility_only
historical_outcome_opened=false
strategy_candidate_available=false
```

Do not amend PR #84 except for a concrete reviewer finding. If accepted, its
next step is one separately frozen historical economic screen. Acceptance does
not authorize Shadow, candidate status, orders, provider calls, or data writes.

## Research policy

Each new family gets one economic hypothesis, one primary variant, at most one
preregistered robustness variant, one role-specific endpoint, and aggregate
feasibility before adapter or outcome access. Use the complete walk-forward OOS
sequence as the primary historical test; short subperiods are diagnostics.

```text
alpha endpoint       = net active return after frozen costs
defensive endpoint   = frozen return lower bound plus drawdown improvement
allocation endpoint  = risk-adjusted growth versus frozen static comparator

aggregate feasibility
-> close on missing inputs, breadth, capacity, or execution panels
-> code frozen primary plus optional robustness only
-> one historical economic screen
-> FAIL permanently closes the family
-> PASS permits SHADOW_ELIGIBLE only
-> prospective Shadow evidence precedes any candidate decision
```

No result-dependent repair, threshold change, source substitution, or extra
variant is permitted after the first outcome is opened.

## Priority queue

1. Relative Variance: finish exact-head external review of PR #84 first.
2. Low abnormal-turnover / anti-speculation: read-only turnover and free-float
   identity check; close before adapter work if incomplete.
3. CH3-style size/value: wait for qualified PIT fundamentals; do not build a
   speculative fundamentals platform.
4. High-turnover daily/intraday: defer until T+1, limits, costs, and capacity
   inputs are qualified.

China price-volume trend is closed at feasibility. The paper defines a
long-short factor requiring PIT size and E/P controls; a future long-only version
is a different hypothesis. ETF and multi-asset trend remain paused, and any
future work is a new data task rather than a Cycle 4 repair.

## Capacity, data, Macro Risk, and combination

```text
capacity = target_order_value / trailing_20_session_median_amount
one canonical provider per dataset
at most one read-only cross-check
no automatic fusion
no provider or database write without explicit authority
```

Apply the existing Capacity Policy; do not impose a universal institutional
liquidity threshold. Macro Risk remains read-only Shadow with no position,
selection, signal, or order effect. Do not build a synthesizer or ensemble until
two independently historically passing families with distinct economic sources
have prospective Shadow evidence.

## Stop budget and review triggers

```text
budget_start=2026-07-18
maximum_new_high_prior_families=4
families_consumed=2
families_remaining=2
maximum_calendar_duration=6_months
stop_when=first_limit_reached
```

Relative Variance and the closed price-volume lane each consume one slot. At the
stop point: two or more Shadow families allow static-combination research; one
continues alone; zero leaves a passive core plus Macro Risk Shadow.

External review is required for shared financial semantics, PIT/availability or
unit-contract changes, a family's first historical PASS, any prospective result,
the first ensemble, any Macro Risk position effect, and any trading stage.
Ordinary feasibility closes and historical FAILs need green CI and a concise
Manager record, not a new architecture review.
