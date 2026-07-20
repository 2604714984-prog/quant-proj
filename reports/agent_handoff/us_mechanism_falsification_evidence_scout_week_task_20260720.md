# US Mechanism Falsification Evidence Scout — Week Task

Date: 2026-07-20  
Role: adversarial literature and replication scout  
Atlas modification authority: none

## Goal

Search specifically for evidence that weakens, reverses, or limits several high-interest mechanisms already present in frozen Atlas R1.

The output is a decision-risk report, not a new Atlas, shortlist, or strategy recommendation.

## Mechanisms to review

```text
USDEM-004 macro announcement premium
USDEM-006 pre-holiday premium
USDEM-012 session decomposition V2
STK_01 52-week-high proximity
STK_04 short-term residual reversal
FND_01 PEAD
FND_07 filing delay
FND_16 cluster insider purchases
FND_22 asset growth
USIOT-008 variance risk premium
```

Do not add mechanisms.

## Search priority

For each mechanism, seek:

1. original mechanism paper;
2. independent replication;
3. out-of-sample or post-publication evidence;
4. transaction-cost evidence;
5. microcap, survivorship, look-ahead, or data-construction critiques;
6. recent null or contrary findings;
7. practical observability in prospective Shadow.

Use original papers, official working papers, journals, and author datasets where possible. Avoid SEO summaries.

## Required classification

For each mechanism, assign one of:

```text
PRIOR_REMAINS_STRONG
PRIOR_MIXED
PRIOR_WEAK_AFTER_COSTS
PRIOR_REPLICATION_SENSITIVE
PRIOR_DATA_CONTRACT_DOMINATES
```

This classification does not change Atlas R1 and cannot authorize implementation.

## Mandatory questions

For each mechanism answer:

- Is the published effect concentrated in microcaps or a short historical period?
- Does it rely on a short leg that the project cannot execute?
- Does the long-only version preserve the mechanism?
- Are transaction costs likely larger than the reported effect?
- Does the original event or signal remain observable point-in-time?
- Has the effect weakened after publication?
- Is a simple ETF or cash benchmark likely to absorb most of the value?
- How quickly can future Shadow accumulate independent evidence?

## Special attention

### USDEM-004

Check whether the announcement premium persists in more recent samples and whether it is robust to the exact event taxonomy, collisions, and risk-free subtraction.

### USDEM-006

Check whether the pre-holiday effect survives in large, liquid instruments and later samples; do not suggest reopening the parked lane.

### STK_04

Check whether short-term reversal survives conservative spreads, open execution, and earnings/event exclusions.

### FND_16

Check whether cluster buying adds information beyond simple insider purchases and whether amendment/10b5-1 rules alter the effect.

### FND_22

Check whether asset growth survives large-cap/liquid-universe restrictions and first-as-filed construction.

## Prohibitions

- no local price or return access;
- no model fitting;
- no parameter recommendation;
- no Atlas edits;
- no new strategy family;
- no provider purchase;
- no claim that literature evidence is local validation.

## Deliverable

One report under 300 lines with:

- mechanism ID;
- strongest supportive source;
- strongest contrary or limiting source;
- key implementation risk;
- prospective observability;
- prior classification;
- one sentence stating what evidence would falsify the mechanism locally.

## Time box

Maximum effort: three working days.

## Callback

```text
BATCH=US_MECHANISM_FALSIFICATION_SCOUT_WEEK_20260720
STATUS=
MECHANISMS_REVIEWED=10
STRONG_PRIOR_COUNT=
MIXED_PRIOR_COUNT=
WEAK_AFTER_COSTS_COUNT=
REPLICATION_SENSITIVE_COUNT=
DATA_CONTRACT_DOMINATES_COUNT=
REPORT_URL=
ATLAS_MODIFIED=false
PRICE_ACCESS=false
OUTCOME_ACCESS=false
DATABASE_WRITE=false
```
