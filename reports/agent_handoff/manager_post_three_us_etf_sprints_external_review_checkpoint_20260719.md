# Manager checkpoint after three US ETF result sprints

Date: 2026-07-19
Repository: `2604714984-prog/quant-proj`
Controlling main commit: `c56db93b4df2d9b7006c03676708a9de7232ab4b`
Status: `NARROW_DOCUMENT_REWORK_AWAITING_DELTA_EXTERNAL_REVIEW`

## Purpose

The three result sprints authorized by the accepted post-PR-94 program are now
terminal. Together with PRs #93 and #94, they bring the recent formal US
retrospective outcome count to five. This checkpoint records the resulting
program-level consumption and selects the already-merged PR #97 Scheduled
Event Atlas Lane B as the only next research line. It is not a request to
retune, rerun, promote, shadow, paper trade, trade, or open another ETF
allocation strategy.

## Exact terminal evidence

| Sprint | Merged PR | Result status | Gates | Result SHA-256 | Decisive failures |
|---|---:|---|---:|---|---|
| SPY/QQQ/GLD dual momentum with cash | #96 | `RETROSPECTIVE_DUAL_MOMENTUM_FAIL` | 7/8 | `9c22a877c13e783b73a164f49569c7a3ddb9739721af7ad973bb7f4a94337f65` | Combined validation-plus-holdout Calmar did not exceed the static equal-weight comparator. |
| SPY/QQQ/GLD inverse volatility | #98 | `RETROSPECTIVE_INVERSE_VOLATILITY_FAIL` | 6/10 | `42772cd61d660e7fab1359bfeeae71d92e656d96fcdf58463b2b54a1f5cab541` | Holdout and combined Calmar, 30-bps robustness, and the four-test adjusted inference family failed. |
| SPY/GLD stress safe-haven sleeve | #100 | `RETROSPECTIVE_STRESS_SAFE_HAVEN_FAIL` | 7/10 | `92cecfef384d243797b1783532a190009c3cff1cdd692751b208569f7dca4ba4` | Holdout Calmar versus the identically timed SPY stress sleeve, 30-bps robustness/concentration, and all four adjusted inference tests failed. |

All three results were produced from committed and remotely pinned code, used
one frozen variant, passed input qualification before result consumption, and
received independent result acceptance. Their exact historical runs are
consumed and must not be reopened or repaired.

## Program-level evidence state

The recent formal US retrospective outcomes are:

| PR | Frozen mechanism | Terminal status |
|---:|---|---|
| #93 | SPY 200-session trend/cash | `RETROSPECTIVE_BASELINE_FAIL` |
| #94 | SPY classic turn-of-month | `RETROSPECTIVE_REPLICATION_FAIL` |
| #96 | SPY/QQQ/GLD dual momentum with cash | `RETROSPECTIVE_DUAL_MOMENTUM_FAIL` |
| #98 | monthly full-liquidation capped inverse volatility | `RETROSPECTIVE_INVERSE_VOLATILITY_FAIL` |
| #100 | SPY-drawdown GLD/cash stress sleeve | `RETROSPECTIVE_STRESS_SAFE_HAVEN_FAIL` |

The controlling program-level state is:

```text
RECENT_FORMAL_US_OUTCOME_COUNT=5
US_VALIDATION_2010_2017=PROGRAM_LEVEL_CONSUMED
US_RETROSPECTIVE_HOLDOUT_2018_2026_06=PROGRAM_LEVEL_CONSUMED
FUTURE_SAME_PERIOD_PASS_CLASSIFICATION=RETROSPECTIVE_SECONDARY_ONLY
FUTURE_SAME_PERIOD_PASS_CAN_CREATE_CANDIDATE=false
```

The current PR disposition is:

```text
MERGE_CURRENT_HEAD=false
KEEP_DRAFT=true
CURRENT_RESULTS_INVALIDATED=false
RERUN_OR_RETUNE=false
```

The five runs may each remain valid evidence about their exact frozen
mechanism. Repeatedly selecting a new mechanism after observing earlier
validation and retrospective-holdout results nevertheless consumes those
periods at the research-program level. A later result on the same periods is
not an independent holdout and cannot by itself authorize candidate, shadow,
paper, live, automatic, or funded use. This requires no new registry or
management framework. Within-strategy Holm adjustment does not correct this
cross-sprint mechanism selection.

## What the third result actually showed

The safe-haven sleeve was not an input failure. It used 5,436 exact common
SPY/GLD sessions through 2026-06-30 and passed the sample, identity, positive
CAGR, drawdown and positive-active-interval gates.

At 15 bps one way, its GLD/cash sleeve reported:

