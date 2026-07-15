from __future__ import annotations

import csv
from datetime import date, timedelta
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace

import duckdb
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_cleanroom_family66.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("run_cleanroom_family66", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _raw(module, signal_date: date, *, incomplete: int = 0):
    return module.RawCohort(
        signal_date,
        signal_date + timedelta(days=1),
        signal_date + timedelta(days=2),
        3 + incomplete,
        3,
        5,
        5,
        10,
        10,
        0.10,
        0.01,
        0.0,
        0.0,
        0.0,
    )


def _full_synthetic_raw(module):
    starts = (
        date(2019, 1, 1),
        date(2022, 1, 1),
        date(2024, 1, 1),
        date(2026, 1, 1),
    )
    return tuple(
        _raw(module, start + timedelta(days=offset))
        for start in starts
        for offset in range(100)
    )


def test_definition_freezes_lineage_data_mechanics_and_exact_48_gates() -> None:
    module = _load_script()
    definition, digest = module._load_definition()

    assert digest == module.DEFINITION_SHA256
    assert definition["family_number"] == 66
    assert definition["source_contract"]["controlling_packet_sha256"] == (
        "d879c5e9d3a3261b0c8f1265628b3ab4c5a5b0d598ec6af6781b8c363239907e"
    )
    assert definition["source_contract"]["feature_dataset_manifest_sha256"] == (
        "e07d6346d919b07f6ddd7b3b8c084136857a2782c6e5cfb80231f863d2accba2"
    )
    assert definition["event_contract"]["holding_sessions"] == 15
    assert definition["cost_contract"]["strict_gate_bps_per_side"] == 100
    assert definition["inference"] == {
        "split": "holdout",
        "series_order": [
            "signal_return",
            "excess_vs_breakout_only",
            "excess_vs_eligible",
            "excess_vs_510300",
            "excess_vs_511880",
        ],
        "observation": "retained signal-date cohort",
        "circular_moving_block_signal_dates": 20,
        "bootstrap_draws": 50000,
        "prng": "NumPy Generator with PCG64",
        "seed": 20260710,
        "null_centering": "subtract observed sample mean before resampling",
        "one_sided_p_value": (
            "(1 + count(centered_bootstrap_mean >= observed_uncentered_mean)) / "
            "(bootstrap_draws + 1)"
        ),
        "lower_bound": "linear alpha-quantile of uncentered bootstrap sample means",
        "alpha": 0.0007575757575757576,
        "bh_family_size": 5,
        "bh_order": "raw p ascending; ties by frozen series_order",
        "bh_adjusted_p": (
            "for rank i, min over j>=i of min(1, m * p_(j) / j), returned in input order"
        ),
    }
    assert len(definition["gate_contract"]["gate_order"]) == 48
    assert definition["gate_contract"]["gate_order"][2] == (
        "global.every_candidate_event_and_label_complete"
    )
    assert definition["lineage_and_execution_boundary"]["strategy_candidate_available"] is False
    assert definition["lineage_and_execution_boundary"]["original_status"] == (
        "REJECTED_BY_METHODOLOGY_RECOMPUTE_GATE"
    )
    assert definition["output_contract"] == {
        "runtime_timestamp_in_content_addressed_result": False,
        "false_fixed_time_permitted": False,
        "determinism": (
            "identical accepted definition, input bytes, and source commit must produce "
            "byte-identical result JSON"
        ),
    }


def test_default_mode_opens_no_database_socket_or_output(monkeypatch, capsys) -> None:
    module = _load_script()
    monkeypatch.setattr(
        module.duckdb, "connect", lambda *args, **kwargs: pytest.fail("database opened")
    )
    monkeypatch.setattr(module, "_publish", lambda *args, **kwargs: pytest.fail("output written"))
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: pytest.fail("socket opened"))

    assert module.main([]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "status": "VALIDATE_DEFINITION_ONLY",
        "definition_sha256": module.DEFINITION_SHA256,
        "database_opened": False,
        "network_used": False,
        "output_written": False,
    }


