import hashlib
import json
import os
from pathlib import Path

import duckdb
import pytest

import quant_system.cli as cli_module
from quant_system.cli import main
from quant_system.data.writer import DataWriteError


def _database(path: Path) -> Path:
    with duckdb.connect(str(path)) as connection:
        connection.execute("CREATE SCHEMA market")
        connection.execute(
            "CREATE TABLE market.daily("
            "symbol VARCHAR NOT NULL, trade_date DATE NOT NULL, close DOUBLE)"
        )
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _controlled_args(tmp_path: Path) -> list[str]:
    publication = tmp_path / "publication.txt"
    publication.write_text("published fixture", encoding="utf-8")
    return [
        "--publication-evidence",
        str(publication),
        "--source-url",
        "https://example.test/rows",
        "--available-at",
        "2026-07-14T00:00:00+00:00",
        "--retrieved-at",
        "2026-07-14T00:01:00+00:00",
        "--revision-id",
        "rows-v1",
        "--source-family-id",
        "market-daily",
        "--provider-id",
        "fixture-provider",
        "--subject-id",
        "market.daily",
        "--canonical-owner",
        "quant-system",
        "--contract-version",
        "market.daily.v1",
    ]


def _limited_config(tmp_path: Path, *, max_rows: int, max_bytes: int) -> Path:
    config = tmp_path / "settings.toml"
    config.write_text(
        "\n".join(
            (
                "[database]",
                'filename = "test.duckdb"',
                "[writer]",
                f"max_rows_per_batch = {max_rows}",
                f"max_input_bytes = {max_bytes}",
                "lock_timeout_seconds = 0",
            )
        ),
        encoding="utf-8",
    )
    return config


