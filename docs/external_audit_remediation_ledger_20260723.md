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

## External review round 1

- Reviewed head: `e38977f0f4448479a3b7ec979928248b745fca48`
- GitHub review ID: `4760627318`
- Review submitted: `2026-07-23T03:50:46Z`
- `external_audit_verdict=REQUEST_CHANGES`
- `code_remediation_complete=false`
- `only_external_evidence_remaining=false`
- GitHub Actions: successful; this does not close research-contract findings.
- The prior P0/P1/final validation records below remain historical execution
  evidence only and are not an external-audit pass.

## Baseline

| Command | Result |
|---|---|
| `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/rongyu/workspace/quant-proj/.venv/bin/python -m pytest -q` | `195 passed in 2.88s` |

## Finding ledger

| Finding ID | Priority | Status | Files and functions | Commit SHA | Tests and execution commands | Result | DB writes | Provider requests | Unverified matters |
|---|---|---|---|---|---|---|---:|---:|---|
| QF-001 | P0 | OPEN_R1 | `data/source_identity.py::capture_source_file`; `capture_source_bytes`; `require_trusted_source` | `e9326a1ad7d8371da85b40dfac49fbf235d01bc5` | `pytest -q tests/test_source_capture.py tests/test_accepted_calendar.py tests/test_execution_semantics.py tests/test_event_loop.py`; focused Ruff | `77 passed`; Ruff passed | 0 | 0 | Round 1: generic callers can self-assert provider metadata and `available_at`; captured bytes are not candidate-qualified evidence. |
| QF-015 | P0 | PARTIAL_R1 | `SourceIdentity`; `select_source_revision` | `e9326a1ad7d8371da85b40dfac49fbf235d01bc5` | Same QF-001/QF-015 focused suite | `77 passed`; Ruff passed | 0 | 0 | Round 1: family/provider/subject binding improved, but migration authority remains self-asserted. |
| QF-002 | P0 | OPEN_R1 | `DecisionArtifact`; `capture_decision_artifact`; `run_candidate_rebalance`; experimental `run_static_rebalance` grade | `e1d320e2316bc0f5b6424cdbc2a5f26c5a5cd9ad` | `pytest -q tests/test_event_loop.py tests/test_source_capture.py`; focused Ruff | `51 passed`; Ruff passed | 0 | 0 | Round 1: caller-supplied weights are not proven to be computed from the captured feature/definition/adapter bytes. |
| QF-003 | P0 | OPEN_R1 | `markets/universe.py::materialize_universe_partition`; `UniverseMaterialization`; `backtest/event_loop.py::run_candidate_rebalance`; `data/source_identity.py::capture_file_bytes` | `4c4cc22ba928b060e45ecd8528a52dea4921d968` | `pytest -q tests/test_event_loop.py tests/test_source_capture.py`; focused Ruff | `54 passed`; Ruff passed | 0 | 0 | Round 1: caller supplies inclusion decisions; the captured rule is not executed. |
| QF-007 | P0 | CLOSED_CODE_R1 | `event_loop._require_matching_suspension`; `event_loop._inputs`; `markets/a_share.py::decide_fill`; `AShareBar.limit_regime`; `ExecutionInput.limit_regime` | `16b771b074884f2cb3a3c796744d0e9219329b85` | `pytest -q tests/test_markets_a_share.py tests/test_event_loop.py tests/test_execution_semantics.py`; focused Ruff | `82 passed`; Ruff passed | 0 | 0 | Real exchange status evidence remains external; round 1 accepted the code mechanism. |
| QF-009 | P0 | CODE_FIXED_R2_EXTERNAL_EVIDENCE_PENDING | `backtest/blocked_orders.py::RetryInstruction`; `NoFillEvent`; `advance_blocked_exit`; `BlockedExitOrder`; `event_loop.blocked_exit_from_receipt` | THIS_COMMIT_PENDING | `pytest -q tests/test_execution_semantics.py tests/test_event_loop.py tests/test_public_api_boundaries.py`; focused Ruff | `87 passed`; Ruff passed; instruction has no reason; pre-open no-fill rejected; instruction/event pairs and consecutive sessions enforced | 0 | 0 | Real timestamped market-event sources remain external evidence. |
| QF-006 | P0 | OPEN_R1 | `markets/a_share.py::capture_a_share_adjustment_receipt`; `AShareAdjustmentReceipt`; `event_loop._require_a_share_adjustment_receipt`; `ExecutionInput.adjustment_receipt` | `d1d52262aa790a2fc943f5da2513a34633f4217f` | `pytest -q tests/test_event_loop.py tests/test_markets_a_share.py tests/test_execution_semantics.py`; focused Ruff | `87 passed`; Ruff passed | 0 | 0 | Round 1: adjustment evidence is not applied to shares, cost basis, cash, prices, or NAV. |
| QF-008 | P0 | CODE_FIXED_R2_EXTERNAL_CALIBRATION_PENDING | `event_loop.run_candidate_rebalance`; explicit base/adverse `TransactionCostModel`; disabled statutory override after base validation | THIS_COMMIT_PENDING | `pytest -q tests/test_event_loop.py tests/test_backtest_core.py`; focused Ruff | `81 passed`; Ruff passed; observed base/adverse regulatory rates `0.0005/0.001` with schedule disabled in both runs | 0 | 0 | Real calibrated spread, impact, fee, capacity, and FX evidence remains external. |
| QF-010 | P0 | CODE_FIXED_R2_EXTERNAL_MIGRATION_PENDING | `cli._package_code_sha256`; `_settings_sha256`; controlled append; existing `writer._bind_target_contract` and `append_rows` | THIS_COMMIT_PENDING | `pytest -q tests/test_data_cli.py tests/test_data_writer.py tests/test_config.py tests/test_paths.py`; focused Ruff | `64 passed`; Ruff passed; CLI code/config digest options removed; stored metadata equals internally recomputed installed-package and active-settings identities | 0 | 0 | No production database migration or write was performed. Existing nonconforming production metadata still requires separately authorized migration. |
| QF-012 | P1 | PARTIAL_R1 | `event_loop.TerminalAction`; `_terminal_checks`; `_actions`; `portfolio.apply_terminal_action`; `PendingCash` | `f5fbd156df2f0ea073a55fa0734b48dcac6c9a57` | `pytest -q tests/test_backtest_core.py tests/test_event_loop.py`; focused Ruff | `78 passed`; Ruff passed | 0 | 0 | Round 1 accepted pending-cash timing; real terminal/payment/calendar evidence remains external. |
| QF-013 | P1 | CLOSED_CODE_R1 | `event_loop._execution_evidence_grade`; `StaticRebalanceResult.execution_evidence_grade`; `run_candidate_rebalance` retrospective restriction | `21b49ced16dbd7ee78d62075452b55564c22dc9f` | `pytest -q tests/test_event_loop.py tests/test_execution_semantics.py`; focused Ruff | `80 passed`; Ruff passed | 0 | 0 | Prospective/timestamped execution evidence remains external; round 1 accepted the code mechanism. |
| QF-004 | P1 | OPEN_R1 | `research/experiments.py::preregister_trial`; `record_holdout_result`; `freeze_experiment_manifest`; `verify_experiment_manifest`; `require_adjusted_holdout_for_candidate` | `90636159f4554422ba38521e5edaa4acf941cdac` | `pytest -q tests/test_experiment_receipts.py tests/test_public_api_boundaries.py`; focused Ruff | `8 passed`; Ruff passed | 0 | 0 | Round 1: in-memory chains can be rebuilt after holdout; timestamps, external anchors, family completeness, pass/alpha rules, and candidate integration are missing. |
| QF-005 | P1 | OPEN_R1 | `research/splits.py::build_split_manifest`; `evaluate_split`; `require_split_evaluation_for_candidate`; stable panel `SplitSample` identity and overlap groups | `bc431e4652bd093e667178623677f6eb3f9d11e1` | `pytest -q tests/test_research_splits_identity.py tests/test_public_api_boundaries.py`; focused Ruff | `18 passed`; Ruff passed | 0 | 0 | Round 1: HAC/block-bootstrap method and effective N are caller assertions rather than computed inference. |
| QF-011 | P1 | OPEN_R1 | `research/identity.py::dataset_identity_sha256`; `build_dataset_manifest`; `backtest/event_loop.py::create_stage_plan`; `genesis_stage`; `next_stage`; `run_static_rebalance`; `_hashes`; candidate dataset/split/universe binding | `8debbc2df07b1e8755dde16c2cbf9e282a09cc6d` | `pytest -q tests/test_research_splits_identity.py tests/test_event_loop.py tests/test_public_api_boundaries.py`; focused Ruff | `83 passed`; Ruff passed | 0 | 0 | Round 1: semantic hashes are not revalidated, costs are not reconciled, stages can restart with one-session plans, and candidate stage hash omits displayed artifacts. |
| QF-014 | P2 | BLOCKED_EXTERNAL_EVIDENCE | Private evidence-room Release `a-share-canonical-evidence-20260712`; repo commit `de38f03466a58b9c786ed35e2cc38abff3e9b0fe`; `MANIFEST.sha256`; bundle/tar/Parquet read-only checks | `c3621cc8b658badf8327c6102c4ce1da6b1aa34a` | `gh release view/download --repo 2604714984-prog/a-share-canonical-evidence-data-room`; `sha256sum -c MANIFEST.sha256`; `git bundle verify`; fresh bundle clone `rev-parse`, `fsck --full --strict`, status and builder hash; tar commit/stream/builder hashes; DuckDB read-only Parquet aggregate query; local source-file existence/hash checks | 10/10 Release assets match; bundle commit `3903977d2480a5ad9be67c4c267cd2a5c5a4bdb8`, tree `40de1564d87c71e3b7695b631fef13d668637ac2`, clean clone and fsck pass; builder `434f2a...1400d9`; tar streams `eac0c3...a4398`; Parquet `136767` rows, `77` symbols, `20180102..20260703`, duplicates `0`, cross-boundary `2779`, crossing non-null `0`, crossing purged `2779`, target/source/target-split/purge-flag/purge-reason mismatches all `0`. Attached checksum file's three nested paths required adapting to the Release's flat layout; repository manifest independently verified all flat assets. | 0 | 0 | No independent reviewer identity or signed external receipt is available. Expected local source DB and universe CSV are absent on this machine, so their live hashes were not rechecked. This remediation executor's successful read-only checks cannot substitute for independent acceptance. |
| OP-001 | P2 | CODE_FIXED | `cli._pinned_input`; `_capture_bytes`; `_jsonl_rows`; `_rows`; `config.WriterSettings.max_input_bytes` | `39795e8a70a65d81706b887c43afb410c0d95fab` | `pytest -q tests/test_data_cli.py tests/test_config.py`; focused Ruff | `18 passed`; Ruff passed; oversized JSON bytes and JSONL rows fail before append, database hash unchanged, target row count `0`, metadata table count `0`; reads bounded to at most 64 KiB | 0 | 0 | Restricted-memory behavior is established by bounded reads and configured aggregate byte/row ceilings; no production database was used. |
| OP-002 | P2 | CODE_FIXED | `paths._default_project_root`; `AppPaths.discover`; `AppPaths.data_root_bound`; `config.load_settings` configured data root; `cli._binding_status`; unbound execute gate and read-only output | `79ec2b59e89e0cf475ab7dba09d13c64dff96402` | `pytest -q tests/test_paths.py tests/test_config.py tests/test_data_cli.py`; focused Ruff; build/install wheel in isolated venv; from unrelated cwd run `quant info`, append dry-run, and append `--execute` without path env | `27 passed`; Ruff passed; wheel SHA-256 `9acf9b5a310c4b8ea60d5f1417e66759195a7dda9ffc43e6d3ccb7788b00e6eb`; info/dry-run reported `UNBOUND_DATA_ROOT`; execute failed with explicit binding error; database absent after rejection | 0 | 0 | Installed-wheel unbound and explicit-environment/config mechanisms verified locally; no production database was used. |

