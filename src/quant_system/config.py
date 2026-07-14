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
    read_only_default: bool


@dataclass(frozen=True)
class WriterSettings:
    max_rows_per_batch: int
    lock_timeout_seconds: float


@dataclass(frozen=True)
class AppSettings:
    paths: AppPaths
    database: DatabaseSettings
    writer: WriterSettings
    config_path: Path


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
    config_path = Path(configured_path).expanduser() if configured_path else path
    if config_path is None:
        config_path = initial_paths.project_root / "config" / "settings.toml"
    if not config_path.is_absolute():
        config_path = initial_paths.project_root / config_path
    config_path = config_path.resolve(strict=False)
    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError(f"cannot load settings: {config_path}") from exc

    database_raw = _table(raw, "database")
    writer_raw = _table(raw, "writer")
    filename = database_raw.get("filename")
    read_only_default = database_raw.get("read_only_default")
    max_rows = writer_raw.get("max_rows_per_batch")
    lock_timeout = writer_raw.get("lock_timeout_seconds")

    if not isinstance(filename, str):
        raise ConfigurationError("database.filename must be a string")
    if type(read_only_default) is not bool:
        raise ConfigurationError("database.read_only_default must be boolean")
    if type(max_rows) is not int or not 1 <= max_rows <= 1_000_000:
        raise ConfigurationError("writer.max_rows_per_batch must be 1..1000000")
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
        database=DatabaseSettings(filename=filename, read_only_default=read_only_default),
        writer=WriterSettings(
            max_rows_per_batch=max_rows,
            lock_timeout_seconds=float(lock_timeout),
        ),
        config_path=config_path,
    )
