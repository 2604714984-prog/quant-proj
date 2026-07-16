# User-Dispatch Manager Handoff — V2 Current State and Future Roadmap

Date: 2026-07-16  
Repository: `https://github.com/2604714984-prog/quant-proj`  
Default branch: `v2-main`

This document is the authoritative handoff for the single logical V2 Manager conversation. Read it before creating any new task. GitHub is the source of truth; conversation memory is not.

---

# 1. Manager mission

Operate one reliable, lightweight personal quantitative-research system for approximately CNY 400,000 of capital.

The Manager is the only long-lived control entry point. It may open isolated subagents or fresh conversations, but must not become a second research engine or a new orchestration platform.

The Manager owns:

- the active strategy-family state;
- task-file publication;
- exact branch and commit pinning;
- snapshot selection;
- PR ordering;
- CI and merge checks;
- PASS / FAIL / BLOCKED closure;
- external-review trigger decisions.

The Manager must not:

- select parameters after reading outcomes;
- rescue a failed strategy with additional filters;
- choose winners based on test or forward results;
- invent a new runner, registry, dispatcher, evidence framework, or database layer;
- implement strategy formulas in the Manager context;
- let two writing agents edit the same files concurrently;
- authorize broker, paper, live, order, or automatic trading paths.

Use the operating principle:

```text
one logical manager
+ one active code-writing strategy subagent
+ at most one read-only macro-risk subagent
+ short-lived review subagents when required
```

Do not maintain multiple permanent Managers.

---

# 2. Current project state

## 2.1 Architecture

The active system remains intentionally small:

```text
one repository
one Python package
one quant CLI
one central DuckDB access layer
one deterministic backtest / portfolio core
small A-share and US market-semantics modules
one test suite
one CI workflow
```

The following remain outside Git:

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

## 2.2 Completed shared-harness corrections

The following are already merged and must not be rebuilt:

- PR #59 — benchmark initial-entry outcome-free precheck and explicit `SHARES` / `CNY` units;
- PR #60 — actual benchmark invested-ratio measurement;
- PR #55 — A-share limit/slippage crossings become conservative unfilled orders;
- PR #56 — fresh run-ID separation and deterministic error terminalization;
- PR #53 — architecture freeze and repeatable input qualification;
- PR #57 — terminal Relative Strength historical failure evidence.

Links:

- `https://github.com/2604714984-prog/quant-proj/pull/59`
- `https://github.com/2604714984-prog/quant-proj/pull/60`
- `https://github.com/2604714984-prog/quant-proj/pull/55`
- `https://github.com/2604714984-prog/quant-proj/pull/56`
- `https://github.com/2604714984-prog/quant-proj/pull/53`
- `https://github.com/2604714984-prog/quant-proj/pull/57`

## 2.3 Relative Strength status

The Relative Strength / medium-term momentum family is permanently closed:

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

All eight validation / retrospective-holdout tests failed every performance and statistical gate. Do not reopen this lineage. Do not add volume, macro, regime, moving-average, or parameter changes and present the result as a repair of the same family.

RS may only return under a genuinely different economic hypothesis, new preregistration, and new lineage after the current three-cycle freeze.

## 2.4 Current active family

The active strategy family is:

```text
A_SHARE_DEFENSIVE_LOW_VOLATILITY_V1_20260717
```

PR #61 is merged:

`https://github.com/2604714984-prog/quant-proj/pull/61`

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
existing costs, limits, suspension, capacity and board-lot rules
```

No outcomes have been opened by the preregistration / adapter merge.

## 2.5 Young-chairman Draft PR

PR #58 is not an active new strategy family:

`https://github.com/2604714984-prog/quant-proj/pull/58`

It is an outcome-informed historical PIT replication, adds approximately 938 lines, requires nine PIT domains, and is inconsistent with the current strategy-priority and lightweight process.

Required Manager action:

```text
close PR #58 without merge
preserve branch/commit as optional historical research material
record: NOT_ACTIVE_NOT_ELIGIBLE_FOR_RESULT_PHASE
```

Do not build a management-data pipeline for this replication unless a future independent, outcome-blind hypothesis and multiple approved uses justify it.

---

# 3. Immediate action checklist

Execute in this order.

## 3.1 Repository housekeeping

- [ ] Verify the current `v2-main` HEAD and record it before dispatch.
- [ ] Confirm PR #61 merge is present on `v2-main`.
- [ ] Run one full CI suite on the final `v2-main` state after PR #61.
- [ ] Close PR #58 without merge and preserve its exact head as historical material only.
- [ ] Update the stale final sentence in `AGENTS.md`.

