# V2 Manager Handoff — Current State and Roadmap

Date: 2026-07-16  
Repository: `https://github.com/2604714984-prog/quant-proj`  
Default branch: `v2-main`

Read first:

`reports/agent_handoff/manager_v2_control_constitution_v1_20260716.md`

The constitution controls. This file records current state and approved sequence only.

## 1. Current state

### Architecture

```text
one repository / package / quant CLI / config path
one DuckDB access layer
one portfolio/backtest core
small A-share and US semantic modules
one test suite and CI workflow
```

No architecture work is required.

### Completed shared fixes

```text
#53 architecture freeze and repeatable qualification
#55 A-share limit/slippage = conservative unfilled
#56 fresh run ID and deterministic terminalization
#57 terminal RS failure
#59 benchmark precheck and SHARES/CNY units
#60 actual benchmark invested ratio
#61 defensive low-volatility preregistration/adapter
```

### Relative Strength

```text
research_id=A_SHARE_RELATIVE_STRENGTH_MEDIUM_TERM_MOMENTUM_V1_20260715
status=HISTORICAL_SCREENING_FAIL
gates=16/48
forward=CLOSED
candidate=false
```

Permanent closure: no rerun, retune, rescue filter, regime reinterpretation, or specialist use.

### Active family

```text
A_SHARE_DEFENSIVE_LOW_VOLATILITY_V1_20260717
```

Frozen variants:

```text
LV60
LV120
DSV60
DSV120
```

Frozen execution:

```text
CNY 400,000
15 equal-weight positions
monthly
D close decision / D+1 open execution
510300.SH benchmark
existing costs, capacity, limits, suspensions and board-lot rules
```

No outcomes opened.

### Young-chairman PR #58

```text
outcome-informed historical replication
not an active outcome-blind family
approximately 938 added lines
nine PIT domains
```

Action: close without merge; preserve branch/commit as optional historical material; do not build its data pipeline.

## 2. Immediate Manager actions

Execute in order:

1. Verify and record current `v2-main` HEAD.
2. Confirm PR #61 is merged.
3. Run full CI on current `v2-main`.
4. Close PR #58 without merge.
5. Replace the stale RS-only sentence in `AGENTS.md` with:

```text
During this freeze, only one strategy family may be active at a time.
The active family is the latest user-approved, merged preregistered family on v2-main.
```

6. Create two self-contained task files under `reports/agent_handoff/`:
   - Low-volatility preflight and historical outcome.
   - Local-market Macro Risk Shadow.
7. Return only their GitHub links to the user.

Do not add an active-family registry.

## 3. Cycle 2 — defensive low volatility

Research question: can a 15-name low-risk A-share portfolio produce positive net return while improving volatility, drawdown, Calmar and downside-risk efficiency versus 510300.SH?

No extra filters, windows, variants, optimization, or grids.

### Outcome-free preflight

Allowed aggregate outputs:

```text
coverage
decision count
eligible/candidate min/max
invalid-decision count
benchmark initial fill
benchmark invested ratio
capacity rejection ratio
unexpected exception count
CNY/SHARES confirmation
```

Hard gate:

```text
benchmark_initial_entry_filled=true
unexpected_exception_count=0
units exact
execution panels complete
no embargo/forward access
```

Input failures do not consume the outcome.

### Historical outcome

After preflight PASS, create one fresh Run ID and publish only result + run receipt.

```text
FAIL → close permanently
PASS → prospective Shadow; candidate=false
INPUT_BLOCKED → repair only proven input/semantic defect; new child lineage
```

Ordinary FAIL needs CI + Manager scope check + merge, not full external audit. First PASS requires external review.

## 4. Cycle 3 — conditional short-term reversal

Start only after Cycle 2 terminal result.

Hypothesis:

```text
abnormal short-term decline
+ explicit liquidity/volume shock
+ normal trading state
+ no ST/suspension/locked limit-down/terminal risk
may represent temporary price pressure
```

Maximum four variants:

```text
10-session residual reversal
20-session residual reversal
each with/without one fixed volume-shock condition
```

No plain largest-loser strategy. No macro filter to force a PASS.

## 5. Cycle 4 — ETF / multi-asset trend and defense

If Cycles 2 and 3 fail, prefer a small ETF/multi-asset family over more A-share indicator variants.

Rationale:

```text
small universe
simpler lifecycle handling
better 400k fit
stock/bond/gold/cash diversification
natural macro-risk-cap compatibility
```

Do not create separate RSI, MACD, Bollinger, OBV, KDJ or CCI families. Swing Count remains deferred and cannot rescue RS.

## 6. Macro Risk Shadow

One read-only subagent. Phase 1 uses local data only:

```text
510300 120-session trend
20/60-session volatility
120-session drawdown
positive-60-day-return breadth
medium-term-MA breadth
amount breadth
limit-down share
suspension share
```

