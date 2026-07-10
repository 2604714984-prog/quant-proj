TASK_ID: AUTOMATED_RESEARCH_FACTORY_V1_S1_CONTRACT_20260711
STATUS: DESIGN_ONLY
TARGET_PROJECT: quant_workspace
RECOMMENDED_AGENT: codex_dev
MODEL_ROLE: executor
MODEL: gpt-5.6-luna
REASONING_EFFORT: medium
SOURCE_COMMIT: 29418d23c4cc07c3e167f355bd5cf31a0bed4783
SOURCE_TREE: 3504e1a538b2903ae51d12d90fbdaa98757da03d
AUTOMATED_GATE_COMMANDS: gate_commands.txt
AUTOMATED_GATE_COMMANDS_SHA256: c75446d4b428bdb23d7026623a2f00d74ff056a77c2ae49cfa188dce85145513
CALLBACK_TARGET: 019f4ca0-2054-77e3-9559-7005c0f9b565
ACCEPTANCE_ROLE: codex_acceptance
CONTEXT_DELTA: context_delta.md
CONTEXT_DELTA_SHA256: d74fd9b785ac2fd5eef427f24301876b13bf6bc87cf058da7dbedcae62632175

# Scope

The assigned Luna executor, not Dispatcher, creates exactly `runbooks/automated_research_factory/research_state_machine.md`, `research_artifact_contract.md`, and `strategy_card_schema.json`. Dispatcher creates no deliverable drafts. Do not dispatch a strategy run or change any source project.

The pilot is deferred until the S1 automated gate is green and separate Luna/high acceptance is green. No provider/network, DB/cache/data write, candidate/readiness/product/trading path, or secret access is authorized.
