# PR A Task — A-Share Swing Structure With Participation Confirmation

Date: 2026-07-18
Repository: `2604714984-prog/quant-proj`
Default branch: `v2-main`
Status: `AUTHORIZED_FOR_OUTCOME_BLIND_PR_A_ONLY`

## Authority and base

The owner selected `Swing Count` on 2026-07-18. This task is bound to:

```text
base_commit=6967c2819a27ae11de0410cbffc65e575b519343
base_tree=cbf9c59fae06bfa24a587ddb17298c7cf086f035
branch=agent/a-share-swing-count-20260718
research_id=A_SHARE_SWING_STRUCTURE_PARTICIPATION_CONFIRMED_TREND_V1_20260718
```

Read the Manager constitution, current roadmap and `AGENTS.md` first. This is
the only active code-writing family. It is not a rescue of Relative Strength,
Family 46, Family 66, Defensive Low Volatility or Cycle 3.

## Economic hypothesis

Repeated higher highs and higher lows, when most trading participation occurs
on advancing sessions, may reflect gradual capital accumulation and persistent
price structure rather than a large endpoint return or a fresh breakout.

Freeze exactly two close-based variants: 20 and 60 accepted sessions. The exact
pivot, participation, ranking, timing, portfolio, split, cost, inference and
gate definitions are controlling in:

```text
research/definitions/a_share_swing_structure_participation_confirmed_trend_v1.json
```

There is no parameter grid. Do not add high/low pivots, breakout thresholds,
endpoint-return rank, volatility, regime, stop, valuation, size, industry or
fundamental filters.

## PR A scope

PR A may contain only:

- this task and the minimal Manager state update;
- one frozen definition;
- one 100–300 line strategy adapter using the shared engine;
- focused deterministic tests;
- one repeatable read-only, aggregate-only preflight entry path at
  `scripts/run_a_share_swing_structure_preflight.py`.

Do not create a CLI, framework, registry, runner abstraction, database layer,
event loop or portfolio core. Do not modify shared execution semantics.

## Preflight contract

Use only the configured read-only database and the exact frozen snapshot. The
preflight may compute features internally but may publish only aggregate counts
and health fields allowed by the definition. It must not publish security
identifiers, rankings, returns, NAV, Sharpe, performance gates, embargo data or
prospective data.

Minimum pass conditions:

```text
every frozen historical decision has at least 500 base-eligible names
every variant has at least 15 candidates at every decision
selected next-open execution panels are complete
benchmark initial entry fills
unexpected_exception_count=0
currency_unit=CNY
position_unit=SHARES
database bytes and snapshot identity remain unchanged
```

Structural insufficiency closes this family at preflight; do not relax a
threshold. An input identity defect blocks without consuming the historical
outcome.

## Validation and stop

Run focused tests, the full suite, Ruff and `git diff --check`. Obtain fresh
independent read-only acceptance before commit and push. PR A and an aggregate
preflight PASS do not require full external review.

Do not execute historical returns in PR A. After PR A is merged, the Manager
may authorize one fresh historical Run ID. Stop for external review if a shared
financial/PIT/snapshot semantic must change or if that one historical run is the
family's first historical PASS. An ordinary historical FAIL closes permanently
with CI and Manager scope review.

## Boundary

Research-only. No provider or network access, database write, forward result,
recommendation, candidate promotion, ensemble, signal publication, broker,
order, paper, live or automatic execution. `strategy_candidate_available=false`.
