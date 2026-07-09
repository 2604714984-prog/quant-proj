# WINDOWS_WSL2_VNPY_TRADING_SYSTEM_READINESS_T1_20260709

## Classification

Boundary-changing trading-system readiness and dry-run design batch.

This is not an ordinary strategy search batch. This task prepares a vn.py-based trading-system path while preserving strict separation from live trading, broker credentials, real order routing, and actionable recommendations.

## GitHub evidence baseline

Current accepted evidence before this task:

- A-share: R30 produced `liquidity_constrained_reversal` as a research-only local-probe-eligible line, but R30 external audit requires R31 validation-only recheck before any local probe execution.
- US: US30W-R22-002 remains observation-only / local-preservation-limited unless later evidence changes this state.
- `strategy_candidate_available=false` remains the controller default until a separate accepted protocol changes it.

Therefore, vn.py integration must begin as infrastructure readiness, simulation harness, and evidence-contract work only. It must not activate paper/live/broker/order paths.

## Objective

Introduce a vn.py integration plan and source-local dry-run harness that can eventually support A-share and US strategy research outputs, without crossing into execution.

The goal is to prepare the trading-system architecture safely:

1. Define the vn.py adapter boundary.
2. Map quant-proj research labels to non-actionable dry-run events.
3. Build a no-broker, no-credential, no-order dry-run gateway/stub design.
4. Define the evidence required before paper trading is even considered.
5. Preserve a hard separation between research probes, strategy candidates, paper trading, and live trading.

## Scope allowed in T1

Allowed:

- Read vn.py documentation/source structure.
- Create a research-only vn.py integration design.
- Create stub/dry-run adapter interfaces.
- Create mock event/order schema using fake broker and fake account only.
- Create mapping from research strategy outputs to simulated dry-run events.
- Add overclaim tests to prevent broker/order/paper/live/auto wording from being treated as active.
- Define future promotion gates.

Not allowed:

- No broker credential reading.
- No vn.py gateway connection to real broker or quote account.
- No paper-trading account activation.
- No live-trading path.
- No order submission, even simulated as a real paper order.
- No recommendation, ticket, candidate promotion, readiness, or product-route activation.
- No daily signal push.
- No environment secrets.

## Lane 0 - Boundary audit and evidence gate

Tasks:

- T1-0-1: Freeze latest accepted strategy evidence states for A-share and US.
- T1-0-2: Verify whether R31 has accepted `liquidity_constrained_reversal` under validation-only rules. If not, A-share remains research-only pre-probe.
- T1-0-3: Verify whether US30W has remote/mirror preservation and stronger robustness. If not, US remains observation-only.
- T1-0-4: Produce an explicit transition-state board.

Deliverables:

- reports/workspace_dispatch/vnpy_t1_strategy_evidence_gate_20260709.md
- reports/workspace_dispatch/vnpy_t1_transition_state_board_20260709.csv

## Lane 1 - vn.py capability and license inventory

Tasks:

- T1-1-1: Inventory vn.py modules relevant to future A-share/US integration: trader, event engine, gateway, CTA/backtester, alpha module, and risk controls.
- T1-1-2: Record license and dependency risks.
- T1-1-3: Identify which modules are safe to reference now and which are forbidden until later authorization.

Deliverables:

- reports/workspace_dispatch/vnpy_t1_capability_inventory_20260709.md
- reports/workspace_dispatch/vnpy_t1_module_boundary_matrix_20260709.csv

## Lane 2 - Dry-run adapter design, no broker

Tasks:

- T1-2-1: Design a dry-run adapter that accepts only research events, not real orders.
- T1-2-2: Define fake gateway / null gateway semantics.
- T1-2-3: Define event schema for research signal, simulated order intent, simulated fill, rejection, and audit log.
- T1-2-4: Ensure all schemas are labelled `DRY_RUN_ONLY` and `NOT_ORDER`.

Deliverables:

- reports/workspace_dispatch/vnpy_t1_dry_run_adapter_design_20260709.md
- reports/workspace_dispatch/vnpy_t1_dry_run_event_schema_20260709.json

## Lane 3 - Strategy-label mapping

Tasks:

- T1-3-1: Map quant-proj labels to vn.py dry-run states.
- T1-3-2: Ensure `LOCAL_RESEARCH_PROBE_ELIGIBLE` does not become a candidate or order.
- T1-3-3: Define future promotion gates: research probe -> candidate review -> paper authorization -> live authorization.

Deliverables:

- reports/workspace_dispatch/vnpy_t1_strategy_label_mapping_20260709.csv
- reports/workspace_dispatch/vnpy_t1_future_promotion_gate_design_20260709.md

## Lane 4 - Safety and overclaim tests

Tasks:

- T1-4-1: Add tests or report checks that fail if dry-run outputs are described as broker orders, paper trades, live trades, candidates, recommendations, or readiness.
- T1-4-2: Add negative examples for A-share and US strategy labels.
- T1-4-3: Add explicit secret/credential access block.

Deliverables:

- reports/workspace_dispatch/vnpy_t1_overclaim_test_plan_20260709.md
- tests/test_vnpy_t1_trading_boundary_overclaim.py if code/tests are changed.

## Lane 5 - Future architecture memo

Tasks:

- T1-5-1: Produce a migration architecture for future vn.py use.
- T1-5-2: Separate A-share and US paths.
- T1-5-3: Define minimum evidence needed before paper trading can be discussed.

Deliverables:

- reports/workspace_dispatch/vnpy_t1_future_trading_architecture_memo_20260709.md
- reports/agent_handoff/vnpy_t1_external_audit_prompt_20260709.md

## Validation

- JSON parse PASS where applicable.
- CSV parse PASS where applicable.
- git diff check PASS.
- focused pytest PASS if code/tests changed.
- No credential or env access.
- No active gateway connection.
- No broker/paper/live/order path.
- No strategy candidate promotion.

## Stop conditions

Stop and return `BOUNDARY_BLOCKED` if any task requires:

- broker credential or account access.
- real gateway connection.
- paper/live order submission.
- daily signal push.
- candidate/readiness/product-route activation.
- secret/env file access.
- treating research probe labels as orders or recommendations.

## Callback envelope

Return callback with batch id, repo, branch, commit, tree, tasks completed, artifacts, validation, vn.py capability status, dry-run adapter status, strategy evidence gate status, boundary result, fixes required, and next source action.
