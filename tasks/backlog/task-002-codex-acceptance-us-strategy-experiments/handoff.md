# Handoff: TASK-002 CODEX_ACCEPTANCE_US_STRATEGY_EXPERIMENTS

To: `Codex-Dev`
Project root: `/Users/rongyuxu/Desktop/US_Stock_Monitor`
Mode: code/test acceptance only

## How To Send

Open a Codex-Dev thread rooted at the US project:

```bash
codex -C /Users/rongyuxu/Desktop/US_Stock_Monitor
```

Then paste this handoff content. Do not pass model/thinking overrides to an existing Codex thread.

## Request

Lightly accept the committed US strategy experiments as research-only diagnostics.

Current controller refresh:

- branch: `codex/duckdb-provider`
- commit: `36aff30da581d01d24ffba89c6bb1e0515337bec`
- tree: `0fcf4a464116e748e5514ab9c2dbcc899ecc2f74`
- working tree: clean

Run:

```bash
python scripts/agent_safety_check.py
pytest -q tests/test_us_strategy_experiments.py
pytest -q
python -m usq smoke
git diff --check
```

Return `CODEX_ACCEPTANCE_US_STRATEGY_EXPERIMENTS` with status, accepted level, remaining blockers, and boundary statement.

## Forbidden

- No ticket emission.
- No recommendation.
- No broker/order/paper/live/auto execution.
- No production gate relaxation.
- No readiness upgrade.
- No `.env` or secrets.

