# Handoff: TASK-001 CODEX_ACCEPTANCE_A11_RESEARCH_RUNNER

To: `Codex-Dev`
Project root: `/Users/rongyuxu/Desktop/A_Share_Monitor`
Mode: code/test acceptance only

## How To Send

Open a Codex-Dev thread rooted at the A-share project:

```bash
codex -C /Users/rongyuxu/Desktop/A_Share_Monitor
```

Then paste this handoff content. Do not pass model/thinking overrides to an existing Codex thread.

## Request

Lightly accept the committed A11 research runner as research-only strategy experiment code.

Current controller refresh:

- branch: `codex/harden-a-share-research-pipeline`
- commit: `1537e9958fdd11a36f6392314228abd02a26507a`
- tree: `c30fa5401789005ff27ca7658fbe5ddf382f4df5`
- working tree: clean

Run:

```bash
python scripts/agent_safety_check.py
pytest -q tests/test_a11_strategy_research_modules.py
python -m qta research a11-experiments
git diff --check
```

Return `CODEX_ACCEPTANCE_A11_RESEARCH_RUNNER` with status, accepted level, candidate count, blocker counts, and boundary statement.

## Forbidden

- No recommendation ticket.
- No buy/sell advice.
- No broker/order/paper/live/auto execution.
- No readiness upgrade.
- No raw DB migration.
- No `.env` or secrets.

