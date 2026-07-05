# Fixed Agent Endpoints

Date: 2026-07-04
Owner: `Quant-Dispatcher`

## Codex Threads

Codex threads are created fresh per fixed role/project lane and pinned in the Codex app. Cross-thread sends must be prompt-only: do not pass model or thinking overrides to existing Codex threads.

| Role | Project | Thread title | Thread id |
|---|---|---|---|
| `Codex-Dev` | `A_Share_Monitor` | `Codex-Dev | A_Share_Monitor | TASK-021 Root Cause` | `019f2a5a-8b4b-76b3-b838-abc6b54e4992` |
| `Codex-Dev` | `US_Stock_Monitor` | `Codex-Dev | US_Stock_Monitor | TASK-023-024 Blockers` | `019f2a5a-8f92-7672-bbff-db71694e8676` |
| `Codex-Dev` | `market_data` | `Codex-Dev | market_data | Registry Readiness Tasks` | `019f2957-de0a-7721-ade9-1abfef298127` |
| `Codex-Dev` | `strategy_work` | `Codex-Dev | strategy_work | DATA_STRATEGY_BATCH_R5_20260705` | `019f30c3-247e-7f43-af60-96164539a183` |
| `Codex-Audit` | `quant-proj` | `Codex-Audit | quant-proj | Dispatcher Execution Test` | `019f2913-528a-7d22-bd0b-589f0750e09f` |

Retired endpoints:

| Role | Project | Thread title | Thread id | Reason |
|---|---|---|---|---|
| `Codex-Dev` | `A_Share_Monitor` | `Codex-Dev | A_Share_Monitor | TASK-001 A11 Acceptance` | `019f2911-ef0c-7053-aa77-a3b0bf0b05de` | Entered `systemError` before executing `TASK-021`; retained as historical evidence only. |
| `Codex-Dev` | `US_Stock_Monitor` | `Codex-Dev | US_Stock_Monitor | TASK-002 Strategy Acceptance` | `019f2913-0031-7513-af16-017b8f990f83` | Entered `systemError` before executing `TASK-023` / `TASK-024`; retained as historical evidence only. |

## Reasonix Fixed Sessions

All Reasonix dispatch uses:

- model: `deepseek-v4-pro`
- effort: `high`
- session policy: `runbooks/reasonix_sessions.md`

| Role | Session name | Prompt |
|---|---|---|
| `Reasonix-DB` | `quant-reasonix-db` | `prompts/reasonix_db_maintainer.md` |
| `Reasonix-Strategy` | `quant-reasonix-strategy` | `prompts/reasonix_strategy_researcher.md` |
| `Reasonix-Advisory` | `quant-reasonix-advisory` | `prompts/reasonix_advisory_review.md` |

Use old mixed Reasonix sessions only as reference, never as automatic dispatch endpoints.

Dispatch format:

- use fixed persistent sessions by default;
- send short `DISPATCH_TASK` envelopes that reference the task packet and source refs;
- use Reasonix compact as the default long-session control;
- request manual `SESSION_SUMMARY` only for audit, handoff, or fresh-session restart;
- start a fresh fixed session only when role drift or context bloat makes the old one unsafe.
