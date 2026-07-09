# R32 Quant Research Stack Closeout

Batch: `WINDOWS_WSL2_QUANT_RESEARCH_STACK_EVALUATION_R32_20260709`

Closeout status: `CLOSED_ACCEPTED_RESEARCH_ONLY_STACK_APPLIED_WITH_WARNINGS`

R32 is closed as a stack-application research batch. It converted the user-selected tool direction into source-local research artifacts and boundaries:

- OpenBB, Qlib, and vectorbt are accepted for research spikes.
- vn.py is accepted only as deferred execution-side reference work.
- FinGPT and TradingAgents remain context/explanation layers only.
- FinRL and Qbot remain reference-only.

Carry-forward warnings:

- No production dependencies were installed or activated.
- Qlib/OpenBB/vectorbt are not yet available in the current A_Share_Monitor venv.
- R32 did not create local or wide probe eligibility.
- R32 did not create a strategy candidate.
- vn.py remains blocked from runtime use until a separate accepted strategy candidate and explicit paper/live authorization exist.

Final counts:

- `local_research_probe_eligible_count=0`
- `wide_research_probe_eligible_count=0`
- `strategy_candidate_available=false`

Next source action: use the Qlib-ready export and vectorized scanner outputs in a separate validation-only research batch. Keep OpenBB, vn.py, and AI-agent components behind research-only boundaries.

Boundary result: `PASS_RESEARCH_ONLY`.
