# Fixed Agent Endpoints

Date: 2026-07-04
Owner: `Quant-Dispatcher`

## Codex Threads

Codex threads are created fresh per fixed role/project lane and pinned in the Codex app. Cross-thread sends must be prompt-only: do not pass model or thinking overrides to existing Codex threads.

| Role | Project | Thread title | Thread id |
|---|---|---|---|
| `Codex-Dev` | `A_Share_Monitor` | `Codex-Dev | A_Share_Monitor | TASK-001 A11 Acceptance` | `019f2911-ef0c-7053-aa77-a3b0bf0b05de` |
| `Codex-Dev` | `US_Stock_Monitor` | `Codex-Dev | US_Stock_Monitor | TASK-002 Strategy Acceptance` | `019f2913-0031-7513-af16-017b8f990f83` |
| `Codex-Audit` | `quant-proj` | `Codex-Audit | quant-proj | Dispatcher Execution Test` | `019f2913-528a-7d22-bd0b-589f0750e09f` |

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
