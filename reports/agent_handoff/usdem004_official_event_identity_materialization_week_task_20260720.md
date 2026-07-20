# USDEM-004 Official Event Identity Materialization — Week Task

Date: 2026-07-20  
Mechanism: `USDEM-004`  
Stage: outcome-blind official event identity  
Target period: `2010-01-01` through `2026-06-30`

## Goal

Build one deterministic, source-bound event identity table for the narrowed macroeconomic announcement-premium mechanism without reading prices, returns, NAV, Validation, Holdout, or the central database.

## Frozen event families

Only these families are allowed:

```text
SCHEDULED_FOMC_DECISION
BLS_EMPLOYMENT_SITUATION
BLS_PRODUCER_PRICE_INDEX
```

Do not add CPI, PCE, advance GDP, ISM, unscheduled FOMC actions, minutes, speeches, press conferences as separate events, or any data-surprise sign.

## Frozen event-day contract

```text
event_window=prior accepted XNYS session close to announcement-day close
nontrading_release=exclude without shifting
same_day_collision=one event day with sorted unique event families
scheduled_fomc_only=true
use_actual_values=false
use_forecasts=false
use_surprise_sign=false
use_revision_values=false
```

## Frozen decision cutoff

Use:

```text
prior_session_decision_cutoff=15:30:00 America/New_York
```

If an already merged project contract requires an earlier cutoff, use the earlier cutoff and cite its path and SHA. Never use a later cutoff.

A revised schedule is causally usable only when its publication timestamp is at or before the cutoff on the prior accepted XNYS session.

## Schedule-evidence precedence

For each event, choose the applicable schedule version mechanically:

1. official cancellation or reschedule notice published by the cutoff;
2. official previous-release footer published by the cutoff;
3. dated official annual or meeting schedule published by the cutoff;
4. original schedule when no later qualifying change exists.

The actual release page verifies actual publication but does not establish prior schedule knowledge unless it independently contains a qualifying earlier publication timestamp.

## Required row schema

Each accepted, excluded, canceled, or blocked event row must contain:

```text
event_id
event_family
reference_period_or_meeting_id
original_schedule_published_at
original_scheduled_release_at
applicable_schedule_version_published_at
applicable_scheduled_release_at
actual_release_at
timezone
status
cancellation_published_at
source_url
source_sha256
retrieved_at
original_or_revision
rescheduled_or_cancelled
accepted_XNYS_session
prior_accepted_XNYS_session
collision_group_id
qualification_status
exclusion_reason
```

Use UTC timestamps plus an explicit `America/New_York` display field. Do not store naive timestamps.

## FOMC rules

Include only scheduled policy-decision dates from the published meeting schedule.

Must reconcile:

- changes from one-day to two-day meetings;
- date changes;
- canceled or added scheduled meetings;
- unscheduled emergency actions;
- notation votes;
- release-time regime changes;
- meetings whose statement was released on the final meeting day.

Unscheduled actions and notation votes are recorded as excluded evidence, not event rows in this mechanism.

Primary routes:

- https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- annual historical pages such as `fomchistorical2010.htm`;
- dated schedule press releases;
- dated change or cancellation notices.

## BLS rules

For Employment Situation and PPI:

- use official release archives and annual schedules;
- use the immediately prior release footer when it gives the next release date and time;
- record cancellations explicitly;
- record delayed releases under their revised dates only when the revision was officially published by the decision cutoff;
- never treat a later mutable schedule page as proof of prior availability without a dated notice or archived official version;
- keep the 2025 lapse rows blocked when prior knowledge cannot be proven.

Primary routes:

- https://www.bls.gov/bls/news-release/empsit.htm
- https://www.bls.gov/bls/news-release/ppi.htm
- https://www.bls.gov/schedule/
- https://www.bls.gov/bls/2025-lapse-revised-release-dates.htm
- historical release footers and dated closure notices.

## Collision rules

When two or three allowed families fall on the same accepted XNYS session:

- create one `collision_group_id`;
- retain all family labels in sorted order;
- count one event day for later research;
- do not choose a dominant family;
- do not inspect any return to resolve collisions.

## XNYS mapping

Do not borrow the parked USDEM-006 calendar as a completed calendar.

Use an event-local session mapping:

- map only the dates needed by the three event families;
- use a pinned candidate XNYS calendar library only as a generator;
- verify every event date, prior session, ad-hoc closure, and early close that affects an event against official exchange or regulatory evidence;
- unresolved rows remain blocked rather than forcing a full-market calendar platform.

## Source storage

Raw source bytes and detailed retrieval logs remain Git-external in an immutable directory.

Record:

```text
source_url
retrieval_timestamp
content_sha256
byte_count
content_type
HTTP status
redirect count
```

Do not commit credentials, cookies, full headers, raw PDFs, or raw HTML.

## Deliverables

Preferred compact package:

1. `usdem004_event_identity_summary_v1.json` — controlling summary, under 300 lines.
2. `usdem004_event_identity_rows_v1.csv` — one line per event, Draft PR only if needed for review.
3. `usdem004_source_manifest_v1.json` — compact source manifest, Draft only.
4. one independent acceptance result from the separate verifier.

Large source material and disposable scripts stay outside Git.

## Allowed terminal statuses

```text
INPUT_QUALIFIED
INPUT_BLOCKED_NONTERMINAL
TERMINAL_DATA_UNAVAILABLE_WITHIN_BOUND
```

`INPUT_QUALIFIED` requires:

- all years complete;
- all three families complete under the frozen taxonomy;
- every accepted event causally scheduled before the cutoff;
- all cancellations and reschedules reconciled;
- all event-local XNYS mappings resolved;
- zero duplicate event IDs;
- zero nonfinite or naive timestamps;
- source manifest hashes verified;
- independent verifier returns `VALID` with zero findings.

## Time box

Maximum active effort: five working days.

If the 2025 BLS prior-availability chain or any other year cannot be resolved within the bound, return `INPUT_BLOCKED_NONTERMINAL`. Do not extend the search indefinitely.

## Prohibitions

Do not:

- read or join prices;
- compute event returns;
- create strategy code;
- create a generalized event framework;
- write the central database;
- add event families;
- use Internet Archive or third-party calendars as controlling evidence without separately labeling them non-qualifying;
- change the research period;
- silently drop difficult years or events.

## Callback

```text
BATCH=USDEM004_OFFICIAL_EVENT_IDENTITY_WEEK_20260720
STATUS=
EVENT_ROWS_TOTAL=
ACCEPTED_ROWS=
BLOCKED_ROWS=
CANCELED_ROWS=
COLLISION_DAYS=
COMPLETE_YEARS=
FOMC_STATUS=
EMPLOYMENT_STATUS=
PPI_STATUS=
BLS_2025_LAPSE_STATUS=
XNYS_MAPPING_STATUS=
SOURCE_MANIFEST_SHA256=
EVENT_TABLE_SHA256=
SUMMARY_URL=
DRAFT_PR_URL=
INDEPENDENT_VERIFIER_STATUS=
PRICE_ACCESS=false
OUTCOME_ACCESS=false
DATABASE_WRITE=false
STRATEGY_CANDIDATE_AVAILABLE=false
NEXT_ACTION=
```
