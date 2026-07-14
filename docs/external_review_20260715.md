# External review brief - 2026-07-15

## Requested verdict

Review whether this V2 repository is a small, maintainable foundation for one
person's quantitative research. The target is not institutional workflow
parity. A valid review should distinguish necessary data-integrity checks from
the controller, packet, registry, and multi-repository layers intentionally
removed from the legacy workspace.

## Scope and boundaries

The active workspace has two top-level directories:

```text
/home/rongyu/workspace/quant-proj/  one Git repository for code and documents
/home/rongyu/workspace/quant-data/  one private mutable data root outside Git
```

The runtime surface is one Python package, one CLI, one DuckDB access layer,
small A-share and US market-rule modules, one deterministic portfolio core, one
test suite, and one CI workflow. There is no dispatcher, task-packet engine,
research registry, product route, web service, broker integration, or live
trading path.

At review preparation time the repository contains 43 tracked files: 2,069
lines of runtime Python, 485 lines in the two migration/recovery scripts, and
1,904 lines of tests. These counts are included so reviewers can judge
proportionality directly rather than inferring it from the number of checks.

This review did not retrieve provider data, write the central database, run a
strategy search, promote a strategy candidate, or access credential values.

## Self-audit findings and repairs

The pre-review audit used line-level inspection plus adversarial dynamic
reproductions. It found real defects rather than an architectural need for more
layers. The repair is confined to existing modules and tests:

1. DuckDB append safety now verifies the actual captured source bytes, exact
   metadata-table contract, natural-key uniqueness after DuckDB coercion,
   replay-count conservation, pinned database identity, and path stability
   around commit. Exact existing rows remain idempotent; conflicts fail closed.
2. Read-only queries pin and verify the database file descriptor and disable
   external access. The CLI accepts only a single read-only `SELECT` statement.
3. Legacy capture and inventory use descriptor-bound hashing, reject symlinks
   and replacements, remove credentials from recorded origin URLs, detect
   concurrent worktree changes, and publish captures atomically.
4. Installed wheels carry functional defaults. Project and data roots cannot
   overlap in either direction. CI installs the wheel and exercises the CLI
   outside the checkout.
5. A-share execution rechecks the final slippage-adjusted price against daily
   limits, applies the dated statutory sell-tax schedule independently of a
   custom commission model, and distinguishes buy board lots from complete
   liquidation of corporate-action odd lots.
6. US execution binds settlement to the complete accepted-session sequence and
   changes from T+2 to T+1 on the frozen effective date. Market inputs and
   corporate actions require explicit qualification; non-finite arithmetic
   fails before portfolio state mutation.

No generic approval engine, lineage database, workflow DSL, or new service was
introduced. Most added lines are focused negative tests for file replacement,
forged metadata, malformed JSON, non-finite values, market-rule edge cases, and
wheel isolation.

## Reproducible checks

From the repository root:

```bash
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/python -m compileall -q src scripts tests
.venv/bin/python -m pip check
git diff --check
```

The pre-publication result is 97 passing tests with no skipped or failed tests;
Ruff, byte compilation, dependency consistency, strict JSON parsing, and Git
whitespace checks pass. Package and test-tool versions are exact-pinned, the
Python runtime line is 3.12, and GitHub Actions are referenced by immutable
commit SHA.

A wheel is also built and installed into an isolated environment. `quant info`
works outside the checkout without repository-level configuration. The
pre-publication wheel SHA-256 is
`45b14ef3c9306c0dfa3df5665281a3d863c23ae33651f80ff4b3d36a0959fdd1`.

## Git and recovery state

The public Git surface was reduced from 40 branches, 20 tags, and 3 open pull
requests to the protected `v2-main` branch before this review branch was
published. Legacy refs were removed only after verified Git bundles were made.
The complete legacy bundle has SHA-256
`48e1f10d27907c65db2a67d5fedd55a500417d7319ccb7fafe7d05a7e337ea99`,
contains the final legacy main tip, and has a verified copy on the host recovery
drive. Secret scanning and push protection are enabled; open secret-scanning
and dependency alerts were zero at preparation time.
`v2-main` requires the strict `test` check, linear history, and resolved review
conversations; the rule applies to administrators and disables force-pushes and
branch deletion.

The central database remained byte-identical and was opened read-only only:

- path: `/home/rongyu/workspace/quant-data/quant_research.duckdb`
- size: 2,411,212,800 bytes
- SHA-256: `936e1ee5230207b1ca59e1fd6245ad5a3c1dd957ae030441e8420c83e57a3869`
- mode: `0600`
- readable tables: 39

## Deliberately unresolved or out of scope

- The 24.1 GB legacy quarantine is retained outside Git because it includes
  data not yet proven redundant. It is inactive rollback material, not runtime
  code. Deleting it is a later data-classification task.
- This release does not claim complete point-in-time data, validated strategies,
  provider qualification, or production ingestion coverage.
- No real central-database append was performed during hardening. Writer tests
  use temporary databases; the next real import should start as a small,
  observable batch through the ordinary CLI.
- Broker, order, paper, live, automatic execution, recommendation, and product
  activation remain absent.

## Reviewer checklist

An external reviewer should independently verify:

1. the release ref resolves to the reviewed V2 commit and CI is green;
2. a clean wheel install passes tests and `quant info` outside the checkout;
3. append replay, coercion collisions, metadata forgery, symlink/replacement,
   and commit-path ambiguity tests fail closed as documented;
4. A-share tax/limit/lot and US settlement tests match their frozen dates;
5. no credential, database, raw payload, cache, or recovery archive is tracked;
6. the implementation remains proportionate to a personal research project.

The desired external verdict is therefore about code integrity and architectural
proportionality, not about strategy profitability or live-trading readiness.

## Primary rule references

- China tax authority: [the securities transaction stamp-tax reduction took
  effect on 2023-08-28](https://fgk.chinatax.gov.cn/zcfgk/c102416/c5211343/content.html).
- U.S. SEC: [the standard settlement cycle changed to T+1 on
  2024-05-28](https://www.sec.gov/newsroom/press-releases/2024-62).
