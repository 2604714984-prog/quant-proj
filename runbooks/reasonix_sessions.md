# Reasonix Session Runbook

Use this when `Quant-Dispatcher` assigns work to `Reasonix-DB`, `Reasonix-Strategy`, or `Reasonix-Advisory`.

## Policy

Reasonix work should use fixed persistent sessions by default. This keeps role context stable and improves cache reuse, while avoiding the risk of one mixed mega-session becoming the automatic dispatch endpoint.

Use Reasonix's built-in compact behavior as the default way to control long-session context. Manual summaries are optional and should be used only when an audit packet, cross-agent handoff, or fresh-session restart needs a durable artifact.

| Role | Fixed session | Model | Effort | Prompt |
|---|---|---|---|---|
| `Reasonix-DB` | `quant-reasonix-db` | `deepseek-v4-pro` | `high` | `prompts/reasonix_db_maintainer.md` |
| `Reasonix-Strategy` | `quant-reasonix-strategy` | `deepseek-v4-pro` | `high` | `prompts/reasonix_strategy_researcher.md` |
| `Reasonix-Advisory` | `quant-reasonix-advisory` | `deepseek-v4-pro` | `high` | `prompts/reasonix_advisory_review.md` |

Old mixed sessions, especially `code-rongyuxu`, are reference-only unless the user explicitly asks to continue them.

## Start Or Resume

Reasonix-DB:

```bash
cd "/Users/rongyuxu/Desktop/quant proj"
reasonix chat \
  --session quant-reasonix-db \
  --resume \
  -m deepseek-v4-pro \
  --effort high \
  --budget 1 \
  --system "$(cat prompts/reasonix_db_maintainer.md)" \
  --transcript reports/workspace_dispatch/reasonix_db_session_YYYYMMDD.jsonl
```

Reasonix-Strategy:

```bash
cd "/Users/rongyuxu/Desktop/quant proj"
reasonix chat \
  --session quant-reasonix-strategy \
  --resume \
  -m deepseek-v4-pro \
  --effort high \
  --budget 1 \
  --system "$(cat prompts/reasonix_strategy_researcher.md)" \
  --transcript reports/workspace_dispatch/reasonix_strategy_session_YYYYMMDD.jsonl
```

Reasonix-Advisory:

```bash
cd "/Users/rongyuxu/Desktop/quant proj"
reasonix chat \
  --session quant-reasonix-advisory \
  --resume \
  -m deepseek-v4-pro \
  --effort high \
  --budget 1 \
  --system "$(cat prompts/reasonix_advisory_review.md)" \
  --transcript reports/workspace_dispatch/reasonix_advisory_session_YYYYMMDD.jsonl
```

## Dispatch Envelope

Do not paste the full project history for every task. Send a concise envelope that points to the task packet and current refs:

```text
DISPATCH_TASK
role: <Reasonix-DB | Reasonix-Strategy | Reasonix-Advisory>
task_id: <task-id>
target_project: <project>
source_ref: <branch/tag/commit/tree or N/A>
task_packet: tasks/backlog/<task-id>/handoff.md
context_delta: <only new facts since the last task, compact, or summary>
expected_output: <classification | roadmap | review | draft>
transcript_path: reports/workspace_dispatch/<name>.jsonl
boundary: no recommendation, no broker/order/paper/live/auto, no secrets, no source edits unless converted to Codex-Dev
human_gate: <required | not required | standing authorization plus HG-EXEC required before execution>
```

Keep this envelope short. If the fixed session already has the relevant background, `context_delta` can be `N/A` or one sentence.

## Compact And Summaries

Default:

- keep using the same fixed session;
- rely on Reasonix compact when the session grows;
- do not replay full project context after compact;
- continue with the task packet plus only the new delta.

Ask for a manual durable summary only when needed for audit, cross-agent handoff, or starting a fresh fixed session:

```text
SESSION_SUMMARY
scope:
completed_tasks:
open_questions:
known_warnings:
next_context_minimum:
boundary_reminders:
```

Store manual summaries under `reports/workspace_dispatch/` when they are created. They are helpful artifacts, not a required step for every task.

## Safety

- Persistent sessions are allowed, but role boundaries still apply.
- A long session is not approval to execute writes, network ingest, readiness changes, HITL ticket emission, or source-project promotion.
- `HG-STANDING-20260704` can avoid repeated user prompts for approved categories, but each actual controlled execution still needs a task-level `HG-EXEC-*` record before the command runs.
- If role drift appears, send a `ROLE_RESET`, compact if appropriate, or start a fresh fixed session with `--new`.
