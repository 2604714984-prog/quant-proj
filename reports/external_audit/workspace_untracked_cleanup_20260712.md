# Workspace Untracked-File Cleanup Evidence

Date: 2026-07-12
Status: `COMPLETE_WITH_ZERO_GIT_VISIBLE_UNTRACKED`

## Scope and result

The cleanup audited 14 repository roots and 70 valid linked worktrees after the external-audit publication. Every deletion target was classified first and constrained to its owning repository or worktree. Broad `git clean`, destructive reset, and default-branch rewrites were not used.

Final cross-workspace status:

- Git-visible untracked files: `0`
- Status/read errors: `0`
- Disposable cache/log/temp residue in audited categories: `0`
- Remaining tracked changes: five pre-existing files in the live `RD-Agent` checkout only
- Stale worktree metadata pruned: three records whose `/tmp` paths no longer existed

The five RD-Agent tracked modifications were not changed or deleted. They had already been preserved on the owner-controlled fork branch `agent/external-audit-local-compat-draft-20260712`, commit `92aa18336f943c4f83fdea49843151dabd254bbb`, and remain explicitly draft/unaccepted.

## Deleted disposable material

| Scope | Deleted material | Reclaimed bytes |
|---|---|---:|
| `strategy_work` | 24 unowned/unopened DuckDB temporary spill files | 111,055,896,576 |
| `A_Share_Monitor`, `market_data`, `quant-proj` | 3,841 log, pickle-cache, temporary RD-Agent workspace, Python/test/tool cache and OS-debris files | 32,617,592 |
| US/external/reference repositories | 380 cache/runtime-log directories and five ignored log/temp files | 21,694,362 |
| **Total** | Verified disposable artifacts only | **111,110,208,530** |

Total reclaimed space was approximately 103.48 GiB. WSL free space increased from approximately 815 GiB to 919 GiB.

## Necessary files converted from untracked debt

Active source, tests, reports, and planning evidence were not deleted. They were scanned, size-checked, committed on preservation-only branches, pushed without force, and verified against exact remote refs.

### strategy_work live research state

- Branch: `agent/live-strategy-research-preservation-20260712`
- Commit: `a27e35b59ef8b59d0771bcf019534ca93748bbcc`
- Tree: `1439e27f10bce9d24d091ecada28116092f145a5`
- Preserved: 572 files, 67,991,096 bytes
- Largest file: 16,062,403 bytes
- Secret/path/size scans: pass
- Final live checkout: clean and tracking the exact remote ref

### A_Share_Monitor active evidence rebuild

- Branch: `agent/live-a-share-research-preservation-20260712`
- Commit: `1a64e70873fc8a3c3d998e509cbcf690010ffef0`
- Tree: `fd280413f18443d1a341d5e142db03180aa85f8f`
- Preserved: one source file and one focused test
- Validation: `py_compile`, two Pytest tests, Ruff, secret scan and `git diff --check` passed
- Final live checkout: clean and tracking the exact remote ref

### us_stock_30w TuShare planning note

The only untracked US30W planning note contained a shared relay credential literal. The value was not reported. Before publication, it was removed, replaced with an environment-variable placeholder, and the document was marked plan-only, token route paused, no provider/network execution and no database write.

- Branch: `agent/tushare-persistence-plan-20260712`
- Commit: `7d72ff9d17c05d88390d5d8df4cae300b4b0a758`
- Tree: `dd265d21afeb81537a0696ed6b79255ccf5bd066`
- Sanitized file SHA-256: `b2672b74b1c279d2424b0060ce94f9406013a2a2d70a1d21d756413107f207e7`
- Remote ref and blob: exact

The shared relay credential should be considered exposed from its earlier chat/local-file use and rotated before any future reuse.

## Intentionally retained local-only assets

The following are untracked in the broad filesystem sense but already ignored and necessary; they were not disposable cleanup targets:

- databases, raw/source snapshots, Parquet research data and current outputs;
- `.venv` environments;
- private manifests, HG/authorization records and identifier-protected inputs;
- current ignored reports and research results;
- `quant_research_lab/.env`, whose content was not read and whose mode was tightened from `0644` to `0600`;
- ignored RD-Agent and QRL research data.

The A-share retained local asset set is approximately 14.376 GB, dominated by its virtual environment and data. US/QRL retained environments and research data are separately documented in the cleanup callback. These assets are excluded from GitHub by design.

## Boundary

No database/raw-data deletion, provider call, token use, strategy execution, result change, recommendation, candidate promotion, readiness activation, broker/order/paper/live/auto action, merge, default-branch change, or force push occurred.
