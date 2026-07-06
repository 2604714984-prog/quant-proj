# Windows WSL2 32GB Staging Migration Readiness

Date: 2026-07-06
Machine: Windows target machine, WSL2 Ubuntu 24.04.4 LTS
Mode: 32GB_STAGING_MODE

## Environment

- Codex host shell observed: Windows PowerShell.
- Execution target used for migration commands: WSL2 `Ubuntu-24.04`.
- WSL workspace: `/home/rongyu/workspace`.
- Workspace rule status: PASS. Repositories were cloned under the WSL Linux filesystem, not `/mnt/c`.
- Linux kernel: `6.18.33.1-microsoft-standard-WSL2`.
- OS: `Ubuntu 24.04.4 LTS (Noble Numbat)`.
- Visible CPU count in WSL: 24.
- WSL root filesystem: `/dev/sdd`, size `1007G`, available `954G` at verification.
- Tooling verified:
  - `git version 2.43.0`
  - `Python 3.12.3`
  - `zstd 1.5.5`
  - `ripgrep 14.1.0`
  - `jq-1.7`
  - `gh version 2.45.0`

## Memory

- Windows physical RAM: 31.74 GiB observed.
- WSL available memory at verification: total `15Gi`, available about `14Gi`, swap `4.0Gi`.
- Current operating mode: 32GB_STAGING_MODE.
- Future operating mode after RAM upgrade: 64GB_PRIMARY_MODE.

## Repository Clone Status

All repositories were cloned from GitHub over HTTPS after GitHub CLI authentication was completed in WSL.

| Repo | Branch | HEAD | Remote | Status |
|---|---|---:|---|---|
| `quant-proj` | `main` | `d6fad1bda0fadb7462a3290f763331c5f3910cf9` | `https://github.com/2604714984-prog/quant-proj.git` | clean before this report |
| `A_Share_Monitor` | `codex/harden-a-share-research-pipeline` | `6bfeb816ac8bd6d38b747e30d6f44e81cc8da0bc` | `https://github.com/2604714984-prog/A_Share_Monitor.git` | clean |
| `US_Stock_Monitor` | `main` | `831ef21eda20ecf971bef9ab2f3487b8e96e1001` | `https://github.com/2604714984-prog/US_Stock_Monitor.git` | clean |
| `market_data` | `main` | `ff24166479638b0f35e1cd7a8d0f1d01cdafb495` | `https://github.com/2604714984-prog/market_data.git` | clean |
| `strategy_work` | `main` | `63c779db89b63ccb65819fe87945cd9e5cbe0c15` | `https://github.com/2604714984-prog/strategy_work.git` | clean |

## R13 Anchor Verification

- Tag `data-strategy-r13-interim-external-audit-20260706`: present.
- Tag object: `262dfc48e44363426113c8a2c1cbc41a6599cfe4`.
- Commit `6a3e509f15cf5b22a9bced561f1a7540df0f4b06`: present as a commit object.
- Reachability: commit is contained by `main`, `origin/main`, and tag `data-strategy-r13-interim-external-audit-20260706`.
- Migration handoff files inspected:
  - `reports/agent_handoff/windows_wsl2_migration_handoff_20260706.md`
  - `reports/agent_handoff/windows_wsl2_new_machine_checklist_20260706.md`
  - `reports/workspace_dispatch/windows_wsl2_migration_source_data_inventory_20260706.md`
  - `reports/workspace_dispatch/windows_wsl2_migration_source_repo_heads_20260706.txt`
  - `strategy_work/MIGRATION.md`
  - `strategy_work/reports/planning/MIGRATION_GUIDE.md`
  - `market_data/reports/agent_handoff/database_maintenance_handoff.md`
  - `market_data/reports/agent_handoff/deepseek_db_p0_p4_final_handoff.md`
  - `market_data/reports/deepseek_db/us_db_2_migration_plan.md`

## Compatibility Symlinks

Created idempotent WSL symlinks:

| Legacy path | Target | Status |
|---|---|---|
| `/Users/rongyuxu/Desktop/quant proj` | `/home/rongyu/workspace/quant-proj` | created |
| `/Users/rongyuxu/Desktop/A_Share_Monitor` | `/home/rongyu/workspace/A_Share_Monitor` | created |
| `/Users/rongyuxu/Desktop/US_Stock_Monitor` | `/home/rongyu/workspace/US_Stock_Monitor` | created |
| `/Users/rongyuxu/Desktop/market_data` | `/home/rongyu/workspace/market_data` | created |
| `/Users/rongyuxu/Desktop/strategy_work` | `/home/rongyu/workspace/strategy_work` | created |

No real directories were overwritten.

## GitHub Auth Status

- GitHub CLI authenticated in WSL as account `2604714984-prog`.
- Git operations protocol: HTTPS.
- No token or credential material was read or recorded.

## Hardware Stability Notes

- CPU observed by Windows: `13th Gen Intel(R) Core(TM) i7-13700K`.
- BIOS version observed without risky tooling: `0816`, release date `2023-02-23`.
- Treat target-machine stability as a first-class requirement. No overclocking was configured or assumed by this migration run.
- If random crashes, WHEA errors, Python segfaults, nondeterministic pytest failures, or decompression errors appear, stop and report `TARGET_MACHINE_STABILITY_BLOCKER`.

## Boundary Statement

This staging run did not authorize or perform recommendation/advice, `PENDING_HUMAN_REVIEW`, ticket emission, eligibility candidate creation, data-clear promotion, product-route activation, production readiness, broker/order/paper/live/auto behavior, provider/network ingest, DB/schema migration, readiness flag changes, registry activation, provider-data persistence, raw-data migration, `.env` reads, key output, or secret handling.

This run also did not run full-frame StrategySearch on wide3068 `features_daily`, and did not run wide3068 backtests.

## Next Phase

Proceed with Python environment preparation using only dependency files and lightweight smoke tests. Keep A-share R13C work constrained to chunked StrategySearch/backtest design, full-frame unsafe guards, small-cache equivalence tests, feature/table metadata validation, and limited smoke checks in 32GB_STAGING_MODE.
