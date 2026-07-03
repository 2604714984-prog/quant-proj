# Task Spec: A-STRAT-1 GAP Fix Re-Acceptance Follow-Up

Task ID: `a-strat-1-gap-reacceptance-followup-20260704`
Created by: `Quant-Dispatcher`
Created at: 2026-07-04T01:01:43+08:00
Status: `ASSIGNED_DRY_RUN`
Primary downstream agent: `reasonix_strategy_researcher`
Target project: `A_Share_Monitor`
Execution mode: dry-run dispatch packet only

## Goal

Prepare a research-only follow-up checklist for re-accepting A-STRAT-1 GAP fixes after the A11/A-STRAT research work changes.

This task exists to prove that Quant-Dispatcher can convert a ChatGPT task into a bounded downstream task packet. It does not execute the downstream work.

## Scope

Allowed:

- Review repo-relative report names, stage handles, and already-published task context.
- Draft re-acceptance questions for Reasonix-Strategy.
- Identify evidence gaps that Codex-Dev would need to validate later.
- Keep all outputs under this task packet or a future workspace dispatch report.

Forbidden:

- Editing `/Users/rongyuxu/Desktop/A_Share_Monitor`.
- Emitting buy/sell advice.
- Creating recommendation tickets.
- Claiming observation or recommendation readiness.
- Changing strategy configs in source repos.
- Running broker/order/paper/live/auto-execution paths.
- Reading `.env` or secrets.
- Moving raw data or DB files.

## Inputs

- External audit conclusion: `ACCEPT_WITH_FIXES`.
- Current registry snapshot: `registry/projects.yaml`.
- Agent rules: `registry/agents.yaml`.
- Dispatcher runbook: `runbooks/task_dispatch.md`.
- Human-Gate runbook: `runbooks/human_gate.md`.

## Expected Output If Executed Later

Reasonix-Strategy should produce a research draft containing:

- A-STRAT-1 GAP re-acceptance questions.
- Evidence required before Codex-Dev implementation.
- Risks of overfitting or data-readiness overclaim.
- Clear statement that no recommendation, broker/order, paper/live, or source-promotion approval is granted.

## Human-Gate

Not required for this dry-run dispatch packet because it does not execute source changes, DB writes, readiness changes, strategy promotion, or migration.

Any later execution that promotes config into `A_Share_Monitor`, changes tests/code, changes readiness, or opens a new audited stage requires a separate task and the appropriate Human-Gate or Codex-Dev validation.

