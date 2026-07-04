# Post-Acceptance Accepted Next Batch P1 Dispatch

Date: 2026-07-04
Owner: `Quant-Dispatcher`
Batch: `post_acceptance_accepted_next_batch_20260704`
Status: `P1_DISPATCH_PREPARED`

## Preconditions

P0 is complete and recorded in `reports/workspace_dispatch/post_acceptance_next_batch_p0_results_20260704.md`.

The controller P0 closeout commit is `b6a206a9e17834029f5d593c16a275e5ffcc7112`, tree `816e8f930f55bed903f50287ee987339e3f2a45d`.

## P1 Dispatch Plan

| Task | Destination | Agent | Mode | How to send |
|---|---|---|---|---|
| `TASK-034` A11 candidate safety regression tests | `A_Share_Monitor` thread `019f2a5a-8b4b-76b3-b838-abc6b54e4992` | Codex-Dev | `L0_RESEARCH_DIAGNOSTIC` | Prompt-only `codex_app.send_message_to_thread`; no model/thinking override |
| `TASK-035` US eligibility gate object contract | `US_Stock_Monitor` thread `019f2a5a-8f92-7672-bbff-db71694e8676` | Codex-Dev | `L0_RESEARCH_DIAGNOSTIC` | Prompt-only `codex_app.send_message_to_thread`; no model/thinking override |
| `TASK-036` A-share L1 to Phase3 evidence upgrade criteria | fixed `Reasonix-DB`, then optional A-share Codex-Dev review | Reasonix-DB + Codex-Dev | `L0_RESEARCH_DIAGNOSTIC` | `reasonix` with `deepseek-v4-pro --effort high`; transcript retained |
| `TASK-037` US crosscheck alternative source decision | fixed `Reasonix-DB` | Reasonix-DB | `L0_RESEARCH_DIAGNOSTIC` | `reasonix` with `deepseek-v4-pro --effort high`; transcript retained |
| `TASK-038` Reasonix transcript retention policy | current `quant-proj` controller workspace | Quant-Dispatcher | `L0_RESEARCH_DIAGNOSTIC` | Local controller docs only |

## Holds Preserved

- A11 ticket emission remains held because eligible ticket candidates remain `0`.
- US ticket refresh remains held because no eligibility candidate exists.
- A-share DB write/network repair requires a future unique pre-execution `HG-EXEC-TASK-*`.
- US metadata bootstrap and expansion rerun require a future unique pre-execution `HG-EXEC-TASK-*`.
- market_data product-route replacement and production recommendation readiness remain out of scope.

## Boundary

This P1 dispatch does not authorize recommendation, buy/sell advice, HITL ticket emission, broker APIs, order routing, order submission, auto execution, paper trading, live trading, trade plans, entry prices, target weights, position sizing, allocation, DB writes, network ingest, schema migration, registry activation, readiness upgrade, raw-data migration, `.env` reads, key output, or secret-handling changes.
