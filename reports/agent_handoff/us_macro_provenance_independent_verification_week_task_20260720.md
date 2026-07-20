# Independent US Macro Provenance Verification — Week Task

Date: 2026-07-20  
Role: independent read-only verifier  
Target: USDEM-004 official event identity workstream

## Independence rule

You must not implement, edit, or repair the primary event-identity artifact. Work from a separate checkout and produce an independent finding set.

Do not accept claims solely because the primary builder reports `VALID`.

## Scope

Verify only:

- mechanism taxonomy;
- source provenance;
- schedule-version causality;
- separate replication and ex-ante event states;
- event classification;
- XNYS event-local mapping;
- hashes and deterministic counts;
- absence of prohibited outcome access.

Do not inspect prices or returns.

## Source taxonomy verification

Confirm that the event table contains only:

```text
SCHEDULED_FOMC_DECISION
BLS_EMPLOYMENT_SITUATION
BLS_PRODUCER_PRICE_INDEX
```

Confirm that CPI, PCE, advance GDP, ISM, unscheduled FOMC actions, speeches, minutes, and press conferences are not silently included.

Primary methodology sources:

- https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2014/04/0906.pdf
- https://www.nber.org/papers/w24432

## Two-state event verification

Every candidate must preserve both:

```text
source_replication_event
ex_ante_trade_event
```

Verify that:

- `source_replication_event` reflects whether an actual qualifying announcement occurred;
- `ex_ante_trade_event` reflects the schedule state public by the prior-session cutoff;
- a late revised date is not backfilled into the ex-ante state;
- a cancellation or reschedule published after the prior close does not erase the ex-ante trade state that existed at the cutoff;
- the two event sets are counted separately;
- the table never uses a single hindsight-cleaned event list for both purposes.

Required exception classifications include:

```text
REPLICATION_ONLY_NOT_KNOWN_BY_CUTOFF
EX_ANTE_ONLY_CANCELED_OR_RESCHEDULED_AFTER_CUTOFF
CANCELED_KNOWN_BEFORE_CUTOFF
EXCLUDE_NONTRADING_RELEASE
EXCLUDE_UNSCHEDULED_FOMC
BLOCKED_SOURCE_AVAILABILITY
```

## Causal schedule verification

Freeze the same cutoff as the builder:

```text
15:30:00 America/New_York on the prior accepted XNYS session
```

For every exception row and a deterministic sample of ordinary rows, verify:

- original schedule publication predates the cutoff;
- any applicable revision predates the cutoff before it changes the ex-ante state;
- a later actual-release page is not used to backfill prior knowledge;
- cancellations remain explicit in both event states;
- delayed releases are not shifted using hindsight;
- nontrading releases are excluded rather than moved.

## Mandatory row review

Review 100% of:

- all 2025 and 2026 lapse-affected BLS rows;
- every canceled release;
- every rescheduled release;
- every replication-only row;
- every ex-ante-only row;
- every same-day collision in either event state;
- every nontrading-date exclusion;
- every FOMC schedule change;
- every row affected by an ad-hoc market closure or early close;
- every blocked row.

Review a deterministic ordinary-row sample:

```text
minimum 10 rows per family
minimum one row per year per family when available
sample selection = SHA256(event_id) lexicographic first N
```

## BLS 2025 lapse test

The current revised-date page proves final dates but may not prove when those dates became known.

For each delayed Employment Situation or PPI release, require one of:

- a dated official notice published before the cutoff;
- a previous official release footer published before the cutoff;
- a preserved official schedule version with a provable publication timestamp before the cutoff.

If none exists:

- actual release identity may still qualify the replication state;
- the revised date must not qualify the ex-ante state;
- classify it deterministically rather than leaving an ambiguous row.

## FOMC test

Check:

- tentative schedules versus final meeting dates;
- changes from one-day to two-day meetings;
- added or canceled scheduled meetings;
- unscheduled emergency actions and notation votes remain excluded;
- the decision date equals the statement-release date for the scheduled meeting;
- no modern release time is backfilled into earlier years;
- any late schedule change preserves the schedule state that existed at the prior cutoff.

## XNYS mapping test

For each reviewed event:

- event day must be an accepted XNYS session for the relevant event state;
- prior session must be unique;
- early close must not alter the event definition unless explicitly frozen;
- ad-hoc closures must shift the prior-session mapping only when officially proven;
- the parked USDEM-006 full-calendar lane must not be cited as complete.

## Hash and scope checks

Recompute:

- event-row file SHA256;
- source-manifest SHA256;
- summary component hashes;
- row counts by family, year, status, event state, and collision group;
- duplicate event IDs;
- naive timestamps;
- nonfinite values;
- unexpected files in the PR.

Reconcile these counts independently:

```text
source_replication_event count
ex_ante_trade_event count
both-state count
replication-only count
ex-ante-only count
canceled-before-cutoff count
canceled-after-cutoff count
blocked count
```

## Boundary audit

Search committed artifacts and logs for forbidden content:

```text
CAGR
Sharpe
NAV
strategy_return
portfolio_value
buy
sell
position
price_join
API key
cookie
credential
```

Contextual words in a prohibition list are allowed only when clearly marked as forbidden. Any actual outcome or credential content is a blocking finding.

## Deliverable

One compact verifier artifact:

```text
USDEM004_PROVENANCE_VERIFICATION_VALID
USDEM004_PROVENANCE_VERIFICATION_FINDINGS
```

Include:

- exact primary artifact SHA;
- exact source manifest SHA;
- reviewed row counts;
- deterministic sample IDs;
- both event-state count reconciliation;
- all findings with severity;
- final `VALID` or `INVALID` decision.

Do not merge the verifier's detailed row notes into mainline. Keep them Git-external or in a Draft review comment.

## Stop rules

Return `INVALID` immediately for:

- any return or price access;
- any event family outside the frozen three;
- any revision accepted ex ante without prior availability evidence;
- any late cancellation used to erase an ex-ante state;
- any unresolved collision counted twice within one event-state lane;
- any hidden period shortening;
- any database write;
- any mismatch between committed and recomputed hashes.

## Callback

```text
BATCH=USDEM004_PROVENANCE_VERIFIER_WEEK_20260720
STATUS=VALID|INVALID
PRIMARY_HEAD=
EVENT_TABLE_SHA256=
SOURCE_MANIFEST_SHA256=
TOTAL_ROWS_REVIEWED=
SOURCE_REPLICATION_EVENT_COUNT=
EX_ANTE_TRADE_EVENT_COUNT=
BOTH_STATE_COUNT=
REPLICATION_ONLY_COUNT=
EX_ANTE_ONLY_COUNT=
EXCEPTION_ROWS_REVIEWED=
ORDINARY_ROWS_SAMPLED=
BLS_2025_ROWS_REVIEWED=
FOMC_CHANGE_ROWS_REVIEWED=
XNYS_MAPPING_FINDINGS=
BOUNDARY_FINDINGS=
FINDING_COUNT=
REPORT_URL=
PRICE_ACCESS=false
OUTCOME_ACCESS=false
DATABASE_WRITE=false
```
