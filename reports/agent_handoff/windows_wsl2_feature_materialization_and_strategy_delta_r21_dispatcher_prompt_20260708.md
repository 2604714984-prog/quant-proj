# Dispatcher Prompt - WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708

```text
DISPATCH WINDOWS_WSL2_FEATURE_MATERIALIZATION_AND_STRATEGY_DELTA_R21_20260708

Use branch:
codex/task-packet-r20-v2-20260708

Read:
- tasks/in_progress/windows-wsl2-feature-materialization-and-strategy-delta-r21-20260708/spec.md
- reports/agent_handoff/windows_wsl2_feature_materialization_and_strategy_delta_r21_dispatcher_prompt_20260708.md
- reports/workspace_dispatch/windows_wsl2_feature_materialization_and_strategy_delta_r21_20260708_intake.md
- tasks/checklists/r21_execution_checklist_20260708.md
- reports/agent_handoff/windows_wsl2_simonlin_strategy_superbatch_r20_v2_external_audit_result_20260708.md

Goal:
Run R21 as an ordinary research-only feature materialization and strategy-delta batch after R20_V2.

Before new strategy diagnostics:
1. Freeze R20 evidence and limitations.
2. Import R20 outputs into experiment store and failure memory.
3. Run source-health before fetch-heavy work.
4. Materialize ETF amount/NAV/premium or preserve explicit limitation labels.
5. Materialize bounded A-share new-feature rows if sources pass health checks.
6. Materialize date-indexed global/news/macro regime rows if sources pass health checks.

Priority:
- ETF: fix amount/NAV/premium gaps or keep limitation labels; rerun only delta diagnostics justified by new fields or limitations.
- A-share: convert PEG/event/funds/hot-money source-review into validated local feature rows; skip strategy search if no local rows exist.
- Global/news/macro: convert context review into date-indexed regime context only.
- Tooling: queryable experiment store, source-health dashboard, duplicate-search blocker, artifact manifest.

Boundary:
Research-only. No actionable output, candidate promotion, readiness promotion, route activation, daily signal push, raw-data migration into controller, active schema/registry activation, or credential output.

Return the callback envelope required in the task packet.
```
