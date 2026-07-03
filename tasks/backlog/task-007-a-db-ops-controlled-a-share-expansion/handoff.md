# TASK-007 Handoff

Role: `Codex-Dev`
Target project: `/Users/rongyuxu/Desktop/A_Share_Monitor`
Task: `A-DB-OPS controlled A-share 500/1000 expansion`

## Base

- branch: `codex/harden-a-share-research-pipeline`
- commit: `012006c40897f999f2a2ba5c69e2630b9d50a552`
- tree: `2447205526791e6bcf3f9b18b512d9fc7093c75c`

## Authorization

Use recorded execution mode only:

- Human-Gate: `HG-NIGHT-BATCH-20260704-L1-L4`
- permission: `L1_CONTROLLED_DB_WRITE`
- add `L2_CONTROLLED_NETWORK_INGEST` only if using Tushare/Baostock/Akshare or another remote provider
- requires `--allow-write`
- requires `--allow-network` for provider ingest
- requires command transcript, manifest/counts/hashes, and Codex acceptance

## Work

Implement or run only controlled A-share expansion paths. `expand_canonical_500.py` was classified as `NEEDS_REWRITE`; do not run an unsafe canonical overwrite path as-is.

## Must Return

- status: `ACCEPTED`, `ACCEPTED_WITH_WARNINGS`, or `REJECTED`
- commands run and transcript path
- provider/date/symbol bounds
- snapshot id
- manifest/counts/hashes
- ST/suspend/limit capability status
- changed files
- validation results
- explicit boundary statement

## Forbidden

No `.env`, no key output, no active registry change, no broker/order/paper/live/auto, no recommendation, no forced ticket.
