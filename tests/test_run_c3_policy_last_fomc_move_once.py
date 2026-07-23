from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import stat
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest


RUNNER_PATH = Path(__file__).resolve().parents[1] / "scripts/run_c3_policy_last_fomc_move_once.py"
SPEC = importlib.util.spec_from_file_location("c3_fomc_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)

from quant_system.data import session_dates_sha256, session_rows_sha256  # noqa: E402


def _private_file(path: Path, payload: bytes) -> Path:
    path.write_bytes(payload)
    path.chmod(0o600)
    return path


def _source(seed: str = "a"):
    return RUNNER.SourceIdentity(
        "https://example.com/source",
        seed * 64,
        datetime(2020, 1, 1, tzinfo=timezone.utc),
        datetime(2020, 1, 2, tzinfo=timezone.utc),
        f"revision-{seed}",
    )


def _source_row(seed: str = "a", available_at: str = "2020-01-01T00:00:00+00:00") -> dict[str, object]:
    return {
        "source_url": "https://example.com/source",
        "content_sha256": seed * 64,
        "available_at": available_at,
        "retrieved_at": "2020-01-02T00:00:00+00:00",
        "revision_id": f"revision-{seed}",
        "supersedes_revision_id": None,
    }


def _calendar_payload(exchange: str = "XNYS", timezone_name: str = "America/New_York") -> dict[str, object]:
    zone = ZoneInfo(timezone_name)
    raw_rows, sessions = [], []
    for index, day in enumerate((date(2021, 12, 31), date(2022, 1, 3))):
        source_row = _source_row("a")
        opened = datetime(day.year, day.month, day.day, 9, 30, tzinfo=zone)
        closed = datetime(day.year, day.month, day.day, 16, 0, tzinfo=zone)
        raw_rows.append({"session_date": day.isoformat(), "open_at": opened.isoformat(), "close_at": closed.isoformat(), "is_early_close": False, "exchange_id": exchange, "exchange_timezone": timezone_name, "row_sha256": hashlib.sha256(f"row-{index}".encode()).hexdigest(), "source": source_row})
        sessions.append(RUNNER.AcceptedSession(day, opened, closed, RUNNER._source(source_row), timezone_name, False, exchange))
    identity_source = _source_row("b")
    return {"calendar_identity": {"exchange_id": exchange, "exchange_timezone": timezone_name, "coverage_start": "2021-12-31", "coverage_end": "2022-01-03", "session_count": 2, "session_dates_sha256": session_dates_sha256(row.session_date for row in sessions), "session_rows_sha256": session_rows_sha256(sessions), "source_identity": identity_source}, "session_rows": raw_rows}


def _execution_row() -> dict[str, object]:
    return {"symbol": "SPY", "market": "us", "session_date": "2022-01-03", "raw_open": 100.0, "currency": "USD", "source": _source_row("e"), "decision_price": 100.0, "decision_price_session": "2021-12-31", "decision_price_effective_at": "2021-12-31T16:00:00-05:00", "decision_price_source": _source_row("f"), "decision_price_basis": "raw_pre_action_per_old_share", "execution_price_effective_at": "2022-01-03T14:30:00+00:00", "execution_price_basis": "retrospective_daily_bar_open_fill", "corporate_action_ids": ["dividend-1"]}


def _official_state_record() -> dict[str, object]:
    decisions, events = [], []
    sizes = (34, 30, 36)
    split_names = ("development", "validation", "retrospective_holdout")
    support: dict[str, dict[str, int]] = {}
    cursor = 0
    for name, size in zip(split_names, sizes, strict=True):
        directions = ["EASING" if index < size // 2 else "TIGHTENING" for index in range(size)]
        support[name] = {
            "months": size,
            "easing": directions.count("EASING"),
            "tightening": directions.count("TIGHTENING"),
            "transitions": 1,
        }
        for direction in directions:
            year, month = 2018 + cursor // 12, cursor % 12 + 1
            session = date(year, month, 1)
            decision_at = datetime(year, month, 1, 9, tzinfo=ZoneInfo("America/New_York"))
            event_hash = hashlib.sha256(f"event-{cursor}".encode()).hexdigest()
            decision_hash = hashlib.sha256(f"decision-{cursor}".encode()).hexdigest()
            old, new = ("5.00", "4.75") if direction == "EASING" else ("5.00", "5.25")
            event = {
                "content_sha256": "a" * 64,
                "direction": direction,
                "document_filename": f"event-{cursor}.pdf",
                "document_text_has_funds_rate_phrase": True,
                "effective_date": session.isoformat(),
                "linked_implementation_note_identity": None,
                "linked_implementation_notes": [],
                "new_lower_bound": new,
                "new_upper_bound": new,
                "old_lower_bound": old,
                "old_upper_bound": old,
                "release_at": (decision_at.replace(hour=8)).isoformat(),
                "release_time_source_text": "08:00",
                "retrieved_at": "2026-07-22T00:00:00+00:00",
                "row_sha256": event_hash,
                "source_url": "https://www.federalreserve.gov/example",
                "statement_date": session.isoformat(),
                "target_range_index_sha256": "b" * 64,
            }
            events.append(event)
            decisions.append(
                {
                    "decision_at": decision_at.isoformat(),
                    "decision_month": session.isoformat()[:7],
                    "decision_session": session.isoformat(),
                    "decision_session_identity": {
                        "close_at": decision_at.replace(hour=16).isoformat(),
                        "early_close": False,
                        "exchange": "XNYS",
                        "is_open": True,
                        "open_at": decision_at.replace(hour=9, minute=30).isoformat(),
                        "row_sha256": "c" * 64,
                        "session_date": session.isoformat(),
                        "snapshot_id": "calendar-v1",
                        "source_available_at": "2017-01-01T00:00:00+00:00",
                        "source_document_set_sha256": "d" * 64,
                        "source_url": "https://www.nyse.com/example",
                        "timezone": "America/New_York",
                    },
                    "row_sha256": decision_hash,
                    "selected_event": event,
                    "state": direction,
                }
            )
            cursor += 1
    return {
        "acquisition": {},
        "calendar_identity": {
            "calendar_rows_used": 100,
            "row_count": 2061,
            "source_path_logical_name": "accepted_xnys_calendar_projection_dst_repaired_v2",
            "source_sha256": RUNNER.CALENDAR_INPUT_SHA256,
            "timezone": "America/New_York",
        },
        "database_write": {},
        "decision_count": 100,
        "decision_rule": {},
        "decisions": decisions,
        "event_count": len(events),
        "events": events,
        "mechanism": "C3_POLICY_LAST_FOMC_MOVE_DIRECTION_PRIMARY_DOCUMENT_STATE",
        "schema_version": "us-fomc-policy-direction-input-v1",
        "source_identities": [],
        "split_support": support,
        "stage": "outcome_free_policy_state",
        "strategy_candidate_available": False,
    }


def test_frozen_code_and_input_identities_are_exact() -> None:
    assert RUNNER._file_sha256(RUNNER.DEFINITION) == RUNNER.DEFINITION_SHA256
    assert RUNNER._file_sha256(RUNNER.ADAPTER) == RUNNER.ADAPTER_SHA256
    assert RUNNER.STATE_INPUT_SHA256 == (
        "153b114ee2df45a232ef7986cc70802f3b8169eb698aa2761d1ade29c06cbbc3"
    )
    assert RUNNER.CALENDAR_INPUT_SHA256 == (
        "08b1722c675012d89e0b4f92ed51f51160adbd1d54961c093c52101c067fc553"
    )
    assert RUNNER.VALIDATION_BUNDLE_SHA256 == "499157cd45b6402aabb8f786ae7e60f9c4bb55992e60bab8ff03f1104baa5b8a"
    assert RUNNER.HOLDOUT_BUNDLE_SHA256 == "ff4b02932079ad013da05dbffcf2dd6e25af8592450e5b09e4a2f00d9f61f8d4"
    identities = json.loads(RUNNER.DEFINITION.read_text())["input_identities"]
    assert (Path(identities["official_policy_state_input_path"]), identities["official_policy_state_input_sha256"], identities["accepted_xnys_calendar_sha256"]) == (RUNNER.STATE_INPUT, RUNNER.STATE_INPUT_SHA256, RUNNER.CALENDAR_INPUT_SHA256)
    assert (Path(identities["validation_bundle_path"]), identities["validation_bundle_sha256"]) == (RUNNER.VALIDATION_BUNDLE, RUNNER.VALIDATION_BUNDLE_SHA256)
    assert (Path(identities["holdout_bundle_path"]), identities["holdout_bundle_sha256"]) == (RUNNER.HOLDOUT_BUNDLE, RUNNER.HOLDOUT_BUNDLE_SHA256)
    with pytest.raises(RUNNER.InputBlockedError, match="SHA-256"):
        RUNNER._sha256(RUNNER.CALENDAR_INPUT_SHA256[:-1], "runtime calendar input SHA-256")
    assert RUNNER._core_identity() == (
        RUNNER.CORE_SOURCE_FILE_COUNT,
        RUNNER.CORE_SOURCE_SHA256,
    )


def test_official_state_rows_are_parsed_bound_and_support_checked() -> None:
    record = _official_state_record()
    states = RUNNER._load_official_states(json.dumps(record).encode())
    assert {key: len(value) for key, value in states.items()} == {
        "development": 34,
        "validation": 30,
        "holdout": 36,
    }
    assert states["validation"][0].state.direction == "easing"
    mutated = json.loads(json.dumps(record))
    mutated["decisions"][34]["state"] = "TIGHTENING"
    with pytest.raises(RUNNER.InputBlockedError, match="direction"):
        RUNNER._load_official_states(json.dumps(mutated).encode())
    for direction in ("PAUSE", "easing"):
        invalid = json.loads(json.dumps(record))
        invalid["decisions"][0]["state"] = direction
        invalid["decisions"][0]["selected_event"]["direction"] = direction
        with pytest.raises(RUNNER.InputBlockedError, match="uppercase vocabulary"):
            RUNNER._load_official_states(json.dumps(invalid).encode())
    reordered = json.loads(json.dumps(record))
    reordered["decisions"][0], reordered["decisions"][1] = (
        reordered["decisions"][1],
        reordered["decisions"][0],
    )
    with pytest.raises(RUNNER.InputBlockedError, match="reordered"):
        RUNNER._load_official_states(json.dumps(reordered).encode())
    missing = json.loads(json.dumps(record))
    missing["decisions"].pop()
    with pytest.raises(RUNNER.InputBlockedError, match="counts"):
        RUNNER._load_official_states(json.dumps(missing).encode())
    truncated = json.loads(json.dumps(record))
    truncated["calendar_identity"]["source_sha256"] = RUNNER.CALENDAR_INPUT_SHA256[:-1]
    with pytest.raises(RUNNER.InputBlockedError, match="SHA-256"):
        RUNNER._load_official_states(json.dumps(truncated).encode())


def test_capture_rejects_identity_mismatch_and_symlink(tmp_path: Path) -> None:
    target = _private_file(tmp_path / "input.json", b"{}")
    with pytest.raises(RUNNER.InputBlockedError, match="SHA-256 mismatch"):
        RUNNER._capture(target, "0" * 64, max_bytes=10)
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(RUNNER.InputBlockedError, match="cannot open"):
        RUNNER._capture(link, None, max_bytes=10)


def test_capture_rejects_path_replacement_after_descriptor_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _private_file(tmp_path / "input.json", b"old")
    replacement = _private_file(tmp_path / "replacement.json", b"new")
    original_read = RUNNER.os.read
    replaced = False

    def replacing_read(fd: int, size: int) -> bytes:
        nonlocal replaced
        payload = original_read(fd, size)
        if payload and not replaced:
            os.replace(replacement, target)
            replaced = True
        return payload

    monkeypatch.setattr(RUNNER.os, "read", replacing_read)
    with pytest.raises(RUNNER.InputBlockedError, match="changed"):
        RUNNER._capture(target, None, max_bytes=10)


def test_stage_claim_precedes_bundle_capture_and_outputs_are_0600(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = _private_file(tmp_path / "bundle.json", b"bundle")
    claim = tmp_path / "private" / "claim.json"
    result = claim.with_name("result.json")
    events: list[str] = []
    original_publish = RUNNER._publish
    original_capture = RUNNER._capture
    bundle_sha = RUNNER._sha256_bytes(bundle.read_bytes())

    def publishing(path: Path, record: dict[str, object]) -> str:
        events.append("claim" if path == claim else "result")
        return original_publish(path, record)

    def capturing(path: Path, expected: str | None, *, max_bytes: int) -> bytes:
        assert path == bundle
        assert claim.exists()
        assert expected == bundle_sha
        events.append("capture")
        return original_capture(path, expected, max_bytes=max_bytes)

    monkeypatch.setattr(RUNNER, "_publish", publishing)
    monkeypatch.setattr(RUNNER, "_capture", capturing)
    def loading(payload, stage, official_states):
        events.append("load")
        return object()

    def simulating(loaded):
        events.append("simulate")
        return (0.01,) * 29, (0.0,) * 29, ("a" * 64,)

    monkeypatch.setattr(RUNNER, "_load_bundle", loading)
    monkeypatch.setattr(RUNNER, "_simulate", simulating)
    record = RUNNER._stage(
        "validation",
        bundle,
        claim,
        result,
        runner_sha256="b" * 64,
        state_sha256=RUNNER.STATE_INPUT_SHA256,
        expected_bundle_sha256=bundle_sha,
        official_states={},
    )
    assert events == ["claim", "capture", "load", "simulate", "result"]
    assert record["classification"] == ("RETROSPECTIVE_SECONDARY_VALIDATION_PASS_HOLDOUT_UNLOCKED")
    assert stat.S_IMODE(claim.stat().st_mode) == 0o600
    assert stat.S_IMODE(result.stat().st_mode) == 0o600
    assert json.loads(claim.read_text())["expected_runtime_bundle_sha256"] == bundle_sha


def test_numeric_bundle_replacement_is_rejected_after_claim_before_simulation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    accepted = json.dumps({"decision_price": 100.0}, separators=(",", ":")).encode()
    mutated = json.dumps({"decision_price": 200.0}, separators=(",", ":")).encode()
    expected_sha = RUNNER._sha256_bytes(accepted)
    bundle = _private_file(tmp_path / "bundle.json", mutated)
    claim = tmp_path / "private" / "claim.json"
    simulated: list[bool] = []
    monkeypatch.setattr(RUNNER, "_simulate", lambda loaded: simulated.append(True))
    record = RUNNER._stage("validation", bundle, claim, claim.with_name("result.json"), runner_sha256="b" * 64, state_sha256=RUNNER.STATE_INPUT_SHA256, expected_bundle_sha256=expected_sha, official_states={})
    assert expected_sha != RUNNER._sha256_bytes(mutated)
    assert record["classification"] == "INPUT_BLOCKED_CLAIM_CONSUMED"
    assert record["error_message"] == "input SHA-256 mismatch"
    assert json.loads(claim.read_text())["expected_runtime_bundle_sha256"] == expected_sha
    assert simulated == []


def test_validation_failure_never_opens_or_claims_holdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    definition = _private_file(tmp_path / "definition.json", b"definition")
    adapter = _private_file(tmp_path / "adapter.py", b"adapter")
    runner = _private_file(tmp_path / "runner.py", b"runner")
    state = _private_file(tmp_path / "state.json", b"state")
    calls: list[str] = []
    monkeypatch.setattr(RUNNER, "DEFINITION", definition)
    monkeypatch.setattr(RUNNER, "ADAPTER", adapter)
    monkeypatch.setattr(RUNNER, "RUNNER", runner)
    monkeypatch.setattr(RUNNER, "DEFINITION_SHA256", RUNNER._file_sha256(definition))
    monkeypatch.setattr(RUNNER, "ADAPTER_SHA256", RUNNER._file_sha256(adapter))
    monkeypatch.setattr(RUNNER, "STATE_INPUT", state)
    monkeypatch.setattr(RUNNER, "STATE_INPUT_SHA256", RUNNER._file_sha256(state))
    monkeypatch.setattr(
        RUNNER,
        "_core_identity",
        lambda: (RUNNER.CORE_SOURCE_FILE_COUNT, RUNNER.CORE_SOURCE_SHA256),
    )
    monkeypatch.setattr(RUNNER, "_load_official_states", lambda payload: {})

    def stage(stage: str, *args, **kwargs) -> dict[str, object]:
        calls.append(stage)
        return {"classification": "RETROSPECTIVE_SECONDARY_VALIDATION_FAIL"}

    monkeypatch.setattr(RUNNER, "_stage", stage)
    assert RUNNER.execute_once()["classification"] == ("RETROSPECTIVE_SECONDARY_VALIDATION_FAIL")
    assert calls == ["validation"]


def test_execution_preserves_rich_action_and_price_basis_into_shared_core(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    action = RUNNER.CorporateActionIdentity(
        "SPY",
        "dividend-1",
        "cash_dividend",
        datetime(2022, 1, 3, 14, 30, tzinfo=timezone.utc),
        _source("c"),
        "America/New_York",
        ex_date=date(2022, 1, 3),
        record_date=date(2022, 1, 4),
        pay_date=date(2022, 1, 7),
        cash_amount=Decimal("1.00"),
        currency="USD",
        unit="per_share",
    )
    status = RUNNER.StatusEvidence(
        "listed-1",
        "SPY",
        "listed",
        True,
        date(1993, 1, 29),
        None,
        "America/New_York",
        _source("d"),
    )
    row = _execution_row()
    signal_session = date(2021, 12, 31)
    decision_at = datetime(2022, 1, 3, 9, tzinfo=ZoneInfo("America/New_York"))
    calendar = RUNNER._calendar(_calendar_payload())
    execution = RUNNER._execution(row, (status,), (action,), signal_session=signal_session, decision_at=decision_at, calendar=calendar)
    forbidden_calls: list[str] = []
    monkeypatch.setattr(RUNNER, "_publish", lambda *args, **kwargs: forbidden_calls.append("publish"))
    monkeypatch.setattr(RUNNER, "_simulate", lambda *args, **kwargs: forbidden_calls.append("simulate"))
    shifted = json.loads(json.dumps(row))
    shifted["execution_price_effective_at"] = "2022-01-03T10:30:00-05:00"
    shifted = RUNNER._json(json.dumps(shifted, separators=(",", ":")).encode(), "synthetic execution")
    with pytest.raises(RUNNER.InputBlockedError, match="accepted execution session open"):
        RUNNER._execution(shifted, (status,), (action,), signal_session=signal_session, decision_at=decision_at, calendar=calendar)
    assert forbidden_calls == []
    observed: dict[str, object] = {}

    def core(portfolio, calendar, **kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            portfolio=portfolio,
            stage_hash="1" * 64,
            final_nav=40000.0,
        )

    monkeypatch.setattr(RUNNER, "run_static_rebalance", core)
    point = RUNNER.Point(
        date(2021, 12, 31),
        datetime(2022, 1, 3, 14, 0, tzinfo=timezone.utc),
        date(2022, 1, 3),
        object(),
        None,
        execution,
        object(),
        object(),
        "a" * 64,
        False,
    )
    RUNNER._rebalance(RUNNER.Portfolio.us(40000.0), point, 1.0, "0" * 64)
    propagated = observed["execution_inputs"][0]
    assert propagated.corporate_actions == (action,)
    assert propagated.decision_price_basis == "raw_pre_action_per_old_share"
    assert propagated.execution_price_basis == "retrospective_daily_bar_open_fill"
    assert observed["slippage_bps"] == 10.0

    with pytest.raises(RUNNER.InputBlockedError, match="coverage"):
        RUNNER._execution_actions((action,), date(2022, 1, 3), [])
    assert RUNNER._execution_actions(
        (action,), date(2022, 1, 3), ["dividend-1"]
    ) == (action,)

    for field, value in (("decision_price_session", "2021-12-30"), ("decision_price_effective_at", "2021-12-31T15:59:59-05:00")):
        mutated = dict(row)
        mutated[field] = value
        with pytest.raises(RUNNER.InputBlockedError, match="price basis"):
            RUNNER._execution(mutated, (status,), (action,), signal_session=signal_session, decision_at=decision_at, calendar=calendar)
    late = dict(row)
    late["decision_price_source"] = _source_row("f", "2022-01-03T09:01:00-05:00")
    late["decision_price_source"]["retrieved_at"] = "2022-01-04T00:00:00+00:00"
    with pytest.raises(RUNNER.InputBlockedError, match="price basis"):
        RUNNER._execution(late, (status,), (action,), signal_session=signal_session, decision_at=decision_at, calendar=calendar)
    doubled = dict(row)
    doubled["decision_price"] = 200.0
    assert hashlib.sha256(json.dumps(row, sort_keys=True).encode()).digest() != hashlib.sha256(json.dumps(doubled, sort_keys=True).encode()).digest()


def test_runtime_venue_timezone_and_epoch_uniqueness_are_fail_closed() -> None:
    assert RUNNER._calendar(_calendar_payload()).exchange_id == "XNYS"
    with pytest.raises(RUNNER.InputBlockedError, match="XNYS"):
        RUNNER._calendar(_calendar_payload(exchange="XNAS"))
    with pytest.raises(RUNNER.InputBlockedError, match="XNYS"):
        RUNNER._calendar(_calendar_payload(timezone_name="America/Chicago"))
    calendar = _calendar_payload()
    with pytest.raises(RUNNER.InputBlockedError, match="duplicate"):
        RUNNER._calendar_epochs({"epoch-a": calendar, "epoch-b": json.loads(json.dumps(calendar))})


def test_decision_records_exact_validation_and_holdout_gates() -> None:
    validation = RUNNER._decision("validation", (0.01,) * 29, (0.0,) * 29)
    assert validation["all_gates_pass"] is True
    assert set(validation["gates"]) == {
        "strategy_terminal_net_wealth_strictly_above_spy",
        "arithmetic_mean_paired_active_returns_strictly_positive",
        "strategy_maximum_drawdown_no_worse_than_spy",
    }
    holdout = RUNNER._decision("holdout", (0.01,) * 35, (0.0,) * 35)
    assert holdout["all_gates_pass"] is True
    assert holdout["inference"]["centered_null_one_sided_p"] <= 0.00625
    assert holdout["inference"]["uncentered_type7_lower_bound"] > 0.0
    assert RUNNER._decision("validation", (0.0,) * 29, (0.0,) * 29)["all_gates_pass"] is False


def test_publish_is_exclusive_and_nonreusable(tmp_path: Path) -> None:
    target = tmp_path / "private" / "claim.json"
    RUNNER._publish(target, {"claimed": True})
    with pytest.raises(RUNNER.InputBlockedError, match="must be absent"):
        RUNNER._publish(target, {"claimed": True})


def test_publish_cleans_temporary_file_after_prelink_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "private" / "claim.json"
    original_fsync = RUNNER.os.fsync
    calls = 0

    def failing_fsync(fd: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("injected fsync failure")
        original_fsync(fd)

    monkeypatch.setattr(RUNNER.os, "fsync", failing_fsync)
    with pytest.raises(OSError, match="injected"):
        RUNNER._publish(target, {"claimed": True})
    assert not target.exists()
    assert list(target.parent.glob(".*.tmp")) == []
