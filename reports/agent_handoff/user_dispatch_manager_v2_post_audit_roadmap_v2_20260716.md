# User-Dispatch Manager Handoff — V2 Post-Audit Roadmap, Version 2

Date: 2026-07-16
Repository: `2604714984-prog/quant-proj`
Default branch: `v2-main`
Status: `CURRENT_MANAGER_HANDOFF`

## Supersession and repository action

This file supersedes:

```text
reports/agent_handoff/user_dispatch_manager_v2_master_handoff_and_future_roadmap_20260716.md
```

When this file is added to `quant-proj`, delete the superseded file in the same PR. Do not keep two active roadmaps.

Before acting, read:

```text
reports/agent_handoff/manager_v2_control_constitution_v2_20260716.md
```

Precedence:

```text
user's latest explicit instruction
> Manager control constitution v2
> merged AGENTS.md
> this roadmap
> task-specific GitHub file
```

This file records current state and authorized next work. It cannot expand the constitution.

## Current terminal-state update — 2026-07-17

This update records the accepted repository state after Cycle 4 closure and the
shared strict-pre-open repair. It supersedes the stale active-Cycle-4 statements
later in this file without creating another roadmap or control layer.

```text
V2_MAIN_HEAD=6967c2819a27ae11de0410cbffc65e575b519343
ACTIVE_FAMILY=A_SHARE_SWING_STRUCTURE_PARTICIPATION_CONFIRMED_TREND_V1_20260718
ACTIVE_STAGE=OUTCOME_BLIND_PR_A_PREFLIGHT_PASS_AWAITING_INDEPENDENT_ACCEPTANCE
CYCLE_4=CLOSED_DATA_AND_SEMANTIC_CONTRACT_INCOMPLETE_NO_OUTCOME
SOURCE_MATRIX_COMPLETE=false
H3=CLOSED_ACCEPTED_STRICT_PREOPEN
M1=DEFERRED
STRATEGY_CANDIDATE_AVAILABLE=false
```

No closed strategy family may be rerun or reinterpreted because of the H3
repair. Listed-fund distribution semantics, cross-type corporate-action IDs,
and mixed US terminal consideration remain future activation gates rather than
current implementation work.

## 1. Accepted project baseline

The architecture is accepted as reliable and lightweight enough:

```text
one repository
one Python package
one quant CLI
one central DuckDB access layer
one deterministic portfolio / event-loop core
small A-share and US market-semantic modules
one test suite
one CI workflow
```

No architecture rebuild is authorized.

Completed shared corrections that must not be rebuilt:

```text
A-share slippage/limit crossing -> conservative unfilled order
fresh Run-ID separation
deterministic terminalization of input errors
repeatable outcome-free input qualification
benchmark initial-entry preflight
explicit SHARES / CNY unit contract
actual benchmark invested-ratio measurement
60-session variants do not inherit a 120-session data requirement
```

## 2. Closed strategy families

### 2.1 Relative Strength

```text
research_id:
A_SHARE_RELATIVE_STRENGTH_MEDIUM_TERM_MOMENTUM_V1_20260715

status:
HISTORICAL_SCREENING_FAIL

gates:
16 / 48

forward:
closed

strategy_candidate_available:
false
```

Permanent action:

```text
do not retune
do not rerun
do not add filters
do not reclassify as a regime specialist
```

### 2.2 Defensive Low Volatility

```text
research_id:
A_SHARE_DEFENSIVE_LOW_VOLATILITY_V1_20260717

status:
HISTORICAL_GATED_FAIL

gates:
48 / 64

forward:
closed

strategy_candidate_available:
false
```

Terminal evidence reference:

```text
PR #63
merge commit:
ec8d2b93d8c8ad7d585ec3ff31bd6d0ccc52cf2a
```

Observed properties:

```text
all four variants had positive net return
all four reduced volatility
all four reduced maximum drawdown
all eight bootstrap lower-bound gates failed
all four holdout Calmar gates failed
all four holdout downside-efficiency gates failed
```

Adjudication:

```text
ACCEPT_TERMINAL_HISTORICAL_GATED_FAIL
```

The defensive properties are `OBSERVATION_ONLY`. They cannot be used as a specialist, ensemble member, synthesizer input, Macro Risk input, or trading candidate.

## 3. Young-chairman Draft PR

PR #58 is outcome-informed historical replication, not an active outcome-blind family.

Required Manager action:

