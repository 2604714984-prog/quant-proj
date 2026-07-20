# Task: resolve Lane B daily-event identities without opening outcomes

Task ID: `US_LANE_B_DAILY_IDENTITY_RESOLUTION_20260720`  
Repository: `2604714984-prog/quant-proj`  
Mode: outcome-blind, official-source identity only

## 1. Objective

Resolve which daily Lane B mechanisms can be made executable without expanding the project or weakening evidence standards.

This task does not authorize a strategy result.

## 2. Frozen evidence

Treat these as immutable memory:

```text
PR #97: frozen Scheduled Event Atlas definition
PR #104: nonterminal official-route qualification
PR #105 HEAD 85e2f1e...: accepted R3 materialization evidence, closed without merge
```

Do not modify or rerun R3.

## 3. Workstream A: final exact-time M3 decision

Use the already materialized 98 Statement, 98 minutes and 98 transcript objects plus directly linked official Federal Reserve records.

Time limit:

```text
2 working days
```

Allowed new access:

- official Federal Reserve domains only;
- record-level pages directly linked from the accepted historical-year pages;
- no price or return data.

Accept an actual timestamp only when the official record clearly identifies first public availability or actual release time. Do not accept:

- planned release time;
- customary release time;
- same-day page last-update time;
- modern schedule backfill;
- inferred time from market movement;
- third-party timestamp without official corroboration.

Terminal rule:

```text
accepted actual timestamps >= 94:
  EXACT_TIME_M3_IDENTITY_FEASIBLE

accepted actual timestamps < 94:
  TERMINAL_DATA_UNAVAILABLE_WITHIN_BOUND_NO_OUTCOME
```

Do not change the 94-record threshold.

## 4. Workstream B: date-anchored daily mechanism alternatives

Create outcome-blind mechanism cards only. Do not preregister code or calculate returns.

Evaluate these new identities:

### B1. `M3_DATE_ANCHORED_NEXT_SESSION_V2`

```text
event identity:
  official Statement release date

entry:
  next accepted NYSE session open after the official release date

exit:
  same session close
```

This is a new mechanism. It must not inherit the frozen exact-time M3 result state.

### B2. `M4_CPI_DATE_CONTROL_V2`

```text
event identity:
  official actual CPI release date

window:
  second prior accepted session close
  to immediately prior accepted session close

promotion:
  never; negative control only
```

### B3. `M5_NFP_DATE_CONTROL_V2`

Same identity and control rules as B2, using Employment Situation releases.

### B4. `M6_MONTHLY_EXPIRATION_RULESPAN_V2`

Identity may be based on:

- authoritative effective rule span;
- ordinary monthly expiration rule;
- explicit holiday shifts;
- explicit historical exceptions;
- accepted XNYS session identity.

Do not require one separate official page for every ordinary event if one authoritative rule was continuously effective.

### B5. `M7_QUARTERLY_EXPIRATION_RULESPAN_V2`

Same structure as B4, with complete options and equity-index-futures rule identities.

## 5. Workstream C: calendar contract

Create one narrow outcome-blind recommendation for a daily Lane B calendar.

Required:

```text
pinned calendar generator and version
4030 session-date parity with the frozen SPY slice
official evidence for seven ad-hoc full closures
explicit resolution of every observed-date difference
immutable calendar rows hash
```

For daily-bar mechanisms, early-close clock times may remain diagnostics unless exact time changes the mechanism endpoint. Do not apply this relaxation to Lane A or Lane C intraday work.

## 6. BLS source-resolution method

The official BLS archives expose dated historical releases back to 1994. A local HTTP 403 is a transport result, not terminal unavailability.

Allowed routes:

- official CPI archive and direct TXT/PDF objects;
- official Employment Situation archive and direct TXT/PDF objects;
- official historical release-date documentation;
- no unofficial replacement source as controlling identity.

For each release preserve:

```text
release_id
reference_period
official_actual_release_date
official_actual_release_time when present
source_url
retrieved_at_utc
source_bytes_sha256
revision or reissue relationship
qualification_status
```

For date-anchored controls, actual date is controlling; time remains diagnostic.

## 7. M6/M7 rule-resolution method

Build a compact rule-span table:

```text
rule_id
mechanism
product class
effective_start
effective_end
ordinary expiration formula
holiday-shift formula
source_url
source_bytes_sha256
qualification_status
```

Build a separate exception table only for dates that differ from the ordinary rule.

Do not commit 192 repeated copies of the same rule identity.

## 8. Deliverables

Return exactly:

1. one compact joint decision JSON;
2. one parser or reconciliation script only if required;
3. focused tests;
4. external raw bytes outside Git;
5. one immutable raw manifest outside Git;
6. a Git manifest containing hashes and aggregate counts.

Target Git scope:

```text
<= 6 files
<= 1500 added lines
```

If the target cannot be met, stop and request approval before expanding.

## 9. Decision outputs

For each mechanism return exactly one:

```text
IDENTITY_FEASIBLE_PENDING_PREREGISTRATION
PARK_SOURCE_INCOMPLETE
TERMINAL_DATA_UNAVAILABLE_WITHIN_BOUND_NO_OUTCOME
```

No PASS/FAIL strategy language is allowed.

## 10. Prohibited actions

```text
price query
return query
Development result
Validation or Holdout access
canonical DuckDB write
new data platform
provider abstraction
Qlib or RD-Agent
strategy code
candidate or trading promotion
```

## 11. Callback

```text
TASK_ID
BRANCH
COMMIT
M3_EXACT_TIME_STATUS
M3_DATE_V2_STATUS
M4_DATE_V2_STATUS
M5_DATE_V2_STATUS
M6_RULESPAN_V2_STATUS
M7_RULESPAN_V2_STATUS
CALENDAR_STATUS
RAW_MANIFEST_SHA256
GIT_FILE_COUNT
GIT_LINE_DELTA
PRICE_RETURN_ACCESS=false
DATABASE_WRITE=false
WORKTREE_STATUS
```
