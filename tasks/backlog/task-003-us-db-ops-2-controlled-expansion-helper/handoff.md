# Handoff: TASK-003 US_DB_OPS_2_CONTROLLED_EXPANSION_HELPER

To: `Codex-Dev`
Project root: `/Users/rongyuxu/Desktop/US_Stock_Monitor`
Mode: implementation rewrite only; no real ingest

## How To Send

Open a Codex-Dev thread rooted at the US project:

```bash
codex -C /Users/rongyuxu/Desktop/US_Stock_Monitor
```

Then paste this handoff content. Do not pass model/thinking overrides to an existing Codex thread.

## Request

Rewrite the US expansion helper into a controlled DB ops helper:

```text
scripts/expand_us_300.py -> scripts/db_ops/expand_us_universe.py
```

Add:

- `--allow-network`;
- `--read-only`;
- duplicate detection;
- `snapshot_id` validation;
- symbol validation against `canonical_symbol_metadata`;
- tests or smoke coverage appropriate to the change.

Do not run real network ingest or write DuckDB in this task unless a separate Human-Gate record exists.

## Forbidden

- No `.env` or secrets.
- No key output.
- No default network.
- No default DB write.
- No product route activation.
- No HITL readiness claim.
- No recommendation readiness claim.
- No recommendation/HITL/ticket/broker/order/live imports.

Return `CODEX_ACCEPTANCE_US_DB_OPS_2`.

