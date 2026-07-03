# Registry Refresh Snapshot

Date: 2026-07-04T01:01:43+08:00
Workspace: `/Users/rongyuxu/Desktop/quant proj`
Mode: read-only source-project inspection

## Purpose

This snapshot supports the external-audit fix response for `MED-001`: registry facts must be refreshed before routine dispatch and must not be treated as permanent source of truth.

## Source Project States

| Project | Branch | Commit | Tree | Working Tree | Nearest Tag |
|---|---|---|---|---|---|
| `A_Share_Monitor` | `codex/harden-a-share-research-pipeline` | `12c6115c1c6d3a19b3cd359ed5863fcabf7c9b34` | `9751a6d3a1a61b06cc851d1d738c29583098c716` | dirty | `stage-a10-external-audit-packet-20260703-7-g12c6115c1c6d` |
| `US_Stock_Monitor` | `codex/duckdb-provider` | `fedd70e68ab29fbfd77c0a07b5b2df6525c2523a` | `b3f7bbad381f78a6b51f06bc899534573f0ef7d2` | dirty | `phase-us13-audit-r1-3-gfedd70e68ab2` |
| `market_data` | `main` | `ff24166479638b0f35e1cd7a8d0f1d01cdafb495` | `03ff42577d23784924511efcc7ccc7f9f3217fc4` | clean | `db-2-high001-closed-external-audit-20260703-2-gff2416647963` |
| `strategy_work` | `main` | `a67404900f424bdf918d3254540653446bda12ad` | `6b1f826123d3a9d078dfe41abbbd89634b140b24` | clean | `a67404900f42` |

## Dirty File Summary

`A_Share_Monitor`:

- `M config/research/a11_strategy_experiments.yaml`
- `M qta/research/a11_experiment_runner.py`
- `M qta/research/a11_factor_library.py`
- `M qta/research/a11_strategy_filters.py`
- `M tests/test_a11_strategy_research_modules.py`

`US_Stock_Monitor`:

- `M usq/cli.py`
- `?? tests/test_us_strategy_experiments.py`
- `?? usq/research/us_strategy_experiments/`

`market_data`: clean.

`strategy_work`: clean.

## Boundary

No source-project files were edited. No `.env`, secrets, raw DB, parquet, SQLite, raw payload, broker/order, paper-trading, live-trading, or auto-execution artifacts were read or copied.

