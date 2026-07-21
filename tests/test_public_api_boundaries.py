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
        "CalendarIdentityError",
        "CorporateActionIdentity",
        "DatabaseInfo",
        "DataWriteError",
        "QueryResult",
        "SourceIdentity",
        "SourceIdentityError",
        "append_rows",
        "database_info",
        "query",
        "select_corporate_action_revision",
        "select_source_revision",
    ]
    assert not hasattr(data_api, "SecFact")


def test_research_top_level_api_is_small_and_explicit() -> None:
    assert research_api.__all__ == [
        "dataset_identity_sha256",
        "purged_embargo_train_mask",
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


def test_shared_source_does_not_depend_on_specific_family_or_scripts() -> None:
    forbidden_fragments = ("permanent_portfolio", "quant_system.family", "scripts.")
    for path in (ROOT / "src" / "quant_system").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert all(fragment not in source for fragment in forbidden_fragments)