```text
close PR #58 without merge
preserve its exact head only as optional historical material
record NOT_ACTIVE_NOT_ELIGIBLE_FOR_RESULT_PHASE
do not build a management-data pipeline for it
```

## 4. Immediate repository actions

Execute in order:

1. Add and merge the two Version 2 Manager files.
2. Delete the two superseded Version 1 files in the same PR.
3. Ensure that PR is documentation-only.
4. Close PR #58 without merge.
5. Update the stale active-family sentence in `AGENTS.md`.
6. Run one complete CI suite on final `v2-main`.
7. Record exact `v2-main` HEAD.
8. Publish exactly two new task files under `reports/agent_handoff/`.

Replace stale active-family text with:

```text
Only one code-writing strategy family may be active at a time.
The active family is stated in the current merged Manager roadmap.
```

Do not create an active-family registry.

## 5. Cycle 3 conditional reversal — closed at preflight

Controlling terminal status as of 2026-07-17:

```text
STATUS=CLOSED_PREFLIGHT_STRUCTURAL_INFEASIBLE_NO_OUTCOME
PR_A=#66
MERGE_COMMIT=efe44b9f61769f73be0ed60dbb499d3efb85b27b
PREFLIGHT_STATUS=INPUT_BLOCKED
DECISION_COUNT=89
MINIMUM_ELIGIBLE_COUNT=1339
MINIMUM_CANDIDATE_COUNT=1
INVALID_DECISION_COUNT=28
OUTCOME_RUN_CONSUMED=false
FORWARD_STATUS=CLOSED
STRATEGY_CANDIDATE_AVAILABLE=false
```

Twenty-five invalid decisions were caused by the frozen shock condition yielding
fewer than 15 candidates. Three additional decisions had 15 candidates but a
selected security was explicitly suspended at the next open. The latter is a
known local preflight-versus-engine representation difference, but repairing it
cannot cure the 25 structurally insufficient decisions. Changing the frozen
shock threshold or candidate rule after these counts were observed is forbidden.

Cycle 3 is therefore closed without a historical return run. Do not create a
child lineage, tune the threshold, repair the suspension representation for this
family, or reopen it. The exact closure record is:

```text
reports/agent_handoff/cycle_3_liquidity_shock_preflight_terminal_closure_20260717.md
```

### Preserved original task design

The closed family's outcome-blind design was:

```text
A-share liquidity-shock conditional short-term reversal
```

It was a new economic hypothesis, not a repair of RS or low volatility. This
subsection is failure memory only and grants no current authority.

#### 5.1 Hypothesis

```text
short-term market-relative price decline
+ one explicit abnormal trading-activity shock
+ normal, liquid, executable market state
may represent temporary price pressure rather than permanent deterioration
```

Do not implement plain “buy the largest losers.”

#### 5.2 Research freedom

Freeze no more than four variants before any outcome access.

Recommended structure:

```text
10-session market-relative reversal
20-session market-relative reversal
each with / without one fixed preregistered trading-activity-shock condition
```

The shock formula and threshold must be fixed in PR A.

No parameter grid. No later macro or regime filter.

#### 5.3 Reused execution contract

```text
CNY 400,000
maximum 15 positions
equal weight
ordinary A shares
listed at least 252 accepted sessions
non-ST
non-suspended
liquid universe
D after-close decision
D+1 accepted-session open execution
existing costs, board lot, capacity, limits, suspension, terminal and blocked-exit rules
510300.SH benchmark
CNY / SHARES units
```

No new engine or runner framework.

#### 5.4 Outcome-free preflight

Prove in aggregate:

```text
required history exists
candidate count is sufficient
execution panels are complete
benchmark initial entry fills
benchmark invested ratio is reported
capacity rejection ratio is reported
unexpected exception count is zero
no embargo or prospective data are accessed
```

Do not emit identifiers, rankings, returns, NAV, or gates.

#### 5.5 Original outcome-handling rule

The following was the pre-preflight rule. The controlling terminal adjudication
above now supersedes its generic `INPUT_BLOCKED` repair path for Cycle 3: no
child lineage or repair is authorized for this closed family.

After preflight PASS:

```text
one fresh Run ID
one historical outcome
one result
one run receipt
```

Terminal behavior:

```text
FAIL:
close permanently

PASS:
enter prospective Shadow; remain non-candidate

INPUT_BLOCKED:
repair only the input or financial-semantic defect with a new child lineage
```

An ordinary FAIL needs CI and Manager scope review, not a full external audit.

## 6. Task file 2 — Macro Risk Shadow Phase 1

