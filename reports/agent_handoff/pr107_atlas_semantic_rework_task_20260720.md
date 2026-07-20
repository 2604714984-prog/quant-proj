# Task — PR #107 narrow semantic rework

Date: 2026-07-20  
Repository: `2604714984-prog/quant-proj`  
PR: `#107`  
Reviewed HEAD: `9f9f0b443260f5d9509971099e73e6d88d272890`  
Review ID: `4732598307`

## Objective

Correct the mechanism taxonomy, source classification and scoring contract without opening any outcome or creating implementation code.

## Allowed files

Modify only:

```text
reports/validation/us_lane_b_daily_identity_resolution_r1.json
reports/validation/us_official_data_mechanism_discovery_atlas_r1.json
```

Do not add a third file to PR #107.

## H1 — restore distinct FOMC economics

The current deduplication incorrectly collapses:

```text
pre-FOMC announcement drift
immediate/post-announcement reaction
next-session open-to-close response
```

These are separate causal and timing hypotheses.

Required correction:

- restore `USIOT-001` and `USIOT-002` as separate retained records, or preserve them as separately identified `PARK` / `TERMINAL_DATA_UNAVAILABLE` cards;
- do not count them as duplicates of `M3_DATE_ANCHORED_NEXT_SESSION_V2`;
- preserve the exact-time route closure under its own identity;
- recompute retained count, removal count, source bindings, scores and validation fields.

Do not reopen exact-time data acquisition.

## H2 — correct M3 source binding

Lucca and Moench document a pre-announcement drift. That source does not establish a next-session open-to-close premium.

Choose one outcome-blind disposition:

```text
A. bind a mechanism-specific original source for next-session FOMC response;
B. classify M3 V2 as ECONOMIC_PRIOR_ONLY;
C. classify M3 V2 as SOURCE_GAP and PARK it.
```

Do not leave M3 V2 as a complete exact source binding while using the pre-FOMC paper.

If no exact source is found, remove M3 V2 from the finalist list.

## H3 — introduce source classes

Every retained card must use one source class:

```text
EXACT_MECHANISM_SOURCE
ECONOMIC_PRIOR_ONLY
OPERATIONAL_ROUTE_ONLY
SOURCE_GAP
```

Definitions:

- `EXACT_MECHANISM_SOURCE`: the cited source studies substantially the same signal direction, event timing and economic channel;
- `ECONOMIC_PRIOR_ONLY`: the source supports the economic state or causal channel, but not the frozen tradable signal;
- `OPERATIONAL_ROUTE_ONLY`: documentation supports data or market mechanics only;
- `SOURCE_GAP`: no credible source for the proposed mechanism.

A card cannot receive the maximum economic-prior score from `ECONOMIC_PRIOR_ONLY` or `OPERATIONAL_ROUTE_ONLY` alone.

## H4 — correct USDEM-018

The cited Andersen et al. source supports volatility persistence and clustering, not the claim that moving a broad-equity account to cash after a shock improves net risk-adjusted returns.

Required correction:

- either bind a volatility-management source and explicitly record that out-of-sample and cost evidence is contested;
- or reclassify `USDEM-018` as a state diagnostic rather than an alpha strategy;
- or downgrade and PARK it.

Do not preserve finalist rank 2 solely from the volatility-distribution paper.

## H5 — make scoring reproducible

The current rubric lists ranges but no score anchors.

Add machine-readable anchors for every level.

Minimum anchor contract:

### economic_prior, 0–3

```text
3 = exact mechanism source plus at least one independent supporting source
2 = exact source with material implementation translation, or strong economic prior only
1 = indirect/analogical evidence
0 = no credible mechanism evidence
```

### data_readiness, 0–3

```text
3 = all required identities qualified locally and immutable
2 = one bounded official-identity or join task remains
1 = paid source, multi-system mapping or major unresolved coverage remains
0 = unavailable or prohibited
```

### sample_sufficiency, 0–2

```text
2 = expected count clearly exceeds frozen minimum across enough years
1 = marginal or highly clustered expected count
0 = expected sample insufficient or unknown
```

### USD_40000_execution_fit, 0–2

```text
2 = liquid, unlevered, whole-share faithful
1 = material concentration, turnover or gap constraints
0 = cannot faithfully execute
```

### cost_robustness_expectation, 0–2

```text
2 = low turnover or large event prior relative to conservative costs
1 = plausible but cost-sensitive
0 = execution friction likely dominates
```

### independence_from_closed_lines, 0–2

```text
2 = distinct economic source and signal
1 = adjacent, requires explicit guard
0 = duplicate or outcome-informed rescue
```

### implementation_simplicity, 0–1

```text
1 = narrow implementation within existing architecture
0 = new platform, NLP stack, optimizer or high-complexity engine needed
```

### prospective_observability, 0–2

```text
2 = frequent and objectively timestamped future observations
1 = slow or sparse observations
0 = future evidence not practically collectable
```

## H6 — deterministic recommendation rule

The current finalist eligibility uses the subjective `recommendation=ADVANCE`.

Replace it with a deterministic rule. At minimum:

```text
CLOSE:
- duplicate/rescue; or
- source gap with no bounded resolution; or
- execution fit = 0.

PARK:
- data readiness <=1; or
- implementation simplicity = 0; or
- economic prior <=1; or
- unresolved source mismatch.

ADVANCE_FOR_QUALIFICATION:
- no CLOSE/PARK condition;
- total score above frozen threshold;
- no source gap;
- no outcome access.
```

Do not call any card a strategy candidate.

## H7 — portable exact-time M3 closure evidence

The current file relies on a local `G:\...` scratch hash.

Add compact controlling evidence:

- PR #105 exact HEAD;
- PR #105 review ID;
- official manifest and qualification hashes;
- searched record classes;
- bounded elapsed time and request scope;
- exact statement that closure is `WITHIN_BOUND`, not a universal proof that no evidence can ever exist.

Do not copy the large PR #105 record mirrors into PR #107.

## Validation

Recompute and verify:

```text
input card count
retained mechanism count
removed variant count
source-binding counts by class
score rows and totals
recommendation counts
finalist list
formal selection count = 0
all boundary flags = false for outcomes/trading
```

Run:

```text
strict JSON duplicate-key and nonfinite checks
Ruff if applicable
git diff --check
full existing CI
independent outcome-blind acceptance
```

## Required terminal state

```text
PR_STATUS=DRAFT
OUTCOME_ACCESS=false
PRICE_RETURN_ACCESS=false
DATABASE_ACCESS=false
STRATEGY_CODE_WRITE=false
FORMAL_DECISION=NO_MECHANISM_READY
STRATEGY_CANDIDATE_AVAILABLE=false
NEXT_ACTION=DELTA_EXTERNAL_REVIEW
```
