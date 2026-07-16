# User-Dispatch Manager Handoff — V2 Current State and Roadmap

Date: 2026-07-16  
Repository: `https://github.com/2604714984-prog/quant-proj`  
Default branch: `v2-main`

This is the current-state and roadmap handoff for the single logical V2 Manager.

Before acting, read the controlling constitution:

`reports/agent_handoff/manager_v2_control_constitution_v1_20260716.md`

Precedence:

```text
user's latest explicit instruction
> Manager control constitution
> merged AGENTS.md
> this roadmap
> task-specific GitHub file
> conversation memory
```

This roadmap cannot expand the constitution. GitHub is the source of truth; conversation memory is not.

---

# 1. Mission

Operate one reliable, lightweight personal quantitative-research system for approximately CNY 400,000.

The project is no longer in an architecture-development phase.

Primary allocation of attention:

```text
75% strategy discovery and rapid rejection
15% input qualification and execution preflight
10% read-only macro-risk Shadow
0% new architecture, platform, Agent framework, or second backtest engine
```

The Manager coordinates. Isolated subagents implement. The Manager must not become a research engine, coding workstream, or orchestration platform.

---

# 2. Current system state

## 2.1 Active architecture

```text
one repository
one Python package
one quant CLI
one configuration path
one central DuckDB access layer
one deterministic portfolio / backtest core
small A-share and US market-semantics modules
one test suite
one CI workflow
```

Outside Git:

```text
DuckDB databases
raw downloads
snapshots and backups
large generated results
caches
credentials
private manifests and run markers
```

No new architecture is required.

## 2.2 Shared-harness corrections already completed

Merged and not to be rebuilt:

```text
PR #53 architecture freeze and repeatable input qualification
PR #55 A-share limit/slippage crossing = conservative unfilled order
PR #56 fresh run identity and deterministic terminalization
PR #57 terminal Relative Strength negative result
PR #59 benchmark precheck and explicit SHARES/CNY units
PR #60 actual benchmark invested-ratio measurement
PR #61 defensive low-volatility preregistration and adapter
```

## 2.3 Relative Strength status

```text
research_id:
A_SHARE_RELATIVE_STRENGTH_MEDIUM_TERM_MOMENTUM_V1_20260715

status:
HISTORICAL_SCREENING_FAIL

gates:
16 / 48 passed

strategy_candidate_available:
false

prospective_forward_opened:
false
```

Permanent decisions:

- do not rerun or retune;
- do not add volume, macro, regime, moving-average, or threshold filters as a repair;
- do not use RS as a post-hoc regime specialist;
- any future trend research requires a genuinely new economic hypothesis and lineage after the current freeze.

## 2.4 Current active family

```text
A_SHARE_DEFENSIVE_LOW_VOLATILITY_V1_20260717
```

Merged definition and adapter: PR #61.

Frozen variants:

```text
LV60
LV120
DSV60
DSV120
```

Frozen portfolio and execution:

```text
capital: CNY 400,000
maximum positions: 15
weighting: equal weight
rebalance: monthly
signal: D after close
execution: D+1 accepted-session open
benchmark: 510300.SH
units: CNY / SHARES
existing costs, capacity, limits, suspension and board-lot rules
```

No real-data outcomes have been opened for this family.

## 2.5 Young-chairman Draft PR #58

PR:

`https://github.com/2604714984-prog/quant-proj/pull/58`

Status:

```text
outcome-informed historical PIT replication
not an active outcome-blind family
approximately 938 added lines
requires nine PIT data domains
not eligible for a result phase under the current roadmap
```

Required action:

```text
close PR #58 without merge
preserve its exact branch/commit only as optional historical material
record NOT_ACTIVE_NOT_ELIGIBLE_FOR_RESULT_PHASE
```

Do not build a management-data pipeline for this idea unless the user later approves a genuinely new outcome-blind hypothesis with multiple justified data uses.

---

# 3. Immediate Manager actions

Execute in order.

## 3.1 Housekeeping

- Verify and record the current `v2-main` HEAD.
- Confirm PR #61 merge is present.
- Run one complete CI suite on the current `v2-main` state.
- Close PR #58 without merge.
- Update the stale final sentence in `AGENTS.md`.

Replace the RS-specific active-family sentence with:

```text
During this freeze, only one strategy family may be active at a time.
The active family is the latest user-approved, merged preregistered family on v2-main.
```

Do not add an active-family registry.

## 3.2 Publish two task files

After housekeeping, create these independent files under `reports/agent_handoff/`:

```text
1. Low-volatility Cycle 2 preflight and historical-outcome task
2. Local-market Macro Risk Shadow task
```

The user should only need the two GitHub links.

Only the low-volatility task may write strategy code. Macro Risk remains read-only and cannot edit strategy files.

---

# 4. Cycle 2 — defensive low volatility

## 4.1 Objective

Test whether a CNY 400,000, 15-name low-risk A-share portfolio can achieve positive net return while improving volatility, drawdown, Calmar and downside-risk efficiency versus 510300.SH.

## 4.2 Frozen variants