def test_default_subprocess_uses_own_worktree_without_pythonpath_or_side_effects(
    tmp_path,
) -> None:
    probe = f"""
import contextlib
import io
import json
from pathlib import Path
import runpy
import socket

namespace = runpy.run_path({str(SCRIPT)!r}, run_name='family66_import_probe')

def forbidden(*args, **kwargs):
    raise AssertionError('default mode attempted a forbidden side effect')

namespace['duckdb'].connect = forbidden
namespace['_publish'] = forbidden
socket.socket = forbidden
captured = io.StringIO()
with contextlib.redirect_stdout(captured):
    return_code = namespace['main']([])
module_path = Path(
    namespace['assign_whole_label_split'].__code__.co_filename
).resolve()
print(json.dumps({{
    'return_code': return_code,
    'module_path': str(module_path),
    'payload': json.loads(captured.getvalue()),
}}, sort_keys=True))
"""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    observed = json.loads(completed.stdout)

    assert observed == {
        "return_code": 0,
        "module_path": str(
            (ROOT / "src/quant_system/research/event_cohort.py").resolve()
        ),
        "payload": {
            "status": "VALIDATE_DEFINITION_ONLY",
            "definition_sha256": _load_script().DEFINITION_SHA256,
            "database_opened": False,
            "network_used": False,
            "output_written": False,
        },
    }
    assert tuple(tmp_path.iterdir()) == ()


def test_synthetic_complete_panel_assembles_exact_48_gates() -> None:
    module = _load_script()
    definition, _ = module._load_definition()
    rows, purged, incomplete_dates, incomplete_events, incomplete_labels = module._observations(
        _full_synthetic_raw(module), definition, bps_per_side=100
    )
    checks = module._gate_checks(
        rows,
        definition,
        incomplete_events=incomplete_events,
        incomplete_label_dates=incomplete_labels,
        incomplete_cohort_dates=incomplete_dates,
    )

    assert purged == incomplete_dates == incomplete_events == incomplete_labels == 0
    assert len(checks) == 48
    assert [item["gate_id"] for item in checks] == definition["gate_contract"]["gate_order"]
    assert all(item["passed"] for item in checks)


def test_incomplete_candidate_event_fails_global_gate_instead_of_disappearing() -> None:
    module = _load_script()
    definition, _ = module._load_definition()
    raw = list(_full_synthetic_raw(module))
    raw[0] = _raw(module, raw[0].signal_date, incomplete=1)
    rows, _, _, incomplete_events, incomplete_labels = module._observations(
        raw, definition, bps_per_side=100
    )
    checks = module._gate_checks(
        rows,
        definition,
        incomplete_events=incomplete_events,
        incomplete_label_dates=incomplete_labels,
        incomplete_cohort_dates=0,
    )
    completeness = checks[2]

    assert incomplete_events == 1
    assert completeness["gate_id"] == "global.every_candidate_event_and_label_complete"
    assert completeness["observed"] == {
        "incomplete_candidate_events": 1,
        "incomplete_label_dates": 0,
        "incomplete_cohort_dates": 0,
    }
    assert completeness["passed"] is False


def test_missing_t_plus_label_inside_split_fails_global_gate() -> None:
    module = _load_script()
    definition, _ = module._load_definition()
    raw = list(_full_synthetic_raw(module))
    row = raw[-1]
    raw[-1] = module.RawCohort(
        row.signal_date,
        None,
        None,
        row.signal_candidate_count,
        0,
        row.breakout_candidate_count,
        0,
        row.eligible_candidate_count,
        0,
        None,
        None,
        None,
        None,
        None,
    )
    rows, _, _, incomplete_events, incomplete_labels = module._observations(
        raw, definition, bps_per_side=100
    )
    checks = module._gate_checks(
        rows,
        definition,
        incomplete_events=incomplete_events,
        incomplete_label_dates=incomplete_labels,
        incomplete_cohort_dates=0,
    )

    assert incomplete_labels == 1
    assert checks[2]["passed"] is False