Use a separate read-only subagent. It must not edit Cycle 3 files.

### 6.1 Inputs

Only existing local-market data:

```text
510300 120-session trend
20-session realized volatility
60-session realized volatility
120-session drawdown
share of stocks with positive 60-session return
share above a frozen medium-term moving average
market amount / turnover breadth
limit-down share
suspension share
```

No external macro provider in Phase 1.

### 6.2 Output

At most one weekly aggregate record:

```text
risk_score: 0–100
risk_level: GREEN / AMBER / RED
confidence
component contributions
stale components
```

### 6.3 Hard boundary

```text
SHADOW_ONLY
NO_POSITION_EFFECT
NO_STRATEGY_SELECTION
NO_ORDER_OR_SIGNAL
NO_USE_AS_A_STRATEGY_GATE
```

Run through current strategy cycles before judging usefulness.

## 7. Subsequent roadmap

### Cycle 4 — terminally closed without outcome

Cycle 4 is no longer active. Its controlling task file remains historical
failure memory:

```text
reports/agent_handoff/cycle_4_a_share_listed_etf_absolute_trend_defensive_allocation_task_20260717.md
```

Current state:

```text
CYCLE_4=CLOSED_DATA_AND_SEMANTIC_CONTRACT_INCOMPLETE_NO_OUTCOME
SOURCE_MATRIX_COMPLETE=false
COMMON_QUALIFIED_DATE_COUNT=0
OUTCOME_STATUS=NOT_RUN
FORWARD_STATUS=CLOSED
STRATEGY_CANDIDATE_AVAILABLE=false
```

Do not reopen this lineage by changing the fixed ETFs, trend rule, cash rule,
costs, source contract, or data threshold. Any future ETF data work must use a
new frozen task and cannot be presented as a Cycle 4 repair.

Future activation gates remain:

```text
LISTED_FUND_DATES=ALLOW_MARKET_VALID_RECORD_EX_PAY_ORDERING
LISTED_FUND_IDENTITY=REQUIRE_SOURCE_BOUND_PRODUCT_TYPE
CORPORATE_ACTION_IDS=REQUIRE_GLOBAL_CROSS_TYPE_UNIQUENESS
US_MIXED_CONSIDERATION=REQUIRE_EXPLICIT_BASIS_ALLOCATION_OR_FAIL_CLOSED
```

Do not launch RSI, MACD, Bollinger Bands, OBV, KDJ, CCI, or separate indicator families.

### Next family — Swing Count selected for PR A

The owner selected Swing Count / volume-confirmed trend on 2026-07-18. It must
remain a new trend-persistence hypothesis, not a rescue of failed RS. The first
authorized implementation phase is one frozen definition, one small adapter and
one aggregate outcome-free preflight. No return, NAV, identifier output or
performance gate is authorized until that preflight passes.

The local read-only preflight completed on 2026-07-18 without opening outcomes
or changing the database. It evaluated 89 historical month-end decisions for
both frozen variants. Minimum eligible counts were 1,212 for SWING20 and 1,210
for SWING60; minimum candidate counts were 56 and 89 respectively. All selected
next-open panels were complete, the benchmark probe filled, and the unexpected
exception count was zero. This remains a local `PREFLIGHT_PASS` pending fresh
independent read-only acceptance; it is not historical strategy evidence.

## 8. Strategy combination remains blocked

Current validated historical specialist count:

```text
0
```

Do not build a synthesizer.

Activation gate:

```text
at least two independently historically passing families
different economic return sources
shared-account executable targets
prospective Shadow evidence
static equal-weight combination implemented first
```

Required order:

```text
best single strategy
→ equal-weight static ensemble
→ fixed-risk-budget static ensemble
→ static ensemble + Macro Risk cap
→ soft synthesizer
```

Failed RS and low volatility cannot enter based on post-hoc regime performance.

## 9. Data and tool policy

### Data

```text
one canonical provider per dataset
at most one read-only cross-check provider
no automatic fusion
new data domains only for the active approved hypothesis
```

Do not speculatively build management, news, macro, options, fundamental, or event domains.

### Tools

Reference-only:

```text
RQAlpha for bounded A-share semantic differential fixtures
Lean for bounded US settlement and corporate-action reference
AKShare / BaoStock / efinance for explicit cross-check roles
```

Deferred:

```text
Qlib after the three-cycle freeze, using read-only V2 exports
```

Rejected from active runtime:

```text
RD-Agent
LangGraph research orchestration
multi-agent buy/sell systems
full financial desktop platforms
second formal backtest engine
automatic provider fusion
```

