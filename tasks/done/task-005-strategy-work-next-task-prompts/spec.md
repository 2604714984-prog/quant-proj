# TASK-005: STRATEGY_WORK_NEXT_TASK_PROMPTS

Task ID: `TASK-005`
Status: `ASSIGNED_READY_TO_SEND`
Priority: `P1`
Primary assignee: `Reasonix-Strategy`
Secondary assignee after draft: `Codex-Dev`
Target project: `strategy_work`
Target root: `/Users/rongyuxu/Desktop/strategy_work`
Dispatcher: `Quant-Dispatcher`
Created at: 2026-07-04T01:25:34+08:00

## Goal

Maintain the next research roadmap and prompt set for strategy work without promoting anything into source repos.

Current refreshed source state:

- branch: `main`
- commit: `a67404900f424bdf918d3254540653446bda12ad`
- tree: `6b1f826123d3a9d078dfe41abbbd89634b140b24`
- working tree: clean

## Assignment

Send to `Reasonix-Strategy` first for a research draft.

If the draft is accepted, create a later Codex-Dev task to commit docs/configs in `strategy_work`. Do not let Reasonix promote files directly into A-share or US source repos.

## Expected Output

```text
STRATEGY_WORK_NEXT_TASK_PROMPTS

sections:
- A-share next research prompts
- US next research prompts
- blocked items
- Codex-Dev implementation candidates
- tasks requiring Human-Gate
- tasks requiring later Codex-Audit or ChatGPT external audit
```

## Required Boundaries

- research-only;
- non-actionable;
- no recommendation tickets;
- no buy/sell advice;
- no broker/order/paper/live/auto execution;
- no source-repo promotion without Codex-Dev;
- no product gate claims.

## Human-Gate Rule

No Human-Gate is required for research prompt drafting.

Human-Gate is required before strategy promotion, readiness changes, ticket gates, or trading-adjacent behavior.

## Dispatcher Boundary

Quant-Dispatcher only created this packet. No source-project files were edited.