def test_cross_split_label_is_purged_before_statistics() -> None:
    module = _load_script()
    definition, _ = module._load_definition()
    row = module.RawCohort(
        date(2021, 12, 30),
        date(2021, 12, 31),
        date(2022, 1, 20),
        3,
        3,
        5,
        5,
        10,
        10,
        0.1,
        0.01,
        0.0,
        0.0,
        0.0,
    )
    rows, purged, incomplete_dates, incomplete_events, incomplete_labels = module._observations(
        (row,), definition, bps_per_side=100
    )

    assert rows == ()
    assert purged == 1
    assert incomplete_dates == incomplete_events == incomplete_labels == 0


def test_outside_split_complete_cohort_is_excluded_without_inflating_purge() -> None:
    module = _load_script()
    definition, _ = module._load_definition()
    outside = _raw(module, date(2018, 6, 1))
    crossing = module.RawCohort(
        date(2021, 12, 30),
        date(2021, 12, 31),
        date(2022, 1, 20),
        3,
        3,
        5,
        5,
        10,
        10,
        0.1,
        0.01,
        0.0,
        0.0,
        0.0,
    )

    rows, purged, incomplete_dates, incomplete_events, incomplete_labels = (
        module._observations((outside, crossing), definition, bps_per_side=100)
    )

    assert rows == ()
    assert purged == 1
    assert incomplete_dates == incomplete_events == incomplete_labels == 0


def _write_synthetic_sources(
    tmp_path: Path, *, reverse_feature_rows: bool = False
) -> tuple[Path, Path, Path]:
    calendar = tmp_path / "calendar.parquet"
    features_dir = tmp_path / "features"
    features_dir.mkdir()
    features = features_dir / "part-00000.parquet"
    etf = tmp_path / "etf.csv"
    days = tuple(date(2022, 1, 1) + timedelta(days=index) for index in range(17))
    connection = duckdb.connect(":memory:")
    try:
        connection.execute(
            "CREATE TABLE cal(exchange VARCHAR, trade_date VARCHAR, is_open BIGINT, "
            "pretrade_date VARCHAR)"
        )
        connection.executemany(
            "INSERT INTO cal VALUES (?, ?, 1, ?)",
            tuple(
                (
                    "SSE",
                    day.strftime("%Y%m%d"),
                    days[max(0, index - 1)].strftime("%Y%m%d"),
                )
                for index, day in enumerate(days)
            ),
        )
        connection.execute(
            f"COPY cal TO '{calendar.as_posix()}' (FORMAT PARQUET)"
        )
        connection.execute(
            "CREATE TABLE feature(ts_code VARCHAR, trade_date VARCHAR, board VARCHAR, "
            "list_days BIGINT, is_st BOOLEAN, is_suspended BOOLEAN, feature_open DOUBLE, "
            "feature_close DOUBLE, breakout_60 BOOLEAN, volatility_20_rank DOUBLE, "
            "volume_ratio_20 DOUBLE, amount_ma_20 DOUBLE, is_limit_up BOOLEAN)"
        )
        signal_rows = (
            ("AAA", "main", True, 0.4, 1.2),
            ("BBB", "main", True, 0.6, 1.2),
            ("CCC", "main", False, 0.2, 1.2),
        )
        rows = []
        for symbol, board, breakout, volatility, volume in signal_rows:
            rows.append(
                (
                    symbol,
                    days[0].strftime("%Y%m%d"),
                    board,
                    500,
                    False,
                    False,
                    10.0,
                    10.0,
                    breakout,
                    volatility,
                    volume,
                    100000.0,
                    False,
                )
            )
            rows.append(
                (
                    symbol,
                    days[1].strftime("%Y%m%d"),
                    None,
                    None,
                    None,
                    None,
                    10.0,
                    10.0,
                    None,
                    None,
                    None,
                    None,
                    symbol == "BBB",
                )
            )
            rows.append(
                (
                    symbol,
                    days[16].strftime("%Y%m%d"),
                    None,
                    None,
                    None,
                    None,
                    {"AAA": 11.0, "BBB": 12.0, "CCC": 12.0}[symbol],
                    10.0,
                    None,
                    None,
                    None,
                    None,
                    False,
                )
            )
        if reverse_feature_rows:
            rows.reverse()
        connection.executemany(
            "INSERT INTO feature VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows
        )
        connection.execute(
            f"COPY feature TO '{features.as_posix()}' (FORMAT PARQUET)"
        )
    finally:
        connection.close()
    with etf.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=("ts_code", "trade_date", "open", "adjustment")
        )
        writer.writeheader()
        for symbol, entry, exit_price in (
            ("510300.SH", 10.0, 10.5),
            ("511880.SH", 10.0, 10.2),
        ):
            writer.writerow(
                {
                    "ts_code": symbol,
                    "trade_date": days[1].strftime("%Y%m%d"),
                    "open": entry,
                    "adjustment": "qfq",
                }
            )
            writer.writerow(
                {
                    "ts_code": symbol,
                    "trade_date": days[16].strftime("%Y%m%d"),
                    "open": exit_price,
                    "adjustment": "qfq",
                }
            )
    return features_dir, calendar, etf