```text
LV60: lowest 60-session realized volatility
LV120: lowest 120-session realized volatility
DSV60: lowest 60-session downside semideviation
DSV120: lowest 120-session downside semideviation
```

Do not add:

```text
relative-strength filters
macro filters
moving averages
volume confirmation
quality filters
industry optimization
additional windows
parameter grids
```

## 4.3 Outcome-free real-data preflight

The preflight is repeatable and must run before any historical return access.

It may output only aggregate health information:

```text
coverage start/end
decision-date count
minimum/maximum eligible count
minimum/maximum candidate count
invalid-decision count
benchmark initial-entry filled
benchmark invested ratio
capacity rejection ratio
unexpected exception count
CNY / SHARES unit confirmation
```

Hard conditions:

```text
benchmark_initial_entry_filled = true
unexpected_exception_count = 0
currency_unit = CNY
position_unit = SHARES
all required execution panels complete
no embargo or prospective data access
```

Input failures do not consume the historical outcome.

## 4.4 Historical outcome

Only after preflight PASS:

- create one fresh Run ID;
- use the frozen four variants and no others;
- run one historical outcome;
- publish only one aggregate result and one run receipt.

Terminal handling:

```text
HISTORICAL_SCREENING_FAIL
→ close permanently
→ no rescue, retune or filter addition

HISTORICAL_SCREENING_PASS
→ enter prospective Shadow
→ candidate remains false

INPUT_BLOCKED
→ repair only the proven input or financial-semantic defect
→ preserve the consumed lineage
→ use a new child lineage
```

Ordinary FAIL does not require a full external audit. CI + Manager scope check + terminal merge is sufficient.

A first historical PASS requires external review.

---

# 5. Cycle 3 — conditional short-term reversal

Start only after Cycle 2 has a terminal result.

New economic hypothesis:

```text
short-term abnormal price decline
+ explicit liquidity or volume shock
+ normal trading state
+ no ST, suspension, locked limit-down or terminal risk
may represent temporary price pressure rather than permanent deterioration
```

Maximum four variants:

```text
10-session residual reversal
20-session residual reversal
each with / without one fixed volume-shock condition
```

Do not implement plain “buy the largest losers.”

Do not use Macro Risk to make this family pass.

Apply the same two-PR and one-outcome limits as Cycle 2.

---

# 6. Cycle 4 — ETF / multi-asset trend and defensive allocation

If Cycle 2 and Cycle 3 both fail, prioritize a small ETF / multi-asset family rather than more A-share technical-indicator variations.

Reasons:

```text
smaller universe
simpler survivorship and corporate-action handling
better fit for CNY 400,000
natural stock / bond / gold / cash diversification
better compatibility with a future macro-risk cap
```

Freeze the investable universe only after data availability and execution semantics are qualified.

Do not create separate RSI, MACD, Bollinger, OBV, KDJ, CCI or fifteen-indicator strategy families.

Swing Count or volume-confirmed trend remains deferred and must be a genuinely new hypothesis, not a rescue of failed RS.

---

# 7. Macro Risk Shadow

Use one separate read-only subagent.

## 7.1 Phase 1 — local market only

Inputs:

```text
510300 120-session trend
20/60-session realized volatility
120-session drawdown
share of stocks with positive 60-session return
share above a medium-term moving average
market amount breadth
limit-down share
suspension share
```

Output at most weekly:

```text
risk_score: 0–100
risk_level: GREEN / AMBER / RED
confidence
component contributions
stale components
```

Hard boundary:

```text
SHADOW_ONLY
NO_POSITION_EFFECT
NO_STRATEGY_SELECTION
NO_GATE_CHANGE
NO_ORDER_OR_SIGNAL
```

Run through at least the current three strategy cycles before judging usefulness.

## 7.2 Deferred phases

After the local Shadow is stable, the user may approve one global financial-stress input.

News sentiment, policy uncertainty and LLM explanations are deferred. If later approved, they may explain risk-score changes but must not directly control positions.

---

# 8. Strategy combination

Do not develop a strategy synthesizer now.

Activation requires all of:

```text
at least two independently historically passing strategy families
different economic return sources
shared-account executable targets
at least one prospective Shadow record per family
static combination implemented and tested
```

Required comparison order:

```text
B0 best single strategy
B1 equal-weight static ensemble
B2 fixed-risk-budget static ensemble
B3 static ensemble + macro total-risk cap
B4 soft strategy synthesizer
```

Default expected solution:

```text
STATIC_ENSEMBLE + MACRO_RISK_CAP
```

A first dynamic version, if later authorized, uses only:

```text
TREND / NEUTRAL / STRESS
soft bounded weight changes
low confidence returns to static weights
no winner-takes-all hard switching
```

A failed family can never enter the combination as a post-hoc specialist.

---

# 9. Data policy

Long-term strict PIT objective:

```text
raw OHLC
adjustment factors
corporate actions
accepted calendar
ST / suspension / limit / listing / delisting status
available_at
source identity
revision identity
```

Retrospective provider-hindsight qfq data supports secondary historical screening only.

