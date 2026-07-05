# Registry Refresh Snapshot - R12 Dispatch

Created: 2026-07-05T22:28:38+08:00
Purpose: refresh before `DATA_STRATEGY_BATCH_R12_20260705` dispatch
Runbook: `runbooks/registry_refresh.md`

## Source Project State

| Project | Dispatch path / worktree | Branch | Commit | Tree | Worktree state |
|---|---|---|---|---|---|
| `A_Share_Monitor` | `/Users/rongyuxu/Desktop/A_Share_Monitor` | `codex/harden-a-share-research-pipeline` | `05b79ddabb05003067e1ae86e10411604271ff26` | `05a99d23041fc09d54796501a35789fdf0caa182` | dirty: pre-existing `reports/research_loop/*` edits |
| `US_Stock_Monitor` | `/Users/rongyuxu/.codex/worktrees/c4f8/US_Stock_Monitor` | `codex/duckdb-provider` | `c9dce3782df1e250987129c7ce5350c786e1821d` | `ed1bd5c17cfd804ee06fabb509fa42c72e148392` | worktree exists for R11 branch; main checkout has unrelated untracked files |
| `market_data` | `/Users/rongyuxu/.codex/worktrees/c385/market_data` | `codex/data-strategy-r10-market-data-data-clear` | `96a325423d00af02c8829d85d770b7d73e30c6f6` | `287fe38fc93d3e0852951638205c99a734e81d0e` | worktree exists for R11 branch; main checkout is older |
| `strategy_work` | `/Users/rongyuxu/Desktop/strategy_work` | `main` | `ad33605ec3ae001bc7c17b132f7333f76f60ae74` | `b84fd7ea66c0a6c771ea021eeabe68111888f11b` | dirty: untracked `analysis/` only |

## Observed Dirty Or Untracked Paths

`A_Share_Monitor` pre-existing dirty paths:

- `reports/research_loop/a_share_micro_next_questions.md`
- `reports/research_loop/a_share_micro_observation_candidates.md`
- `reports/research_loop/a_share_micro_phase3_handoff_required.md`
- `reports/research_loop/a_share_micro_rejected_patterns.md`
- `reports/research_loop/a_share_micro_research_ledger.csv`
- `reports/research_loop/a_share_micro_strategy_backlog.md`

`US_Stock_Monitor` main checkout has unrelated untracked paths, including `reports/recommendation/`, `reports/research/`, `reports/trade_reviews/`, several `scripts/fill_us*.py` files, and `yfinance_cache.sqlite`. R12 dispatch should use the Codex worktree path above for the R11 branch and must not stage main-checkout noise.

`strategy_work` has untracked `analysis/`, untouched.

`quant-proj` has pre-existing modified old Reasonix JSONL files:

- `reports/workspace_dispatch/reasonix_db_data_strategy_batch_r8_20260705.jsonl`
- `reports/workspace_dispatch/reasonix_strategy_data_strategy_batch_r7_20260705.jsonl`

These are not R12 dispatch artifacts and must not be staged.

## Fresh R11 Evidence State For R12

- A-share R11: no true post-freeze forward holdout found; `strict_v2` retains `2` records / `1` symbol; balanced variants retain `3` and `7` records; amount-scale artifact risk remains.
- US R11: `165` row blocker matrix; `121` signal-review records and `44` metadata-queue records remain blocked; metadata validator remains `IMPORT_BLOCKED_DRY_RUN_ONLY`; offline crosscheck is synthetic-only with zero research evidence.
- market_data R11: US-300A remains `DATA_CLEAR_RESEARCH_PENDING_CRITERIA`; only `a_expand_20260704_l1_local1000_0317` contains `600177.SH`; inventory terminology needs R12 semantics hardening to avoid misreading baseline rows as true forward holdout.
- strategy_work R11: final memo sync complete and research-only.

## Validation

- `registry/projects.yaml` parsed as YAML before dispatch.
- `registry/agents.yaml` parsed as YAML before dispatch.
- Forbidden artifact scan in quant-proj found no `.env`, `.duckdb`, `.sqlite`, `.parquet`, `.zip`, or `.tar.gz` files.
- No raw DB/cache/output artifact was copied into quant-proj.