def test_append_cli_is_dry_run_by_default(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    db = _database(tmp_path / "test.duckdb")
    rows = tmp_path / "rows.json"
    rows.write_text(
        json.dumps(
            [{"symbol": "AAA", "trade_date": "2026-07-14", "close": 10.0}]
        ),
        encoding="utf-8",
    )
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("QUANT_PROJECT_ROOT", str(project))
    monkeypatch.setenv("QUANT_DATA_ROOT", str(tmp_path))

    result = main(
        [
            "data",
            "append",
            "--db",
            str(db),
            "--schema",
            "market",
            "--table",
            "daily",
            "--keys",
            "symbol,trade_date",
            "--input",
            str(rows),
            "--batch-id",
            "batch-001",
            "--source-sha256",
            _sha256(rows),
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "DRY_RUN"
    assert payload["writes"] is False
    assert payload["data_root_binding"] == "EXPLICIT_DATA_ROOT"
    with duckdb.connect(str(db), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)
        assert connection.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema='_quant_meta'"
        ).fetchone() == (0,)


def test_append_cli_requires_execute_and_then_writes(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    db = _database(tmp_path / "test.duckdb")
    rows = tmp_path / "rows.jsonl"
    rows.write_text(
        '{"symbol":"AAA","trade_date":"2026-07-14","close":10.0}\n',
        encoding="utf-8",
    )
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("QUANT_PROJECT_ROOT", str(project))
    monkeypatch.setenv("QUANT_DATA_ROOT", str(tmp_path))

    result = main(
        [
            "data",
            "append",
            "--db",
            str(db),
            "--schema",
            "market",
            "--table",
            "daily",
            "--keys",
            "symbol,trade_date",
            "--input",
            str(rows),
            "--batch-id",
            "batch-001",
            "--source-sha256",
            _sha256(rows),
            *_controlled_args(tmp_path),
            "--execute",
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "COMPLETED"
    assert payload["inserted_rows"] == 1
    with duckdb.connect(str(db), read_only=True) as connection:
        code_sha, config_sha = connection.execute(
            "SELECT code_sha256, config_sha256 FROM _quant_meta.ingest_runs"
        ).fetchone()
    assert code_sha == cli_module._package_code_sha256()
    assert config_sha == cli_module._settings_sha256(
        cli_module.load_settings(None)
    )


def test_unbound_data_root_is_visible_and_execute_fails_before_write(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    project = tmp_path / "installed-package-anchor"
    project.mkdir()
    rows = tmp_path / "rows.jsonl"
    rows.write_text('{"symbol":"AAA","trade_date":"2026-07-14","close":10}\n')
    monkeypatch.setenv("QUANT_PROJECT_ROOT", str(project))
    monkeypatch.delenv("QUANT_DATA_ROOT", raising=False)
    common = [
        "data",
        "append",
        "--schema",
        "market",
        "--table",
        "daily",
        "--keys",
        "symbol,trade_date",
        "--input",
        str(rows),
        "--batch-id",
        "batch-unbound",
        "--source-sha256",
        _sha256(rows),
    ]

    assert main(common) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "DRY_RUN"
    assert payload["data_root_binding"] == "UNBOUND_DATA_ROOT"
    with pytest.raises(ValueError, match="requires QUANT_DATA_ROOT"):
        main([*common, "--execute"])
    assert not (tmp_path / "quant-data" / "quant_research.duckdb").exists()


def test_append_cli_rejects_source_hash_mismatch(
    tmp_path: Path, monkeypatch
) -> None:
    db = _database(tmp_path / "test.duckdb")
    rows = tmp_path / "rows.json"
    rows.write_text('[{"symbol":"AAA","trade_date":"2026-07-14","close":10}]')
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("QUANT_PROJECT_ROOT", str(project))
    monkeypatch.setenv("QUANT_DATA_ROOT", str(tmp_path))

    with pytest.raises(ValueError, match="does not match"):
        main(
            [
                "data",
                "append",
                "--db",
                str(db),
                "--schema",
                "market",
                "--table",
                "daily",
                "--keys",
                "symbol,trade_date",
                "--input",
                str(rows),
                "--batch-id",
                "batch-001",
                "--source-sha256",
                "a" * 64,
            ]
        )


@pytest.mark.parametrize(
    ("suffix", "contents", "max_rows", "max_bytes", "message"),
    [
        (".json", '[{"value":"' + "x" * 1024 + '"}]', 10, 128, "byte limit"),
        (".jsonl", '{"value":1}\n{"value":2}\n{"value":3}\n', 2, 1024, "row limit"),
    ],
)
def test_append_cli_limits_input_before_any_database_write(
    tmp_path: Path,
    monkeypatch,
    suffix: str,
    contents: str,
    max_rows: int,
    max_bytes: int,
    message: str,
) -> None:
    db = _database(tmp_path / "test.duckdb")
    before = _sha256(db)
    rows = tmp_path / f"rows{suffix}"
    rows.write_text(contents, encoding="utf-8")
    config = _limited_config(tmp_path, max_rows=max_rows, max_bytes=max_bytes)
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("QUANT_PROJECT_ROOT", str(project))
    monkeypatch.setenv("QUANT_DATA_ROOT", str(tmp_path))
    real_read = cli_module.os.read

    def bounded_read(descriptor: int, size: int) -> bytes:
        assert size <= 64 * 1024
        return real_read(descriptor, size)

    monkeypatch.setattr(cli_module.os, "read", bounded_read)
    with pytest.raises(ValueError, match=message):
        main(
            [
                "--config",
                str(config),
                "data",
                "append",
                "--db",
                str(db),
                "--schema",
                "market",
                "--table",
                "daily",
                "--keys",
                "symbol,trade_date",
                "--input",
                str(rows),
                "--batch-id",
                "batch-limit",
                "--source-sha256",
                _sha256(rows),
                *_controlled_args(tmp_path),
                "--execute",
            ]
        )

    assert _sha256(db) == before
    with duckdb.connect(str(db), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)
        assert connection.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema='_quant_meta'"
        ).fetchone() == (0,)


def test_append_cli_rejects_duplicate_json_keys(
    tmp_path: Path, monkeypatch
) -> None:
    db = _database(tmp_path / "test.duckdb")
    rows = tmp_path / "rows.json"
    rows.write_text(
        '[{"symbol":"AAA","symbol":"BBB",'
        '"trade_date":"2026-07-14","close":10}]',
        encoding="utf-8",
    )
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("QUANT_PROJECT_ROOT", str(project))
    monkeypatch.setenv("QUANT_DATA_ROOT", str(tmp_path))

    with pytest.raises(ValueError, match="duplicate JSON key"):
        main(
            [
                "data",
                "append",
                "--db",
                str(db),
                "--schema",
                "market",
                "--table",
                "daily",
                "--keys",
                "symbol,trade_date",
                "--input",
                str(rows),
                "--batch-id",
                "batch-001",
                "--source-sha256",
                _sha256(rows),
            ]
        )


def test_append_cli_rejects_input_path_replacement(
    tmp_path: Path, monkeypatch
) -> None:
    db = _database(tmp_path / "test.duckdb")
    rows = tmp_path / "rows.json"
    moved = tmp_path / "moved.json"
    rows.write_text('[{"symbol":"AAA","trade_date":"2026-07-14","close":10}]')
    expected = _sha256(rows)
    original_inode = rows.stat().st_ino
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("QUANT_PROJECT_ROOT", str(project))
    monkeypatch.setenv("QUANT_DATA_ROOT", str(tmp_path))
    real_read = cli_module.os.read
    replaced = False

    def replacing_read(descriptor: int, size: int) -> bytes:
        nonlocal replaced
        if not replaced and os.fstat(descriptor).st_ino == original_inode:
            replaced = True
            os.replace(rows, moved)
            rows.write_text("[]", encoding="utf-8")
        return real_read(descriptor, size)

    monkeypatch.setattr(cli_module.os, "read", replacing_read)
    with pytest.raises(ValueError, match="changed while"):
        main(
            [
                "data",
                "append",
                "--db",
                str(db),
                "--schema",
                "market",
                "--table",
                "daily",
                "--keys",
                "symbol,trade_date",
                "--input",
                str(rows),
                "--batch-id",
                "batch-001",
                "--source-sha256",
                expected,
            ]
        )


def test_database_override_must_remain_inside_data_root(
    tmp_path: Path, monkeypatch
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    outside = _database(tmp_path / "outside.duckdb")
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("QUANT_PROJECT_ROOT", str(project))
    monkeypatch.setenv("QUANT_DATA_ROOT", str(data_root))

    with pytest.raises(ValueError, match="inside the configured data root"):
        main(["data", "inspect", "--db", str(outside)])


def test_append_cli_rejects_hardlink_boundary_alias(
    tmp_path: Path, monkeypatch
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    outside = _database(tmp_path / "outside.duckdb")
    alias = data_root / "allowed.duckdb"
    os.link(outside, alias)
    rows = tmp_path / "rows.json"
    rows.write_text(
        '[{"symbol":"AAA","trade_date":"2026-07-14","close":10}]',
        encoding="utf-8",
    )
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("QUANT_PROJECT_ROOT", str(project))
    monkeypatch.setenv("QUANT_DATA_ROOT", str(data_root))

    with pytest.raises(DataWriteError, match="single-link regular file"):
        main(
            [
                "data",
                "append",
                "--db",
                str(alias),
                "--schema",
                "market",
                "--table",
                "daily",
                "--keys",
                "symbol,trade_date",
                "--input",
                str(rows),
                "--batch-id",
                "batch-001",
                "--source-sha256",
                _sha256(rows),
                *_controlled_args(tmp_path),
                "--execute",
            ]
        )
    with duckdb.connect(str(outside), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM market.daily").fetchone() == (0,)


def test_cli_rejects_bidirectional_project_data_overlap(
    tmp_path: Path, monkeypatch
) -> None:
    db = _database(tmp_path / "test.duckdb")
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("QUANT_PROJECT_ROOT", str(project))
    monkeypatch.setenv("QUANT_DATA_ROOT", str(project.parent))

    with pytest.raises(ValueError, match="non-overlapping|must not overlap"):
        main(["data", "inspect", "--db", str(db)])


def test_cli_never_prints_nonstandard_nan_json(
    tmp_path: Path, monkeypatch
) -> None:
    db = _database(tmp_path / "test.duckdb")
    project = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("QUANT_PROJECT_ROOT", str(project))
    monkeypatch.setenv("QUANT_DATA_ROOT", str(tmp_path))

    with pytest.raises(ValueError, match="Out of range float values"):
        main(
            [
                "data",
                "query",
                "--db",
                str(db),
                "--sql",
                "SELECT CAST('NaN' AS DOUBLE) AS value",
            ]
        )
