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
| QF-001 | P0 | OPEN_CONFIRMED | `data/source_identity.py`; trusted capture entry | PENDING | PENDING | PENDING | 0 | 0 | Real provider publication evidence is not part of fixture tests. |
| QF-015 | P0 | OPEN_CONFIRMED | `SourceIdentity`; `select_source_revision` | PENDING | PENDING | PENDING | 0 | 0 | Formal URL-migration receipt evidence remains external. |
| QF-002 | P0 | OPEN_CONFIRMED | `backtest/event_loop.py`; candidate decision input | PENDING | PENDING | PENDING | 0 | 0 | Python cannot provide a general-purpose sandbox; controlled candidate input must avoid callables. |
| QF-003 | P0 | OPEN_CONFIRMED | `markets/universe.py`; universe materialization | PENDING | PENDING | PENDING | 0 | 0 | A real complete historical source partition remains external evidence. |
| QF-007 | P0 | OPEN_CONFIRMED | `event_loop._inputs`; `markets/a_share.py::decide_fill` | PENDING | PENDING | PENDING | 0 | 0 | Real exchange status receipts remain external evidence. |
| QF-009 | P0 | OPEN_CONFIRMED | `backtest/blocked_orders.py` | PENDING | PENDING | PENDING | 0 | 0 | Timestamped market-event source remains external evidence. |
| QF-006 | P0 | OPEN_CONFIRMED | A-share corporate-action and adjustment-basis inputs | PENDING | PENDING | PENDING | 0 | 0 | Real dividends, splits, delistings, and adjustment-factor receipts remain external evidence. |
| QF-008 | P0 | OPEN_CONFIRMED | `backtest/costs.py`; candidate execution assumptions | PENDING | PENDING | PENDING | 0 | 0 | Calibrated spread, impact, fee, capacity, and FX evidence remains external. |
| QF-010 | P0 | OPEN_CONFIRMED | `data/writer.py`; `_quant_meta.target_contracts` | PENDING | PENDING | PENDING | 0 | 0 | No production database migration or write is authorized by fixture tests. |
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
