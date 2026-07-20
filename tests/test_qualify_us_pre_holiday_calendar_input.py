from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import socket

import pytest

from scripts import qualify_us_pre_holiday_calendar_input as q


def _snapshot(tmp_path: Path) -> tuple[Path, tuple[dict[str, object], ...]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    specs: list[dict[str, object]] = []
    for index, original in enumerate(q.SOURCE_SPECS):
        spec = dict(original)
        if str(spec["content_type"]) == "application/pdf":
            raw = f"%PDF-1.4\nsynthetic-{index}\n".encode()
        else:
            raw = f"<html><body>synthetic-{index}</body></html>\n".encode()
        spec["bytes"] = len(raw)
        spec["content_sha256"] = q.sha256_bytes(raw)
        (tmp_path / str(spec["filename"])).write_bytes(raw)
        headers = (
            "HTTP/1.1 200 OK\r\n"
            f"Content-Type: {spec['content_type']}\r\n"
            f"Content-Length: {len(raw)}\r\n"
            "Date: Mon, 20 Jul 2026 10:48:30 GMT\r\n"
            "Last-Modified: Fri, 19 Dec 2025 15:38:22 GMT\r\n"
            "Set-Cookie: must-not-be-published\r\n\r\n"
        ).encode()
        (tmp_path / f"{spec['filename']}.meta.headers").write_bytes(headers)
        (tmp_path / f"{spec['filename']}.meta").write_text(
            "\n".join(
                (
                    "200",
                    str(spec["url"]),
                    "0",
                    str(len(raw)),
                    str(spec["content_type"]),
                )
            )
            + "\n",
            encoding="utf-8",
        )
        specs.append(spec)
    return tmp_path, tuple(specs)


def test_complete_snapshot_is_blocked_only_on_historical_archive_gaps(
    tmp_path: Path,
) -> None:
    source, specs = _snapshot(tmp_path)
    bundle = q.build_bundle(source, specs)
    result = bundle["input_qualification.json"]

    assert result["status"] == "INPUT_BLOCKED_NONTERMINAL"
    assert result["blocked_annual_calendar_years"] == list(range(2010, 2022))
    assert result["accepted_annual_calendar_years"] == [2022, 2023, 2024, 2025, 2026]
    assert result["strategy_candidate_available"] is False
    assert result["gate_counts"] is None
    assert result["boundaries"] == {
        "database_or_cache_write_performed": False,
        "market_price_data_accessed": False,
        "network_performed_by_qualification": False,
        "outcome_accessed": False,
        "strategy_candidate_available": False,
        "strategy_execution_performed": False,
    }


def test_holiday_and_ad_hoc_semantics_are_exact(tmp_path: Path) -> None:
    source, specs = _snapshot(tmp_path)
    bundle = q.build_bundle(source, specs)
    denominator = bundle["holiday_denominator.json"]
    sessions = bundle["accepted_pre_holiday_sessions.json"]
    ad_hoc = bundle["ad_hoc_closure_identity.json"]

    assert denominator["total_candidate_count"] == 152
    assert denominator["accepted_denominator_count"] == 45
    assert sessions["accepted_event_count"] == 45
    assert sessions["early_close_event_count"] == 5
    assert len({row["closure_date"] for row in denominator["rows"]}) == 152
    assert all(date.fromisoformat(row["closure_date"]).weekday() < 5 for row in denominator["rows"])
    assert ad_hoc["block_count"] == 3
    assert ad_hoc["closure_date_count"] == 4
    assert ad_hoc["holiday_denominator_inclusion_count"] == 0
    sandy = next(row for row in ad_hoc["rows"] if row["block_id"] == "ADHOC_2012_SANDY")
    assert sandy["closure_dates"] == ["2012-10-29", "2012-10-30"]
    assert sandy["closure_date_count"] == 2


def test_ordinary_early_close_never_creates_an_event(tmp_path: Path) -> None:
    source, specs = _snapshot(tmp_path)
    bundle = q.build_bundle(source, specs)
    early = bundle["early_close_identity.json"]
    event_sessions = {
        row["session_date"]
        for row in bundle["accepted_pre_holiday_sessions.json"]["rows"]
    }
    ordinary = {
        row["session_date"]
        for row in early["rows"]
        if row["session_date"] not in event_sessions
    }

    assert early["row_count"] == 9
    assert early["source_full_year_observed_count"] == 11
    assert all(row["session_date"] <= "2026-06-30" for row in early["rows"])
    assert ordinary == {"2022-11-25", "2023-11-24", "2024-11-29", "2025-11-28"}
    assert all(row["generates_event_independently"] is False for row in early["rows"])


def test_source_hash_drift_and_missing_year_fail_closed(tmp_path: Path) -> None:
    source, specs = _snapshot(tmp_path / "drift")
    path = source / str(specs[0]["filename"])
    path.write_bytes(path.read_bytes() + b"drift")
    with pytest.raises(q.QualificationError, match="source bytes changed"):
        q.build_bundle(source, specs)

    source, specs = _snapshot(tmp_path / "missing")
    (source / "ICE_NYSE_2024_Yearly_Trading_Calendar.pdf").unlink()
    with pytest.raises(q.QualificationError, match="regular non-symlink"):
        q.build_bundle(source, specs)


def test_http_metadata_mismatch_and_unexpected_file_fail_closed(tmp_path: Path) -> None:
    source, specs = _snapshot(tmp_path / "status")
    meta = source / f"{specs[0]['filename']}.meta"
    meta.write_text(meta.read_text(encoding="utf-8").replace("200\n", "503\n", 1))
    with pytest.raises(q.QualificationError, match="retrieval identity changed"):
        q.build_bundle(source, specs)

    source, specs = _snapshot(tmp_path / "extra")
    (source / "unapproved.txt").write_text("unexpected", encoding="ascii")
    with pytest.raises(q.QualificationError, match="unexpected file"):
        q.build_bundle(source, specs)


def test_strict_json_rejects_duplicate_and_nonfinite_values() -> None:
    with pytest.raises(q.QualificationError, match="duplicate JSON key"):
        q.strict_load_bytes(b'{"value": 1, "value": 2}')
    with pytest.raises(q.QualificationError, match="nonfinite"):
        q.strict_load_bytes(b'{"value": NaN}')


def test_official_calendar_constant_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed = deepcopy(q.ANNUAL_MARKET_CLOSED_DATES)
    changed[2024] = changed[2024] + ("2024-07-06",)
    monkeypatch.setattr(q, "ANNUAL_MARKET_CLOSED_DATES", changed)
    with pytest.raises(q.QualificationError, match="disagree for 2024"):
        q._validate_official_calendar_constants()


def test_rule_sources_are_bound_to_the_representative_year() -> None:
    rows = q.build_holiday_denominator()["rows"]
    by_year = {
        year: next(row for row in rows if row["closure_date"].startswith(f"{year}-"))
        for year in (2010, 2017, 2022)
    }
    assert by_year[2010]["rule_source_ids"] == [
        "sec_nyse_rule_51_2010",
        "sec_nyse_pillar_rule_7_2_2017",
    ]
    assert by_year[2017]["rule_source_ids"] == ["sec_nyse_pillar_rule_7_2_2017"]
    assert by_year[2022]["rule_source_ids"] == [
        "sec_nyse_pillar_rule_7_2_2017",
        "nyse_rule_7_2_juneteenth",
    ]


def test_source_symlink_is_rejected(tmp_path: Path) -> None:
    source, specs = _snapshot(tmp_path)
    payload = source / str(specs[0]["filename"])
    backing = source / "backing"
    backing.mkdir()
    target = backing / "real-source.pdf"
    payload.rename(target)
    payload.symlink_to(target)
    with pytest.raises(q.QualificationError, match="non-symlink"):
        q.build_bundle(source, specs)


def test_duplicate_closure_mapping_and_ad_hoc_overlap_fail_closed() -> None:
    denominator = q.build_holiday_denominator()
    early = q.build_early_close_identity()
    duplicate = deepcopy(denominator)
    duplicate["rows"].append(deepcopy(duplicate["rows"][-1]))
    with pytest.raises(q.QualificationError, match="accepted session|closure"):
        q.build_accepted_preholiday_sessions(duplicate, early)

    blocks = list(deepcopy(q.AD_HOC_BLOCKS))
    blocks.append(
        {
            "block_id": "OVERLAP",
            "closure_dates": ("2012-10-30",),
            "label": "bad",
            "source_ids": ("sec_nyse_sandy_closure_2012",),
        }
    )
    with pytest.raises(q.QualificationError, match="cannot overlap"):
        q.build_ad_hoc_identity(tuple(blocks))


def test_output_bundle_is_exact_atomic_and_non_overwriting(tmp_path: Path) -> None:
    source, specs = _snapshot(tmp_path / "source")
    bundle = q.build_bundle(source, specs)
    output = tmp_path / "output"
    hashes = q.write_bundle(bundle, output)

    assert set(hashes) == set(q.OUTPUT_NAMES)
    assert {path.name for path in output.iterdir()} == set(q.OUTPUT_NAMES)
    for name, digest in hashes.items():
        raw = (output / name).read_bytes()
        assert raw == q.canonical_json(q.strict_load_bytes(raw))
        assert q.sha256_bytes(raw) == digest
    with pytest.raises(q.QualificationError, match="overwrite is forbidden"):
        q.write_bundle(bundle, output)


def test_headers_secrets_and_outcome_values_are_not_published(tmp_path: Path) -> None:
    source, specs = _snapshot(tmp_path)
    encoded = b"\n".join(
        q.canonical_json(value) for value in q.build_bundle(source, specs).values()
    ).lower()
    for forbidden in (
        b"must-not-be-published",
        b"set-cookie",
        b"api_key",
        b"sharpe",
        b"cagr",
        b"strategy_return",
        b"portfolio_value",
    ):
        assert forbidden not in encoded


def test_default_dry_run_opens_no_socket_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("dry run must not open a socket")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    assert q.main([]) == 0
    assert set(tmp_path.iterdir()) == before
    assert json.loads(capsys.readouterr().out) == {
        "files_written": False,
        "network_executed": False,
        "qualification_id": q.QUALIFICATION_ID,
        "source_count": 12,
        "status": "DRY_RUN_PLAN",
    }
