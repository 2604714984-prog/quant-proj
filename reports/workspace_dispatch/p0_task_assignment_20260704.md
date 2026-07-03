# P0 Task Assignment

Date: 2026-07-04T01:25:34+08:00
Role: `Quant-Dispatcher`
Mode: assignment only
Status: `ASSIGNED_READY_TO_SEND`

## Registry Refresh

Batch dispatch was preceded by a read-only registry refresh:

- `reports/workspace_status/registry_refresh_snapshot_20260704_dispatch_p0.md`
- `registry/projects.yaml`

Important refresh result:

- `A_Share_Monitor` is clean at `1537e9958fdd11a36f6392314228abd02a26507a`.
- `US_Stock_Monitor` is clean at `36aff30da581d01d24ffba89c6bb1e0515337bec`.
- `market_data` is clean at `ff24166479638b0f35e1cd7a8d0f1d01cdafb495`.
- `strategy_work` is clean at `a67404900f424bdf918d3254540653446bda12ad`.

## Assignment Table

| Task | Priority | Assigned to | Target | Human-Gate | How to send |
|---|---:|---|---|---|---|
| `TASK-001 CODEX_ACCEPTANCE_A11_RESEARCH_RUNNER` | P0 | `Codex-Dev` | `/Users/rongyuxu/Desktop/A_Share_Monitor` | Not required for research-only acceptance | Open `codex -C /Users/rongyuxu/Desktop/A_Share_Monitor`, paste `tasks/backlog/task-001-codex-acceptance-a11-research-runner/handoff.md` |
| `TASK-002 CODEX_ACCEPTANCE_US_STRATEGY_EXPERIMENTS` | P0 | `Codex-Dev` | `/Users/rongyuxu/Desktop/US_Stock_Monitor` | Not required for research-only acceptance | Open `codex -C /Users/rongyuxu/Desktop/US_Stock_Monitor`, paste `tasks/backlog/task-002-codex-acceptance-us-strategy-experiments/handoff.md` |
| `TASK-003 US_DB_OPS_2_CONTROLLED_EXPANSION_HELPER` | P0 | `Codex-Dev` | `/Users/rongyuxu/Desktop/US_Stock_Monitor` | Not required for rewrite only; required before network or DB writes | Open `codex -C /Users/rongyuxu/Desktop/US_Stock_Monitor`, paste `tasks/backlog/task-003-us-db-ops-2-controlled-expansion-helper/handoff.md` |
| `TASK-004 A_DB_OPS_SCRIPTS_FINAL_CLASSIFICATION` | P1 | `Reasonix-DB` | `/Users/rongyuxu/Desktop/A_Share_Monitor` | Not required for read-only classification; required before writes or ingest | Run Reasonix with `prompts/reasonix_db_maintainer.md` and `tasks/backlog/task-004-a-db-ops-scripts-final-classification/handoff.md` |
| `TASK-005 STRATEGY_WORK_NEXT_TASK_PROMPTS` | P1 | `Reasonix-Strategy` | `/Users/rongyuxu/Desktop/strategy_work` | Not required for research draft | Run Reasonix with `prompts/reasonix_strategy_researcher.md` and `tasks/backlog/task-005-strategy-work-next-task-prompts/handoff.md` |

## Send Order

1. Send `TASK-001` to Codex-Dev.
2. Send `TASK-002` to Codex-Dev.
3. Send `TASK-003` to Codex-Dev only after `TASK-002` is at least accepted or not blocking the US repo state.
4. Send `TASK-004` to Reasonix-DB in parallel with Codex-Dev work if desired.
5. Send `TASK-005` to Reasonix-Strategy after or alongside `TASK-001` and `TASK-002`; it is research planning only.

## Exact Send Instructions

### TASK-001

```bash
codex -C /Users/rongyuxu/Desktop/A_Share_Monitor
```

Paste:

```text
tasks/backlog/task-001-codex-acceptance-a11-research-runner/handoff.md
```

### TASK-002

```bash
codex -C /Users/rongyuxu/Desktop/US_Stock_Monitor
```

Paste:

```text
tasks/backlog/task-002-codex-acceptance-us-strategy-experiments/handoff.md
```

### TASK-003

```bash
codex -C /Users/rongyuxu/Desktop/US_Stock_Monitor
```

Paste:

```text
tasks/backlog/task-003-us-db-ops-2-controlled-expansion-helper/handoff.md
```

### TASK-004

```bash
cd "/Users/rongyuxu/Desktop/quant proj"
reasonix run --effort high --budget 0.50 \
  --transcript reports/workspace_dispatch/reasonix_db_task_004_20260704.jsonl \
  --system "$(cat prompts/reasonix_db_maintainer.md)" \
  "$(cat tasks/backlog/task-004-a-db-ops-scripts-final-classification/handoff.md)"
```

### TASK-005

```bash
cd "/Users/rongyuxu/Desktop/quant proj"
reasonix run --effort high --budget 0.50 \
  --transcript reports/workspace_dispatch/reasonix_strategy_task_005_20260704.jsonl \
  --system "$(cat prompts/reasonix_strategy_researcher.md)" \
  "$(cat tasks/backlog/task-005-strategy-work-next-task-prompts/handoff.md)"
```

## Not Assigned Now

- RunOps: no current action.
- Codex-Audit: no current action; these are assignments, not completed delivery packets.
- ChatGPT external audit: no current action; controller plan is already accepted for dispatch/process scope.
- Reasonix-Advisory: no current P0 assignment in this batch; can be assigned later for read-only review of A11 and US strategy experiments after Codex-Dev acceptance output exists.

## Boundary

This dispatch only assigns tasks. It does not execute downstream work, edit source projects, write databases, run network ingest, change schemas, activate registry routes, change readiness, emit tickets, generate recommendations, touch broker/order paths, run paper/live trading, or handle secrets.

