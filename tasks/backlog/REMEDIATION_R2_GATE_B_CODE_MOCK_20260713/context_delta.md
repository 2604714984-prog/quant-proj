# Context delta

Gate A is internally green, but the prior external verdict remains
`NOT_PASSED_REWORK_REQUIRED` until a targeted external reviewer returns a new
verdict. The accepted private ingestion baseline implements only DB-603 through
DB-607. The central publisher and canonical activation path remain absent and
disabled.

Implement the DB-608 through DB-612 code/mock precondition from clean
`central-data-ingestion main` commit
`287416f79cd1fcb1c066f25fa7bbaedc574b0ce9`, tree
`c2a62d079bcb08b04b2425c7160bf9ca8344038a`.

An unaccepted five-commit candidate exists at
`0bc1007235a96ab2e4c0e92700a999930761e73a`, tree
`d14939354fda31adfedec22febd29b37cb360285`. It contains Replay canary
observations. Its status is `UNACCEPTED_SUPERSEDED_DESIGN_INPUT`. Treat it
only as read-only architectural/negative-test reference under
`candidate_input.json`; do not cherry-pick it or reuse its Replay HG, consumed
marker, canary, network observation or authorization claim.

The current central DuckDB file identity is SHA-256
`e1826d04191e5014ddcbb12f9d96acdded0ff54b58c90068c9c4001160e074b9`,
1,001,664,512 bytes, mode `0600`. It differs from the consumed Wave 0
baseline. This task must reject the real path and use only test-owned temporary
files. It does not authorize a new backup, HG record, database write, provider
call, token read, timer deployment or timer activation.

Implementation code must be incapable of generating or self-approving
`HG_EXEC_GRANTED`. There is no direct-library publish bypass, public
`lock_held` bypass or caller assertion that substitutes for the accepted
queue, independent activation manifest, future exact HG and held-descriptor
validation of every artifact.

The required output is implementation code, focused tests, inert unit-file
templates and a mock five-symbol/full-calendar-month canary harness. A green
result may be
reported only as `GATE_B_CODE_MOCK_PRECONDITION_GREEN`. It cannot complete
operational DB-612, pass Gate B, activate canonical views, or unlock DB-613 and
later work.

Independent packet review also found that the accepted baseline workflow
installs pinned pytest/Ruff and then runs `pip install --no-deps -e .`.
Publisher implementation therefore cannot import DuckDB until package metadata
and clean-runner CI explicitly install the same accepted runtime version. The
implementation must pin `duckdb==1.5.4` in `pyproject.toml`, install that
exact version in the workflow before the no-deps editable install, assert the
imported runtime version in CI, run the full suite, and pass the local CI-parity
semantic gate. This dependency hardening does not authorize a provider/data
network call.
