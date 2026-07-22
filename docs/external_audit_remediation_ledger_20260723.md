# External Audit Remediation Ledger

This ledger tracks remediation of
`docs/external_audit_codex_remediation_20260723.md` on the single long-lived
branch `agent/external-audit-codex-remediation-20260723` and Draft PR #126.

## Frozen boundary

- Base branch: `v2-main`
- Base commit: `35b3246e40f8315e2bbef847d995a3b6d3a3b4fc`
- Audit-report commit: `d1f2338b4751d3f251cc40842575bf13f83c0c5f`
- `strategy_candidate_available=false`
- `recommendation_authorized=false`
- `paper_trading_authorized=false`
- `live_trading_authorized=false`
- `automatic_execution_authorized=false`
- Database write count: `0`
- Provider request count: `0`

Fixture-only tests in this branch prove code mechanisms only. They do not close
real-data, provider, Release-asset, or independent-review evidence requirements.

## Baseline

| Command | Result |
|---|---|
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/rongyu/workspace/quant-proj/.venv/bin/python -m pytest -q` | `195 passed in 2.88s` |

## Finding ledger

| Finding ID | Priority | Status | Files and functions | Commit SHA | Tests and execution commands | Result | DB writes | Provider requests | Unverified matters |
|---|---|---|---|---|---|---|---:|---:|---|
| QF-001 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `data/source_identity.py::capture_source_file`; `capture_source_bytes`; `require_trusted_source` | `e9326a1ad7d8371da85b40dfac49fbf235d01bc5` | `pytest -q tests/test_source_capture.py tests/test_accepted_calendar.py tests/test_execution_semantics.py tests/test_event_loop.py`; focused Ruff | `77 passed`; Ruff passed | 0 | 0 | Real provider publication evidence is not part of fixture tests. |
| QF-015 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `SourceIdentity`; `select_source_revision` | `e9326a1ad7d8371da85b40dfac49fbf235d01bc5` | Same QF-001/QF-015 focused suite | `77 passed`; Ruff passed | 0 | 0 | Formal URL-migration receipt evidence remains external. |
| QF-002 | P0 | CODE_FIXED | `DecisionArtifact`; `capture_decision_artifact`; `run_candidate_rebalance`; experimental `run_static_rebalance` grade | `e1d320e2316bc0f5b6424cdbc2a5f26c5a5cd9ad` | `pytest -q tests/test_event_loop.py tests/test_source_capture.py`; focused Ruff | `51 passed`; Ruff passed | 0 | 0 | Python cannot provide a general-purpose sandbox; candidate interface therefore accepts no callable and remains unauthorized for promotion. |
| QF-003 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `markets/universe.py::materialize_universe_partition`; `UniverseMaterialization`; `backtest/event_loop.py::run_candidate_rebalance`; `data/source_identity.py::capture_file_bytes` | `4c4cc22ba928b060e45ecd8528a52dea4921d968` | `pytest -q tests/test_event_loop.py tests/test_source_capture.py`; focused Ruff | `54 passed`; Ruff passed | 0 | 0 | A real complete historical source partition remains external evidence. Fixtures prove only full-partition coverage, lifecycle exclusion, controlled construction, and byte-drift rejection. |
| QF-007 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `event_loop._require_matching_suspension`; `event_loop._inputs`; `markets/a_share.py::decide_fill`; `AShareBar.limit_regime`; `ExecutionInput.limit_regime` | `16b771b074884f2cb3a3c796744d0e9219329b85` | `pytest -q tests/test_markets_a_share.py tests/test_event_loop.py tests/test_execution_semantics.py`; focused Ruff | `82 passed`; Ruff passed | 0 | 0 | Real exchange suspension and price-limit status receipts remain external evidence. |
| QF-009 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `backtest/blocked_orders.py::RetryDecision`; `FillEvent`; `advance_blocked_exit`; `execute_ready_blocked_exit`; `BlockedExitOrder` | `cd584e97ba638635bf2089065e89d54a37ce7c9d` | `pytest -q tests/test_execution_semantics.py tests/test_event_loop.py`; focused Ruff | `71 passed`; Ruff passed | 0 | 0 | Timestamped market-event source and real retrospective daily-bar receipts remain external evidence. |
| QF-006 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `markets/a_share.py::capture_a_share_adjustment_receipt`; `AShareAdjustmentReceipt`; `event_loop._require_a_share_adjustment_receipt`; `ExecutionInput.adjustment_receipt` | `d1d52262aa790a2fc943f5da2513a34633f4217f` | `pytest -q tests/test_event_loop.py tests/test_markets_a_share.py tests/test_execution_semantics.py`; focused Ruff | `87 passed`; Ruff passed | 0 | 0 | Real dividends, splits, delistings, adjustment factors, and action-day completeness receipts remain external evidence. The adjustment-basis path deliberately rejects adjustment-only delisting. |
| QF-008 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `backtest/costs.py::ExecutionCostAssumptions`; `CostStressCase`; `event_loop.run_candidate_rebalance`; candidate base/adverse identities and results | `96cf1505eecd4f3df0977955a8b7df183cb427d7` | `pytest -q tests/test_event_loop.py tests/test_backtest_core.py tests/test_execution_semantics.py`; focused Ruff | `99 passed`; Ruff passed | 0 | 0 | Calibrated spread, impact, fee, capacity, and FX evidence remains external. Gross-only runs remain `GROSS_ONLY_EXPERIMENT` with every authorization flag false. |
| QF-010 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `data/writer.py::_ensure_metadata`; `_bind_target_contract`; `append_rows`; structured ingest lineage; `event_loop.run_candidate_rebalance` partition-manifest binding; controlled CLI append | `b02c0a3bdeb9e75aa076e03d263927c4b1d15d49` | `pytest -q tests/test_data_writer.py tests/test_data_cli.py tests/test_event_loop.py`; focused Ruff | `99 passed`; Ruff passed | 0 | 0 | No production database migration or write was performed. Fixture DuckDB writes are isolated test artifacts and are not counted as project database writes. Existing nonconforming production metadata requires an externally authorized migration. |
| QF-012 | P1 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `event_loop.TerminalAction`; `_terminal_checks`; `_actions`; `portfolio.apply_terminal_action`; `PendingCash` | `f5fbd156df2f0ea073a55fa0734b48dcac6c9a57` | `pytest -q tests/test_backtest_core.py tests/test_event_loop.py`; focused Ruff | `78 passed`; Ruff passed | 0 | 0 | Real terminal-event payment dates, accepted settlement calendars, and source receipts remain external evidence. |
| QF-013 | P1 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `event_loop._execution_evidence_grade`; `StaticRebalanceResult.execution_evidence_grade`; `run_candidate_rebalance` retrospective restriction | `21b49ced16dbd7ee78d62075452b55564c22dc9f` | `pytest -q tests/test_event_loop.py tests/test_execution_semantics.py`; focused Ruff | `80 passed`; Ruff passed | 0 | 0 | Prospective/timestamped execution evidence remains external. Fixture tests prove grade computation and restriction only. |
| QF-004 | P1 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `research/experiments.py::preregister_trial`; `record_holdout_result`; `freeze_experiment_manifest`; `verify_experiment_manifest`; `require_adjusted_holdout_for_candidate` | `90636159f4554422ba38521e5edaa4acf941cdac` | `pytest -q tests/test_experiment_receipts.py tests/test_public_api_boundaries.py`; focused Ruff | `8 passed`; Ruff passed | 0 | 0 | Existing historical trial completeness and prior holdout access cannot be reconstructed from code fixtures; those remain external evidence. |
| QF-005 | P1 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `research/splits.py::build_split_manifest`; `evaluate_split`; `require_split_evaluation_for_candidate`; stable panel `SplitSample` identity and overlap groups | `bc431e4652bd093e667178623677f6eb3f9d11e1` | `pytest -q tests/test_research_splits_identity.py tests/test_public_api_boundaries.py`; focused Ruff | `18 passed`; Ruff passed | 0 | 0 | Strategy-specific HAC or block-bootstrap outputs and effective sample-size evidence remain external. Fixtures prove only the split/evaluation enforcement mechanism. |
| QF-011 | P1 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `research/identity.py::dataset_identity_sha256`; `build_dataset_manifest`; `backtest/event_loop.py::create_stage_plan`; `genesis_stage`; `next_stage`; `run_static_rebalance`; `_hashes`; candidate dataset/split/universe binding | `8debbc2df07b1e8755dde16c2cbf9e282a09cc6d` | `pytest -q tests/test_research_splits_identity.py tests/test_event_loop.py tests/test_public_api_boundaries.py`; focused Ruff | `83 passed`; Ruff passed | 0 | 0 | Existing historical dataset artifacts and stage chains remain unverified; fixtures prove the binding and fail-closed chain mechanisms only. |
| QF-014 | P2 | EXTERNAL_CHECK_PENDING | evidence-room Release assets and independent receipt | PENDING | PENDING | PENDING | 0 | 0 | Requires read-only access to all 10 Release assets and independent reviewer identity. |
| OP-001 | P2 | OPEN_CONFIRMED | `cli._capture_bytes`; `cli._rows` | PENDING | PENDING | PENDING | 0 | 0 | Restricted-memory behavior will be tested locally only. |
| OP-002 | P2 | OPEN_CONFIRMED | `paths.AppPaths.discover`; CLI append gate | PENDING | PENDING | PENDING | 0 | 0 | Installed-wheel behavior must be verified from a built wheel. |

## Phase validation

| Phase | Head SHA | Commands | Result | DB writes | Provider requests |
|---|---|---|---|---:|---:|
| Baseline | `d1f2338b4751d3f251cc40842575bf13f83c0c5f` | Full pytest | `195 passed` | 0 | 0 |
| P0 | `54b6fca59312b50fea38752058e8195e47ac7375` | `ruff check .`; source-tree `pytest -q -o pythonpath=` with `PYTHONPATH=src`; build wheel; force-install wheel in isolated `/tmp` venv; `pip check`; installed-wheel `pytest -q -o pythonpath=` | Ruff passed; source tree `225 passed`; wheel SHA-256 `3e3e3f4d755e7298150039f7596c54a078611c177ef9217abcbe3873311fdea9`; pip check passed; installed wheel `225 passed`. Initial shared-venv installed-package run failed collection because it resolved the old worktree; corrected by isolated current-head wheel validation. | 0 | 0 |
| P1 | `8debbc2df07b1e8755dde16c2cbf9e282a09cc6d` | `ruff check .`; source-tree `pytest -q -o pythonpath=` with `PYTHONPATH=src`; `pip wheel --no-deps`; force-install wheel in isolated `/tmp` venv; `pip check`; installed-wheel `pytest -q -o pythonpath=` | Ruff passed; source tree `243 passed`; wheel SHA-256 `1c437563b270941e9041d36bfeeefcbb6a15ba9fffb37a4e6f6eae95a65b57b7`; pip check passed; installed wheel `243 passed`. First attempt was safely rejected by premature PowerShell variable expansion; second `python -m build` attempt found the shared environment's shadowed `build` package; fixed-path `pip wheel --no-deps` succeeded. | 0 | 0 |
| Final | PENDING | PENDING | PENDING | 0 | 0 |