Replace:

```text
During this freeze, relative-strength data qualification is the only active family.
```

With a minimal rule such as:

```text
During this freeze, only one strategy family may be active at a time.
The active family is the latest merged preregistered family on v2-main.
```

Do not add an active-family registry.

## 3.2 Low-volatility Cycle 2

- [ ] Create one task file for the strategy subagent in `reports/agent_handoff/`.
- [ ] Bind the exact merged low-volatility definition and module identities.
- [ ] Run a repeatable, outcome-free real-data preflight.
- [ ] Confirm every hard preflight condition before consuming any outcome run.
- [ ] Only after preflight PASS, create one fresh run ID and one outcome lineage.
- [ ] Publish only the final aggregate result and one run receipt.
- [ ] Close the family permanently on FAIL; enter prospective Shadow on PASS.

## 3.3 Macro-risk Shadow

- [ ] Create a separate read-only task file after the low-volatility task is dispatched.
- [ ] Allow only local-market risk features in phase 1.
- [ ] Do not let macro-risk output change portfolio weights or strategy selection.
- [ ] Publish at most one aggregate weekly Shadow record.

---

# 4. Three-cycle architecture freeze

For the next three active strategy families, the following are prohibited:

```text
new CLI
new database layer
new event loop
new portfolio core
new runner framework
new evidence framework
new manifest schema
new strategy registry
new dispatcher
new agent framework
new provider aggregation framework
second formal backtest engine
broker / paper / live / automatic execution
```

Only concrete defects in the existing shared path may be fixed.

A new strategy adapter should normally be 100–300 runtime lines. A larger adapter requires an explicit Manager stop and user approval.

Each strategy family should normally require no more than two PRs:

```text
PR A:
definition + adapter + focused tests + repeatable outcome-free preflight

PR B:
terminal aggregate result + run receipt
```

Do not reproduce the multi-PR Relative Strength process.

Durable artifacts per family are limited to:

```text
definition
snapshot / qualification identity
result
run receipt
```

Prefer Git commit/blob identities over extra sidecars.

---

# 5. Standard strategy-cycle contract

## Stage 1 — outcome-blind preregistration

Freeze before outcome access:

```text
economic hypothesis
universe
required fields
signal formula
variant count and exact order
capital and position count
rebalance and execution timing
costs and capacity
benchmark
historical splits
statistical family size
gates
forward boundary
```

Maximum variants per family:

```text
4–6
```

No parameter grid.

## Stage 2 — repeatable outcome-free preflight

The preflight may be rerun and repaired. It must not output:

```text
security identifiers
rankings
returns
NAV
Sharpe
performance gates
forward outcomes
```

It may output only aggregate health fields such as:

```text
coverage dates
decision count
minimum / maximum eligible count
minimum / maximum candidate count
invalid-decision count
benchmark initial-entry filled
benchmark invested ratio
capacity rejection ratio
unexpected exception count
currency and position units
```

Hard requirements before outcome access:

```text
benchmark_initial_entry_filled = true
unexpected_exception_count = 0
currency_unit = CNY
position_unit = SHARES
all required execution panels complete
no prospective data access
```

Input failures must not consume the first outcome run.

## Stage 3 — one historical outcome

Use one fresh run ID. The historical result may be:

```text
HISTORICAL_SCREENING_PASS
HISTORICAL_SCREENING_FAIL
INPUT_BLOCKED
```

Rules:

```text
FAIL -> permanently close; no retuning or rescue filters
PASS -> enter prospective Shadow; not an automatic candidate
INPUT_BLOCKED -> repair only the input or financial semantic defect; use a new child lineage
```

Never change variants, thresholds, costs, benchmark, or holding count after reading outcomes.

## Stage 4 — prospective Shadow

A historical PASS remains research-only.

Prospective results must use data accumulated after preregistration, with immutable availability identities. Forward results must not be used to tune the strategy.

Only a future separately reviewed prospective PASS may open a strategy-intake decision.

---

# 6. Research roadmap

## Cycle 2 — defensive low volatility

Current active family. Complete it before starting another code-writing strategy family.

Frozen variants:

```text
LV60: lowest 60-session realized volatility
LV120: lowest 120-session realized volatility
DSV60: lowest 60-session downside semideviation
DSV120: lowest 120-session downside semideviation
```

The family must remain free of:

```text
relative-strength filters
macro filters
moving-average filters
volume confirmation
quality or industry optimization
```

Primary research question:

```text
Can a CNY 400,000, 15-name low-risk A-share portfolio achieve positive net return while improving volatility, drawdown, Calmar and downside-risk efficiency versus 510300.SH?
```

