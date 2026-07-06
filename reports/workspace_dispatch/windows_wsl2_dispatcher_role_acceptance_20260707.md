# Windows WSL2 Quant-Dispatcher Role Acceptance

Project: quant-proj
Role: Quant-Dispatcher
Recorded: 2026-07-07T00:15:15+08:00
Status: QUANT_DISPATCHER_ROLE_MIGRATION_READY
Mode: controller dispatch, record, and closed-loop coordination only

## Role Acceptance

Quant-Dispatcher is now accepted on the Windows + WSL2 Ubuntu workspace at:

```text
/home/rongyu/workspace/quant-proj
```

The dispatcher role is controller-only. It may write intake, task packet,
dispatch, callback, result, closeout, and role records in `quant-proj`. It must
not directly edit downstream source-project implementation files unless the
user explicitly changes the role boundary.

## Controller Files Read

Required controller files were present and inspected:

| File | Status | sha256 |
|---|---|---|
| `AGENTS.md` | OK | `fd334356a145869dd0205216d3179407556e57a51520876010e0284bf2e00fce` |
| `reports/workspace_dispatch/continuous_closed_loop_goal_20260705.md` | OK | `b203afa87d52c5a30ee07c72ae85d9b2d183a2257ab923c02a9e96c2fb9c6011` |
| `runbooks/task_dispatch.md` | OK | `bf883884939c5b3e1914986b982f5bb8b87cb3a0b07eacd7c3e96000f9a785f7` |
| `runbooks/human_gate.md` | OK | `b5c986e9645608bf32aaaf17878b3c3f4e15008aa0208b915abd88a222fb1034` |
| `runbooks/recorded_execution_mode.md` | OK | `0e7ffbd2ef625a310ce7dfc8f54f687a7d21889105138a5fee247a97f58d72c5` |
| `runbooks/reasonix_sessions.md` | OK | `5b94b052c4782e09fc2a917eeb65ace61f87068ccf5065092286b1a589a7d22a` |
| `reports/workspace_dispatch/downstream_completion_callback_protocol_20260706.md` | OK | `e1393edccb5ffa46e1ead3408ada0a5875e88b035c997efce92db7a163f85e7d` |
| `reports/workspace_dispatch/simonlin1212_data_source_policy_20260706.md` | OK | `b3a0eca0ebb7b083870702c2b0377e8d8bf3ecc6414834df7b413083ffa66a97` |
| `reports/agent_handoff/windows_wsl2_migration_handoff_20260706.md` | OK | `d60c299955bd68ea657def2723cbf9035aa7b1bd9866a2eba255e63acf8741e0` |

Related migration checklist also exists:

- `reports/agent_handoff/windows_wsl2_new_machine_checklist_20260706.md`
- `reports/workspace_dispatch/windows_wsl2_migration_source_repo_heads_20260706.txt`
- `reports/workspace_dispatch/windows_wsl2_migration_source_data_inventory_20260706.md`

## Workspace Status

Observed WSL environment:

| Item | Observed |
|---|---|
| OS target | WSL2 Ubuntu 24.04 |
| Kernel | `6.18.33.1-microsoft-standard-WSL2` |
| Workspace root | `/home/rongyu/workspace` |
| CPU count visible to WSL | `24` |
| Memory visible to WSL | `23Gi` total, `22Gi` available at inspection |
| Swap | `8.0Gi` |
| Root filesystem | `/dev/sdd`, `1007G` size, `946G` available |

Compatibility symlinks are present:

| Legacy path | Target |
|---|---|
| `/Users/rongyuxu/Desktop/quant proj` | `/home/rongyu/workspace/quant-proj` |
| `/Users/rongyuxu/Desktop/A_Share_Monitor` | `/home/rongyu/workspace/A_Share_Monitor` |
| `/Users/rongyuxu/Desktop/US_Stock_Monitor` | `/home/rongyu/workspace/US_Stock_Monitor` |
| `/Users/rongyuxu/Desktop/market_data` | `/home/rongyu/workspace/market_data` |
| `/Users/rongyuxu/Desktop/strategy_work` | `/home/rongyu/workspace/strategy_work` |

## Repository Status

All fixed repositories are present under `/home/rongyu/workspace` and were clean
at inspection.

