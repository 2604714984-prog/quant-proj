# Lightweight Architecture Guard — Week Task

Date: 2026-07-20  
Role: independent scope and maintainability auditor  
Authority: may block merges; may not expand implementation

## Mission

Protect the project's reliability-and-lightweight standard while several outcome-blind workstreams run in parallel.

The guard's objective is to prevent temporary research investigation from becoming permanent architecture.

## Core standard

This is a personal project for approximately CNY 400,000 / USD 40,000 research and eventual manual or lightly assisted execution.

It is not:

- a multi-tenant platform;
- an institutional data lake;
- a distributed event system;
- an agent orchestration product;
- a generalized research operating system.

## Daily review targets

Inspect every new branch and PR created under the week program for:

- file count;
- line count;
- runtime dependency changes;
- new modules and packages;
- duplicated source manifests;
- raw data committed to Git;
- one-off scripts proposed for mainline;
- evidence and registry framework growth;
- hidden price or outcome access;
- database write paths;
- provider credentials or cookies;
- task-scope drift.

## Automatic blocking conditions

Return `BLOCK_MERGE` if any PR introduces:

```text
new framework or registry
new database abstraction
new service or scheduler
new agent orchestration code
new backtest engine
new provider abstraction
raw official PDFs or HTML
credentials, cookies, or private headers
price or return outcomes without authorization
central database writes
more than one unrelated workstream
```

Also block when:

- a partial input investigation commits code and record mirrors without an authorized consumer;
- a compact terminal record can replace a large implementation;
- a strategy-specific task expands into a reusable platform without an existing second consumer;
- a PR changes Atlas R1 or opens Atlas R2;
- a closed lineage is revived or renamed.

## Size limits

### Outcome-blind terminal/control artifact

```text
files <= 1
added lines <= 300
code files = 0
```

### Draft input qualification package

```text
files <= 3 preferred
added lines <= 900
mainline code = 0 preferred
raw sources = Git-external
```

Anything larger requires a written exception and must remain Draft until the user returns.

## Compaction order

When a workstream is too large, reduce in this order:

1. keep exact status, scope, hashes, blockers, and reopen conditions;
2. keep one compact controlling summary;
3. keep a compact row CSV only when external review truly requires it;
4. move disposable scripts and detailed records Git-external;
5. delete duplicate manifests and narrative repetition;
6. do not replace deleted weight with a generalized framework.

## Reliability requirements

Lightweight does not mean permissive. Every controlling artifact must still include:

- exact repository and commit identity;
- source hashes or snapshot identity;
- fail-closed status;
- explicit no-outcome boundaries;
- deterministic counts;
- duplicate and nonfinite checks where relevant;
- independent verification result;
- exact reopen or next-action conditions.

## Merge authority

During the user's absence, the guard may allow a compact PR to merge only if it meets the Manager task's merge conditions.

The guard must not approve its own artifact. Use a separate independent verifier.

Code-bearing PRs remain Draft even when technically correct.

## End-of-week report

Produce one report under 250 lines containing:

```text
PR number
workstream
head SHA
files changed
added/deleted lines
runtime dependency delta
mainline architecture delta
boundary status
compaction required
merge status
findings
```

Also report:

```text
week mainline net line delta
new runtime modules
new test modules
new dependencies
raw data committed
open Draft PRs
closed-without-merge PRs
```

## Required terminal status

```text
VALID_LIGHTWEIGHT_WEEK
VALID_WITH_COMPACTION_FINDINGS
BLOCKED_OVERDESIGN
```

## Callback

```text
BATCH=LIGHTWEIGHT_ARCHITECTURE_GUARD_WEEK_20260720
STATUS=
PRS_REVIEWED=
MERGES_ALLOWED=
MERGES_BLOCKED=
COMPACTIONS_REQUIRED=
MAINLINE_NET_LINE_DELTA=
NEW_RUNTIME_MODULES=
NEW_DEPENDENCIES=
RAW_DATA_COMMITTED=
DATABASE_WRITE_PATHS_ADDED=
OUTCOME_PATHS_ADDED=
REPORT_URL=
```
