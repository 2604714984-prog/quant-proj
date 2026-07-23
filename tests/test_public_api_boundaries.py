from __future__ import annotations

import ast
from pathlib import Path

import quant_system.data as data_api
import quant_system.research as research_api


ROOT = Path(__file__).resolve().parents[1]


def test_data_top_level_api_is_small_and_explicit() -> None:
    assert data_api.__all__ == [
        "AcceptedSession",
        "AcceptedSessionCalendar",
        "AppendResult",
        "CalendarIdentity",
        "CalendarIdentityError",
        "CorporateActionIdentity",
        "DatabaseInfo",
        "DataWriteError",
        "QueryResult",
        "SourceCaptureReceipt",
        "SourceIdentity",
        "SourceIdentityError",
        "TypedObservationReceipt",
        "append_rows",
        "capture_file_bytes",
        "capture_file_digest",
        "capture_github_release_asset",
        "capture_source_bytes",
        "capture_source_file",
        "parse_provider_observation",
        "calendar_identity_sha256",
        "database_info",
        "query",
        "require_trusted_source",
        "require_provider_qualified_source",
        "require_typed_observation",
        "select_corporate_action_revision",
        "select_source_revision",
        "session_dates_sha256",
        "session_rows_sha256",
    ]
    assert not hasattr(data_api, "SecFact")


def test_research_top_level_api_is_small_and_explicit() -> None:
    assert research_api.__all__ == [
        "dataset_identity_sha256",
        "build_dataset_manifest",
        "capture_dataset_manifest",
        "DatasetManifest",
        "TransformationReceipt",
        "ExperimentEvent",
        "ExperimentAnchorReceipt",
        "ExperimentLedgerReceipt",
        "ExperimentManifest",
        "FinalRunReceipt",
        "HoldoutResultReceipt",
        "SplitEvaluation",
        "SplitEvaluationPlan",
        "SplitManifest",
        "SplitSample",
        "build_split_evaluation_plan",
        "build_split_manifest",
        "capture_holdout_result",
        "capture_family_anchor",
        "capture_final_run_receipt",
        "evaluate_split",
        "execute_transformation",
        "freeze_experiment_manifest",
        "load_split_manifest",
        "preregister_trial",
        "persist_experiment_ledger",
        "purged_embargo_train_mask",
        "record_holdout_family_results",
        "record_holdout_result",
        "require_adjusted_holdout_for_candidate",
        "require_split_evaluation_for_candidate",
        "serialize_split_manifest",
        "verify_experiment_manifest",
        "walk_forward_masks",
    ]
    assert not hasattr(research_api, "newey_west_mean_test")


def test_active_tree_has_no_governance_control_plane_or_sidecars() -> None:
    forbidden = (
        ROOT / "reports" / "agent_handoff",
        ROOT / "reports" / "external_audit",
        ROOT / "reports" / "validation",
    )
    assert all(not path.exists() or not any(path.rglob("*")) for path in forbidden)
    definitions = tuple((ROOT / "research" / "definitions").glob("*.json"))
    results = tuple((ROOT / "research" / "reports").glob("*.json"))
    assert len(definitions) <= 1
    assert len(results) <= 1
    assert not tuple(ROOT.rglob("*.sha256"))


def test_terminal_research_is_not_an_active_tree_dependency() -> None:
    terminal_roots = (
        ROOT / "research" / "archive",
        ROOT / "research" / "reports",
        ROOT / "research" / "results",
    )
    assert all(not path.exists() or not any(path.rglob("*")) for path in terminal_roots)


def test_at_most_one_adapter_and_no_script_to_script_import() -> None:
    scripts_root = ROOT / "scripts"
    scripts = tuple(sorted(scripts_root.glob("*.py"))) if scripts_root.exists() else ()
    assert len(scripts) <= 1
    for path in scripts:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module != "scripts"
                assert not (node.module or "").startswith("scripts.")
            elif isinstance(node, ast.Import):
                assert all(not alias.name.startswith("scripts") for alias in node.names)


def test_only_canonical_writer_can_open_duckdb_for_writes() -> None:
    source_roots = (ROOT / "src", ROOT / "scripts", ROOT / "research")
    canonical_writer = ROOT / "src" / "quant_system" / "data" / "writer.py"
    for source_root in source_roots:
        if not source_root.exists():
            continue
        for path in source_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "duckdb"
                    and node.func.attr == "connect"
                ):
                    continue
                if path == canonical_writer:
                    continue
                read_only = next(
                    (keyword.value for keyword in node.keywords if keyword.arg == "read_only"),
                    None,
                )
                assert isinstance(read_only, ast.Constant) and read_only.value is True, (
                    f"{path.relative_to(ROOT)} opens DuckDB outside the canonical writer "
                    "without read_only=True"
                )


def test_shared_source_does_not_depend_on_specific_family_or_scripts() -> None:
    forbidden_fragments = ("permanent_portfolio", "quant_system.family", "scripts.")
    for path in (ROOT / "src" / "quant_system").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert all(fragment not in source for fragment in forbidden_fragments)
