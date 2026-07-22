"""Small TOML configuration surface for the V2 runtime."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tomllib
from typing import Any, Mapping

from .paths import AppPaths


class ConfigurationError(ValueError):
    """Raised for malformed runtime settings."""


@dataclass(frozen=True)
class DatabaseSettings:
    filename: str


@dataclass(frozen=True)
class WriterSettings:
    max_rows_per_batch: int
    max_input_bytes: int
    lock_timeout_seconds: float


@dataclass(frozen=True)
class AppSettings:
    paths: AppPaths
    database: DatabaseSettings
    writer: WriterSettings
    config_path: Path


DEFAULT_DATABASE_FILENAME = "quant_research.duckdb"
DEFAULT_MAX_ROWS_PER_BATCH = 100_000
DEFAULT_MAX_INPUT_BYTES = 64 * 1024 * 1024
DEFAULT_LOCK_TIMEOUT_SECONDS = 5.0


def _built_in_settings() -> dict[str, Any]:
    return {
        "database": {"filename": DEFAULT_DATABASE_FILENAME},
        "writer": {
            "max_rows_per_batch": DEFAULT_MAX_ROWS_PER_BATCH,
            "max_input_bytes": DEFAULT_MAX_INPUT_BYTES,
            "lock_timeout_seconds": DEFAULT_LOCK_TIMEOUT_SECONDS,
        },
    }


def _table(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name)
    if not isinstance(value, dict):
        raise ConfigurationError(f"[{name}] table is required")
    return value


def load_settings(
    path: Path | None = None,
    *,
    project_root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> AppSettings:
    env = os.environ if environ is None else environ
    initial_paths = AppPaths.discover(project_root=project_root, environ=env)
    configured_path = env.get("QUANT_CONFIG")
    explicit_config = configured_path is not None or path is not None
    config_path = Path(configured_path).expanduser() if configured_path else path
    if config_path is None:
        config_path = initial_paths.project_root / "config" / "settings.toml"
    if not config_path.is_absolute():
        config_path = initial_paths.project_root / config_path
    config_path = config_path.resolve(strict=False)
    if config_path.is_file():
        try:
            raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ConfigurationError(f"cannot load settings: {config_path}") from exc
    elif explicit_config:
        raise ConfigurationError(f"cannot load settings: {config_path}")
    else:
        raw = _built_in_settings()

    database_raw = _table(raw, "database")
    writer_raw = _table(raw, "writer")
    filename = database_raw.get("filename")
    max_rows = writer_raw.get("max_rows_per_batch")
    max_input_bytes = writer_raw.get("max_input_bytes")
    lock_timeout = writer_raw.get("lock_timeout_seconds")

    if not isinstance(filename, str):
        raise ConfigurationError("database.filename must be a string")
    if type(max_rows) is not int or not 1 <= max_rows <= 1_000_000:
        raise ConfigurationError("writer.max_rows_per_batch must be 1..1000000")
    if type(max_input_bytes) is not int or not 1 <= max_input_bytes <= 1_073_741_824:
        raise ConfigurationError("writer.max_input_bytes must be 1..1073741824")
    if (
        type(lock_timeout) not in {int, float}
        or not 0 <= float(lock_timeout) <= 300
    ):
        raise ConfigurationError("writer.lock_timeout_seconds must be 0..300")

    paths = AppPaths.discover(
        project_root=initial_paths.project_root,
        database_filename=filename,
        environ=env,
    )
    return AppSettings(
        paths=paths,
        database=DatabaseSettings(filename=filename),
        writer=WriterSettings(
            max_rows_per_batch=max_rows,
            max_input_bytes=max_input_bytes,
            lock_timeout_seconds=float(lock_timeout),
        ),
        config_path=config_path,
    )
