# FeatureStore.build Compatibility Rollback

Date: 2026-07-05
Controller role: Quant-Dispatcher
Source project: A_Share_Monitor
Source branch: `codex/harden-a-share-research-pipeline`
Source commit: `89373e8f133b946e7d8c3048e704b8c6c5a6f9e2`

## Scope

User reported that the guarded `FeatureStore.build()` path made research runs unusable and requested restoring the old behavior.

Classification: source implementation fix, research/data tooling only.

External-audit trigger opened: `no`.

## Change

Restored `FeatureStore.build()` compatibility:

- `FeatureStore.build()` no longer raises `MemoryError` based on row-count guard checks.
- Legacy callers such as `StrategySearch.run()` can again call `self.feature_store.build()` and receive a DataFrame.
- The explicit chunked path remains available through `FeatureStore.build_to_store()` and `build(streaming=True, return_frame=False)`.

Updated tests:

- Memory-safety tests now verify legacy in-memory compatibility instead of expecting `MemoryError`.
- Chunked `build_to_store()` behavior remains covered.

## Validation

Executed in `/Users/rongyuxu/Desktop/A_Share_Monitor`:

- `python -m pytest tests/test_feature_store_memory_safety.py`
- `python -m pytest tests/test_feature_store_memory_safety.py tests/test_strategy_search_smoke.py`
- `FeatureStore(store).build(start='20240102', end='20240131', output_table='features_daily_smoke', max_in_memory_rows=1)` on the 50-symbol Phase3 cache
- `python -m qta research discover --config /Users/rongyuxu/Desktop/strategy_work/configs/bare_minimum.yaml`

Research smoke result:

- run id: `research_20260705_163753`
- run dir: `outputs/bare_minimum/research_20260705_163753`
- warnings: `cost_stress_status=FAIL`

## Boundary Statement

No recommendation, ticket, product route, production readiness, broker/order path, paper trading, live trading, auto execution, raw-data migration, or secret handling was authorized or performed.
