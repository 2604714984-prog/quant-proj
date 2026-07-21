# Working rules

This is a personal research project. Prefer the smallest implementation that is
easy to understand, test, and remove.

## Repository boundary

- All active source, configuration, tests, documentation, and non-sensitive
  research definitions belong in this repository.
- Databases, raw data, caches, backups, large generated results, and credentials
  stay outside Git under the configured data root.
- Never commit credentials or copy secret values into logs, tests, reports, or
  callbacks.
- Do not add absolute machine-specific paths to active code or configuration.

## Engineering boundary

- One CLI and one configuration path are preferred over controllers,
  dispatchers, registries, task packets, and duplicated workflows.
- Routine append-only data imports need schema validation, uniqueness checks,
  and an atomic transaction; they do not need a bespoke approval framework.
- Destructive schema migrations require an explicit backup and rollback check.
- New behavior needs focused tests. Synthetic or temporary databases are the
  default for tests.
- Preserve point-in-time semantics explicitly; fail closed when required market
  state is missing.

## Research boundary

- Default state is research-only.
- Do not add broker, order, paper, live, or automatic trading paths.
- Do not present an unvalidated strategy as a candidate or recommendation.
- Legacy research results are evidence, not executable dependencies.

## Lightweight repository shape

- Do not add controllers, dispatchers, task packs, callbacks, strategy
  registries, mechanism atlases, or a runner framework.
- Keep at most one current strategy adapter on a research branch. It contains
  only the feature, selection, and fixed parameters and reuses the shared core.
- Terminal experiments stay recoverable through Git history and Releases; they
  do not remain as active source, reports, receipts, or checksum sidecars.
- Use ordinary branches, one PR, and CI. Require external review only for
  changes to shared data, point-in-time (PIT), unit, or execution contracts;
  event-loop, portfolio, or market semantics; the first historical `PASS`;
  any prospective result; the first combination result; or any opening of
  position-effect or trading boundaries.
- An ordinary `FAIL` or `INPUT_BLOCKED` terminal result needs only that PR with
  green CI, one compact terminal result, and permanent closure; it does not
  require external review. Intermediate milestones do not need review.
- Do not migrate or reopen rejected legacy strategy families.