def _verified_source_identity_fixture(tmp_path: Path):
    features_dir, calendar, etf = _write_synthetic_sources(tmp_path)
    part = features_dir / "part-00000.parquet"
    packet = tmp_path / "packet.json"
    metadata = tmp_path / "metadata.json"
    packet.write_text('{"packet":1}\n', encoding="utf-8")
    metadata.write_text('{"metadata":1}\n', encoding="utf-8")
    part_sha = hashlib.sha256(part.read_bytes()).hexdigest()
    manifest_sha = hashlib.sha256(
        f"{part.name}\0{part.stat().st_size}\0{part_sha}\n".encode()
    ).hexdigest()
    baseline_payload = {
        "features_daily_dataset": {
            "files": 1,
            "bytes": part.stat().st_size,
            "rows": 9,
            "columns": 13,
            "manifest_sha256": manifest_sha,
            "parts": [
                {"path": part.name, "bytes": part.stat().st_size, "sha256": part_sha}
            ],
        }
    }
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(baseline_payload), encoding="utf-8")
    definition = {
        "source_contract": {
            "controlling_packet_sha256": hashlib.sha256(packet.read_bytes()).hexdigest(),
            "baseline_manifest_file_sha256": hashlib.sha256(
                baseline.read_bytes()
            ).hexdigest(),
            "feature_metadata_sha256": hashlib.sha256(metadata.read_bytes()).hexdigest(),
            "trade_calendar_sha256": hashlib.sha256(calendar.read_bytes()).hexdigest(),
            "etf_csv_sha256": hashlib.sha256(etf.read_bytes()).hexdigest(),
            "feature_part_count": 1,
            "feature_total_bytes": part.stat().st_size,
            "feature_row_count": 9,
            "feature_column_count": 13,
            "feature_dataset_manifest_sha256": manifest_sha,
        }
    }
    paths = {
        "packet": packet,
        "baseline_manifest": baseline,
        "feature_metadata": metadata,
        "features_dir": features_dir,
        "trade_calendar": calendar,
        "etf_csv": etf,
    }
    return definition, paths


def test_verified_inputs_feed_duckdb_through_zero_copy_proc_descriptors(tmp_path) -> None:
    module = _load_script()
    definition, paths = _verified_source_identity_fixture(tmp_path)

    with module._verified_input_staging(definition, **paths) as verified:
        proc_paths = (
            *verified.feature_files,
            verified.trade_calendar,
            verified.etf_csv,
        )
        assert all(str(path).startswith("/proc/self/fd/") for path in proc_paths)
        rows = module._load_raw_cohorts(
            feature_files=verified.feature_files,
            trade_calendar=verified.trade_calendar,
            etf_csv=verified.etf_csv,
        )

    assert len(rows) == 1


