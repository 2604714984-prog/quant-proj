from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import subprocess
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_central_db_db2_manager_packet as builder  # noqa: E402
import validate_projects_registry as registry_validator  # noqa: E402


def _packet() -> dict[Path, bytes]:
    return builder.build(
        argparse.Namespace(
            foundation_callback="reports/foundation.json",
            foundation_sha256="a" * 64,
            foundation_commit="b" * 40,
            foundation_tree="c" * 40,
        )
    )


def test_exact_lane_set_and_prompt_contract() -> None:
    files = _packet()
    prompts = {
        path.name
        for path in files
        if path.parent == Path("reports/agent_handoff/central_database_db2")
    }
    assert prompts == {f"lane_{lane.lower()}_dispatch_20260713.md" for lane in builder.QUEUE_ORDER}
    for lane in builder.QUEUE_ORDER:
        body = files[Path(f"reports/agent_handoff/central_database_db2/lane_{lane.lower()}_dispatch_20260713.md")].decode()
        for field in (
            "BATCH_ID:",
            "LANE_ID:",
            "TARGET_DATABASE:",
            "TARGET_TABLES:",
            "SOURCE_POLICY:",
            "PIT_REQUIREMENTS:",
            "QUALITY_THRESHOLDS:",
            "STOP_CONDITIONS:",
        ):
            assert field in body
        for control in (
            "ACQUISITION_AUTHORITY: separate machine-verifiable single-use authority",
            "STAGING_BOUNDARY: isolated content-addressed staging only",
            "RESULT_ACCEPTANCE: fresh independent read-only acceptance",
            "CENTRAL_APPEND_AUTHORITY: separate locked single-writer append authority",
            "ROUTINE_FAST_LANE_LIMIT: already-qualified source and profile",
        ):
            assert control in body
        assert "strategy_candidate_available=false" in body


def test_matrix_and_status_boards_are_complete_and_frozen() -> None:
    files = _packet()
    matrix = list(
        csv.DictReader(
            io.StringIO(
                files[Path("reports/central_database/manager/central_db_full_ingestion_task_matrix_20260713.csv")].decode()
            )
        )
    )
    assert [row["lane_id"] for row in matrix] == builder.QUEUE_ORDER
    assert all(row["status"] == "NOT_DISPATCHED" for row in matrix)
    assert all(row["source_policy"] and row["quality_thresholds"] for row in matrix)
    assert len({row["implementation_branch"] for row in matrix}) == len(matrix)
    a0 = matrix[0]
    for field in ("name", "board", "list_status", "status_effective_from", "status_effective_to"):
        assert field in a0["required_fields"].split("|")
    x1 = next(row for row in matrix if row["lane_id"] == "X1")
    assert set(x1["dependencies"].split("|")) == {
        *(f"A{i}" for i in range(7)),
        *(f"U{i}" for i in range(7)),
    }


def test_manifest_hashes_match_all_generated_files() -> None:
    files = _packet()
    manifest_path = Path("reports/central_database/manager/central_db_db2_manager_packet_manifest_20260713.json")
    manifest = json.loads(files[manifest_path])
    assert manifest["lane_order"] == builder.QUEUE_ORDER
    assert manifest["strategy_candidate_available"] is False
    assert len(manifest["files"]) == len(files) - 1
    for entry in manifest["files"]:
        import hashlib

        path = Path(entry["path"])
        assert hashlib.sha256(files[path]).hexdigest() == entry["sha256"]


def test_no_secret_or_mutation_overclaim_in_generated_packet() -> None:
    text = b"\n".join(_packet().values()).decode()
    assert "API_KEY" not in text
    assert "token=" not in text.lower()
    assert ".duckdb" not in "\n".join(str(path) for path in _packet())
    assert "per-batch Sol/Luna/human review" in text
    assert "cannot itself authorize network or database" in text
    assert "single-use acquisition authority" in text
    assert "isolated staging" in text
    assert "fresh independent read-only acceptance" in text
    assert "separate locked central-append authority" in text
    assert "already-qualified source/profile with unchanged schema, natural key" in text


def test_registry_commit_tree_pairs_are_real_git_objects() -> None:
    registry = yaml.safe_load((ROOT / "registry/projects.yaml").read_text())
    for project in registry["projects"].values():
        commit = project.get("commit") or project.get("accepted_commit") or project.get("base_commit")
        tree = project.get("tree") or project.get("accepted_tree") or project.get("base_tree")
        assert commit and tree
        path = project["path"]
        object_type = subprocess.run(
            ["git", "-C", path, "cat-file", "-t", commit],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        actual_tree = subprocess.run(
            ["git", "-C", path, "rev-parse", f"{commit}^{{tree}}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert object_type == "commit"
        assert actual_tree == tree


def test_registry_foundation_status_is_accepted() -> None:
    registry = yaml.safe_load((ROOT / "registry/projects.yaml").read_text())
    status = registry["projects"]["central_data_ingestion"]["foundation_status"]
    assert "independently accepted" in status
    assert "b9b5d7e9aeeae98696debe94ac31464f56a9d155" in status


def test_registry_passes_the_ci_schema_validator() -> None:
    registry_validator.validate(verify_local_git=False)
    gates = _packet()[
        Path("tasks/in_progress/central-database-full-ingestion-db2-20260713/gate_commands.txt")
    ].decode()
    assert "scripts/validate_projects_registry.py" in gates
