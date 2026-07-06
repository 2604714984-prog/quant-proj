# Windows WSL2 Registry Refresh

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-07T00:42:00+08:00
Status: REGISTRY_REFRESHED_FOR_WSL2

## Scope

This refresh updates `registry/projects.yaml` from the old macOS point-in-time
snapshot to the current Windows + WSL2 workspace state.

No source-project implementation files were modified. No raw databases, parquet
caches, SQLite files, logs, outputs, `.env`, keys, tokens, credentials, or
secret files were read, copied, moved, or committed.

## Current Workspace

| Repo | Branch | HEAD | Tree | Status |
|---|---|---:|---:|---|
| `quant-proj` | `main` | `4f3d0dea6bab26bdc7ab44ea1f5f8d8d0209015d` | `5d5858df67aa47a493b8f25a9198eeb39373dbb5` | clean |
| `A_Share_Monitor` | `codex/harden-a-share-research-pipeline` | `dd3089e2a9c1693ea0571db37c185d6584f1bc14` | `d6d35676e5753ae42dab7fa08459fb9c3e9d4810` | clean |
| `US_Stock_Monitor` | `main` | `831ef21eda20ecf971bef9ab2f3487b8e96e1001` | `fe5442c0846a8fb5b432ed4a0fe28d143f8c234f` | clean |
| `market_data` | `main` | `ff24166479638b0f35e1cd7a8d0f1d01cdafb495` | `03ff42577d23784924511efcc7ccc7f9f3217fc4` | clean |
| `strategy_work` | `main` | `2bfbe33e654e7ceb76117ab7b156ff44f2d979be` | `6695c18a446743c2d21d1fedd6788c0a47ac7f43` | clean |

## Worktree Result

Only the primary WSL2 worktree was observed for each source project:

- `/home/rongyu/workspace/A_Share_Monitor`
- `/home/rongyu/workspace/US_Stock_Monitor`
- `/home/rongyu/workspace/market_data`
- `/home/rongyu/workspace/strategy_work`

Old macOS active-dispatch worktrees under
`/Users/rongyuxu/.codex/worktrees/...` are not current WSL2 state and were set
to `null` in the refreshed registry.

## Thread Result

Current dispatcher thread:

```text
019f3830-4b44-7a83-944d-247a0d4dc169
```

Old fixed downstream thread ids from the Mac-side controller records were not
visible on the current local Codex host. Read/send smoke checks for the old
`market_data` and `A_Share_Monitor` ids returned `No Codex thread found`.

Interpretation:

- The old `market_data` approval-blocked thread is not actionable from this
  host.
- Future prompt-only downstream dispatch requires new WSL2-visible downstream
  threads or a fallback final-answer callback envelope.

## Notable State

- `A_Share_Monitor` has advanced beyond R13C to WSL2 R14/data-chain evidence.
- `strategy_work` has advanced to the WSL2 data-chain repair memo sync.
- `US_Stock_Monitor` has no WSL2 DuckDB observed at
  `/home/rongyu/workspace/US_Stock_Monitor/data/local_market/us_stock_market.duckdb`.
- `market_data` is clean on `main`, but no live downstream thread state is
  available.

## Validation

Minimum validation performed:

- `registry/projects.yaml` parses as YAML.
- `registry/agents.yaml` parses as YAML.
- Forbidden-artifact scan in `quant-proj` found no `.env`, `.duckdb`,
  `.sqlite`, `.parquet`, `.zip`, or `.tar.gz` files.
- `git diff --check` passed after the registry/report updates.

## Boundary

This refresh is controller bookkeeping only. It does not authorize
recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket emission, eligibility
candidates, product-route activation, production readiness,
broker/order/paper/live/auto behavior, DB writes, network ingest, schema
migration, bulk ingest, readiness changes, registry activation,
provider-data persistence, raw-data migration, `.env` reads, key output, or
secret handling.
