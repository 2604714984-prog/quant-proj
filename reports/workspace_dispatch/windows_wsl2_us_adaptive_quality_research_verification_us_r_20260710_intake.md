# US-R Adaptive+Quality Research Verification Intake

Batch: `WINDOWS_WSL2_US_ADAPTIVE_QUALITY_RESEARCH_VERIFICATION_US_R_20260710`

The user requested restoration of the formal local simulation and Strategy Vault
research-lead status while preserving the US strategy as a research lead only.

Key boundaries:

- Keep US strategy as research lead.
- Do not delete it.
- Do not treat it as active strategy.
- Do not daily run it.
- Prioritize Adaptive+Quality verification.
- Decide CONTINUE_RESEARCH / BENCHMARK_ONLY / REPAIR_REQUIRED / DO_NOT_RETRY.

Local simulation status:

- `evidence_trader.py` is preserved as manual local simulation evidence
  collection.
- US-R must not invoke it.
- `run_daily.sh` remains disabled.
