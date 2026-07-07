# Windows WSL2 RTX 5090 400W Power Cap Revocation - 20260707

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-07T16:32:56+08:00
Source: user directive to revoke the 400W limit and continue running R17.

## Decision

The prior standing RTX 5090 400W cap is revoked for R17 continuation and future research GPU diagnostics unless the user later reinstates a cap.

Downstream GPU work may proceed under the host/driver default power policy. The current observed RTX 5090 driver state is:

- `power.limit=600.00W`
- `power.default_limit=600.00W`
- `power.max_limit=600.00W`

## Required Reporting

Future GPU callbacks must still report observed GPU power policy and telemetry when feasible:

- observed `power.limit`;
- observed `power.draw` if available;
- whether any manual power-limit change was attempted;
- whether sustained GPU work was executed.

## Superseded Stop Conditions

The following prior stop conditions are superseded for R17 and future GPU research unless reinstated by the user:

- `GPU_POWER_LIMIT_ABOVE_400W_WITHOUT_AUTH`
- `GPU_POWER_CAP_REQUIRED_BUT_NOT_VERIFIABLE`
- `HIGHER_GPU_POWER_REQUESTED_WITHOUT_AUTH`

## Boundary

This revocation is power-policy only. It does not authorize local LLM/Qwen deployment, recommendation/advice, ticket creation, eligibility candidate creation, strategy candidate promotion, product-route activation, production readiness, broker/order/paper/live/auto, provider/network fetch, DB/cache write, schema/readiness/registry change, raw-data migration, or secret access/output.