Weekly output at most:

```text
risk_score 0–100
GREEN/AMBER/RED
confidence
contributions
stale components
```

Boundary:

```text
SHADOW_ONLY
NO_POSITION_EFFECT
NO_STRATEGY_SELECTION
NO_GATE_CHANGE
NO_ORDER_OR_SIGNAL
```

External macro, news, sentiment and LLM explanation are deferred pending user approval after local Shadow stability.

## 7. Strategy combination

Do not develop now.

Activation gate:

```text
2 independently passing families
different economic sources
shared-account executable targets
prospective Shadow records
static combination tested
```

Comparison sequence:

```text
best single
→ equal-weight static
→ fixed-risk static
→ static + macro cap
→ soft synthesizer
```

Default expectation: `STATIC_ENSEMBLE + MACRO_RISK_CAP`. Failed families are never specialists.

## 8. Data and tools

Long-term PIT fields:

```text
raw OHLC / adjustment factors / corporate actions
calendar / ST / suspension / limits / listing / delisting
available_at / source / revision identity
```

Provider policy:

```text
one canonical provider
one optional read-only cross-check
no automatic fusion
```

Potential roles:

```text
Tushare canonical candidate
AKShare exploratory/cross-check
BaoStock bounded status cross-check
```

Tushare ingestion conversion:

```text
vol × 100 → SHARES
amount × 1000 → CNY
```

Do not build speculative data domains. RQAlpha and Lean are reference oracles only. Qlib is deferred to an isolated read-only experiment after the freeze. RD-Agent, LangGraph, multi-agent trading and a second engine remain excluded.

## 9. Manager/subagent operation

Normal structure:

```text
one logical Manager
one code-writing strategy subagent
one read-only Macro Shadow subagent
short-lived reviewer when required
```

Each task file must pin base commit, active family/stage, allowed/forbidden files, frozen definition, budgets, input/outcome boundary, tests, review trigger and callback.

No oral scope expansion. No concurrent file ownership. Manager does not edit an active subagent branch.

## 10. Review triggers

Full review only for shared accounting/execution/PIT contract changes, first historical PASS, prospective result, first ensemble, first macro position effect, first synthesizer, or trading-stage opening.

No full review for ordinary adapter PRs, preflight PASS, historical FAIL, read-only macro records, or document-only terminal publication.

## 11. Stop conditions

Return `SCOPE_EXPANSION_REQUIRES_USER_APPROVAL` for any constitution breach, budget breach, second active family/writer, post-outcome change, early forward access, failed-family rescue, speculative data, macro position effect, premature synthesizer, trading path, or committed private/large data.

## 12. Manager state and callbacks

Maintain only:

```text
ACTIVE_FAMILY
ACTIVE_STAGE
BASE_COMMIT
SNAPSHOT_ID
CURRENT_PR
PREFLIGHT_STATUS
OUTCOME_STATUS
FORWARD_STATUS
STRATEGY_CANDIDATE_AVAILABLE
NEXT_ACTION
BLOCKERS
```

Expected after housekeeping:

```text
ACTIVE_FAMILY=A_SHARE_DEFENSIVE_LOW_VOLATILITY_V1_20260717
ACTIVE_STAGE=OUTCOME_FREE_REAL_DATA_PREFLIGHT
OUTCOME_STATUS=NOT_RUN
FORWARD_STATUS=CLOSED
STRATEGY_CANDIDATE_AVAILABLE=false
PR_58=TO_CLOSE_WITHOUT_MERGE
NEXT_ACTION=DISPATCH_LOW_VOL_AND_MACRO_SHADOW_TASK_LINKS
```

Housekeeping callback:

```text
STATUS:
V2_MAIN_HEAD:
FULL_CI_STATUS:
PR_58_STATUS:
AGENTS_TEXT_STATUS:
ACTIVE_FAMILY:
LOW_VOL_TASK_FILE_URL:
MACRO_SHADOW_TASK_FILE_URL:
BLOCKERS:
```

Low-volatility terminal callback:

```text
STATUS:
BASE_COMMIT:
SNAPSHOT_ID:
PREFLIGHT_STATUS:
RUN_ID:
RESULT_STATUS:
GATE_COUNTS:
FORWARD_STATUS:
STRATEGY_CANDIDATE_AVAILABLE: false
RESULT_URL:
RUN_RECEIPT_URL:
NEXT_ACTION:
BLOCKERS:
```

## Final directive

Complete low volatility, then conditional reversal, then ETF/multi-asset if needed. Run macro risk only as Shadow. Do not build a synthesizer until two economically distinct families pass and static baselines exist.

Measure success by trustworthy terminal strategy decisions per unit of code, time and complexity—not by files, tests, agents, reports or abstractions.