## Cycle 3 — conditional short-term reversal

Start only after Cycle 2 has a terminal result.

New economic hypothesis:

```text
short-term abnormal price decline
+ explicit liquidity / volume shock
+ normal trading state
+ no ST, suspension, locked limit-down or terminal risk
may represent temporary price pressure rather than permanent deterioration
```

Maximum four frozen variants:

```text
10-session residual reversal
20-session residual reversal
each with / without one fixed volume-shock condition
```

Do not implement plain “buy the largest losers.”

Do not use the macro-risk Shadow to make this family pass.

## Cycle 4 — ETF / multi-asset trend and defensive allocation

If Cycle 2 and Cycle 3 both fail, prioritize a small ETF / multi-asset family rather than additional A-share indicator variations.

Reasons:

```text
smaller universe
simpler survivorship and corporate-action handling
better fit for 400k capital
natural stock / bond / gold / cash diversification
better compatibility with a future macro-risk cap
```

Freeze the investable universe only after data availability and execution semantics are qualified.

Do not immediately add RSI, MACD, Bollinger Bands, OBV, KDJ, CCI, or fifteen separate technical-indicator families.

## Deferred idea — Swing Count / volume-confirmed trend

This is not active during the three-cycle freeze.

It may be considered later only as a genuinely new trend-persistence hypothesis, not as a rescue of failed RS.

---

# 7. Macro-risk Shadow roadmap

Use a separate read-only subagent. Do not let it edit strategy files.

## Phase 1 — local-market stress only

Use already available market data:

