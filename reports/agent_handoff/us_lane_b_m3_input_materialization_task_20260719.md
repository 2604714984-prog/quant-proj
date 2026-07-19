# US Lane B M3 input-materialization task

Date: 2026-07-19  
Repository: `2604714984-prog/quant-proj`  
Workstream: `US_SCHEDULED_EVENT_ATLAS_DEVELOPMENT_V1 / LANE_B / M3`  
Task type: `DATA_AND_EVIDENCE_ONLY`

## Objective

Materialize and qualify the minimum inputs required for the frozen M3 mechanism:

```text
FOMC_NEXT_SESSION_OPEN_TO_CLOSE_REACTION
```

Do not calculate any event return.

Do not modify the frozen mechanism.

## Controlling definition

Use the merged PR #97 definition exactly:

```text
research/definitions/us_scheduled_event_atlas_development_v1.json
```

M3 contract:

```text
event: scheduled FOMC decision with official public timestamp
entry: raw open of the first accepted NYSE session whose open is strictly after the event timestamp
exit: corporate-action-complete close of that same session
period: 1994-01-01 through 2009-12-31
```

## Allowed operations

```text
official public network retrieval
write a versioned local evidence bundle outside Git
read the existing central DuckDB in read-only mode
create a narrow parser and focused tests
create aggregate manifest and qualification JSON
compute hashes, counts and coverage
```

## Forbidden operations

```text
strategy or event-return calculation
Validation or Holdout access
2010-or-later event outcome analysis
canonical DuckDB write
new database schema
Provider abstraction framework
automatic multi-source fusion
strategy module or runner
Qlib or RD-Agent
Paper, broker or live path
```

## Part 1 — FOMC official event identities

### Source route

Use Federal Reserve official historical FOMC materials.

Primary route:

```text
https://www.federalreserve.gov/monetarypolicy/fomc_historical.htm
```

### Required scope

```text
1994-01-01 through 2009-12-31
scheduled FOMC decisions only
actual official public timestamp
America/New_York timezone
```

Do not infer all historical timestamps from modern practice.

### Required event fields

```text
event_id
event_type
official_date
official_timestamp_et
source_url
source_bytes_sha256
retrieved_at_utc
revision_or_reschedule_status
qualification_status
```

### Rules

```text
one stable event ID per decision
no duplicate event IDs
no missing timestamp for a qualified event
no scheduled-time default when actual time is absent
no time inferred from price movement
raw source bytes preserved outside Git
```

## Part 2 — XNYS calendar candidate

### Generator

Use one pinned version of:

```text
exchange_calendars
```

Record:

```text
package version
package source or wheel SHA-256
calendar name XNYS
generator configuration
```

### Required scope

```text
1994-01-01 through 2009-12-31
session date
open ET
close ET
early close
unscheduled closure
```

### Reconciliation

Compare the generated dates with the frozen SPY development slice.

Every difference must be classified as one of:

```text
official closure or exceptional session
SPY source omission
calendar-generator error
unresolved conflict
```

An unresolved conflict blocks M3.

Required equality after accepted exceptions:

```text
accepted_XNYS_session_dates == observed_SPY_session_dates
```

## Part 3 — SPY development slice

Read only:

```text
table: us_equity_research.us_daily_total_return_research
snapshot: tiingo_raw_20260711T142010Z_5c24877d23cfc4a0
symbol: SPY
period: 1994-01-03 through 2009-12-31
expected unique dates: 4030
```

Required fields:

```text
trade_date
raw open
raw close
adjusted open
adjusted close
split factor
cash distribution
row hash
source document hash
```

Do not change the database.

Record before/after SHA-256 and WAL absence.

## Part 4 — Joint input manifest

Create one aggregate Git artifact containing:

```text
manifest schema version
FOMC event-table hash
FOMC event count and date range
calendar hash and session count
SPY slice hash and row count
source bundle ID
parser commit and file hashes
duplicate counts
missing counts
calendar difference counts
M3 structural denominator
M3 complete-event numerator
M3 completeness fraction
minimum-gate vector
terminal decision
```

Do not commit raw event pages or large source payloads.

## M3 input gates

Pass only if:

```text
structural event count >= 24
complete event count >= 24
distinct calendar years >= 6
completeness >= 0.95
event duplicate count = 0
qualified-event missing timestamp count = 0
calendar unresolved conflict count = 0
SPY duplicate/missing/nonfinite/nonpositive count = 0
all required hashes present
central database unchanged
```

## Terminal states

Return exactly one:

```text
M3_INPUT_QUALIFIED
M3_INPUT_BLOCKED
```

### Qualified

Publish only input identities and aggregate counts.

Do not run returns.

### Blocked

Publish the narrow blocker and stop.

Do not change the event window, period, calendar or data source to obtain a pass.

## Scope budget

```text
elapsed time: maximum 5 working days
Git runtime additions: narrow parser only
new architecture: zero
```

## Verification

Required:

```text
strict JSON duplicate-key rejection
nonfinite rejection
parser golden fixtures from official source bytes
calendar holiday and early-close fixtures
SPY date-set equality test
read-only database identity test
git diff --check
Ruff
focused pytest
full repository CI
```

## Git and publication

Use one isolated branch and one Draft PR.

The PR should contain only:

```text
narrow parser, if needed
focused tests
aggregate qualification result
joint manifest
short closeout
```

Do not merge before external or Manager scope review.

## Required callback

```text
BATCH:
STATUS:
BRANCH:
HEAD:
PR_URL:
EVIDENCE_BUNDLE_ID:
FOMC_STRUCTURAL_EVENT_COUNT:
FOMC_QUALIFIED_EVENT_COUNT:
DISTINCT_EVENT_YEARS:
XNYS_SESSION_COUNT:
SPY_SESSION_COUNT:
CALENDAR_RAW_DIFFERENCE_COUNT:
CALENDAR_UNRESOLVED_CONFLICT_COUNT:
M3_COMPLETE_EVENT_COUNT:
M3_COMPLETENESS:
SPY_INPUT_FAILURE_COUNT:
DATABASE_SHA_BEFORE_AFTER:
WAL_STATUS:
MANIFEST_URL:
RESULTS_OPENED:false
STRATEGY_CANDIDATE_AVAILABLE:false
NEXT_ACTION:
```
