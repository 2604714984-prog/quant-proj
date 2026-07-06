# Windows WSL2 Downstream Threads

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-07T01:13:00+08:00
Status: DOWNSTREAM_THREADS_READY

## User Directive

The user directed Quant-Dispatcher to directly create new downstream Codex
threads for the Windows WSL2 workspace.

## Active Dispatcher

```text
019f3830-4b44-7a83-944d-247a0d4dc169
```

## New Downstream Threads

| Project | Thread id | Role | Acknowledgement |
|---|---|---|---|
| `A_Share_Monitor` | `019f387b-617e-7273-b539-161216ae3002` | A-share data, features, and strategy execution | `CODEX_ACCEPTANCE / A_SHARE_MONITOR_WSL2_DOWNSTREAM_THREAD_READY` |
| `US_Stock_Monitor` | `019f387b-a161-7ad0-8678-f03a099612ba` | US stock data, metadata, and strategy execution | `CODEX_ACCEPTANCE / US_STOCK_MONITOR_WSL2_DOWNSTREAM_THREAD_READY` |
| `market_data` | `019f387b-e763-7c01-ae3d-6be552cdb6dc` | shared data registry, data-clear contract, gate regression | `CODEX_ACCEPTANCE / MARKET_DATA_WSL2_DOWNSTREAM_THREAD_READY` |
| `strategy_work` | `019f3881-5293-74a1-8535-814bd83c8681` | strategy research summaries, configs, archives, memos | `CODEX_ACCEPTANCE / STRATEGY_WORK_WSL2_DOWNSTREAM_THREAD_READY` |

## Callback Rule

All four downstream threads acknowledged the callback target:

```text
019f3830-4b44-7a83-944d-247a0d4dc169
```

Each future downstream completion must return a prompt-only callback containing:

- final status: `CODEX_ACCEPTANCE`, `DATA_REPORT`, `STRATEGY_REPORT`, `BLOCKED`, or equivalent;
- commit/tree when files changed;
- branch/push status;
- artifacts;
- validation;
- residual blockers;
- explicit boundary statement.

If direct thread messaging is unavailable, the downstream final answer must
include the callback envelope.

## Initialization Scope

The initialization prompts requested no source edits, no commits, no pushes, and
no large commands. Each acknowledgement reported no file changes and no commits.

## Boundary

This thread creation record does not authorize recommendation/advice,
`PENDING_HUMAN_REVIEW`, ticket emission, eligibility candidates, product-route
activation, production readiness, broker/order/paper/live/auto behavior, DB
writes, network ingest, schema migration, bulk ingest, readiness changes,
registry activation, provider-data persistence, raw-data migration, `.env`
reads, key output, or secret handling.
