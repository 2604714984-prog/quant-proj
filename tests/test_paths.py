from pathlib import Path

import pytest

from quant_system.paths import AppPaths, PathConfigurationError


def test_paths_default_to_external_sibling(tmp_path: Path) -> None:
    project = tmp_path / "quant-proj"
    project.mkdir()
    paths = AppPaths.discover(project_root=project, environ={})

    assert paths.project_root == project
    assert paths.data_root == tmp_path / "quant-data"
    assert paths.database == tmp_path / "quant-data" / "quant_research.duckdb"
    assert paths.data_root_bound is False


def test_paths_accept_explicit_external_store(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    data = tmp_path / "large-data"
    paths = AppPaths.discover(
        project_root=project,
        environ={
            "QUANT_DATA_ROOT": str(data),
            "QUANT_DB_PATH": str(data / "research.duckdb"),
        },
    )

    assert paths.data_root == data
    assert paths.database == data / "research.duckdb"
    assert paths.data_root_bound is True


def test_paths_accept_configured_data_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    data = tmp_path / "configured-data"

    paths = AppPaths.discover(project_root=project, data_root=data, environ={})

    assert paths.data_root == data
    assert paths.data_root_bound is True


@pytest.mark.parametrize("relative", ["data", "runtime/db"])
def test_paths_reject_database_storage_inside_project(
    tmp_path: Path,
    relative: str,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    data = project / relative
    with pytest.raises(PathConfigurationError, match="non-overlapping"):
        AppPaths.discover(
            project_root=project,
            environ={"QUANT_DATA_ROOT": str(data)},
        )


def test_paths_reject_project_nested_inside_data_root(tmp_path: Path) -> None:
    data = tmp_path / "data"
    project = data / "project"
    project.mkdir(parents=True)

    with pytest.raises(PathConfigurationError, match="non-overlapping"):
        AppPaths.discover(
            project_root=project,
            environ={"QUANT_DATA_ROOT": str(data)},
        )


def test_paths_reject_database_outside_data_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with pytest.raises(PathConfigurationError, match="inside QUANT_DATA_ROOT"):
        AppPaths.discover(
            project_root=project,
            environ={
                "QUANT_DATA_ROOT": str(tmp_path / "data"),
                "QUANT_DB_PATH": str(tmp_path / "elsewhere" / "db.duckdb"),
            },
        )
