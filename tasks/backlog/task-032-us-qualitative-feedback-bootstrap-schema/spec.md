# TASK-032 US Qualitative Feedback Bootstrap Schema

Status: `ASSIGNED`
Target project: `US_Stock_Monitor`
Agent: `Reasonix-Strategy` first, then `Codex-Dev` if implementation is needed
Priority: `P0`
Permission: `L0_RESEARCH_DIAGNOSTIC`

## Goal

Design a non-trading feedback schema for collecting user feedback on research/tickets when no real fill exists, without authorizing recommendations.

## Allowed Fields

- `user_watch_reason`
- `user_rejected_reason`
- `sector_preference`
- `risk_concern`
- `time_horizon_preference`
- `data_quality_concern`
- `wants_more_evidence`

## Forbidden Fields

- buy now;
- sell now;
- execute;
- position size;
- target weight;
- entry price;
- broker/order.

## Must Include

- how the schema maps into US-10/US-11 research backlog;
- why it cannot become recommendation authorization;
- required tests.

## Output

- `reports/deepseek_research/task_032_us_qualitative_feedback_bootstrap_schema.md`
- `reports/deepseek_research/task_032_us_qualitative_feedback_bootstrap_schema.json`

## Forbidden

No recommendation, ticket, broker/order/live, DB write, network ingest, registry activation, readiness change, `.env` access, or secret handling.
