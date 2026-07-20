# Manager Weeklong Autonomous Program After PR #110

Date: 2026-07-20  
Control period: seven calendar days from dispatch  
Primary market: US  
Repository: `2604714984-prog/quant-proj`

## Mission

Advance several independent research-enabling directions while the user is unavailable, without turning the lightweight personal project into a data platform, research factory, or multi-service architecture.

The objective is not to maximize commits. The objective is to return with several concrete, compact, outcome-blind readiness decisions and one main research lane prepared for the next external review.

## Authority chain

```text
latest explicit user instruction
> accepted external audit of PR #110
> merged control constitution and AGENTS.md
> this task
> subagent task files
```

No subagent may expand its own authority.

## Initial required action

Mark PR #110 Ready and merge only if its HEAD remains:

```text
783059c6e4176af87de7de3f8f80c29e05083031
```

Record the merge commit in the week closeout. If the HEAD has changed, do not merge; request a new exact-head review.

## Program structure

Run the following workstreams in parallel, using separate branches or Git-external scratch areas:

1. `A_USDEM004_EVENT_IDENTITY` — primary lane.
2. `B_MACRO_PROVENANCE_VERIFIER` — independent verification of A.
3. `C_SURVIVOR_AWARE_STOCK_DATA_READINESS` — future stock research data qualification.
4. `D_SEC_INSIDER_FUNDAMENTAL_READINESS` — official SEC data feasibility.
5. `E_HIGH_COST_DATA_NO_PURCHASE_SCOUT` — intraday/options/text availability only.
6. `F_MECHANISM_FALSIFICATION_SCOUT` — adversarial literature and replication evidence.
7. `G_LIGHTWEIGHT_ARCHITECTURE_GUARD` — continuous control and final closeout.

Only Workstream A may become the next formal research input lane. All other workstreams are supporting qualification or scout work and may not select a strategy.

## Global prohibitions

During the full week, do not:

- read strategy returns, NAV, CAGR, Sharpe, Validation, Holdout, or forward results;
- implement or run a strategy;
- create Atlas R2 or add cards to Atlas R1;
- write to the central database;
- purchase data, activate trials, or use credentials not already explicitly authorized;
- install Qlib, RD-Agent, FinRL, vn.py, LEAN, or a new backtest engine;
- create a new framework, registry, scheduler, service, or data abstraction;
- revive any closed A-share or US strategy lineage;
- change the frozen 2010-01-01 through 2026-06-30 research period;
- silently replace XNYS with another market calendar.

## Allowed data access by workstream

### Workstream A and B

May access public official sources and Git-external source bytes. No price data and no database access.

### Workstream C

May perform read-only schema, field-name/type, row-count, date-coverage, null-rate, duplicate-key, identifier, corporate-action-table, and listing-status checks against already available local data. It may confirm that raw or adjusted OHLCV fields exist, but it may not read, export, print, or retain per-security price values; calculate adjustment ratios, returns, ranks, signals, portfolios, or outcome metrics; or join price fields to events or fundamentals.

### Workstream D

May download public SEC bulk files into Git-external scratch storage and perform schema/coverage checks. It may not write the central database or join to returns.

### Workstream E

May inspect public vendor documentation and pricing pages. It may not create accounts, start trials, purchase data, use API keys, or download paid samples.

### Workstream F

May inspect public papers, official working papers, journals, and author datasets for contrary, limiting, post-publication, cost, and replication evidence. It may not access local prices or returns, fit models, change Atlas R1, create a strategy family, or recommend parameters.

### Workstream G

May inspect all week branches and PRs. It may not rewrite research content except to request compaction or boundary corrections.

## Mainline and PR policy

### May merge during the week

A compact, outcome-blind artifact may merge only when all of the following are true:

- one JSON or Markdown file only;
- no code, raw source files, record-level dump, database change, per-security price, volume, or dollar-volume values, or return/result content;
- exact-head CI green;
- independent read-only verification is `VALID` with zero findings;
- no more than 300 added lines;
- the artifact is a terminal decision or stable controlling summary.

### Must remain Draft

- any code-bearing PR;
- any event-row table or source manifest with more than 300 lines;
- any data-qualification implementation;
- any preregistration;
- any artifact that could authorize price access;
- any PR over the size limits below.

## Size budgets

Per workstream:

```text
committed controlling summary <= 300 lines
committed one-off code = 0 by default
if code is unavoidable, keep it Git-external
raw source bytes = Git-external
large row tables = Git-external or compact CSV, Draft only
```

Across the week, do not add more than 1,000 mainline lines excluding an exact externally reviewed merge of PR #110.

## Autonomous dependency rules

### If Workstream A returns `INPUT_QUALIFIED`

Create a compact preregistration Draft PR, but do not access prices or run results. The preregistration must freeze:

- the three event families;
- event inclusion/exclusion rules;
- `prior_session_decision_cutoff`;
- schedule-evidence precedence;
- collision handling;
- canceled and unscheduled events;
- exact historical period;
- future outcome label as retrospective secondary only.

Stop at external-review readiness.

### If Workstream A returns `INPUT_BLOCKED_NONTERMINAL`

Publish one compact terminal or parking JSON, keep the detailed investigation Git-external, and do not start a substitute macro-event lineage.

### If Workstream A returns `TERMINAL_DATA_UNAVAILABLE_WITHIN_BOUND`

Close USDEM-004 with no outcome and do not weaken the event taxonomy or historical period. Continue the supporting workstreams only.

### If both A and B disagree

A cannot be accepted or merged. Record the discrepancy and stop the main lane until the user returns.

## Daily operating rhythm

### Day 1

- merge PR #110 exact HEAD;
- dispatch all seven workstreams;
- confirm every workstream's branch, allowed sources, and stop conditions.

### Days 2–4

- A builds official event identity;
- B independently audits source availability and schedule versions;
- C and D run bounded data-readiness checks;
- E builds the no-purchase market survey;
- F builds the adversarial mechanism-falsification report;
- G reviews scope and size daily.

### Day 5

- A and B reconcile only factual source discrepancies; B must not edit A's artifact;
- C, D, E, and F freeze their results;
- G issues any required compaction findings.

### Days 6–7

- create compact final artifacts or explicit blockers;
- run independent acceptance and CI;
- leave all code-bearing or unresolved PRs Draft;
- publish one Manager closeout with links, exact SHAs, and no narrative inflation.

## Minimum completion chain

The week is not complete until Workstreams A through G each have an explicit terminal or blocked status and an exact artifact URL or an explicit `NO_ARTIFACT` reason. The Manager closeout must collect all seven receipts; an undispatched, uncollected, or unlinked workstream remains incomplete.

## Required Manager closeout

Return exactly:

```text
PR_110_MERGE_COMMIT=
USDEM004_STATUS=
USDEM004_ARTIFACT_URL=
USDEM004_PR_URL=
PROVENANCE_VERIFIER_STATUS=
SURVIVOR_AWARE_DATA_STATUS=
SEC_DATA_STATUS=
HIGH_COST_DATA_SCOUT_STATUS=
FALSIFICATION_SCOUT_STATUS=
FALSIFICATION_REPORT_URL=
ARCHITECTURE_GUARD_STATUS=
MAINLINE_NET_LINE_DELTA=
OPEN_DRAFT_PRS=
DATABASE_WRITE=false
OUTCOME_ACCESS=false
STRATEGY_IMPLEMENTATION=false
STRATEGY_CANDIDATE_AVAILABLE=false
NEXT_EXTERNAL_REVIEW_TARGET=
```

Do not report work as complete if its exact artifact, SHA, or PR is missing.