| Repo | Branch | HEAD | Upstream | Dirty count |
|---|---|---:|---|---:|
| `quant-proj` | `main` | `61c71087cb33ac55c6f00b9aa7da12e8a111a13b` | `origin/main` | `0` |
| `A_Share_Monitor` | `codex/harden-a-share-research-pipeline` | `dd3089e2a9c1693ea0571db37c185d6584f1bc14` | `origin/codex/harden-a-share-research-pipeline` | `0` |
| `US_Stock_Monitor` | `main` | `831ef21eda20ecf971bef9ab2f3487b8e96e1001` | `origin/main` | `0` |
| `market_data` | `main` | `ff24166479638b0f35e1cd7a8d0f1d01cdafb495` | `origin/main` | `0` |
| `strategy_work` | `main` | `2bfbe33e654e7ceb76117ab7b156ff44f2d979be` | `origin/main` | `0` |

Observed source-state drift beyond the original migration handoff:

- `A_Share_Monitor` has advanced beyond R13C to WSL2 R14/data-chain repair evidence, with current HEAD `dd3089e2a9c1693ea0571db37c185d6584f1bc14`.
- `strategy_work` has advanced beyond the handoff to `2bfbe33e654e7ceb76117ab7b156ff44f2d979be`.
- The drift is clean and already aligned with each repository's upstream branch.

## Closed-Loop Goal

The closed-loop controller goal still exists and is active:

```text
reports/workspace_dispatch/continuous_closed_loop_goal_20260705.md
Status: ACTIVE
Current task batch: DATA_STRATEGY_BATCH_R13_CHUNKED_SEARCH_20260706 active dispatch
```

R13 interim anchors are present:

| Anchor | Status |
|---|---|
| Tag `data-strategy-r13-interim-external-audit-20260706` | present |
| Tag object | `262dfc48e44363426113c8a2c1cbc41a6599cfe4` |
| Commit `6a3e509f15cf5b22a9bced561f1a7540df0f4b06` | present |

## Current Mainline

Controller state says the active closed-loop task remains
`DATA_STRATEGY_BATCH_R13_CHUNKED_SEARCH_20260706`.

Current source evidence also shows a later Windows WSL2 data-chain repair path
has been received:

- A-share staging repair and rerun evidence was accepted with warnings at the
  source layer.
- East Money cross-check evidence remains partial coverage, not data-clear.
- Survivor-bias evidence improved, but not fully proven eliminated.
- Strategy reruns remain rejected and research-only.
- Chunked StrategySearch remains required; wide3068 full-frame remains unsafe.

## Downstream Callback Protocol

The downstream Codex completion callback protocol is active:

```text
reports/workspace_dispatch/downstream_completion_callback_protocol_20260706.md
dispatcher thread: 019f2766-7c5f-7562-b2e3-b4d76de7bfa9
```

Every future Codex-Dev handoff must require prompt-only callback with:

- `CODEX_ACCEPTANCE`, `DATA_REPORT`, `STRATEGY_REPORT`, `BLOCKED`, or equivalent final status;
- commit, tree, branch, and push status when files changed;
- artifacts;
- validation;
- residual blockers;
- boundary statement.

Recorded acknowledgements:

- `A_Share_Monitor`: acknowledged.
- `strategy_work`: acknowledged.
- `US_Stock_Monitor`: acknowledged.
- `market_data`: not yet recorded; older approval-blocked thread state remains the controller-level blocker.

## Blocked / Watch Items

- `market_data`: controller records still show the active thread blocked by an older git-index approval state; active thread/worktree state should be reconfirmed before assigning more `market_data` implementation work.
- A-share strategy line: current wide reruns remain rejected. This is honest research evidence, not a candidate recovery.
- Data-source policy: future provider/data-source candidates remain restricted to `https://github.com/simonlin1212` unless the user explicitly changes the rule.
- External audit: ordinary research/data/strategy batches do not get controller external-audit packets unless a boundary trigger opens.

## Boundary Statement

This controller acceptance does not authorize recommendation/advice,
`PENDING_HUMAN_REVIEW`, ticket emission, eligibility candidates, product-route
activation, production readiness, broker/order/paper/live/auto behavior, DB
writes, network ingest, schema migration, bulk ingest, readiness changes,
registry activation, provider-data persistence, raw-data migration, `.env`
reads, key output, or secret handling.

Quant-Dispatcher accepts the role as controller, recorder, dispatcher, and
closed-loop coordinator only.
