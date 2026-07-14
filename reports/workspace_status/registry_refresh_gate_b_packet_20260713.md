# Registry refresh for the Gate B code/mock packet

Refreshed at `2026-07-13T21:44:54+08:00` before dispatch planning for
`REMEDIATION_R2_GATE_B_CODE_MOCK_20260713`.

All registered source paths were inspected read-only. The registered local
worktrees were clean. The only live source-ref changes relative to the prior
controller snapshot were:

- `us_stock_30w` is now
  `research/c2-remediation-r2-20260713@e47d4155d4e2bace2c15ae22e53f66556d19d832`,
  tree `0029859c454a1a94dc8024a5c2a4ea91c898ce0b`.
- the authoritative local remote-tracking identity for `quant_research_lab`
  is `origin/master@6b98b94d0cdd674d6e07cce93726f204ab3a6594`, tree
  `3207d3a834d1d52785c4cb7c2978c285a19540d2`. Its older local checkout remains
  non-dispatch evidence.

`central-data-ingestion` `main` remains clean and exact at
`287416f79cd1fcb1c066f25fa7bbaedc574b0ce9`, tree
`c2a62d079bcb08b04b2425c7160bf9ca8344038a`; that is the only accepted
implementation baseline for this packet.

A separate clean local/remote-tracking branch exists at
`origin/codex/central-ingestion-gate-b-20260713@0bc1007235a96ab2e4c0e92700a999930761e73a`,
tree `d14939354fda31adfedec22febd29b37cb360285`. It is five commits ahead of
`main`, is not independently accepted, and contains Replay canary result files.
It is frozen as `UNACCEPTED_SUPERSEDED_DESIGN_INPUT`. Only architectural
skeletons and negative-test ideas may be compared read-only. It cannot be
cherry-picked as a branch, treated as a Gate B result, or used to reuse its
Replay HG/marker/canary or authorize provider, database, or timer execution.

The central DuckDB was not opened or queried. A read-only file hash/stat check
recorded current bytes as 1,001,664,512, mode `0600`, SHA-256
`e1826d04191e5014ddcbb12f9d96acdded0ff54b58c90068c9c4001160e074b9`.
Those bytes differ from the consumed Wave 0 baseline and backup. Consequently,
the old backup/HG record cannot authorize a real publish canary. A fresh
descriptor-bound baseline, byte-identical backup and exact single-use L1 HG are
mandatory before any future write.

This refresh authorizes only the controller to dispatch a code-only,
mock/tmp-only task. No Git fetch, provider call, token access, database write,
schema migration, systemd deployment/activation, strategy process, readiness or
registry activation, recommendation, candidate promotion, or trading path was
performed. `strategy_candidate_available=false`.
