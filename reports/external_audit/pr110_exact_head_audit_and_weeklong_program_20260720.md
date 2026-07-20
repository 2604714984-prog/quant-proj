# PR #110 Exact-Head External Audit and Weeklong Program

Date: 2026-07-20  
Repository: `2604714984-prog/quant-proj`  
Reviewed PR: `#110`  
Reviewed HEAD: `783059c6e4176af87de7de3f8f80c29e05083031`  
Reviewed tree: `6fef10f2f0a723265d1de814ce4bb7bf039be962`  
GitHub review ID: `4736557018`

## Verdict

```text
VERDICT=ACCEPT_COMPACT_METHOD_SOURCE_TAXONOMY_CORRECTION
MERGE_DECISION=MERGE_EXACT_HEAD_ONLY
CURRENT_STATUS=INPUT_BLOCKED_NONTERMINAL
QUALIFIED_EVENT_ROWS=0
COMPLETE_YEARS=0
INPUT_QUALIFIED=false
STRATEGY_CANDIDATE_AVAILABLE=false
```

PR #110 may merge only while its exact HEAD remains `783059c6e4176af87de7de3f8f80c29e05083031`. Any added commit invalidates this review.

## Accepted methodology correction

The previous six-event Atlas union was too broad. For the 2010-01-01 through 2026-06-30 replication period, the exact baseline mechanism is narrowed to:

1. scheduled FOMC policy decisions;
2. BLS Employment Situation releases;
3. BLS Producer Price Index releases.

The following remain outside this lineage:

- CPI;
- PCE;
- advance GDP;
- ISM Manufacturing;
- unscheduled FOMC actions.

Savor and Wilson define announcement days using CPI before January 1971, PPI after January 1971, employment numbers, and FOMC interest-rate decisions. Wachter and Zhu extend the announcement-day evidence by following that lineage for post-2010 FOMC, inflation, and employment dates. The narrowed three-family taxonomy is therefore the defensible exact translation for the present period.

Primary sources:

- https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2014/04/0906.pdf
- https://www.nber.org/papers/w24432

## Accepted outcome-blind contract

The current artifact correctly freezes:

```text
event_window=prior accepted XNYS session close to announcement-day close
return_concept=unconditional daily market excess return
same_day_collision=one event day with sorted unique event families
nontrading_release=exclude without shifting
use_actual_values=false
use_forecasts=false
use_surprise_sign=false
use_revision_values=false
scheduled_fomc_only=true
```

No event table is claimed complete. No event row may be joined to prices under PR #110.

The literature estimand is not yet an executable SPY whole-share ledger. Any tradable proxy requires a separate frozen definition after event identity qualification.

## Accepted blockers

The following are real unresolved blockers rather than strategy failures:

- the complete 2010-2026H1 official event table has not been built;
- BLS annual schedules are mutable and do not alone prove first availability of revised dates;
- the 2025 lapse requires an official, dated schedule-version chain for delayed and canceled releases;
- scheduled FOMC changes, cancellations, emergency actions, and notation votes are not fully reconciled;
- no accepted event-to-XNYS-session mapping exists.

The BLS revised-date page proves final revised and canceled dates, but its later state does not automatically prove that each revised date was public before the prior-session trading decision cutoff.

Official routes:

- https://www.bls.gov/bls/2025-lapse-revised-release-dates.htm
- https://www.bls.gov/bls/news-release-dates-to-change-for-government-closure.htm
- https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm

## Required controls for the next artifact

Before any event row is accepted, the next artifact must freeze:

```text
prior_session_decision_cutoff=15:30:00 America/New_York
```

If the repository already contains a stricter pre-close cutoff, use the stricter existing cutoff and record the controlling file and SHA.

Schedule-evidence precedence must be deterministic:

1. dated official cancellation or reschedule notice published by the cutoff;
2. dated official prior-release footer published by the cutoff;
3. dated official annual or meeting schedule published by the cutoff;
4. original schedule only when no later qualifying change exists.

An actual release page may verify the actual release time, but it cannot by itself prove that a revised schedule was known before the trading cutoff.

The event table must also preserve two separate states:

```text
source_replication_event
ex_ante_trade_event
```

- `source_replication_event` records whether an actual qualifying announcement occurred.
- `ex_ante_trade_event` records whether the then-applicable date was public by the prior-session cutoff.

A revised date lacking prior-cutoff proof must be excluded from the ex-ante lane even when it remains a valid actual announcement for source replication. A cancellation or reschedule published after the prior close must not be used with hindsight to erase the ex-ante schedule state that existed at the cutoff.

## Weeklong operating model

The user will be unavailable for one week. Work may continue under a wide-search, narrow-authority model:

```text
parallel outcome-blind qualification workstreams=allowed
formal strategy implementations=0
price or return outcome lanes=0
new Atlas versions=0
central database writes=0
provider purchases=0
active code-bearing strategy families=0
```

The week should produce concrete data and source qualification artifacts, not new planning frameworks.

## Merge policy during the week

Manager may merge without fresh user confirmation only:

1. PR #110 at the reviewed exact HEAD;
2. a compact outcome-blind terminal or input-qualification artifact that contains no strategy code, no price/return result, no database write, no provider purchase, and no more than one small JSON or Markdown file;
3. only after exact-head CI is green and an independent read-only verifier returns `VALID` with zero findings.

All code-bearing, row-level data, preregistration, result, database, or architecture PRs must remain Draft until the user returns.

## Mainline size guard

Across the whole week:

```text
new frameworks=0
new registries=0
new runner frameworks=0
new database abstractions=0
new agent orchestration code=0
```

Raw source bytes, large row-level extracts, temporary scripts, and investigation logs remain Git-external. Mainline receives only compact controlling artifacts.

## End-of-week minimum deliverables

1. PR #110 merged at exact HEAD.
2. One deterministic USDEM-004 event-identity qualification package or a compact terminal blocker.
3. One independent provenance verification report.
4. One survivor-aware US stock data-readiness result.
5. One SEC insider/fundamental data-readiness result.
6. One high-cost-data no-purchase market survey.
7. One adversarial mechanism-falsification report.
8. One architecture-guard closeout covering every PR created during the week.

No historical strategy PASS/FAIL is required or authorized during this absence period.
