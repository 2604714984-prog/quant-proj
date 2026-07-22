"""Environment-driven project and data paths.

Source, tests, and project documentation live in the repository. Optional
runtime configuration and the mutable DuckDB store may live outside it.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping


class PathConfigurationError(ValueError):
    """Raised when project and mutable-data boundaries overlap."""


def _absolute(value: str | Path, label: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise PathConfigurationError(f"{label} must be an absolute path")
    return path.resolve(strict=False)


def _inside(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def _default_project_root() -> Path:
    """Use the source checkout when present, otherwise the installed package.

    A wheel installs ``quant_system`` below ``site-packages`` and intentionally
    does not bundle repository-level configuration. The package location is a
    stable read-only discovery anchor; the caller's current directory is never
    inferred as a project or mutable-data root.
    """

    source_root = Path(__file__).resolve().parents[2]
    if (source_root / "pyproject.toml").is_file():
        return source_root
    return Path(__file__).resolve().parent


@dataclass(frozen=True)
class AppPaths:
    """Resolved locations for the one-repository application."""

    project_root: Path
    data_root: Path
    database: Path
    data_root_bound: bool

    @classmethod
    def discover(
        cls,
        *,
        project_root: Path | None = None,
        data_root: Path | None = None,
        database_filename: str = "quant_research.duckdb",
        environ: Mapping[str, str] | None = None,
    ) -> AppPaths:
        env = os.environ if environ is None else environ
        detected_root = _default_project_root()
        root_value = env.get("QUANT_PROJECT_ROOT") or project_root or detected_root
        root = _absolute(root_value, "project root")

        explicit_data_root = env.get("QUANT_DATA_ROOT") or data_root
        data_value = explicit_data_root or root.parent / "quant-data"
        data_root = _absolute(data_value, "data root")

        db_override = env.get("QUANT_DB_PATH")
        if db_override:
            database = _absolute(db_override, "database path")
        else:
            if (
                not database_filename
                or Path(database_filename).name != database_filename
                or not database_filename.endswith(".duckdb")
            ):
                raise PathConfigurationError("database filename must be a .duckdb basename")
            database = data_root / database_filename

        if _inside(data_root, root) or _inside(root, data_root) or _inside(database, root):
            raise PathConfigurationError(
                "project and mutable data roots must be separate, non-overlapping paths"
            )
        if not _inside(database, data_root):
            raise PathConfigurationError("database path must be inside QUANT_DATA_ROOT")
        if database.suffix != ".duckdb":
            raise PathConfigurationError("database path must end in .duckdb")
        return cls(
            project_root=root,
            data_root=data_root,
            database=database,
            data_root_bound=explicit_data_root is not None,
        )
