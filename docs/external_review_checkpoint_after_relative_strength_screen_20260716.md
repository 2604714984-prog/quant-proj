# External-review checkpoint after the first relative-strength screen

## Review target

This checkpoint records the first execution of the newly preregistered A-share
medium-term relative-strength strategy on the lightweight V2 architecture. The
project remains a personal research system: one Git repository, one private
DuckDB, no service platform, and no broker, paper, live, automatic-trading, or
recommendation path.

The frozen runner executed from source commit
`4283705e855ce9285f556d5ac599bcae388b28e8` and tree
`8c70dd786ea57794a057e4e5d4f1997bae0e385b`. Review the pull-request commit
containing this checkpoint and the three result artifacts together. Do not
interpret this run as strict PIT evidence or as a strategy candidate.

## Data publication completed before execution

The private central database published snapshot
`a_share_qfq_personal_research_20260716_v2` by content-addressed atomic
replacement. The accepted source contained 4,720,765 rows. A complete-case
rule removed 4,734 rows whose volume and amount were both null, leaving
4,716,031 rows, 2,910 symbols, and 2,058 benchmark rows from 2018-01-02 through
2026-06-30.

The published database SHA-256 is
`ef7fe066da06e0011d2c1c59fd1a36e373a3f1cc066e5685489a2dafb77a1a9f`.
Its ordered row-hash digest is
`ccfb4f98428a36442f962912aa8fc77501706bbc5e622e08ce8c97e67c62f7c5`.
The publication receipt SHA-256 is
`36929ab494934b2cad18f07e0cdc30dc1e67fe27e33b3dba1ac54de8d3f1462c`.
The pre-publication backup remains byte-exact. No schema change occurred.

The controlling classification is
`RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT`. Dropping the
4,734 incomplete rows may create continuity or selection effects and is
explicitly disclosed rather than treated as harmless cleaning.

## Frozen one-use execution result

The private aggregate-only data manifest has SHA-256
`f01db1de1deed3fb795a0080d196b90d73785fc8029063e6fa51432b2a9034b7`.
It contains 102 ordered monthly identity partitions and no security list or
strategy outcome. The local one-use guard has SHA-256
`e2fbb9de1606b23ea7a6e26180733630156dfe4ad017935ce88f672ae8cbf634`.

The guard consumed its marker before starting the child exactly once. The
child returned code 2 after 23.5 seconds and published the terminal status
`INPUT_BLOCKED` with `reason_class=SecondaryScreenError`. Retry is forbidden.

| Evidence | SHA-256 |
|---|---|
| Result JSON | `6acb25e0fe8641c59050da9e49f3b9c4b3813e31491a71d75a0ccf1b6c6eaf60` |
| Result sidecar | `d5481e5019e89cb60751918e04da148df524f4fc0924211f6d6063f0185fb01c` |
| Run receipt | `134a208516d379673006f4cc91f73b1056c7ec74f281614b088aca275b733172` |
| Private consumed marker | `f9a22c8a7d07ea806bae6019b020d26dce6969dea1e7b4ca9bc8c21932b12872` |

Database SHA-256 before and after the child is identical. No provider or
network call, database write, identifier publication, prospective-forward
access, recommendation, or candidate promotion occurred.

## Meaning of `INPUT_BLOCKED`

This is neither a performance pass nor a performance fail. No historical gate
count or return statistic was accepted. It is valid negative system evidence:
the frozen input/runner contract stopped before producing an admissible
strategy result.

The aggregate result deliberately retains only the exception class, so the
exact raise site cannot be recovered without rerunning. A no-outcome static
diagnosis established that all 53 signal dates exist and that structural base
eligibility ranges from 2,050 to 2,694 names. The minimum-500 universe gate is
therefore excluded. The remaining earliest causes are:

1. fewer than 15 positive-relative-strength candidates for a variant/date; or
2. strict execution-panel continuity failure for a selected or held symbol.

The second is more plausible because complete-case publication removed 4,734
rows while the frozen runner requires exact current/prior rows for every
selected or held symbol, including blocked-exit retries. Benchmark coverage is
complete. This diagnosis did not compute or expose portfolio returns, and the
run will not be repeated merely to recover the redacted error text.

For future lineages, reviewers should decide whether aggregate results should
retain a stable non-sensitive reason code (not raw exception text) and whether
data qualification should include a strategy-independent continuity matrix.
Neither change may retroactively reopen this consumed run.

## Validation and reproducibility boundary

- focused relative-strength tests: 25 passed;
- full repository suite: 463 passed;
- scoped Ruff and `git diff --check`: passed;
- result, sidecar, receipt, manifest, and marker: regular single-link `0600`
  files;
- independent result-chain acceptance: `RESULT_ACCEPTED`.

GitHub contains the runner, research contract, result, sidecar, run receipt,
and this checkpoint. It does not contain the private 3.37 GB DuckDB, private
manifest, publication receipt, or consumed marker. A GitHub-only reviewer can
audit code, identities, classification, and terminal evidence, but cannot
independently recompute the market-data scan. That is an explicit limitation.

## Requested external verdict

Return one top-level verdict:

- `ACCEPT_TERMINAL_INPUT_BLOCKED_EVIDENCE`
- `ACCEPT_WITH_NARROW_FIXES`
- `REWORK_RESULT_EVIDENCE`

For each finding, provide severity, exact file and line, reasoning or a bounded
reproduction, and the smallest sufficient repair. Please review proportionality
for a personal project. Do not request institutional workflow layers unless a
concrete defect requires them, and do not recommend rerunning or retuning this
consumed strategy lineage.