## 10. External-review rules

Full review is required only for:

```text
shared financial-semantic changes
PIT / availability / unit / snapshot-contract changes
Cycle 3 first historical PASS
any prospective result
first static ensemble
first Macro Risk position effect
first synthesizer result
any trading-stage opening
```

It is not required for an ordinary Cycle 3 FAIL.

## 11. Required Manager callbacks

### Callback A — housekeeping and task publication

```text
STATUS:
V2_MAIN_HEAD:
CONTROL_CONSTITUTION_V2_URL:
CURRENT_ROADMAP_V2_URL:
SUPERSEDED_FILES_DELETED:
PR_58_STATUS:
AGENTS_ACTIVE_FAMILY_TEXT_STATUS:
FULL_CI_STATUS:
CYCLE_3_TASK_FILE_URL:
MACRO_SHADOW_TASK_FILE_URL:
BLOCKERS:
```

### Callback B — Cycle 3 preflight

```text
STATUS:
BASE_COMMIT:
SNAPSHOT_ID:
DEFINITION_SHA256:
ADAPTER_SHA256:
PREFLIGHT_STATUS:
DECISION_COUNT:
MIN_ELIGIBLE_COUNT:
MIN_CANDIDATE_COUNT:
INVALID_DECISION_COUNT:
BENCHMARK_INITIAL_ENTRY_FILLED:
BENCHMARK_INVESTED_RATIO:
CAPACITY_REJECTION_RATIO:
UNEXPECTED_EXCEPTION_COUNT:
OUTCOME_RUN_AUTHORIZED:
NEXT_ACTION:
```

### Callback C — Cycle 3 terminal result

```text
STATUS:
RUN_ID:
RESULT_STATUS:
GATE_COUNTS:
PROSPECTIVE_FORWARD_OPENED: false
STRATEGY_CANDIDATE_AVAILABLE: false
FAMILY_CLOSED_OR_SHADOW:
RESULT_URL:
RUN_RECEIPT_URL:
NEXT_ACTIVE_FAMILY:
NEXT_ACTION:
```

### Callback D — Macro Risk Shadow start

```text
STATUS:
TASK_FILE_URL:
MODULE_SCOPE:
INPUT_COMPONENTS:
OUTPUT_FREQUENCY:
POSITION_EFFECT_ENABLED: false
STRATEGY_SELECTION_ENABLED: false
NEXT_ACTION:
```

## 12. Expected Manager state

```text
ACTIVE_FAMILY=A_SHARE_SWING_STRUCTURE_PARTICIPATION_CONFIRMED_TREND_V1_20260718
ACTIVE_STAGE=OUTCOME_BLIND_PR_A_PREFLIGHT_PASS_AWAITING_INDEPENDENT_ACCEPTANCE
BASE_COMMIT=6967c2819a27ae11de0410cbffc65e575b519343
SNAPSHOT_ID=a_share_qfq_personal_research_20260716_v5
PREFLIGHT_STATUS=LOCAL_PASS_AWAITING_INDEPENDENT_ACCEPTANCE
OUTCOME_STATUS=NOT_RUN
FORWARD_STATUS=CLOSED
STRATEGY_CANDIDATE_AVAILABLE=false
RS_STATUS=HISTORICAL_SCREENING_FAIL_CLOSED
LOW_VOLATILITY_STATUS=HISTORICAL_GATED_FAIL_CLOSED
LIQUIDITY_SHOCK_STATUS=CLOSED_PREFLIGHT_STRUCTURAL_INFEASIBLE_NO_OUTCOME
CYCLE_4_STATUS=CLOSED_DATA_AND_SEMANTIC_CONTRACT_INCOMPLETE_NO_OUTCOME
H3_STATUS=CLOSED_ACCEPTED_STRICT_PREOPEN
M1_STATUS=DEFERRED
YOUNG_CHAIRMAN_PR=CLOSED_WITHOUT_MERGE
NEXT_ACTION=INDEPENDENTLY_ACCEPT_AND_PRESERVE_SWING_COUNT_PR_A_WITHOUT_OUTCOMES
```

## Final directive

The project has zero validated specialists.

The next priority is:

```text
Manager terminal-state sync
-> owner selected Swing Count
-> one outcome-free feasibility scan
+ read-only local Macro Risk Shadow after its separate start gates pass
```

Do not convert partial observations into a specialist. Do not build a synthesizer. Do not add another platform or framework.