def test_descriptor_capture_rejects_deterministic_source_replacement(
    tmp_path,
    monkeypatch,
) -> None:
    module = _load_script()
    definition, paths = _verified_source_identity_fixture(tmp_path)
    calendar = paths["trade_calendar"]
    replacement = tmp_path / "replacement-calendar.parquet"
    replacement.write_bytes(calendar.read_bytes())
    target_inode = calendar.stat().st_ino
    real_read = module.os.read
    replaced = False

    def replacing_read(descriptor, count):
        nonlocal replaced
        chunk = real_read(descriptor, count)
        if chunk and not replaced and module.os.fstat(descriptor).st_ino == target_inode:
            os.replace(replacement, calendar)
            replaced = True
        return chunk

    monkeypatch.setattr(module.os, "read", replacing_read)
    with pytest.raises(
        module.Family66ReplayError,
        match="changed during descriptor capture|path was replaced",
    ):
        with module._verified_input_staging(definition, **paths):
            pytest.fail("replacement must fail before yielding inputs")
    assert replaced is True


@pytest.mark.parametrize("source", ("calendar", "feature_part"))
def test_descriptor_capture_rejects_duckdb_input_symlinks(tmp_path, source) -> None:
    module = _load_script()
    definition, paths = _verified_source_identity_fixture(tmp_path)
    if source == "calendar":
        target = paths["trade_calendar"]
        link = tmp_path / "calendar-link.parquet"
        link.symlink_to(target)
        paths["trade_calendar"] = link
        message = "cannot safely open trade calendar"
    else:
        part = paths["features_dir"] / "part-00000.parquet"
        target = paths["features_dir"] / "part-payload.bin"
        os.replace(part, target)
        part.symlink_to(target)
        message = "cannot safely open feature part"

    with pytest.raises(module.Family66ReplayError, match=message):
        with module._verified_input_staging(definition, **paths):
            pytest.fail("symlink must fail before yielding inputs")


def test_post_capture_replacement_cannot_change_duckdb_bytes_and_fails_closed(
    tmp_path,
) -> None:
    module = _load_script()
    definition, paths = _verified_source_identity_fixture(tmp_path)
    calendar = paths["trade_calendar"]
    replacement = tmp_path / "post-capture-calendar.parquet"
    replacement.write_bytes(calendar.read_bytes())
    queried = False

    with pytest.raises(module.Family66ReplayError, match="changed after descriptor capture"):
        with module._verified_input_staging(definition, **paths) as verified:
            os.replace(replacement, calendar)
            rows = module._load_raw_cohorts(
                feature_files=verified.feature_files,
                trade_calendar=verified.trade_calendar,
                etf_csv=verified.etf_csv,
            )
            queried = len(rows) == 1
    assert queried is True


