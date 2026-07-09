# R32 Quant Research Stack Result Summary

Batch: `WINDOWS_WSL2_QUANT_RESEARCH_STACK_EVALUATION_R32_20260709`

Status: `COMPLETED_RESEARCH_ONLY_STACK_APPLIED_WITH_LOCAL_ARTIFACTS`

## Source Preservation

A_Share_Monitor completed and pushed:

- branch: `codex/r32-quant-research-stack-evaluation-20260709`
- commit: `e4459a0a254901c0c2578a7ca8e7320c226aa917`
- tree: `9b13797dad06859a713da9e1eff3e55e529247c9`

strategy_work final sync completed and pushed:

- branch: `main`
- commit: `8b70996aa0bf4c722a6f7ef1cbe6cf1ade4faacf`
- tree: `e4ec502a2287daaba1382192525ae3d6a544c355`

## Stack Outcome

R32 applied the requested project direction as source-local research infrastructure:

- `OpenBB`: `ADOPT_FOR_RESEARCH_SPIKE`
- `Qlib`: `ADOPT_FOR_RESEARCH_SPIKE`
- `vectorbt`: `ADOPT_FOR_RESEARCH_SPIKE`
- `vn.py`: `DEFER_EXECUTION_SIDE_REFERENCE_ONLY`
- `FinGPT`: `CONTEXT_ONLY_SPIKE`
- `TradingAgents`: `CONTEXT_ONLY_SPIKE`
- `FinRL`: `REFERENCE_ONLY`
- `Qbot`: `REFERENCE_ONLY`

R32 did not install production dependencies or activate runtime paths. The current A_Share_Monitor venv still records `qlib`, `openbb`, `vectorbt`, `vnpy`, and `finrl` as unavailable.

## Research Artifacts

- Qlib-ready pass77 local export: `136,767` rows.
- Vectorized reversal scanner: `18` fixed variants.
- OpenBB public/no-secret adapter contract.
- vn.py execution boundary.
- FinGPT / TradingAgents context-only boundary.

The vectorized scanner emitted validation-interesting diagnostics, but no row was promoted to local probe eligibility.

## Final Counts

- `local_research_probe_eligible_count=0`
- `wide_research_probe_eligible_count=0`
- `strategy_candidate_available=false`

## Validation

- py_compile PASS
- focused pytest PASS: `8 passed`
- JSON parse PASS
- CSV/parquet read PASS
- agent_safety_check PASS
- git diff --check PASS
- push verification PASS

## Boundary

Research-only boundary passed. No recommendation/advice, ticket, candidate promotion, readiness/product route, daily signal, broker/order/paper/live/auto path, active registry/schema change, secret output, or test-result parameter selection.
