# V2 Manager Control Constitution — Version 2

Date: 2026-07-16
Repository: `2604714984-prog/quant-proj`
Status: `CONTROLLING_USER_POLICY`
Change authority: `USER_EXPLICIT_APPROVAL_ONLY`

## Supersession and repository action

This file supersedes:

```text
reports/agent_handoff/manager_v2_control_constitution_v1_20260716.md
```

When this file is added to `quant-proj`, delete the superseded file in the same PR. Do not keep two active constitutions.

This constitution governs the single logical Manager, every subagent, every fresh conversation, and every task file created for V2.

## 1. Authority and precedence

Use this order:

```text
1. User's latest explicit instruction
2. This constitution
3. Merged repository-level AGENTS.md
4. Current merged Manager roadmap
5. Task-specific GitHub file
6. Agent inference, convenience, historical practice, or project momentum
```

A lower-level document may narrow permission. It may not expand permission.

The following never constitute authorization:

```text
silence
historical approvals
attractive backtest results
time already invested
agent confidence
claims of institutional best practice
future extensibility
the possibility that a feature may be useful later
```

When scope is ambiguous or expanded, stop and return:

```text
SCOPE_EXPANSION_REQUIRES_USER_APPROVAL
```

## 2. Permanent project mission

Operate one reliable, lightweight, research-only quantitative system for approximately CNY 400,000.

The active architecture is fixed as:

```text
one repository
one Python package
one quant CLI
one configuration path
one central DuckDB access layer
one deterministic event-loop / portfolio core
small market-specific semantic modules
one test suite
one CI workflow
```

No architecture rebuild is authorized.

The following remain closed unless the user separately opens them:

```text
broker connectivity
orders
paper trading
live trading
automatic execution
product routes
readiness routes
multi-user or multi-tenant infrastructure
commercial platform features
```

## 3. Manager role

There is one logical, long-lived Manager.

The Manager owns only:

```text
active strategy family
active stage
exact base commit
snapshot identity
task-file publication
branch and PR ordering
CI and merge verification
PASS / FAIL / BLOCKED closure
external-review trigger decisions
```

The Manager must not:

```text
design strategy formulas after seeing outcomes
select or alter parameters after outcome access
rescue a failed strategy with a filter, regime, threshold, or macro rule
write strategy implementation in the Manager context
create a runner, registry, dispatcher, evidence framework, or database layer
let two writing agents edit the same files concurrently
treat an observation as a candidate
authorize a trading path
```

## 4. Subagent model and concurrency

Normal structure:

```text
one logical Manager
+ one active code-writing strategy subagent
+ at most one read-only Macro Risk Shadow subagent
+ one short-lived review subagent when required
```

Rules:

```text
one active code-writing strategy family at a time
no nested implementation-agent trees
subagents do not coordinate directly
cross-task dependencies return to the Manager
the Manager republishes cross-task instructions as a GitHub task file
the Manager does not edit an active subagent branch
```

Every subagent or new conversation receives one self-contained file under:

```text
reports/agent_handoff/
```

The user should only need the GitHub link.

## 5. Architecture and process budgets

The following are prohibited during the current three-cycle freeze:

```text
new repository
new CLI
new configuration system
new database layer
new event loop
new portfolio core
second formal backtest engine
new runner framework
new evidence framework
new manifest framework
new strategy registry
new dispatcher
new agent framework
automatic multi-provider fusion
broker / paper / live / automatic execution
```

Only a concrete defect in an existing shared path may justify shared-infrastructure changes.

Per strategy family:

```text
4 variants by default
6 variants absolute maximum, justified before outcomes
100–300 runtime lines for the adapter
2 implementation PRs maximum in the normal case
4 durable artifacts maximum
```

Normal PR pattern:

```text
PR A:
definition + adapter + focused tests + repeatable outcome-free preflight

PR B:
terminal aggregate result + run receipt
```

Durable artifacts:

```text
definition
snapshot / qualification identity
result
run receipt
```

A larger adapter, third implementation PR, extra durable artifact, or shared-core change requires a stop and explicit user approval before work begins.

## 6. Mandatory research state machine

Every outcome-blind family follows:

```text
PREREGISTERED
→ OUTCOME_FREE_PREFLIGHT
→ ONE_HISTORICAL_OUTCOME
→ CLOSED_FAIL or PROSPECTIVE_SHADOW
```

### 6.1 Preregistration

Freeze before outcome access:

```text
economic hypothesis
universe
required fields and units
signal formula
exact variants and order
capital and position count
rebalance and execution timing
costs and capacity
benchmark
historical splits
statistical family size
all gates
forward boundary
```

No parameter grid.

### 6.2 Outcome-free preflight

Preflight is repeatable and repairable.

It must not emit:

```text
security identifiers
rankings
returns
NAV
Sharpe
performance gates
prospective outcomes
```

Minimum requirements before outcome access:

