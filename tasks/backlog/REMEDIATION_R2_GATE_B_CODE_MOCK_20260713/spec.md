# REMEDIATION_R2_GATE_B_CODE_MOCK_20260713

TASK_ID: REMEDIATION_R2_GATE_B_CODE_MOCK_20260713
STATUS: BACKLOG_CODE_ONLY_MOCK_TMP_ONLY
TARGET_PROJECT: central_data_ingestion
RECOMMENDED_AGENT: codex_dev
MODEL_ROLE: executor
MODEL: gpt-5.6-luna
REASONING_EFFORT: medium
SOURCE_COMMIT: 287416f79cd1fcb1c066f25fa7bbaedc574b0ce9
SOURCE_TREE: c2a62d079bcb08b04b2425c7160bf9ca8344038a
AUTOMATED_GATE_COMMANDS: gate_commands.txt
AUTOMATED_GATE_COMMANDS_SHA256: 29c79cbceacdb5d76d85f1d1f0f7bd2a7a6d1ca7412fcdc4807cff6cb1f99e40
CALLBACK_TARGET: 019f4c70-cac3-7211-8e04-47b8b51c819e
ACCEPTANCE_ROLE: codex_acceptance
CONTEXT_DELTA: context_delta.md
CONTEXT_DELTA_SHA256: c395bd5040b189ac33427c66601a16d75d3f2b1d683cc2dd7a6d267fc352018e
UNACCEPTED_CANDIDATE_RECORD: candidate_input.json
UNACCEPTED_CANDIDATE_RECORD_SHA256: 3167756de7be36f6d068df000ebbf449c5ede898859e9935fa49b6fe1ac85caf

## Objective

Implement the code/mock precondition for DB-608 through DB-612 without touching
real data or crossing Gate B. This task creates a fail-closed single-writer
publisher, versioned canonical-view contract, inert timer templates and a
five-symbol/full-calendar-month synthetic canary harness.

The source baseline is exact clean `central-data-ingestion main`. A separate
candidate branch is frozen only as `UNACCEPTED_SUPERSEDED_DESIGN_INPUT` in
`candidate_input.json`.

## Allowed implementation scope

- `central_data_ingestion/`: publisher, publish authorization, contracts,
  CLI integration, mock canary and directly required Wave 1 hardening.
- `tests/`: focused deterministic unit, adversarial and temporary-DuckDB
  integration tests.
- `scripts/scan_boundaries.py`: include all intended tracked and precommit
  source/test/deploy/doc paths in the boundary scan; fail on strategy imports,
  token values, network clients in the publisher, central-path literals and
  Replay result artifacts.
- `deploy/`: inert collector and publisher unit templates only.
- one code/mock status document with no provider values and no Gate B claim.
- `pyproject.toml`: exact runtime dependency `duckdb==1.5.4`; no unpinned
  DuckDB range or unrelated dependency change.
- `.github/workflows/ci.yml`: exact clean-runner dependency closure only.
  Preserve action SHA pins, install
  `duckdb==1.5.4 pytest==9.0.2 ruff==0.14.10` before the existing
  `pip install --no-deps -e .`, explicitly import DuckDB and assert
  `duckdb.__version__ == "1.5.4"`, then compile, Ruff, full pytest and
  boundary scan. Do not rely on a preinstalled module.

No other repository may be modified.

## Fail-closed publisher contract

- Default invocation is a dry-run plan and opens no database, socket, token,
  environment file, staging file or output file.
- An explicit test-only execution flag must be paired with a test-root sentinel
  and must reject the central database path, its parent, symlinks, hardlinks,
  bind/replaced parents and any target outside the held test root.
- Hash, stat, parse and publish use the same held descriptor bytes wherever an
  input file is involved. Parent and leaf identities are checked before and
  after every mutation boundary.
- Only a fully accepted, non-quarantined immutable batch from an append-only
  accepted queue may publish.
- The batch identity binds schema, normalized natural keys, row content,
  provenance, source snapshot, queue receipt and accepted validation receipt.
- One writer lock covers one transaction. Reusing the exact batch is a no-op;
  the same batch ID with different bytes fails. Rollback leaves database bytes
  and active-view identity unchanged.
- Natural-key conflicts preserve historical rows and fail/quarantine rather
  than silently overwrite. Historical versions are append-only.
- Canonical activation requires a complete and continuous accepted snapshot
  plus a separately supplied independent activation manifest whose bytes and
  identity are not authored by the publisher. It is atomic, versioned and
  cannot make a partial backfill active.
- Production-shaped write code accepts only an external exact HG record; it
  cannot create, mutate, infer, default or self-approve `HG_EXEC_GRANTED`.
- There is no direct-library write path, public/internal `lock_held` flag, or
  caller assertion that bypasses the CLI, accepted queue, independent
  activation manifest, HG, descriptor, lock, transaction or rollback checks.
- Every accepted queue receipt, batch, provenance record, validation receipt,
  activation manifest, HG record, database target and result identity used for
  a decision is captured, hashed and parsed from the same held descriptor.

## Timer and capability contract

- Both collector and publisher service templates remain inert with
  `ExecStart=/usr/bin/false`.
- No user unit is copied, linked, enabled, started or reloaded.
- Publisher runtime code cannot import HTTP/provider/token modules, read an
  environment/token file, or invoke collector, strategy, recommendation,
  candidate, broker, order, paper, live or auto paths.

## Mock canary and status semantics

The only canary in this packet is deterministic synthetic data for exactly five
symbols and every accepted session of one fixed full synthetic calendar month
in a test-owned temporary root. It must prove accepted
batch publication, consumer query, exact counts/hashes, idempotent repeat,
forced rollback, partial-snapshot rejection and zero strategy invocation.

Passing this task may produce only:

`GATE_B_CODE_MOCK_PRECONDITION_GREEN`

It must not produce `GATE_B_PASS`, `DB_612_COMPLETE`, activate a canonical
view, authorize a real canary, or unlock DB-613 through DB-616.

## Boundaries

No provider/network request, Replay route, token or `.env` access, response
payload, real staging read/write, central DB open/write, backup creation,
schema migration, timer deployment/activation, registry/readiness activation,
strategy/outcome access, recommendation, candidate promotion, product route,
daily signal, broker/order/paper/live/auto action, or secret output.

`strategy_candidate_available=false`.

The exact package-manager install declared in GitHub Actions is CI dependency
bootstrap after a later accepted push, not provider/data ingestion authority.
This packet itself performs no network operation.