def test_duckdb_query_builds_expected_signal_breakout_and_eligible_sleeves(tmp_path) -> None:
    module = _load_script()
    features_dir, calendar, etf = _write_synthetic_sources(tmp_path)
    rows = module._load_raw_cohorts(
        features_dir=features_dir, trade_calendar=calendar, etf_csv=etf
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.signal_candidate_count == row.signal_complete_count == 1
    assert row.breakout_candidate_count == row.breakout_complete_count == 2
    assert row.eligible_candidate_count == row.eligible_complete_count == 3
    assert row.signal_gross_return == pytest.approx(0.10)
    assert row.breakout_gross_return == pytest.approx(0.06)
    assert row.eligible_gross_return == pytest.approx((0.10 + 0.02 + 0.20) / 3)
    assert row.equity_gross_return == pytest.approx(0.05)
    assert row.cash_gross_return == pytest.approx(0.02)


def test_duckdb_cohort_bytes_are_invariant_to_feature_row_order(tmp_path) -> None:
    module = _load_script()
    normal_dir = tmp_path / "normal"
    reversed_dir = tmp_path / "reversed"
    normal_dir.mkdir()
    reversed_dir.mkdir()
    normal_features, normal_calendar, normal_etf = _write_synthetic_sources(normal_dir)
    reversed_features, reversed_calendar, reversed_etf = _write_synthetic_sources(
        reversed_dir, reverse_feature_rows=True
    )

    normal = module._load_raw_cohorts(
        features_dir=normal_features,
        trade_calendar=normal_calendar,
        etf_csv=normal_etf,
    )
    reversed_rows = module._load_raw_cohorts(
        features_dir=reversed_features,
        trade_calendar=reversed_calendar,
        etf_csv=reversed_etf,
    )

    assert normal == reversed_rows


def _append_duplicate_parquet_row(path: Path) -> None:
    replacement = path.with_name(f"{path.stem}-duplicate.parquet")
    connection = duckdb.connect(":memory:")
    try:
        connection.execute("CREATE TABLE duplicated AS SELECT * FROM read_parquet(?)", (str(path),))
        connection.execute("INSERT INTO duplicated SELECT * FROM duplicated LIMIT 1")
        connection.execute(
            f"COPY duplicated TO '{replacement.as_posix()}' (FORMAT PARQUET)"
        )
    finally:
        connection.close()
    os.replace(replacement, path)


@pytest.mark.parametrize(
    ("source", "message"),
    (
        ("calendar", "duplicate calendar date key"),
        ("feature", "duplicate feature symbol-date key"),
        ("etf", "duplicate ETF symbol-date key"),
    ),
)
def test_duplicate_source_keys_cannot_shift_labels_or_multiply_cohorts(
    tmp_path,
    source,
    message,
) -> None:
    module = _load_script()
    features_dir, calendar, etf = _write_synthetic_sources(tmp_path)
    assert len(
        module._load_raw_cohorts(
            features_dir=features_dir,
            trade_calendar=calendar,
            etf_csv=etf,
        )
    ) == 1

    if source == "calendar":
        _append_duplicate_parquet_row(calendar)
    elif source == "feature":
        _append_duplicate_parquet_row(features_dir / "part-00000.parquet")
    else:
        lines = etf.read_text(encoding="utf-8").splitlines()
        etf.write_text("\n".join((*lines, lines[1])) + "\n", encoding="utf-8")

    with pytest.raises(module.Family66ReplayError, match=message):
        module._load_raw_cohorts(
            features_dir=features_dir,
            trade_calendar=calendar,
            etf_csv=etf,
        )


def test_feature_manifest_and_every_part_are_hash_bound(tmp_path) -> None:
    module = _load_script()
    packet = tmp_path / "packet.json"
    metadata = tmp_path / "metadata.json"
    calendar = tmp_path / "calendar.parquet"
    etf = tmp_path / "etf.csv"
    features_dir = tmp_path / "features"
    features_dir.mkdir()
    part = features_dir / "part-00000.parquet"
    for path, raw in (
        (packet, b"packet"),
        (metadata, b"metadata"),
        (calendar, b"calendar"),
        (etf, b"etf"),
        (part, b"part-bytes"),
    ):
        path.write_bytes(raw)
    part_sha = hashlib.sha256(part.read_bytes()).hexdigest()
    manifest_sha = hashlib.sha256(
        f"{part.name}\0{part.stat().st_size}\0{part_sha}\n".encode()
    ).hexdigest()
    baseline_payload = {
        "features_daily_dataset": {
            "files": 1,
            "bytes": part.stat().st_size,
            "rows": 7,
            "columns": 13,
            "manifest_sha256": manifest_sha,
            "parts": [
                {"path": part.name, "bytes": part.stat().st_size, "sha256": part_sha}
            ],
        }
    }
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(baseline_payload), encoding="utf-8")
    definition = {
        "source_contract": {
            "controlling_packet_sha256": hashlib.sha256(packet.read_bytes()).hexdigest(),
            "baseline_manifest_file_sha256": hashlib.sha256(
                baseline.read_bytes()
            ).hexdigest(),
            "feature_metadata_sha256": hashlib.sha256(metadata.read_bytes()).hexdigest(),
            "trade_calendar_sha256": hashlib.sha256(calendar.read_bytes()).hexdigest(),
            "etf_csv_sha256": hashlib.sha256(etf.read_bytes()).hexdigest(),
            "feature_part_count": 1,
            "feature_total_bytes": part.stat().st_size,
            "feature_row_count": 7,
            "feature_column_count": 13,
            "feature_dataset_manifest_sha256": manifest_sha,
        }
    }
    module._verify_inputs(
        definition,
        packet=packet,
        baseline_manifest=baseline,
        feature_metadata=metadata,
        features_dir=features_dir,
        trade_calendar=calendar,
        etf_csv=etf,
    )
    part.write_bytes(b"changed")
    with pytest.raises(module.Family66ReplayError, match="feature part changed"):
        module._verify_inputs(
            definition,
            packet=packet,
            baseline_manifest=baseline,
            feature_metadata=metadata,
            features_dir=features_dir,
            trade_calendar=calendar,
            etf_csv=etf,
        )


