# TASK-004: A_DB_OPS_SCRIPTS_FINAL_CLASSIFICATION

Task ID: `TASK-004`
Status: `ASSIGNED_READY_TO_SEND`
Priority: `P1`
Primary assignee: `Reasonix-DB`
Secondary assignee after classification: `Codex-Dev`
Target project: `A_Share_Monitor`
Target root: `/Users/rongyuxu/Desktop/A_Share_Monitor`
Dispatcher: `Quant-Dispatcher`
Created at: 2026-07-04T01:25:34+08:00

## Goal

Produce a read-only final classification for A-share DB ops scripts before any controlled namespace rewrite.

## Assignment

Send to `Reasonix-DB` first for read-only DB-tool classification. Do not send to Codex-Dev until classification output exists.

## Inputs For Reasonix-DB

Classify:

- `A_Share_Monitor/scripts/expand_cache_300.py`
- `A_Share_Monitor/scripts/expand_canonical_500.py`
- `A_Share_Monitor/scripts/fill_akshare.py`
- `A_Share_Monitor/scripts/fill_baostock.py`
- `A_Share_Monitor/qta/data/local_market_db/*fetcher.py`

## Required Output

```text
A_DB_OPS_SCRIPTS_FINAL_CLASSIFICATION

For each script:
ACCEPT_AS_DB_TOOL / NEEDS_REWRITE / QUARANTINE / DELETE

Required controls:
--allow-network
--allow-write
--dry-run
read-only mode
output path restriction
```

## Human-Gate Rule

No Human-Gate is required for read-only classification.

Human-Gate is required before any DB write, data/cache write, network ingest, schema migration, physical DB movement, registry activation, readiness change, or product route activation.

## Dispatcher Boundary

Quant-Dispatcher only created this packet. No source-project files were edited.

