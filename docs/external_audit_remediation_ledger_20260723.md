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
| QF-001 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `data/source_identity.py::capture_source_file`; `capture_source_bytes`; `require_trusted_source` | THIS_COMMIT_PENDING | `pytest -q tests/test_source_capture.py tests/test_accepted_calendar.py tests/test_execution_semantics.py tests/test_event_loop.py`; focused Ruff | `77 passed`; Ruff passed | 0 | 0 | Real provider publication evidence is not part of fixture tests. |
| QF-015 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `SourceIdentity`; `select_source_revision` | THIS_COMMIT_PENDING | Same QF-001/QF-015 focused suite | `77 passed`; Ruff passed | 0 | 0 | Formal URL-migration receipt evidence remains external. |
| QF-002 | P0 | CODE_FIXED | `DecisionArtifact`; `capture_decision_artifact`; `run_candidate_rebalance`; experimental `run_static_rebalance` grade | THIS_COMMIT_PENDING | `pytest -q tests/test_event_loop.py tests/test_source_capture.py`; focused Ruff | `51 passed`; Ruff passed | 0 | 0 | Python cannot provide a general-purpose sandbox; candidate interface therefore accepts no callable and remains unauthorized for promotion. |
| QF-003 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `markets/universe.py::materialize_universe_partition`; `UniverseMaterialization`; `backtest/event_loop.py::run_candidate_rebalance`; `data/source_identity.py::capture_file_bytes` | THIS_COMMIT_PENDING | `pytest -q tests/test_event_loop.py tests/test_source_capture.py`; focused Ruff | `54 passed`; Ruff passed | 0 | 0 | A real complete historical source partition remains external evidence. Fixtures prove only full-partition coverage, lifecycle exclusion, controlled construction, and byte-drift rejection. |
| QF-007 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `event_loop._require_matching_suspension`; `event_loop._inputs`; `markets/a_share.py::decide_fill`; `AShareBar.limit_regime`; `ExecutionInput.limit_regime` | THIS_COMMIT_PENDING | `pytest -q tests/test_markets_a_share.py tests/test_event_loop.py tests/test_execution_semantics.py`; focused Ruff | `82 passed`; Ruff passed | 0 | 0 | Real exchange suspension and price-limit status receipts remain external evidence. |
| QF-009 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `backtest/blocked_orders.py::RetryDecision`; `FillEvent`; `advance_blocked_exit`; `execute_ready_blocked_exit`; `BlockedExitOrder` | THIS_COMMIT_PENDING | `pytest -q tests/test_execution_semantics.py tests/test_event_loop.py`; focused Ruff | `71 passed`; Ruff passed | 0 | 0 | Timestamped market-event source and real retrospective daily-bar receipts remain external evidence. |
| QF-006 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `markets/a_share.py::capture_a_share_adjustment_receipt`; `AShareAdjustmentReceipt`; `event_loop._require_a_share_adjustment_receipt`; `ExecutionInput.adjustment_receipt` | THIS_COMMIT_PENDING | `pytest -q tests/test_event_loop.py tests/test_markets_a_share.py tests/test_execution_semantics.py`; focused Ruff | `87 passed`; Ruff passed | 0 | 0 | Real dividends, splits, delistings, adjustment factors, and action-day completeness receipts remain external evidence. The adjustment-basis path deliberately rejects adjustment-only delisting. |
| QF-008 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `backtest/costs.py::ExecutionCostAssumptions`; `CostStressCase`; `event_loop.run_candidate_rebalance`; candidate base/adverse identities and results | THIS_COMMIT_PENDING | `pytest -q tests/test_event_loop.py tests/test_backtest_core.py tests/test_execution_semantics.py`; focused Ruff | `99 passed`; Ruff passed | 0 | 0 | Calibrated spread, impact, fee, capacity, and FX evidence remains external. Gross-only runs remain `GROSS_ONLY_EXPERIMENT` with every authorization flag false. |
| QF-010 | P0 | CODE_FIXED_EXTERNAL_EVIDENCE_PENDING | `data/writer.py::_ensure_metadata`; `_bind_target_contract`; `append_rows`; structured ingest lineage; `event_loop.run_candidate_rebalance` partition-manifest binding; controlled CLI append | THIS_COMMIT_PENDING | `pytest -q tests/test_data_writer.py tests/test_data_cli.py tests/test_event_loop.py`; focused Ruff | `99 passed`; Ruff passed | 0 | 0 | No production database migration or write was performed. Fixture DuckDB writes are isolated test artifacts and are not counted as project database writes. Existing nonconforming production metadata requires an externally authorized migration. |
| QF-012 | P1 | OPEN_CONFIRMED | `TerminalAction`; `Portfolio.apply_terminal_action` | PENDING | PENDING | PENDING | 0 | 0 | Real payment-date and settlement evidence remains external. |
| QF-013 | P1 | OPEN_CONFIRMED | execution evidence grade and candidate restriction | PENDING | PENDING | PENDING | 0 | 0 | Prospective/timestamped execution evidence remains external. |
| QF-004 | P1 | OPEN_CONFIRMED | append-only experiment receipt and holdout lock | PENDING | PENDING | PENDING | 0 | 0 | Existing historical trial completeness cannot be reconstructed from code fixtures. |
| QF-005 | P1 | OPEN_CONFIRMED | split manifest, overlap handling, effective N | PENDING | PENDING | PENDING | 0 | 0 | Strategy-specific inference outputs remain external. |
| QF-011 | P1 | OPEN_CONFIRMED | dataset manifest and stage-chain contract | PENDING | PENDING | PENDING | 0 | 0 | Existing historical stage chains remain unverified. |
| QF-014 | P2 | EXTERNAL_CHECK_PENDING | evidence-room Release assets and independent receipt | PENDING | PENDING | PENDING | 0 | 0 | Requires read-only access to all 10 Release assets and independent reviewer identity. |
| OP-001 | P2 | OPEN_CONFIRMED | `cli._capture_bytes`; `cli._rows` | PENDING | PENDING | PENDING | 0 | 0 | Restricted-memory behavior will be tested locally only. |
| OP-002 | P2 | OPEN_CONFIRMED | `paths.AppPaths.discover`; CLI append gate | PENDING | PENDING | PENDING | 0 | 0 | Installed-wheel behavior must be verified from a built wheel. |

## Phase validation

| Phase | Head SHA | Commands | Result | DB writes | Provider requests |
|---|---|---|---|---:|---:|
| Baseline | `d1f2338b4751d3f251cc40842575bf13f83c0c5f` | Full pytest | `195 passed` | 0 | 0 |
| P0 | PENDING | PENDING | PENDING | 0 | 0 |
| P1 | PENDING | PENDING | PENDING | 0 | 0 |
| Final | PENDING | PENDING | PENDING | 0 | 0 |
