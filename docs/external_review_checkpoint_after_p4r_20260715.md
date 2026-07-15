# V2 external-review checkpoint after P4-R

## Review target

Review the current lightweight V2 as a personal quantitative-research project,
not as an institutional platform. The implementation baseline is
[`v2-main@0bf51596`](https://github.com/2604714984-prog/quant-proj/tree/0bf51596b108ea8ee1cf8f2a63aeaa1b5763101b)
with tree `efbefc433d80528b7f956de2129ae424004ee5af`.

The earlier [external-review brief](external_review_20260715.md) describes the
pre-P3 rebuild. Its historical size, test, wheel, and database snapshot claims
are no longer current-state claims. This checkpoint is the controlling review
entry for the repository after P3, P4-R, and the first legacy-strategy migration
replay.

Please review architecture, implementation, evidence classification, and scope
discipline. Do not judge strategy profitability from the reported historical
returns and do not infer live-trading readiness.

## Intended lightweight shape

- one Git repository for code and documentation;
- one private data root and one DuckDB outside Git;
- one Python package, one CLI, one CI workflow, and one test suite;
- no dispatcher, task-packet engine, research registry, service mesh, broker,
  paper/live/automatic trading, or recommendation path.

Current tracked surface at the baseline is 79 files: 5,405 lines under `src/`,
2,753 lines of scripts, and 6,183 lines of tests. These counts are disclosed
because the main external-review question is whether the post-P3/P4 additions
remain proportionate for one person. In particular, reviewers should decide
whether one-off qualification and validation scripts should remain in the
active repository or be reduced/archived after their evidence is frozen.

## Evidence currently available

| Area | Exact result | What it proves | What it does not prove |
|---|---|---|---|
| Build and CI | [`ci` run 29399188859](https://github.com/2604714984-prog/quant-proj/actions/runs/29399188859) passed on baseline commit; local suite passed 265 tests | Package builds, installed CLI runs, tests and Ruff pass | Data quality or strategy validity |
| Synthetic engine | [`p4_v2_engine_golden_static_allocation_v1_result.json`](../research/reports/p4_v2_engine_golden_static_allocation_v1_result.json), SHA-256 `3a7e062031742f372b185d17d84e17f37f00130395f06434aa7d553284d7a5fb` | 13/13 deterministic accounting and execution conformance gates | Real-data or strategy evidence |
| Official SPY source qualification | [`p3_spy_official_source_qualification_v1_result.json`](../research/reports/p3_spy_official_source_qualification_v1_result.json), SHA-256 `f809e2a004e9c4344d7b0ab79fd0ebba5377bae67eed50d117302f09399d061b` | Official identity, distributions, NAV and partial calendar mechanics | Anonymous official 2016-2025 raw OHLC, complete lifecycle, or PIT availability |
| SPY real-data system path | [`p4_spy_retrospective_real_data_v1_result.json`](../research/reports/p4_spy_retrospective_real_data_v1_result.json), SHA-256 `df5302b4fb6edf5f06fe21a3d1092e17562b1329ca4d2af3255194322f87d33b` | 14/14 retrospective multi-source accounting/reconciliation gates | Strict PIT evidence or a strategy candidate |
| Four legacy ETF formulas | [`legacy_us_etf_migration_replay_v1_result.json`](../research/reports/legacy_us_etf_migration_replay_v1_result.json), SHA-256 `377241b26c3705e99d680dbfe651d561ce4a8be1cc418a8aaf60719698b0b457` | Expected local row/session counts, boundary dates, and deterministic replay of the old close-to-close formulas | Reproduction of old headlines, corporate-action completeness, PIT validity, or reopening rejected strategies |

The four-strategy replay is intentionally a 235-line migration check rather
than a generic strategy framework. Its script SHA-256 is
`33f6d8e8132c5958feff0d1f98efd4e1e2efe968cb1ff0b68b19244b6f849d28`;
the focused test SHA-256 is
`de81f4f62343d0a6d7e2fe9fe9adef4ccc3db9e7632621d135aab0f692b0eaa1`.

## Legacy replay result

The input slice contains 7,542 raw Sina rows across SPY, QQQ, and GLD, with
2,514 common sessions from 2016-01-04 through 2025-12-31. All 7,542 rows lack
`available_at`. `coverage_exact=true` means only that row count, common-session
count, and first/last session dates match the frozen expectations. It does not
pin the slice hash and is not a claim of source completeness or PIT correctness.

| Formula | Old headline return | Current replay return | Old / current Sharpe | Old / current drawdown |
|---|---:|---:|---:|---:|
| US31 SPY/GLD | 284.00% | 256.77% | 1.188 / 1.127 | -20.50% / -20.54% |
| US36 SPY/QQQ | 338.00% | 307.16% | 0.846 / 0.809 | -31.10% / -31.13% |
| US41 SPY/QQQ/GLD | 346.00% | 299.48% | 1.115 / 1.038 | -23.50% / -24.42% |
| US46 QQQ/GLD | 404.00% | 367.86% | 1.246 / 1.193 | -23.80% / -24.35% |

The controlling status is
`REPLAY_COMPLETE_HEADLINES_NOT_REPRODUCED / RETROSPECTIVE_MIGRATION_CONSISTENCY_ONLY`.
US31, US36, US41, and US46 remain rejected lineage entries. This replay neither
rescues nor retests them.

## Reproduction boundary

GitHub contains the code, tests, result files, and checksums, but not the private
DuckDB. A GitHub-only reviewer can reproduce the package and synthetic tests:

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/python -m compileall -q src scripts tests
git diff --check
```

Recomputing the real-data reports requires the separately held database and its
frozen row identities. Therefore the GitHub package alone supports code and
classification review, not independent verification of the market-data
values. Please treat that limitation explicitly rather than silently upgrading
the reports to fully reproducible strategy evidence.

The legacy replay result also does not embed the current V2 commit/tree, full
database SHA-256, script SHA-256, or exact invocation. Its two legacy blob OIDs
are not resolvable from the deliberately rebuilt V2 object database alone. The
reviewer should decide whether the hashes and links in this checkpoint are
sufficient for a migration-only check, or whether a compact immutable run
manifest and legacy-bundle locator are a necessary narrow repair. The reviewer
should also decide whether `coverage_exact=false` should merely classify a
report or should block report generation entirely.

## Questions for the external reviewer

1. Is the current one-repository/one-database architecture still proportionate
   for a personal project, given the disclosed code and test size?
2. Which P3/P4 one-off scripts, if any, should be shortened, moved to an archive,
   or retained as executable evidence?
3. Is the legacy replay correctly limited to migration consistency, including
   its handling of missing `available_at` and raw close data?
4. Are the report flags and wording strong enough to prevent synthetic or
   retrospective system checks from being mistaken for strategy validation?
5. What is the smallest necessary change set before testing one genuinely new,
   outcome-blind hypothesis on this architecture?
6. Should broader runner generalization be deferred until two or three
   materially different strategy shapes have been migrated?

## Requested verdict format

Return exactly one top-level verdict:

- `ACCEPT_LIGHTWEIGHT_BASELINE`
- `ACCEPT_WITH_NARROW_FIXES`
- `REWORK_ARCHITECTURE`

For every finding, provide severity, exact file and line, a reproduction or
reasoning trace, and the smallest sufficient repair. Separate blocking defects
from optional improvements. Do not request institutional workflow layers unless
a concrete failure in this personal-project scope requires them.

No strategy search, provider retrieval, database write, candidate promotion,
recommendation, or trading action was performed to prepare this checkpoint.
