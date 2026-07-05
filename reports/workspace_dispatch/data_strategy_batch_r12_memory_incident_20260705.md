# DATA_STRATEGY_BATCH_R12_20260705 Memory Incident

Recorded: 2026-07-05T15:12:02Z
Local time context: 2026-07-05 around 23:06 Asia/Shanghai
Controller role: Quant-Dispatcher
Source project affected: `/Users/rongyuxu/Desktop/A_Share_Monitor`

## Summary

A local memory incident was attributed to an A_Share_Monitor Python feature build launched under a Reasonix node process. The task attempted to build the full feature store from `data/cache`:

```text
from qta.data.data_store import ParquetDataStore
from qta.features.feature_store import FeatureStore
store = ParquetDataStore('data/cache')
fs = FeatureStore(store)
feat = fs.build()
```

The user-provided incident report identified PID `5966` with a physical footprint around `20.6 GB` on an `8 GB` machine. Terminal itself was not the primary memory source.

## Dispatcher Action

- Confirmed the original Python child process still existed.
- Sent `SIGINT` first, then `SIGTERM` when it did not exit.
- Observed a replacement Python feature-build child process under the same Reasonix parent chain.
- Interrupted the relevant Reasonix process group and terminated the replacement child.
- Confirmed no matching A_Share_Monitor `python3 -u -c` FeatureStore build process remained.
- Left unrelated Reasonix sessions alone where possible; persistent sessions should be reused after the runaway command is no longer active.

## Follow-Up Dispatch

The active A-share R12 Codex-Dev thread `019f32bd-082d-73e2-b902-3d48b8d198ba` was sent an urgent dispatcher update:

- Do not run full-cache `FeatureStore(store).build()` over all of `data/cache`.
- Use bounded existing artifacts, chunked reads, manifest inspection, or narrow symbol/date windows only.
- If a full build is necessary, return `BLOCKED` with a chunking plan instead of executing it.
- Include in `CODEX_ACCEPTANCE` whether memory-heavy paths were avoided and whether a later root code change is needed.

## Root Cause Direction

The likely root fix belongs in `A_Share_Monitor`: make `FeatureStore.build()` bounded or streaming/chunked by symbol, date window, or partition instead of expanding the full local cache in memory. That implementation is not performed in the controller workspace and should be assigned to Codex-Dev as a scoped source-repo task if it becomes required by the next batch or by A-share R12 acceptance.

## Boundary Statement

No recommendation, ticket, eligibility candidate, product route, production readiness, broker/order path, paper trading, live trading, or auto execution was created or authorized. No DB write, network ingest, schema migration, bulk ingest, readiness change, registry activation, provider-data persistence, or raw-data migration was performed by this incident handling.
