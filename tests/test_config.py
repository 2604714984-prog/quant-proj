from pathlib import Path

import pytest

from quant_system.config import ConfigurationError, load_settings


VALID = """
[database]
filename = "research.duckdb"

[writer]
max_rows_per_batch = 5000
max_input_bytes = 1048576
lock_timeout_seconds = 2.5
"""


def test_load_settings_resolves_external_database(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config = project / "settings.toml"
    config.write_text(VALID, encoding="utf-8")

    settings = load_settings(
        config,
        project_root=project,
        environ={"QUANT_DATA_ROOT": str(tmp_path / "data")},
    )

    assert settings.paths.database == tmp_path / "data" / "research.duckdb"
    assert settings.database.filename == "research.duckdb"
    assert settings.writer.max_rows_per_batch == 5000
    assert settings.writer.max_input_bytes == 1_048_576
    assert settings.writer.lock_timeout_seconds == 2.5


def test_load_settings_binds_data_root_from_config(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    data = tmp_path / "configured-data"
    config = project / "settings.toml"
    config.write_text(
        VALID + f'\n[paths]\ndata_root = "{data}"\n',
        encoding="utf-8",
    )

    settings = load_settings(config, project_root=project, environ={})

    assert settings.paths.data_root == data
    assert settings.paths.data_root_bound is True


@pytest.mark.parametrize(
    "replacement, message",
    [
        ("max_rows_per_batch = 5000", "max_rows_per_batch"),
        ("max_input_bytes = 1048576", "max_input_bytes"),
        ("lock_timeout_seconds = 2.5", "lock_timeout_seconds"),
    ],
)
def test_load_settings_rejects_missing_writer_values(
    tmp_path: Path,
    replacement: str,
    message: str,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config = project / "settings.toml"
    config.write_text(VALID.replace(replacement, ""), encoding="utf-8")

    with pytest.raises(ConfigurationError, match=message):
        load_settings(
            config,
            project_root=project,
            environ={"QUANT_DATA_ROOT": str(tmp_path / "data")},
        )


def test_load_settings_rejects_invalid_toml(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    config = project / "settings.toml"
    config.write_text("[database\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="cannot load settings"):
        load_settings(
            config,
            project_root=project,
            environ={"QUANT_DATA_ROOT": str(tmp_path / "data")},
        )


def test_load_settings_uses_code_defaults_without_repository_config(
    tmp_path: Path,
) -> None:
    project = tmp_path / "installed-wheel-runtime"
    project.mkdir()

    settings = load_settings(
        project_root=project,
        environ={"QUANT_DATA_ROOT": str(tmp_path / "data")},
    )

    assert settings.database.filename == "quant_research.duckdb"
    assert settings.writer.max_rows_per_batch == 100_000
    assert settings.writer.max_input_bytes == 64 * 1024 * 1024
    assert settings.writer.lock_timeout_seconds == 5.0
    assert settings.config_path == project / "config" / "settings.toml"


def test_explicit_missing_config_fails_closed(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(ConfigurationError, match="cannot load settings"):
        load_settings(
            tmp_path / "missing.toml",
            project_root=project,
            environ={"QUANT_DATA_ROOT": str(tmp_path / "data")},
        )
