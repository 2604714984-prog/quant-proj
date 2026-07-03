# Reasonix Existing Sessions Assessment

Date: 2026-07-04
Role: `Quant-Dispatcher`
Mode: read-only session routing assessment

## Local Sessions Observed

Reasonix has saved sessions under `~/.reasonix/sessions/`.

Observed useful entries:

| Session | Observed summary | Dispatcher assessment |
|---|---|---|
| `code-rongyuxu` | Large active mixed session; includes market-data maintenance, A-share/US project inspection, strategy work, source edits, reports, commits, and pushed work | Do not use as a clean fixed `Reasonix-DB` or `Reasonix-Strategy` endpoint. It can be used only for continuity/reference when the user explicitly wants the old mixed context. |
| `subagent-sub-2-202607030742` | A-share data-source alternatives research | Useful as reference context for data-source or crosscheck research, but not a fixed DB-maintenance role. |
| `subagent-sub-1-202607030711` | Scheduling/automation survey | Not a current dispatcher endpoint. |
| `code-rongyuxu__archive_202607030708` | Older broad project overview | Archive/reference only. |

## Decision

Do not directly reuse the existing mixed Reasonix sessions as the durable downstream agents for automated dispatch.

Reason:

- the active session has mixed DB, strategy, code-editing, commit, and project-survey context;
- it is not cleanly constrained to `Reasonix-DB`, `Reasonix-Strategy`, or `Reasonix-Advisory`;
- it has historical access patterns that are broader than the new controller-workspace rules;
- dispatcher tasks need predictable role boundaries and transcripts.

## Recommended Fixed Reasonix Endpoints

Create or use these fixed session names going forward:

| Role | Session name | Use |
|---|---|---|
| `Reasonix-DB` | `quant-reasonix-db` | Database diagnostics, schema/readiness review, manifest/SQL drafts, DB ops classification |
| `Reasonix-Strategy` | `quant-reasonix-strategy` | Strategy research drafts, factor hypotheses, blocker diagnosis, experiment design |
| `Reasonix-Advisory` | `quant-reasonix-advisory` | Read-only second review, test-gap review, overclaim review |

All fixed Reasonix endpoints use:

- model: `deepseek-v4-pro`
- effort: `high`

## How To Start Fixed Sessions

Reasonix-DB:

```bash
cd "/Users/rongyuxu/Desktop/quant proj"
reasonix chat \
  --session quant-reasonix-db \
  -m deepseek-v4-pro \
  --effort high \
  --budget 1 \
  --system "$(cat prompts/reasonix_db_maintainer.md)" \
  --transcript reports/workspace_dispatch/reasonix_db_session_20260704.jsonl
```

Reasonix-Strategy:

```bash
cd "/Users/rongyuxu/Desktop/quant proj"
reasonix chat \
  --session quant-reasonix-strategy \
  -m deepseek-v4-pro \
  --effort high \
  --budget 1 \
  --system "$(cat prompts/reasonix_strategy_researcher.md)" \
  --transcript reports/workspace_dispatch/reasonix_strategy_session_20260704.jsonl
```

Reasonix-Advisory:

```bash
cd "/Users/rongyuxu/Desktop/quant proj"
reasonix chat \
  --session quant-reasonix-advisory \
  -m deepseek-v4-pro \
  --effort high \
  --budget 1 \
  --system "$(cat prompts/reasonix_advisory_review.md)" \
  --transcript reports/workspace_dispatch/reasonix_advisory_session_20260704.jsonl
```

## If Reusing Old Sessions Anyway

Use this only with explicit user intent:

```bash
reasonix chat --session code-rongyuxu --resume
```

Before pasting any task, prepend a strict role reset:

```text
ROLE_RESET
You are acting only as <Reasonix-DB / Reasonix-Strategy / Reasonix-Advisory> for this task.
Follow the quant-proj role prompt.
Do not edit files unless explicitly allowed.
Do not read .env or secrets.
Do not emit recommendations, tickets, broker/order/paper/live instructions, or readiness changes.
```

This is still less safe than using a clean fixed session.

## Dispatcher Rule

Default route:

- fixed session names for all new dispatched Reasonix work;
- old sessions are reference-only unless the user explicitly asks to continue them;
- every dispatched task must still have a task packet and saved transcript path.
