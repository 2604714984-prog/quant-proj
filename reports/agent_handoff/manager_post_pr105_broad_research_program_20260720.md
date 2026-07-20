# Manager task: close PR #105 and run the broad US mechanism-search program

Date: 2026-07-20  
Repository: `2604714984-prog/quant-proj`  
Controlling audit: `reports/external_audit/pr105_exact_head_audit_and_broad_research_program_20260720.md`

## 1. Required repository action

PR #105 exact HEAD:

```text
85e2f1e803d10067f63cb6edce83911d1922a6b2
```

External-review disposition:

```text
EVIDENCE_ACCEPTED=true
MERGE=false
ACTION=CLOSE_WITHOUT_MERGE
R3_RERUN=false
R3_REWRITE=false
```

Record the exact PR, commit, review ID `4731989819`, artifact hashes and external raw-bundle location as failure/input memory. Do not copy its 19,971-line scope into mainline.

## 2. Program objective

Create a wide, outcome-blind US mechanism pool while keeping formal result production narrow.

```text
WIDE_DISCOVERY=PARALLEL_READ_ONLY
FORMAL_RESULT_LANE=ONE_AT_A_TIME
```

The objective is not to produce another roadmap. The objective is to deliver:

- a 50-100-card mechanism pool within ten working days;
- a bounded Lane B identity decision;
- one selected mechanism that can produce a numerical Development result;
- no architecture expansion.

## 3. Dispatch order

Dispatch the following tasks after this control package is merged:

1. `us_lane_b_daily_identity_resolution_task_20260720.md`
2. `us_daily_etf_market_mechanism_scout_task_20260720.md`
3. `us_survivor_aware_stock_mechanism_scout_task_20260720.md`
4. `us_earnings_corporate_fundamental_scout_task_20260720.md`
5. `us_intraday_options_text_availability_scout_task_20260720.md`

Tasks 2-5 are read-only scouts and may run in parallel. Task 1 is the only active formal data-contract lane.

No task may coordinate directly with another task. All dependencies return to the Manager.

## 4. Shared scout boundary

Every scout is prohibited from:

```text
price queries
return queries
NAV or Sharpe calculation
Validation or Holdout access
strategy implementation
parameter grids
canonical DuckDB writes
new framework creation
candidate promotion
Shadow/Paper/broker/live actions
```

Every scout must return mechanism cards only.

## 5. Shared mechanism-card schema

Reject any callback that does not use this schema:

```text
mechanism_id
economic_mechanism
primary_original_source
market_role
universe
signal_and_holding_period
required_data
current_data_status
sample_size_estimate
turnover_and_cost_risk
USD_40000_execution_fit
survivorship_and_PIT_risk
closed_lineage_duplicate_screen
implementation_size_estimate
result_time_estimate
recommendation=ADVANCE|PARK|CLOSE
```

Historical return values are forbidden.

## 6. Mechanism-pool targets

Minimum outcome-blind card counts:

```text
Daily ETF / market scout:               20 cards
Survivor-aware stock scout:             20 cards
Earnings / corporate / fundamental:     20 cards
Intraday / options / text availability: 15 cards
Lane B resolution alternatives:          5 cards or terminal closures
```

Duplicated mechanisms count once.

## 7. Scoring and selection

Score each card before any outcome access:

```text
economic prior                 0-3
data readiness                 0-3
sample sufficiency             0-2
USD 40,000 execution fit       0-2
cost robustness expectation    0-2
independence from closed lines 0-2
implementation simplicity      0-1
prospective observability      0-2
```

Maximum score: 17.

Manager may advance only cards scoring at least 11, unless the user explicitly overrides.

Tie-breaking:

1. data readiness;
2. prospective observability;
3. implementation simplicity;
4. fixed mechanism ID order.

No hidden return-based tie-breaking is allowed.

## 8. Formal-result selection

After scout callbacks and Lane B resolution, select exactly one formal mechanism.

Selection priority:

```text
1. independently qualified Lane B daily mechanism;
2. existing-data daily ETF or broad-market mechanism;
3. survivor-aware stock mechanism only after full identity qualification;
4. earnings/fundamental mechanism only after PIT filing identity qualification;
5. high-cost data mechanism only after explicit user authorization.
```

The selected mechanism gets:

```text
one new research ID
one primary variant
at most one preregistered robustness variant
one Development run
one terminal status
```

Do not create a shortlist PR before the result. Freeze the definition and produce code, tests, result and receipt in one substantive PR whenever technically possible.

## 9. Historical-evidence boundary

The following periods are consumed at program level:

```text
2010-01-01..2017-12-31
2018-01-01..2026-06-30
```

Any later result on those dates is:

```text
RETROSPECTIVE_SECONDARY_ONLY
```

It cannot independently set:

```text
strategy_candidate_available=true
```

A historical PASS may seek exact-head review and zero-capital prospective Shadow on observations strictly after the frozen cutoff.

## 10. Lane B decision budget

The current exact-time M3 search receives:

```text
maximum elapsed time: 2 working days
maximum new official-source requests: 200
price/return access: forbidden
```

If fewer than 94 accepted actual publication timestamps result, close exact-time M3 as:

```text
TERMINAL_DATA_UNAVAILABLE_WITHIN_BOUND_NO_OUTCOME
```

A new date-anchored daily V2 requires a new research ID and its own outcome-blind review.

## 11. Data-spend boundary

Combined unapproved data-spend ceiling:

```text
USD 0
```

Scouts may document current prices and trial coverage but may not purchase anything.

Any proposed purchase must include:

- exact coverage;
- sample extract;
- license terms;
- reproducibility;
- total one-year cost;
- a clear mechanism that cannot be tested with existing data.

## 12. Architecture freeze

The following remain prohibited:

```text
new repository
new CLI
new database layer
new event loop
new portfolio core
second formal backtest engine
new runner framework
new evidence framework
strategy registry
dispatcher
agent framework
automatic provider fusion
Qlib integration
RD-Agent integration
broker or trading path
```

A scout may mention Qlib or RD-Agent only as deferred tools. It may not install or integrate them.

## 13. Callback requirements

Each scout callback must provide:

```text
task_id
exact branch and commit
card_count
ADVANCE count
PARK count
CLOSE count
top five mechanism IDs
all source URLs
confirmation of zero outcome access
confirmation of zero database writes
worktree status
```

Manager callback must provide direct GitHub links to every task result.

## 14. Thirty-day execution target

```text
>= 50 unique outcome-blind cards
1 bounded Lane B terminal decision
>= 3 numerical Development results from independent mechanisms
<= 1 retrospective-secondary confirmation
0 new architecture
0 Qlib/RD-Agent integrations
0 broker/live work
```

## 15. Stop conditions

Stop and return to the user if any agent:

- reads a prohibited result;
- uses Validation/Holdout to edit a mechanism;
- creates a parameter grid;
- changes a closed lineage;
- writes the canonical database;
- proposes a new platform or framework;
- cannot distinguish a source route from qualified historical identity.

## 16. Current controlling state

```text
PRIMARY_MARKET=US
PR_105=CLOSE_WITHOUT_MERGE
ACTIVE_FORMAL_DATA_LANE=LANE_B_IDENTITY_RESOLUTION
ACTIVE_CODE_RESULT_MECHANISM=NONE
READ_ONLY_SCOUTS=AUTHORIZED
VALIDATED_SPECIALISTS=0
STRATEGY_CANDIDATE_AVAILABLE=false
SHADOW=false
PAPER=false
LIVE=false
```
