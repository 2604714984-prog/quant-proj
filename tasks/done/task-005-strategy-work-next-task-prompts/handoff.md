# Handoff: TASK-005 STRATEGY_WORK_NEXT_TASK_PROMPTS

To: `Reasonix-Strategy`
Mode: research roadmap and prompt draft only
Target project: `/Users/rongyuxu/Desktop/strategy_work`

## How To Send

Use Reasonix-Strategy with the workspace strategy-researcher system prompt:

```bash
cd "/Users/rongyuxu/Desktop/quant proj"
reasonix run --effort high --budget 0.50 \
  -m deepseek-v4-pro \
  --transcript reports/workspace_dispatch/reasonix_strategy_task_005_20260704.jsonl \
  --system "$(cat prompts/reasonix_strategy_researcher.md)" \
  "$(cat tasks/backlog/task-005-strategy-work-next-task-prompts/handoff.md)"
```

This command is the send method. Quant-Dispatcher has not executed it.

Fixed Reasonix settings: `deepseek-v4-pro`, effort `high`.

## Request

Create `STRATEGY_WORK_NEXT_TASK_PROMPTS` as a research-only roadmap draft.

Include:

- A-share next research prompts;
- US next research prompts;
- blocked items;
- Codex-Dev implementation candidates;
- tasks requiring Human-Gate;
- tasks requiring later Codex-Audit or ChatGPT external audit.

Use the current boundary:

- `strategy_work` is research-only and non-actionable;
- it is not a product gate;
- it does not emit HITL tickets;
- it does not authorize recommendations;
- it does not connect to brokers;
- it does not execute trades;
- it does not enable paper or live trading.

## Forbidden

- Do not edit files.
- Do not promote configs into source repos.
- Do not emit recommendation tickets.
- Do not output buy/sell advice.
- Do not claim readiness or product gate approval.