Provider rule:

```text
one canonical provider per dataset
at most one read-only cross-check provider
no automatic source selection or fusion
```

Potential future positioning:

```text
Tushare: canonical A-share provider candidate
AKShare: exploratory or cross-check
BaoStock: bounded status/historical cross-check when explicitly qualified
```

Tushare conversions at ingestion:

```text
volume_shares = tushare vol × 100
amount_cny = tushare amount × 1000
```

A missing Tushare daily row during suspension must be reconciled with a qualified suspension-status source. Do not silently delete it or treat it as an ordinary provider gap.

Add a data domain only for an approved active hypothesis, with exact fields, units, availability, source and revision identity. Do not speculatively build management, news, macro, options, fundamentals or event domains.

---

# 10. External tools

Reference only:

```text
RQAlpha: A-share market-semantics differential oracle
Lean: US company-action, settlement and order-lifecycle reference
AKShare / efinance: exploratory cross-check only
AI Berkshire / daily_stock_analysis: research-template inspiration only
```

Deferred isolated experiment:

```text
Qlib read-only factor / ML sandbox after the three-cycle freeze
```

Any Qlib output must return to the V2 event loop for validation.

Rejected from the active runtime:

```text
RD-Agent
LangGraph research orchestration
FinceptTerminal-style platform
multi-agent buy/sell systems
full financial terminal
multi-provider automatic fusion
second formal backtest engine
```

---

# 11. Subagent operating model

One logical Manager controls:

```text
one active code-writing strategy subagent
at most one read-only Macro Risk subagent
one short-lived review subagent when required
```

For each new subagent or fresh conversation, create a self-contained task file under:

```text
reports/agent_handoff/
```

Every task file includes:

```text
mission
exact base branch and commit
active family and stage
allowed files
forbidden files and scope
frozen definition
input and outcome boundary
line and PR budgets
acceptance tests
review trigger
terminal callback
```

No oral correction may expand scope. Material changes require a replacement GitHub task file.

No nested implementation-agent trees. No concurrent file ownership. The Manager does not edit an active subagent branch.

---

# 12. External-review policy

Full independent review is required only for:

```text
Event Loop or Portfolio-accounting changes
market execution, settlement, corporate-action or cost-semantic changes
PIT, availability, data-unit or snapshot-contract changes
first historical PASS
any prospective result
first static ensemble result
first macro-risk position effect
first dynamic synthesizer result
any trading-stage opening
```

Full external review is not required for:

```text
ordinary preregistered adapters
aggregate preflight PASS
ordinary historical FAIL
read-only Macro Shadow records
document-only terminal result PRs
```

---

# 13. Mandatory stop conditions

Stop and return `SCOPE_EXPANSION_REQUIRES_USER_APPROVAL` if a task proposes:

```text
new repository, CLI, database layer, writer, event loop or backtest engine
new runner, registry, dispatcher, evidence or manifest framework
more than one active strategy family
more than one code-writing subagent
strategy adapter above 300 runtime lines
more than two implementation PRs for a family
more than six variants
parameter or gate changes after outcome access
early embargo or prospective access
rescuing a failed strategy
using a failed strategy as a regime specialist
speculative data-domain construction
macro position effect without approval
strategy synthesizer before its activation gate
broker, order, paper, live, automatic or production trading
committing a database, credential, raw payload or large private artifact
```

Do not partially implement while waiting for approval.

---

# 14. Manager state

Maintain only this logical state; do not create a registry:

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

Expected state after housekeeping:

```text
ACTIVE_FAMILY=A_SHARE_DEFENSIVE_LOW_VOLATILITY_V1_20260717
ACTIVE_STAGE=OUTCOME_FREE_REAL_DATA_PREFLIGHT
OUTCOME_STATUS=NOT_RUN
FORWARD_STATUS=CLOSED
STRATEGY_CANDIDATE_AVAILABLE=false
YOUNG_CHAIRMAN_PR=TO_CLOSE_WITHOUT_MERGE
NEXT_ACTION=DISPATCH_LOW_VOLATILITY_AND_MACRO_SHADOW_TASK_FILES
```

---

# 15. Required callbacks

## Housekeeping

```text
STATUS:
V2_MAIN_HEAD:
FULL_CI_STATUS:
PR_58_STATUS:
AGENTS_ACTIVE_FAMILY_TEXT_STATUS:
ACTIVE_FAMILY:
LOW_VOL_TASK_FILE_URL:
MACRO_SHADOW_TASK_FILE_URL:
BLOCKERS:
```

## Low-volatility preflight

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

## Low-volatility terminal result

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

## Macro Shadow start

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

---

# Final directive

Complete low volatility first. Then conditional reversal. If both fail, prioritize a small ETF / multi-asset family. Run macro risk only as a read-only Shadow. Do not develop a strategy synthesizer until at least two economically distinct families have passed and static-combination baselines exist.

Success is measured by economically distinct families reaching trustworthy terminal decisions per unit of code, time and complexity—not by the number of files, tests, tasks, agents, reports or abstractions.