```text
510300 120-session trend
20 / 60-session realized volatility
120-session drawdown
share of stocks with positive 60-session return
share above a medium-term moving average
market turnover / amount breadth
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

Boundary:

```text
SHADOW_ONLY
NO_POSITION_EFFECT
NO_STRATEGY_SELECTION
NO_ORDER_OR_SIGNAL
```

Run through at least the three active strategy cycles before judging usefulness.

## Phase 2 — one global financial-stress input

Only after local Shadow is stable, consider one primary external measure such as OFR Financial Stress Index.

Do not add many overlapping macro indicators.

## Phase 3 — narrative / policy context

News sentiment, policy uncertainty, or LLM-generated explanations are deferred.

If later added, they may explain risk-score changes but must not directly control position weights.

---

# 8. Strategy-combination roadmap

Do not develop a strategy synthesizer now.

Minimum activation gate:

```text
at least two independently historically passing strategy families
different economic return sources
shared-account executable targets
at least one prospective Shadow record per family
static combination fully implemented and tested
```

Required benchmark order:

```text
B0: best single strategy
B1: equal-weight static ensemble
B2: fixed-risk-budget static ensemble
B3: static ensemble + macro total-risk cap
B4: soft strategy synthesizer
```

The default expected solution is:

```text
STATIC_ENSEMBLE + MACRO_RISK_CAP
```

Dynamic allocation must prove incremental benefit after costs, lag, state errors and turnover.

First dynamic version, if eventually permitted:

```text
three states only: TREND / NEUTRAL / STRESS
soft bounded weight changes
low confidence returns to static weights
no winner-takes-all hard switching
```

A failed strategy cannot be included as a regime specialist based on post-hoc episode analysis.

---

# 9. Data roadmap

## 9.1 Long-term PIT objective

Accumulate immutable prospective data with:

```text
raw OHLC
adjustment factors
corporate actions
accepted calendar
ST / suspension / limit / listing / delisting state
available_at
source identity
revision identity
```

Retrospective provider-hindsight qfq data may be used only for secondary historical screening, not final candidate evidence.

## 9.2 Provider policy

Each dataset has:

```text
one canonical provider
at most one read-only cross-check provider
```

No automatic multi-source selection or fusion.

Recommended future positioning:

```text
Tushare: canonical A-share provider candidate
AKShare: exploratory / secondary cross-check
BaoStock: bounded status or historical cross-check where explicitly qualified
```

Tushare unit conversion must occur at ingestion:

```text
volume_shares = tushare vol * 100
amount_cny = tushare amount * 1000
```

Tushare daily missing rows during suspension must be reconciled with a separate qualified suspension-status source; do not treat absence as an ordinary data gap or silently delete the status row.

## 9.3 Add data only for an approved hypothesis

Do not build full management, news, macro, options, fundamentals, or event domains speculatively.

A new data domain requires:

```text
an approved current hypothesis
an exact field list
availability semantics
source and revision identity
at least two expected uses, unless the user explicitly approves one-off research
```

---

# 10. External tools policy

## Reference-only

```text
RQAlpha: A-share market-semantics differential oracle
Lean: US corporate-action, settlement and order-lifecycle reference
AKShare / efinance: exploratory cross-check only
AI Berkshire / daily_stock_analysis: research-template inspiration only
```

Do not make any of them a runtime dependency.

## Deferred isolated experiments

```text
Qlib: future read-only factor / ML sandbox after three cycles
```

Any Qlib output must return to the V2 event loop for validation.

## Rejected from the active project

```text
RD-Agent
LangGraph research orchestration
FinceptTerminal-style platform
multi-agent buy/sell decision systems
full financial desktop terminal
multi-provider automatic fusion
second formal backtest engine
```

---

# 11. Manager / subagent operating model

## 11.1 Task publication

For every new subagent or fresh conversation, create a self-contained task file under:

```text
reports/agent_handoff/
```

The user should only need the GitHub link.

Each task file must include:

```text
mission
exact base branch and commit
allowed files
forbidden files and scope
frozen research definition
input and outcome boundary
acceptance tests
PR requirements
terminal callback
```

Do not rely on oral corrections outside the task file.

## 11.2 Concurrency

Maximum normal concurrency:

```text
one code-writing strategy subagent
one read-only macro-risk subagent
one temporary review subagent when needed
```

No nested subagent trees for implementation.

Subagents do not coordinate directly. Cross-task dependencies return to the Manager and are republished as a new GitHub task file.

## 11.3 File ownership

No two writing agents may edit the same files at the same time.

Manager must not “help” by editing an active subagent branch.

---

# 12. External-review policy

Full independent external review is required only for:

```text
changes to Event Loop or Portfolio accounting
changes to market execution, settlement, corporate-action or cost semantics
changes to PIT, availability, data-unit or snapshot contracts
first historical PASS of a strategy family
any prospective-forward result
first static ensemble result
first macro-risk position effect
first dynamic synthesizer result
any broker, paper, live or trading-stage opening
```

Full external review is not required for:

```text
ordinary outcome-blind strategy adapter PRs
aggregate preflight PASS
ordinary HISTORICAL_SCREENING_FAIL
Shadow macro records that cannot affect positions
document-only result publication
```

For normal negative strategy results:

```text
CI
+ Manager scope check
+ terminal merge
```

is sufficient.

---

# 13. Stop conditions

Stop immediately and return to the user if any task proposes:

```text
a new repository
a new CLI or database layer
a new runner / registry / evidence framework
a second event or backtest engine
more than one active strategy family
parameter changes after outcome access
opening embargo or prospective outcomes early
rescuing a failed family with a new filter
using a failed strategy as a regime specialist
automatic multi-source data selection
broker, order, paper, live or automatic execution
committing database, credential, raw payload or large private artifacts
```

Return:

```text
SCOPE_EXPANSION_REQUIRES_USER_APPROVAL
```

---

# 14. Manager status model

Maintain only this small logical state, preferably in the Manager response rather than a new registry:

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

Current expected state after housekeeping:

```text
ACTIVE_FAMILY=A_SHARE_DEFENSIVE_LOW_VOLATILITY_V1_20260717
ACTIVE_STAGE=OUTCOME_FREE_REAL_DATA_PREFLIGHT
OUTCOME_STATUS=NOT_RUN
FORWARD_STATUS=CLOSED
STRATEGY_CANDIDATE_AVAILABLE=false
YOUNG_CHAIRMAN_PR=TO_CLOSE_WITHOUT_MERGE
NEXT_ACTION=DISPATCH_LOW_VOLATILITY_PREFLIGHT_AND_OUTCOME_TASK
```

---

# 15. Required Manager callbacks

## Callback A — housekeeping complete

```text
STATUS:
V2_MAIN_HEAD:
FULL_CI_STATUS:
PR_58_STATUS:
AGENTS_ACTIVE_FAMILY_TEXT_STATUS:
ACTIVE_FAMILY:
NEXT_TASK_FILE_URL:
BLOCKERS:
```

## Callback B — low-volatility preflight

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

## Callback C — low-volatility terminal outcome

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

## Callback D — macro-risk Shadow start

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

The system is no longer in an architecture-development phase.

The governing priority is:

```text
75% strategy discovery and rapid rejection
15% input qualification and execution preflight
10% macro-risk Shadow research
0% new architecture, platform, Agent or backtest-engine development
```

Complete low volatility, then conditional reversal, then ETF / multi-asset trend. Start macro-risk as a read-only Shadow. Do not build a strategy synthesizer until at least two independent strategy families have genuinely passed and static combination baselines exist.