- validation CAGR `0.3392%`;
- retrospective-holdout CAGR `1.8131%`;
- combined CAGR `1.0952%` and cumulative net return `19.6656%`;
- combined positive active-interval fraction `54.8673%`.

Those positive numbers are insufficient for acceptance. In the holdout, the
GLD sleeve Calmar was `0.09284`, below the identically timed SPY stress sleeve
at `0.12671`. At 30 bps, GLD-sleeve combined maximum drawdown was `-28.08%`
versus `-22.61%` for the SPY stress sleeve, and its largest positive-year
contribution was `51.37%`, above the frozen `40%` ceiling. All four Holm-family
tests had negative simultaneous lower bounds.

## Program-level conclusion

The lightweight engine is producing reproducible numerical decisions. The
current bottleneck is not another architecture rewrite. The three tested ETF
mechanisms did not meet their own frozen comparison and inference standards.

Therefore:

- `strategy_candidate_available=false`;
- no exact mechanism or parameter from these three sprints may be rerun;
- rejected legacy `US31`, `US36`, `US41` and `US46` remain closed;
- no prospective-forward, shadow, paper, broker, live, or automatic path is
  authorized;
- infrastructure improvements may support a genuinely new lineage but cannot
  rescue these results.

Gate counts are reported only to replay each mechanism's frozen contract. They
are not comparable measures of distance to acceptance because the contracts
and inference families differ:

```text
GATE_COUNTS_ARE_MECHANISM_SPECIFIC=true
GATE_COUNTS_MUST_NOT_BE_RANKED=true
TERMINAL_STATUS_IS_BINARY=true
```

Future formal mechanisms share only a minimum decision layer: qualified input
and timing, positive primary-cost net return, explicit comparator advantage,
stress-cost survival, non-concentrated returns, multiplicity control for the
current formal family, and zero execution or identity failures. A mechanism may
add economically necessary gates, but its pass count is never ranked against a
different mechanism.

Static initial equal-weight SPY/QQQ/GLD remains a useful benchmark, but it has
been repeatedly observed and was not independently preregistered as a
strategy. `STATIC_EQUAL_WEIGHT_CANDIDATE=false`.

## Interpretation boundaries carried forward

The three closed ETF results are classified as
`WHOLE_SHARE_EXECUTION + PROVIDER_ADJUSTED_TOTAL_RETURN_MARKING_PROXY`. They did
not implement a full
broker-style ledger for distribution pay dates, dividend cash, reinvestment,
and split-driven share changes. This does not invalidate or reopen their
frozen results, but it limits their interpretation.

For the Scheduled Event Atlas Lane B:

- M3 is a same-session raw open-to-raw close return and does not require a
  cross-close adjusted-price proxy.
- M4 through M7 must either use explicit split and cash-distribution accounting
  or be labelled `PROVIDER_ADJUSTED_TOTAL_RETURN_PROXY`, not true whole-share
  cash accounting. Explicit accounting requires dividend-only and 2:1 split
  regression tests.
- Every formal calculation must bind an accepted XNYS session set and require
  exact observed-date equality, or an independently accepted exception for
  every difference. Tests must cover an all-symbol missing session, an added
  non-session date, an early close, and an official-exception conflict.

```text
observed_session_dates == accepted_XNYS_session_dates
```

- Each event's inferential unit must be its complete net round trip:
  `post_exit_cash / pre_entry_cash - 1`, including entry cost, price movement,
  accepted corporate actions, and exit cost.

The safe-haven inference used unconditional account daily returns even though
its economic question concerned conditional stress performance, and its active
interval attribution did not charge every event the complete round-trip cost.
The result therefore does not establish that gold has no conditional safe-haven
effect; it rejects only its exact account-level frozen question.
Likewise, inverse volatility rejects only the frozen
contract:

```text
MONTHLY_FULL_LIQUIDATION_AND_REBUILD
CAPPED_60_SESSION_INVERSE_VOLATILITY
= FAIL
```

This does not reject every inverse-volatility implementation. A net-rebalance
rerun would nevertheless be an outcome-informed rescue and is not authorized
in that consumed lineage.

## Next active phase

PR #97 is already merged at merge commit
`b797a7d571a77cc76521b731a539e0d0a1d492c0` and supplies the selected
outcome-blind feasibility route. Do not create another shortlist or a fourth
SPY/QQQ/GLD allocation sprint:

```text
NEXT_ACTIVE_RESEARCH_LINEAGE=US_SCHEDULED_EVENT_ATLAS_DEVELOPMENT_V1
NEXT_ACTIVE_ROUTE=US_SCHEDULED_EVENT_ATLAS_LANE_B
NEXT_TASK=LANE_B_INPUT_MATERIALIZATION
NEW_SHORTLIST_REQUIRED=false
FOURTH_ALLOCATION_STRATEGY_REQUIRED=false
```

