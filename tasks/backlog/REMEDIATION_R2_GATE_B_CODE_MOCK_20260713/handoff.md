# Dispatcher handoff

Assign one Luna/medium Codex-Dev executor in a new isolated worktree created
from the exact accepted `central-data-ingestion main` source commit/tree in
`spec.md`.

The executor must implement and validate:

1. DB-608 `publish-one`: one OS writer lock, descriptor-bound and
   parent/leaf replacement-resistant inputs, an append-only accepted queue,
   accepted-batch identity,
   quarantine exclusion, strict schema and natural-key validation,
   idempotent batch ID, one transaction, deterministic rollback, and immutable
   historical version retention. No exported direct-library entry point or
   caller-provided `lock_held` assertion may bypass the CLI, queue, lock,
   manifest, authorization or descriptor checks.
2. DB-609 versioned canonical views: a partial, gapped, quarantined or
   unaccepted snapshot can never become active; activation in tests is atomic
   and preserves the prior version on failure.
3. DB-610 and DB-611 templates: collector and publisher services remain
   `ExecStart=/usr/bin/false`; no `systemctl`, user-unit installation,
   enablement or start is permitted. The publisher code has no token or network
   capability.
4. DB-612 mock harness only: exactly five synthetic symbols over every accepted
   session of one fixed full synthetic calendar month, wholly inside a
   test-owned temporary root, proving collect-contract
   input, quality acceptance, publish, canonical-view query, idempotent replay,
   forced rollback, and zero strategy imports. It is not a real canary.
5. Clean-runner dependency closure: declare exact runtime dependency
   `duckdb==1.5.4` in `pyproject.toml`; update
   `.github/workflows/ci.yml` so the pinned install step installs
   `duckdb==1.5.4 pytest==9.0.2 ruff==0.14.10` before the existing
   `pip install --no-deps -e .`; preserve pinned GitHub Action SHAs. The
   workflow must then import DuckDB and assert
   `duckdb.__version__ == "1.5.4"`, and run the full tests, Ruff, compile and
   boundary scan from a clean checkout. Do not rely on the developer machine's
   preinstalled DuckDB.

Required security tests include parent and leaf symlinks, hardlinks/multiple
links, descriptor replacement/TOCTOU, lock contention, path escape, central-path
rejection, batch forgery, duplicate and conflicting natural keys, quarantine
exclusion, rollback at every mutation boundary, partial snapshot activation
rejection, forged/absent accepted-queue receipt, forged/absent independent
activation manifest, self-authored `HG_EXEC_GRANTED`, direct library calls,
`lock_held=True` bypass attempts, and default dry-run
no-write/no-network/no-token behavior. Every queue receipt, batch, provenance,
validation receipt, activation manifest, HG record, database target and output
identity used for a decision must be read/hash/parsed from the same held
descriptor, with post-operation identity checks.

The existing candidate recorded in `candidate_input.json` is
`UNACCEPTED_SUPERSEDED_DESIGN_INPUT`, not a source baseline or acceptance
result. Do not cherry-pick its branch/commits. Replay HG records, consumed
markers, canary result files, observations and authorization claims must be
absent from the implementation scope. Selective architectural skeletons or
negative-test ideas may be reimplemented only after clean-room review and new
mock tests.

Return `LUNA_EXECUTION_COMPLETE` only after all exact gate commands pass and
an automated-gate manifest is created. The callback must report exact
branch/base/commit/tree, file hashes, test counts, inert timer proof, default
dry-run proof, zero real-data/network/token/central-write evidence and
`GATE_B_CODE_MOCK_PRECONDITION_GREEN`. Then route a fresh independent
Luna/high read-only acceptance. Do not claim operational Gate B or DB-612
completion and do not commit/push before that acceptance.

The executor may edit `pyproject.toml` and `.github/workflows/ci.yml` only
for this exact dependency/CI closure. Manual provider/data network calls remain
forbidden. A later post-acceptance push may let ordinary GitHub Actions install
the pinned build/test dependencies; that CI infrastructure behavior is not a
provider-ingestion authorization.
