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

## Three-cycle architecture freeze

- For the next three strategy cycles, do not add a CLI, database layer, event
  loop, evidence framework, manifest schema, registry, agent, or runner
  framework. Fix concrete defects in the existing path only.
- Run repeatable, outcome-free data qualification before consuming a one-use
  strategy result. Input failures must not consume the first outcome run.
- A strategy adapter should contain only its feature, selection, and fixed
  parameters, normally in 100--300 lines, while reusing the shared engine.
- Keep at most four durable run artifacts: definition, snapshot, result, and
  run receipt. Prefer Git object identity over additional sidecars.
- Do not migrate or reopen rejected legacy strategy families. During this
  freeze, relative-strength data qualification is the only active family.
