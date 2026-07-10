# A-share BaoStock fundamental smoke code

TASK_ID: A_SHARE_BAOSTOCK_FUNDAMENTAL_SMOKE_CODE_20260710
STATUS: LUNA_ACCEPTED_CODE_ONLY
TARGET_PROJECT: a_share_monitor
RECOMMENDED_AGENT: codex_dev
MODEL_ROLE: executor
MODEL: gpt-5.6-luna
REASONING_EFFORT: medium
SOURCE_COMMIT: f39c9bcf5fc05c0c9b89aa2c13db525e434de5b7
SOURCE_TREE: 817aa52f834fd4328b937adb0fd151c9ea1bdb40
AUTOMATED_GATE_COMMANDS: gate_commands.txt
AUTOMATED_GATE_COMMANDS_SHA256: 161caf8fc7e5ac9e680e5f9c355c43bb96e0bf4be0c56d041946ca7d0e050545
CALLBACK_TARGET: 019f4ca0-2054-77e3-9559-7005c0f9b565
ACCEPTANCE_ROLE: codex_acceptance
CONTEXT_DELTA: context_delta.md
CONTEXT_DELTA_SHA256: 681566a50d3ca0d99a90a7e2095b685d076d40c1c9d573d2049a1b5437427735

## Scope

- `scripts/materialize_baostock_fundamentals_research.py`
- `tests/test_materialize_baostock_fundamentals_research.py`
- `reports/runops/baostock_fundamental_smoke_schema_20260710.json`

## Boundary

Code-only and research-only. No real provider/network/DB/data execution.
`strategy_candidate_available=false` remains unchanged.