def test_publish_is_atomic_and_non_overwriting(tmp_path) -> None:
    module = _load_script()
    output = tmp_path / "result.json"
    digest, sidecar = module._publish({"finite": 1.0}, output)
    assert hashlib.sha256(output.read_bytes()).hexdigest() == digest
    assert sidecar.read_text(encoding="ascii") == f"{digest}  result.json\n"
    repeated = tmp_path / "repeated.json"
    repeated_digest, _ = module._publish({"finite": 1.0}, repeated)
    assert repeated.read_bytes() == output.read_bytes()
    assert repeated_digest == digest
    with pytest.raises(module.Family66ReplayError, match="already exists"):
        module._publish({"finite": 2.0}, output)


def test_git_identity_requires_clean_committed_sha1_or_sha256(monkeypatch) -> None:
    module = _load_script()

    def clean_run(args, **kwargs):
        del kwargs
        if args[1:] == ["status", "--porcelain=v1"]:
            return SimpleNamespace(stdout="")
        if args[1:] == ["rev-parse", "HEAD"]:
            return SimpleNamespace(stdout=f"{'a' * clean_run.length}\n")
        raise AssertionError(args)

    monkeypatch.setattr(module.subprocess, "run", clean_run)
    for length in (40, 64):
        clean_run.length = length
        assert module._git_identity() == "a" * length

    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=" M changed.py\n"),
    )
    with pytest.raises(module.Family66ReplayError, match="clean committed"):
        module._git_identity()


def test_report_preserves_exact_rejection_and_candidate_boundaries() -> None:
    module = _load_script()
    definition, digest = module._load_definition()
    report = module.build_report(
        definition,
        digest,
        _full_synthetic_raw(module),
        source_commit="a" * 40,
        source_paths={"features_dir": "/synthetic"},
    )
    repeated = module.build_report(
        definition,
        digest,
        tuple(reversed(_full_synthetic_raw(module))),
        source_commit="a" * 40,
        source_paths={"features_dir": "/synthetic"},
    )
    canonical = (
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode()
    repeated_canonical = (
        json.dumps(repeated, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode()

    assert report == repeated
    assert canonical == repeated_canonical
    assert hashlib.sha256(canonical).hexdigest() == hashlib.sha256(
        repeated_canonical
    ).hexdigest()
    assert "executed_at_utc" not in report
    assert report["gate_count"] == 48
    assert report["original_status_preserved"] == (
        "REJECTED_BY_METHODOLOGY_RECOMPUTE_GATE"
    )
    assert report["strict_pit_eligible"] is False
    assert report["eligible_for_new_evidence"] is False
    assert report["strategy_candidate_available"] is False
    assert report["broker_order_paper_live_auto"] is False