The next task is data and evidence only. It must materialize, for 1994-2009:

- the accepted XNYS calendar including open, close, early-close and official
  exception identity;
- actual FOMC, CPI and Employment Situation release identities;
- mutually exclusive standard monthly and quarterly expiration identities;
- the frozen SPY daily snapshot identity; and
- one joint immutable input manifest.

Each M3 through M7 mechanism is qualified independently against the already
frozen minimum of 24 complete events, six calendar years and 95% completeness.
The structural denominator is frozen before price endpoint checks. M4 and M5
remain non-promotable negative controls. One blocked mechanism does not block a
different qualified mechanism.

Raw official-source bytes belong in the versioned evidence bundle. Git contains
only a narrow parser, focused tests, manifests, hashes and aggregate
qualification. This phase may not write canonical DuckDB, build a data
platform, calculate returns, read 2010-or-later outcomes, or access validation
or retrospective holdout.

This documentation-only checkpoint does not authorize provider/network access,
evidence-bundle mutation, or canonical database writes; each requires a
separate bounded task authorization.

Only after at least one Lane B mechanism independently qualifies may one
one-use development-only result run cover `1994-01-01..2009-12-31`. M1, M2 and
M8 remain p-value 1.0 when independently closed as input-blocked under the
frozen eight-test family. M4 and M5 can never be promoted. Any development
pass stops at exact-head external review; it is not a strategy candidate.

Lane A and Lane C may receive only a bounded data-availability decision, with a
combined phase budget cap of USD 400. If exact historical minute coverage and
identities are unavailable within that limit, they close as
`TERMINAL_DATA_UNAVAILABLE_WITHIN_BUDGET_NO_OUTCOME`; daily proxies are
forbidden.

```text
PHASE_DATA_BUDGET_CAP_USD=400
```

Do not build a data platform, agent framework, regime router, or broker path as
part of this decision.

## Controlling next-state summary

```text
PRIMARY_MARKET=US
ACCOUNT_CAPITAL_USD=40000
RECENT_FORMAL_US_RETROSPECTIVE_OUTCOMES=5
VALIDATED_STRATEGIES=0
STRATEGY_CANDIDATE_AVAILABLE=false

US_VALIDATION_2010_2017=PROGRAM_LEVEL_CONSUMED
US_HOLDOUT_2018_2026_06=PROGRAM_LEVEL_CONSUMED
FUTURE_SAME_PERIOD_PASS_CLASSIFICATION=RETROSPECTIVE_SECONDARY_ONLY
FUTURE_SAME_PERIOD_PASS_CAN_CREATE_CANDIDATE=false

ACTIVE_STRATEGY_FAMILY=NONE
ACTIVE_RESEARCH_LINEAGE=US_SCHEDULED_EVENT_ATLAS_DEVELOPMENT_V1
ACTIVE_STAGE=LANE_B_INPUT_MATERIALIZATION
NEXT_NUMERIC_RESULT=LANE_B_DEVELOPMENT_ONLY_ATLAS

NEW_SHORTLIST_REQUIRED=false
FOURTH_ETF_ALLOCATION_SPRINT=false
ARCHITECTURE_REWRITE=false
DATABASE_WRITE=false
SHADOW=false
PAPER=false
LIVE=false
```

## Questions for external review

1. Does this revision correctly record all five recent formal US outcomes and
   the program-level consumption of 2010-2017 and 2018-2026-06?
2. Are gate-count non-ranking, adjusted-return-proxy, accepted-calendar and
   complete-event-return boundaries sufficiently explicit without reopening
   any terminal result?
3. Is already-merged PR #97 Lane B now the unambiguous sole active research
   line, with no new shortlist or fourth ETF allocation strategy?
4. After this exact-head delta is accepted and merged, may the Manager proceed
   only with the outcome-free Lane B input-materialization task described
   above?

## Validation and boundaries

- PR #100 exact-head CI: green, run `29689742353`.
- Local exact committed-code suite: `821 passed`.
- Safe-haven result and receipt independent acceptance: `VALID`.
- Central database SHA-256 before/after:
  `e636bb80e300f89e46831e91275c6f2167e370e81a00b21b300e253f6107bee0`.
- Database write: false; provider/network use: false; prospective-forward
  access: false; candidate promotion: false; trading activation: false.
- `strategy_candidate_available=false`; no new result or event outcome was
  opened by this documentation-only revision.

External review should bind its verdict to the exact PR HEAD containing this
file. Any later commit requires a fresh incremental review.
