# TASK-032 US Qualitative Feedback Bootstrap Schema

Date: 2026-07-04
Role: `Reasonix-Strategy`
Model: `deepseek-v4-pro`
Effort: `high`
Mode: `L0_RESEARCH_DIAGNOSTIC`
Transcript: `reports/workspace_dispatch/reasonix_strategy_task_032_20260704.jsonl`
Status: `RESEARCH_DRAFT_NORMALIZED`

## Scope

This report designs a non-trading qualitative feedback bootstrap schema for `US_Stock_Monitor`.

The schema is intended to help unblock future research around:

- `feedback_context.actionable_feedback=false`;
- `evidence_reentry.status=EVIDENCE_GAP_PERSISTING`;
- `ticket_eligibility_candidate=false`;
- `eligibility_candidate=null`;
- `ticket_emitted=false`.

It does not make feedback actionable by itself and does not authorize recommendations, tickets, broker/order paths, paper/live trading, or source-project writes.

## Allowed Schema Fields

| Field | Type | Purpose |
|---|---|---|
| `user_watch_reason` | string | why a user is watching a ticker or theme |
| `user_rejected_reason` | string | why a user rejected a ticker or theme from research follow-up |
| `sector_preference` | enum/string | sector preference signal for future research grouping |
| `risk_concern` | enum/string | user-stated non-execution risk concern |
| `time_horizon_preference` | enum/string | preferred research horizon |
| `data_quality_concern` | boolean/string | user concern about data reliability |
| `wants_more_evidence` | boolean | user requests more evidence before any later review |

Recommended free-text fields should have length limits and should be treated as research metadata only.

## Forbidden Fields

The schema must reject or omit fields that imply trading, execution, allocation, or advice:

- `buy_now`
- `sell_now`
- `execute`
- `position_size`
- `target_weight`
- `entry_price`
- `broker_id`
- `order_type`
- `allocation_pct`
- `trade_plan`

Free-text values should also be scanned for explicit order or recommendation commands before any later source-project integration.

## US-10 / US-11 Backlog Mapping

Potential research-only mapping:

- `US-10` earnings sentiment overlay:
  - `user_watch_reason`
  - `user_rejected_reason`
  - `wants_more_evidence`
- `US-11` sector rotation quality scoring:
  - `sector_preference`
  - `risk_concern`
  - `time_horizon_preference`

This mapping is hypothesis-level only. It may support future experiment design, but it must not directly set `actionable_feedback=true`, create an eligibility candidate, or emit a ticket.

## Why This Cannot Become Recommendation Authorization

The schema is metadata-only and does not encode:

- side;
- order intent;
- execution instruction;
- entry price;
- target weight;
- position size;
- allocation;
- broker route;
- ticket approval.

Any derived signal must remain disabled by default until a future Codex-Dev implementation, validation, Human-Gate review where needed, Codex-Audit review, and external-audit review where appropriate.

## Required Tests For Future Codex-Dev Work

If this schema is later implemented in `US_Stock_Monitor`, tests should prove:

- only allowed fields are accepted;
- forbidden field names are rejected;
- forbidden trading/advice terms in free text are blocked or quarantined;
- reads from the schema do not set `ticket_emitted=true`;
- reads from the schema do not set `actionable_feedback=true` by themselves;
- reads from the schema do not create `eligibility_candidate`;
- no broker/order/paper/live/auto flags can be set;
- any derived qualitative signal is disabled by default behind a research-only feature flag.

## Reasonix Draft Normalization

The raw Reasonix draft included a suggested `HG-EXEC-TASK-032-*` naming pattern and a mislabeled next Codex task reference. Quant-Dispatcher normalizes this as follows:

- `TASK-032` is L0 research/schema draft only and does not require an `HG-EXEC-TASK-*` record.
- A future source-project implementation task may require Codex-Dev validation.
- Any future DB write, network ingest, readiness change, registry activation, or ticket-gate entry would require a new scoped task and, for L1-L4 execution, a unique pre-execution `HG-EXEC-TASK-*`.
- The next source-project implementation task should not reuse `TASK-033`, which is reserved for final publication metadata standards in `quant-proj`.

## Status

`RESEARCH_DRAFT_NORMALIZED`

Ready to hand to `US_Stock_Monitor` Codex-Dev as a future implementation or contract-review input, but not itself an accepted source-project change.

## Non-Authorization

This schema draft does not authorize recommendations, buy/sell advice, HITL ticket emission, broker APIs, order routing, order submission, auto execution, paper trading, live trading, trade plans, entry prices, target weights, position sizing, allocation, DB writes, network ingest, registry activation, readiness changes, raw-data migration, `.env` access, key output, or secret handling.