## Phase validation

| Phase | Head SHA | Commands | Result | DB writes | Provider requests |
|---|---|---|---|---:|---:|
| Baseline | `d1f2338b4751d3f251cc40842575bf13f83c0c5f` | Full pytest | `195 passed` | 0 | 0 |
| P0 | `54b6fca59312b50fea38752058e8195e47ac7375` | `ruff check .`; source-tree `pytest -q -o pythonpath=` with `PYTHONPATH=src`; build wheel; force-install wheel in isolated `/tmp` venv; `pip check`; installed-wheel `pytest -q -o pythonpath=` | Ruff passed; source tree `225 passed`; wheel SHA-256 `3e3e3f4d755e7298150039f7596c54a078611c177ef9217abcbe3873311fdea9`; pip check passed; installed wheel `225 passed`. Initial shared-venv installed-package run failed collection because it resolved the old worktree; corrected by isolated current-head wheel validation. | 0 | 0 |
| P1 | `8debbc2df07b1e8755dde16c2cbf9e282a09cc6d` | `ruff check .`; source-tree `pytest -q -o pythonpath=` with `PYTHONPATH=src`; `pip wheel --no-deps`; force-install wheel in isolated `/tmp` venv; `pip check`; installed-wheel `pytest -q -o pythonpath=` | Ruff passed; source tree `243 passed`; wheel SHA-256 `1c437563b270941e9041d36bfeeefcbb6a15ba9fffb37a4e6f6eae95a65b57b7`; pip check passed; installed wheel `243 passed`. First attempt was safely rejected by premature PowerShell variable expansion; second `python -m build` attempt found the shared environment's shadowed `build` package; fixed-path `pip wheel --no-deps` succeeded. | 0 | 0 |
| Final | `17d1f0c04ffbe6bfe1032a79e2d531b034a57e00` (validated implementation/evidence head before this ledger-only closeout) | `ruff check .`; source-tree `pytest -q -o pythonpath=` with `PYTHONPATH=src`; `pip wheel --no-deps`; force-install wheel in isolated `/tmp` venv; `pip check`; installed-wheel `pytest -q -o pythonpath=`; `git diff --check`; authorization/path/finding coverage checks | Ruff passed; source tree `249 passed`; wheel SHA-256 `2cfbc1b0343dfcfd9cec60e57f20f3345b50709937065b6b77aea78da40a2107`; pip check passed; installed wheel `249 passed`; clean diff and worktree; no fixed local path added to source; all 17 finding IDs present. The final ledger-only commit is followed by the same full test gates at the frozen PR head and reported in the PR body. | 0 | 0 |
