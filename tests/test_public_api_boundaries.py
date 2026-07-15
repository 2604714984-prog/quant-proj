from __future__ import annotations

import ast
from pathlib import Path

import quant_system.data as data_api
import quant_system.research as research_api
from quant_system.data.sec_edgar import SecFact
from quant_system.research.stats import newey_west_mean_test


ROOT = Path(__file__).resolve().parents[1]


def test_data_top_level_excludes_experimental_sec_edgar_api() -> None:
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
    assert SecFact.__module__ == "quant_system.data.sec_edgar"


def test_research_top_level_excludes_experimental_advanced_stats_api() -> None:
    assert research_api.__all__ == [
        "dataset_identity_sha256",
        "purged_embargo_train_mask",
        "walk_forward_masks",
    ]
    assert not hasattr(research_api, "newey_west_mean_test")
    assert newey_west_mean_test.__module__ == "quant_system.research.stats"


def test_one_off_evidence_scripts_forbid_runtime_generalization() -> None:
    paths = (
        "scripts/qualify_spy_official_sources.py",
        "scripts/replay_legacy_us_etf_strategies.py",
        "scripts/run_p4_system_validation.py",
        "scripts/run_p4_real_data_validation.py",
    )
    for relative in paths:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        docstring = " ".join((ast.get_docstring(tree) or "").lower().split())
        assert "frozen_one_off_evidence" in docstring
        assert "no_generalization" in docstring
        assert "frozen one-off evidence reproducer" in docstring
        assert "not a general" in docstring or "not a reusable" in docstring
        assert "do not import or generalize" in docstring