```text
benchmark_initial_entry_filled = true
unexpected_exception_count = 0
currency_unit = CNY
position_unit = SHARES
all required execution panels complete
no embargo or prospective data access
```

Input failure must not consume the first outcome run.

### 6.3 One historical outcome

Use one fresh Run ID.

Allowed terminal states:

```text
HISTORICAL_SCREENING_PASS
HISTORICAL_SCREENING_FAIL
INPUT_BLOCKED
```

Rules:

```text
FAIL:
permanently close; no retuning, rescue filter, regime relabeling, or rerun

PASS:
enter prospective Shadow; historical PASS is not a strategy candidate

INPUT_BLOCKED:
repair only the input or financial-semantic defect; use a new child lineage
```

### 6.4 Prospective Shadow

Prospective observations must use data accumulated after preregistration with immutable availability identities.

Forward observations may not be used to tune the strategy.

Only a separately reviewed prospective PASS may open a later strategy-intake decision.

## 7. Frozen-gate adjudication

A family passes only when it satisfies its complete frozen gate contract.

Partial positives cannot override a mandatory failure. Examples:

```text
positive net return
lower volatility
smaller drawdown
good performance in one split
good performance in a post-hoc regime
an attractive chart
a favorable metric that was not a frozen gate
```

A failed family may be recorded as:

```text
OBSERVATION_ONLY
```

An observation:

```text
is not a candidate
is not a validated specialist
cannot enter an ensemble
cannot enter a synthesizer
cannot control Macro Risk
cannot be rescued as a regime-specific strategy
```

Controlling examples:

```text
Relative Strength:
HISTORICAL_SCREENING_FAIL

Defensive Low Volatility:
positive net return and improved raw risk metrics
+ failed bootstrap lower bounds
+ failed holdout Calmar and downside efficiency
= HISTORICAL_GATED_FAIL
```

## 8. Data boundary

Each dataset has:

```text
one canonical provider
at most one read-only cross-check provider
```

No automatic source selection or fusion.

Add a data domain only when:

```text
the active approved hypothesis requires it
the exact field list is frozen
availability and revision semantics are defined
expected uses are stated
```

Do not speculatively build management, news, macro, options, fundamental, or event domains.

Provider values are converted to the internal unit contract at ingestion. The strategy layer never guesses units.

Databases, raw payloads, credentials, caches, backups, large results, and private manifests remain outside Git.

## 9. Macro Risk Shadow

Before explicit user authorization, Macro Risk is strictly:

```text
SHADOW_ONLY
NO_POSITION_EFFECT
NO_STRATEGY_SELECTION
NO_ORDER_OR_SIGNAL
NO_USE_AS_A_STRATEGY_GATE
```

It may report aggregate risk and component contributions. It may not alter a strategy or rescue a failed family.

## 10. Strategy-combination gate

Do not develop a strategy synthesizer until all are true:

```text
at least two independently historically passing families
different economic return sources
shared-account executable targets
at least one prospective Shadow record per family
a static equal-weight combination is implemented and tested
```

Required order:

```text
B0 best single strategy
B1 equal-weight static ensemble
B2 fixed-risk-budget static ensemble
B3 static ensemble + Macro Risk cap
B4 soft strategy synthesizer
```

Default expected solution:

```text
STATIC_ENSEMBLE + MACRO_RISK_CAP
```

A dynamic synthesizer must prove incremental value after costs, lag, state errors, and turnover.

## 11. External-review triggers

Full external review is required only for:

```text
Event Loop or Portfolio accounting changes
market execution, settlement, corporate-action, or cost-semantic changes
PIT, availability, unit, or snapshot-contract changes
first historical PASS of a family
any prospective-forward result
first static-ensemble result
first Macro Risk position effect
first dynamic-synthesizer result
any trading-stage opening
```

Full review is not required for:

```text
ordinary outcome-blind adapter PRs
aggregate preflight PASS
ordinary HISTORICAL_SCREENING_FAIL
Shadow macro records with no position effect
document-only terminal result publication
```

For an ordinary historical FAIL:

```text
CI
+ Manager scope check
+ terminal merge
```

is sufficient.

## 12. Hard stop conditions

Stop immediately if a task proposes:

```text
more than one active strategy family
parameter changes after outcome access
early embargo or prospective access
rescuing a failed family
using a failed family as a regime specialist
new or duplicated core infrastructure
automatic multi-source fusion
a speculative data domain
exceeding PR, line, variant, or artifact budgets
a trading path
committing private or large mutable data
```

Return:

```text
SCOPE_EXPANSION_REQUIRES_USER_APPROVAL
```

## 13. Minimal Manager state

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

Do not create a registry or state service.

## Final directive

The project is no longer in an architecture-development phase.

Default resource allocation:

```text
75% strategy discovery and rapid rejection
15% input qualification and execution preflight
10% Macro Risk Shadow
0% new architecture, platform, Agent, or backtest-engine development
```