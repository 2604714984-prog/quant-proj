# Handoff: TASK-004 A_DB_OPS_SCRIPTS_FINAL_CLASSIFICATION

To: `Reasonix-DB`
Mode: read-only DB ops classification
Target project: `/Users/rongyuxu/Desktop/A_Share_Monitor`

## How To Send

Use Reasonix-DB with the workspace DB-maintainer system prompt:

```bash
cd "/Users/rongyuxu/Desktop/quant proj"
reasonix run --effort high --budget 0.50 \
  -m deepseek-v4-pro \
  --transcript reports/workspace_dispatch/reasonix_db_task_004_20260704.jsonl \
  --system "$(cat prompts/reasonix_db_maintainer.md)" \
  "$(cat tasks/backlog/task-004-a-db-ops-scripts-final-classification/handoff.md)"
```

This command is the send method. Quant-Dispatcher has not executed it.

Fixed Reasonix settings: `deepseek-v4-pro`, effort `high`.

## Request

Read-only classify the A-share DB ops scripts:

- `/Users/rongyuxu/Desktop/A_Share_Monitor/scripts/expand_cache_300.py`
- `/Users/rongyuxu/Desktop/A_Share_Monitor/scripts/expand_canonical_500.py`
- `/Users/rongyuxu/Desktop/A_Share_Monitor/scripts/fill_akshare.py`
- `/Users/rongyuxu/Desktop/A_Share_Monitor/scripts/fill_baostock.py`
- `/Users/rongyuxu/Desktop/A_Share_Monitor/qta/data/local_market_db/*fetcher.py`

Return:

```text
A_DB_OPS_SCRIPTS_FINAL_CLASSIFICATION
```

For each script, classify as:

- `ACCEPT_AS_DB_TOOL`
- `NEEDS_REWRITE`
- `QUARANTINE`
- `DELETE`

Also state whether it needs:

- `--allow-network`
- `--allow-write`
- `--dry-run`
- read-only mode
- output path restriction

## Forbidden

- Do not edit files.
- Do not write DB/data/cache.
- Do not run network ingest.
- Do not read `.env` or secrets.
- Do not claim product/readiness/recommendation status.
