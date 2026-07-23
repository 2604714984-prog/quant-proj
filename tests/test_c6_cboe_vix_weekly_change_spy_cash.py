from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import research.adapters.c6_cboe_vix_weekly_change_spy_cash as ADAPTER
from research.adapters.c6_cboe_vix_weekly_change_spy_cash import (
    BOOTSTRAP_BLOCK_LENGTH,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    HOLDOUT_INTERVALS,
    PROGRAM_ALPHA,
    RESEARCH_ID,
    VALIDATION_INTERVALS,
    BootstrapInference,
    InputContractError,
    bootstrap_inference,
    circular_block_bootstrap_indices,
    derive_weekly_state,
    holdout_decision,
    split_support,
    validation_decision,
)
from quant_system.data import session_dates_sha256, session_rows_sha256


RUNNER_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts/run_c6_cboe_vix_weekly_change_spy_cash_once.py"
)
SPEC = importlib.util.spec_from_file_location("c6_vix_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def _state(index: int, state: str):
    observation = date(2019, 1, 4) + timedelta(days=7 * index)
    prior = observation - timedelta(days=7)
    execution = observation + timedelta(days=3)
    prior_close = 20.0
    current_close = 21.0 if state == "cash" else 20.0
    return derive_weekly_state(
        prior_observation_date=prior,
        observation_date=observation,
        execution_date=execution,
        prior_close=prior_close,
        current_close=current_close,
        available_at=datetime(
            observation.year,
            observation.month,
            observation.day,
            16,
            15,
            tzinfo=ZoneInfo("America/New_York"),
        ),
        row_sha256=hashlib.sha256(f"state-{index}".encode()).hexdigest(),
    )


def _private_file(path: Path, payload: bytes) -> Path:
    path.write_bytes(payload)
    path.chmod(0o600)
    return path


def _source_row(
    seed: str = "a",
    *,
    available_at: str = "2020-01-01T00:00:00+00:00",
) -> dict[str, object]:
    return {
        "source_url": "https://example.com/source",
        "content_sha256": seed * 64,
        "available_at": available_at,
        "retrieved_at": "2020-01-02T00:00:00+00:00",
        "revision_id": f"revision-{seed}",
        "supersedes_revision_id": None,
    }


def _source(seed: str = "a"):
    return RUNNER._source(_source_row(seed))


def _calendar_payload(
    *,
    exchange: str = "XNYS",
    timezone_name: str = "America/New_York",
) -> dict[str, object]:
    zone = ZoneInfo(timezone_name)
    raw_rows: list[dict[str, object]] = []
    sessions = []
    for index, day in enumerate((date(2021, 12, 31), date(2022, 1, 3))):
        source_row = _source_row("a")
        opened = datetime(day.year, day.month, day.day, 9, 30, tzinfo=zone)
        closed = datetime(day.year, day.month, day.day, 16, 0, tzinfo=zone)
        raw_rows.append(
            {
                "session_date": day.isoformat(),
                "open_at": opened.isoformat(),
                "close_at": closed.isoformat(),
                "is_early_close": False,
                "exchange_id": exchange,
                "exchange_timezone": timezone_name,
                "row_sha256": hashlib.sha256(f"row-{index}".encode()).hexdigest(),
                "source": source_row,
            }
        )
        sessions.append(
            RUNNER.AcceptedSession(
                day,
                opened,
                closed,
                RUNNER._source(source_row),
                timezone_name,
                False,
                exchange,
            )
        )
    return {
        "calendar_identity": {
            "exchange_id": exchange,
            "exchange_timezone": timezone_name,
            "coverage_start": "2021-12-31",
            "coverage_end": "2022-01-03",
            "session_count": 2,
            "session_dates_sha256": session_dates_sha256(
                session.session_date for session in sessions
            ),
            "session_rows_sha256": session_rows_sha256(sessions),
            "source_identity": _source_row("b"),
        },
        "session_rows": raw_rows,
    }


def _status():
    return RUNNER.StatusEvidence(
        "listed-1",
        "SPY",
        "listed",
        True,
        date(1993, 1, 29),
        None,
        "America/New_York",
        _source("d"),
    )


def _action():
    return RUNNER.CorporateActionIdentity(
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


def _execution_row(*, basis: str = "raw_pre_action_per_old_share"):
    return {
        "symbol": "SPY",
        "market": "us",
        "session_date": "2022-01-03",
        "raw_open": 100.0,
        "currency": "USD",
        "source": _source_row("e"),
        "decision_price": 100.0,
        "decision_price_session": "2021-12-31",
        "decision_price_effective_at": "2021-12-31T16:00:00-05:00",
        "decision_price_source": _source_row("f"),
        "decision_price_basis": basis,
        "execution_price_effective_at": "2022-01-03T09:30:00-05:00",
        "execution_price_basis": "retrospective_daily_bar_open_fill",
        "corporate_action_ids": ["dividend-1"],
    }


def test_frozen_constants_and_code_identities_are_exact() -> None:
    assert RESEARCH_ID == "C6_VIX_WEEKLY_CHANGE_IMPULSE_SPY_CASH_V1"
    assert PROGRAM_ALPHA == 0.0015625
    assert (VALIDATION_INTERVALS, HOLDOUT_INTERVALS) == (129, 156)
    assert (BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED, BOOTSTRAP_BLOCK_LENGTH) == (
        10_000,
        1_196_101,
        13,
    )
    assert RUNNER._file_sha256(RUNNER.DEFINITION) == RUNNER.DEFINITION_SHA256
    assert RUNNER._file_sha256(RUNNER.ADAPTER) == RUNNER.ADAPTER_SHA256
    assert RUNNER._core_identity() == (
        RUNNER.CORE_SOURCE_FILE_COUNT,
        RUNNER.CORE_SOURCE_SHA256,
    )
    assert RUNNER.STATE_INPUT_SHA256 == (
        "3a221b43b625634f456a4e29a010b7eb8746508933aaeba1b29e3540911a4491"
    )
    assert RUNNER.CALENDAR_INPUT_SHA256 == (
        "08b1722c675012d89e0b4f92ed51f51160adbd1d54961c093c52101c067fc553"
    )
    assert RUNNER.VALIDATION_BUNDLE_SHA256 == (
        "51c402ef95ab93a235dd38c862be517f9f0ed06fa47c3bb91becc33e914aa2d6"
    )
    assert RUNNER.HOLDOUT_BUNDLE_SHA256 == (
        "120eeeacd724af31125c7209985621d90d1edd1c95cfe068098fc3bf903a8db1"
    )
    assert RUNNER.TECHNICAL_CONTINUATION_ID == "PREOUTCOME_TECHNICAL_CONTINUATION_1"
    assert RUNNER.PRIOR_VALIDATION_CLAIM_SHA256 == (
        "b238f671e9c1f5f71106da5ca31dc54fc8389f6e61b138dc1f911710d9bd2d03"
    )
    assert RUNNER.PRIOR_VALIDATION_RESULT_SHA256 == (
        "72b76ad796245c031a83bc42afd6277248ab18c6fb0a883eb0610862de715494"
    )
    assert RUNNER.VALIDATION_CLAIM != RUNNER.PRIOR_VALIDATION_CLAIM
    assert RUNNER.VALIDATION_RESULT != RUNNER.PRIOR_VALIDATION_RESULT
    definition = json.loads(RUNNER.DEFINITION.read_text())
    assert definition["runtime_bundle_contract"][
        "expected_inclusion_rule_sha256"
    ] == RUNNER.INCLUSION_RULE_SHA256
    assert definition["input_identities"]["adapter_sha256"] == (
        RUNNER.ADAPTER_SHA256
    )


def test_state_top_and_row_provenance_classes_are_distinct_and_exact() -> None:
    assert RUNNER.STATE_TOP_SOURCE_CLASS == (
        "RETROSPECTIVE_SECONDARY_NOT_STRICT_HISTORICAL_PIT"
    )
    assert RUNNER.STATE_ROW_SOURCE_CLASS == (
        "CBOE_CURRENT_SNAPSHOT_RETROSPECTIVE_SECONDARY_NOT_STRICT_HISTORICAL_PIT"
    )
    assert RUNNER.STATE_TOP_SOURCE_CLASS != RUNNER.STATE_ROW_SOURCE_CLASS


def test_pinned_external_state_labels_map_exactly_to_internal_states() -> None:
    assert RUNNER._state_label_matches("SPY", "spy") is True
    assert RUNNER._state_label_matches("cash", "cash") is True
    assert RUNNER._state_label_matches("spy", "spy") is False
    assert RUNNER._state_label_matches("CASH", "cash") is False
    assert RUNNER._state_label_matches(None, "spy") is False


def test_equality_maps_to_spy_and_missing_or_late_values_fail_closed() -> None:
    equal = _state(0, "spy")
    assert (equal.state, equal.spy_target_weight) == ("spy", 1.0)
    increasing = _state(1, "cash")
    assert (increasing.state, increasing.spy_target_weight) == ("cash", 0.0)
    with pytest.raises(InputContractError, match="int or float"):
        derive_weekly_state(
            prior_observation_date=date(2021, 1, 1),
            observation_date=date(2021, 1, 8),
            execution_date=date(2021, 1, 11),
            prior_close=20.0,
            current_close=None,  # type: ignore[arg-type]
            available_at=datetime(
                2021,
                1,
                8,
                16,
                15,
                tzinfo=ZoneInfo("America/New_York"),
            ),
            row_sha256="a" * 64,
        )
    with pytest.raises(InputContractError, match="16:15"):
        derive_weekly_state(
            prior_observation_date=date(2021, 1, 1),
            observation_date=date(2021, 1, 8),
            execution_date=date(2021, 1, 11),
            prior_close=20.0,
            current_close=21.0,
            available_at=datetime(
                2021,
                1,
                8,
                16,
                16,
                tzinfo=ZoneInfo("America/New_York"),
            ),
            row_sha256="a" * 64,
        )


def test_support_uses_exact_count_states_and_both_transition_directions() -> None:
    states = tuple(
        _state(index, "spy" if index % 2 == 0 else "cash")
        for index in range(VALIDATION_INTERVALS)
    )
    support = split_support(states, split_id="validation")
    assert support.all_gates_pass is True
    assert tuple(name for name, _ in support.gates) == (
        "complete_intervals_at_least_104",
        "spy_state_intervals_at_least_13",
        "cash_state_intervals_at_least_13",
        "spy_to_cash_transitions_at_least_4",
        "cash_to_spy_transitions_at_least_4",
    )
    with pytest.raises(InputContractError, match="exactly 129"):
        split_support(states[:-1], split_id="validation")
    weak = tuple(
        _state(index, "cash" if index < 3 else "spy")
        for index in range(VALIDATION_INTERVALS)
    )
    assert split_support(weak, split_id="validation").all_gates_pass is False


def test_validation_uses_exact_three_gates_and_strict_equality() -> None:
    strategy = (0.01,) * VALIDATION_INTERVALS
    spy = (0.0,) * VALIDATION_INTERVALS
    passing = validation_decision(strategy, spy)
    assert passing.all_gates_pass is True
    assert tuple(name for name, _ in passing.gates) == (
        "strategy_terminal_net_wealth_strictly_above_spy",
        "arithmetic_mean_paired_weekly_active_return_strictly_positive",
        "strategy_maximum_drawdown_no_worse_than_spy",
    )
    equal = validation_decision(spy, spy)
    assert dict(equal.gates) == {
        "strategy_terminal_net_wealth_strictly_above_spy": False,
        "arithmetic_mean_paired_weekly_active_return_strictly_positive": False,
        "strategy_maximum_drawdown_no_worse_than_spy": True,
    }
    with pytest.raises(InputContractError, match="exactly 129"):
        validation_decision(strategy[:-1], spy[:-1])


def test_nonconstant_bootstrap_has_literal_golden_paths_and_output() -> None:
    paths = circular_block_bootstrap_indices(17)
    assert paths[:3] == (
        (14, 15, 16, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 6, 7, 8, 9),
        (12, 13, 14, 15, 16, 0, 1, 2, 3, 4, 5, 6, 7, 14, 15, 16, 0),
        (9, 10, 11, 12, 13, 14, 15, 16, 0, 1, 2, 3, 4, 5, 6, 7, 8),
    )
    payload = json.dumps(paths, separators=(",", ":")).encode()
    assert hashlib.sha256(payload).hexdigest() == (
        "9e53f1e2f904f48af251f911fd4c0c771217b7724cd80f087e041409a61039cd"
    )
    active = tuple(
        0.003 + ((index % 11) - 5) * 0.0004
        for index in range(HOLDOUT_INTERVALS)
    )
    result = bootstrap_inference(active)
    assert result.observed_mean_active_return == pytest.approx(
        0.002976923076923077
    )
    assert result.centered_null_one_sided_p == pytest.approx(1 / 10_001)
    assert result.uncentered_type7_lower_bound == pytest.approx(
        0.002824675480769231
    )


def test_holdout_uses_exact_five_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ADAPTER,
        "bootstrap_inference",
        lambda active: BootstrapInference(0.01, PROGRAM_ALPHA, 0.001),
    )
    decision = holdout_decision(
        (0.01,) * HOLDOUT_INTERVALS,
        (0.0,) * HOLDOUT_INTERVALS,
    )
    assert decision.all_gates_pass is True
    assert tuple(name for name, _ in decision.gates) == (
        "strategy_terminal_net_wealth_strictly_above_spy",
        "strategy_maximum_drawdown_no_worse_than_spy",
        "interval_count_exactly_156",
        "centered_null_one_sided_p_at_most_0_0015625",
        "uncentered_type7_0_0015625_lower_bound_strictly_positive",
    )


def test_placeholder_hashes_fail_before_claim_or_state_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    monkeypatch.setattr(
        RUNNER,
        "VALIDATION_BUNDLE_SHA256",
        "__PATCH_C6_VALIDATION_BUNDLE_SHA256__",
    )
    monkeypatch.setattr(
        RUNNER,
        "HOLDOUT_BUNDLE_SHA256",
        "__PATCH_C6_HOLDOUT_BUNDLE_SHA256__",
    )
    monkeypatch.setattr(RUNNER, "_publish", lambda *args, **kwargs: events.append("claim"))
    monkeypatch.setattr(RUNNER, "_capture", lambda *args, **kwargs: events.append("open"))
    with pytest.raises(RUNNER.InputBlockedError, match="not materialized"):
        RUNNER.execute_once()
    assert events == []


def test_capture_rejects_duplicate_json_identity_mismatch_and_symlink(
    tmp_path: Path,
) -> None:
    with pytest.raises(RUNNER.InputBlockedError, match="duplicate JSON key"):
        RUNNER._json(b'{"a":1,"a":2}', "synthetic")
    target = _private_file(tmp_path / "input.json", b"{}")
    with pytest.raises(RUNNER.InputBlockedError, match="SHA-256 mismatch"):
        RUNNER._capture(target, "0" * 64, max_bytes=10)
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(RUNNER.InputBlockedError, match="cannot open"):
        RUNNER._capture(link, None, max_bytes=10)


def test_runtime_bundle_preflight_precedes_0600_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _private_file(tmp_path / "bundle.json", b"bundle")
    claim = tmp_path / "private" / "claim.json"
    result = claim.with_name("result.json")
    bundle_sha = RUNNER._sha256_bytes(bundle.read_bytes())
    events: list[str] = []
    original_publish = RUNNER._publish
    original_capture = RUNNER._capture

    def publishing(path: Path, record: dict[str, object]) -> str:
        events.append("claim" if path == claim else "result")
        return original_publish(path, record)

    def capturing(path: Path, expected: str | None, **kwargs) -> bytes:
        assert path == bundle and not claim.exists() and expected == bundle_sha
        events.append("capture")
        return original_capture(path, expected, **kwargs)

    monkeypatch.setattr(RUNNER, "_publish", publishing)
    monkeypatch.setattr(RUNNER, "_capture", capturing)
    monkeypatch.setattr(
        RUNNER,
        "_load_bundle",
        lambda payload, **kwargs: events.append("load") or object(),
    )
    monkeypatch.setattr(
        RUNNER,
        "_simulate",
        lambda loaded: (
            events.append("simulate")
            or ((0.01,) * VALIDATION_INTERVALS, (0.0,) * VALIDATION_INTERVALS, ())
        ),
    )
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
    assert events == ["capture", "load", "claim", "simulate", "result"]
    assert record["classification"] == (
        "RETROSPECTIVE_SECONDARY_VALIDATION_PASS_HOLDOUT_UNLOCKED"
    )
    assert stat.S_IMODE(claim.stat().st_mode) == 0o600
    assert stat.S_IMODE(result.stat().st_mode) == 0o600
    claim_record = json.loads(claim.read_text())
    assert claim_record["technical_continuation_id"] == RUNNER.TECHNICAL_CONTINUATION_ID
    assert claim_record["prior_claim_sha256"] == RUNNER.PRIOR_VALIDATION_CLAIM_SHA256
    assert claim_record["prior_result_sha256"] == RUNNER.PRIOR_VALIDATION_RESULT_SHA256


def test_bundle_identity_failure_before_claim_creates_no_private_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _private_file(tmp_path / "bundle.json", b"bundle")
    claim = tmp_path / "private" / "claim.json"
    result = claim.with_name("result.json")
    bundle_sha = RUNNER._sha256_bytes(bundle.read_bytes())
    events: list[str] = []

    def rejecting(payload: bytes, **kwargs):
        events.append("load")
        raise RUNNER.InputBlockedError("universe snapshot calendar identity mismatch")

    monkeypatch.setattr(
        RUNNER,
        "_capture",
        lambda *args, **kwargs: events.append("capture") or bundle.read_bytes(),
    )
    monkeypatch.setattr(RUNNER, "_load_bundle", rejecting)
    monkeypatch.setattr(
        RUNNER,
        "_publish",
        lambda *args, **kwargs: events.append("publish"),
    )
    with pytest.raises(RUNNER.InputBlockedError, match="calendar identity mismatch"):
        RUNNER._stage(
            "validation",
            bundle,
            claim,
            result,
            runner_sha256="b" * 64,
            state_sha256=RUNNER.STATE_INPUT_SHA256,
            expected_bundle_sha256=bundle_sha,
            official_states={},
        )
    assert events == ["capture", "load"]
    assert not claim.exists()
    assert not result.exists()


def test_technical_continuation_requires_exact_prior_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prior = tmp_path / "prior"
    prior.mkdir(mode=0o700)
    prior_claim = _private_file(prior / "claim.json", b"old-claim")
    prior_result = _private_file(prior / "result.json", b"old-result")
    monkeypatch.setattr(RUNNER, "PRIOR_VALIDATION_CLAIM", prior_claim)
    monkeypatch.setattr(RUNNER, "PRIOR_VALIDATION_RESULT", prior_result)
    monkeypatch.setattr(
        RUNNER, "PRIOR_VALIDATION_CLAIM_SHA256", RUNNER._file_sha256(prior_claim)
    )
    monkeypatch.setattr(
        RUNNER, "PRIOR_VALIDATION_RESULT_SHA256", RUNNER._file_sha256(prior_result)
    )
    validation_claim = tmp_path / "continuation-validation" / "claim.json"
    holdout_claim = tmp_path / "continuation-holdout" / "claim.json"
    monkeypatch.setattr(RUNNER, "VALIDATION_CLAIM", validation_claim)
    monkeypatch.setattr(RUNNER, "VALIDATION_RESULT", validation_claim.with_name("result.json"))
    monkeypatch.setattr(RUNNER, "HOLDOUT_CLAIM", holdout_claim)
    monkeypatch.setattr(RUNNER, "HOLDOUT_RESULT", holdout_claim.with_name("result.json"))
    RUNNER._validate_technical_continuation()
    prior_result.write_bytes(b"changed")
    with pytest.raises(RUNNER.InputBlockedError, match="SHA-256 mismatch"):
        RUNNER._validate_technical_continuation()
    assert not validation_claim.exists()
    assert not holdout_claim.exists()


@pytest.mark.parametrize(
    "classification",
    ["RETROSPECTIVE_SECONDARY_VALIDATION_FAIL", "INPUT_BLOCKED_CLAIM_CONSUMED"],
)
def test_validation_failure_or_input_block_keeps_holdout_sealed(
    classification: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(RUNNER, "VALIDATION_BUNDLE_SHA256", "a" * 64)
    monkeypatch.setattr(RUNNER, "HOLDOUT_BUNDLE_SHA256", "b" * 64)
    monkeypatch.setattr(RUNNER, "_capture", lambda *args, **kwargs: b"{}")
    monkeypatch.setattr(RUNNER, "_validate_definition", lambda payload: None)
    monkeypatch.setattr(
        RUNNER,
        "_file_sha256",
        lambda path: RUNNER.ADAPTER_SHA256 if path == RUNNER.ADAPTER else "c" * 64,
    )
    monkeypatch.setattr(
        RUNNER,
        "_core_identity",
        lambda: (RUNNER.CORE_SOURCE_FILE_COUNT, RUNNER.CORE_SOURCE_SHA256),
    )
    monkeypatch.setattr(RUNNER, "_load_states", lambda payload: {})
    monkeypatch.setattr(RUNNER, "_validate_technical_continuation", lambda: None)

    def stage(stage: str, *args, **kwargs):
        calls.append(stage)
        return {"classification": classification}

    monkeypatch.setattr(RUNNER, "_stage", stage)
    assert RUNNER.execute_once()["classification"] == classification
    assert calls == ["validation"]


def test_inclusion_rule_decision_basis_calendar_and_actions_are_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calendar = RUNNER._calendar(_calendar_payload())
    action = _action()
    decision_at = datetime(
        2022,
        1,
        3,
        9,
        tzinfo=ZoneInfo("America/New_York"),
    )
    execution = RUNNER._execution(
        _execution_row(),
        (_status(),),
        (action,),
        signal_session=date(2021, 12, 31),
        decision_at=decision_at,
        calendar=calendar,
    )
    assert execution.corporate_actions == (action,)
    assert execution.decision_price_basis == "raw_pre_action_per_old_share"
    assert execution.execution_price_basis == "retrospective_daily_bar_open_fill"
    with pytest.raises(RUNNER.InputBlockedError, match="price basis"):
        RUNNER._execution(
            _execution_row(basis="raw_execution_units"),
            (_status(),),
            (action,),
            signal_session=date(2021, 12, 31),
            decision_at=decision_at,
            calendar=calendar,
        )
    with pytest.raises(RUNNER.InputBlockedError, match="XNYS"):
        RUNNER._calendar(_calendar_payload(exchange="XNAS"))
    with pytest.raises(RUNNER.InputBlockedError, match="coverage"):
        RUNNER._execution_actions((action,), date(2022, 1, 3), [])

    snapshot_row = {
        "market": "us",
        "exchange_id": "XNYS",
        "effective_session": "2022-01-03",
        "member_count": 1,
        "ordered_members_sha256": "a" * 64,
        "lifecycle_coverage_sha256": "b" * 64,
        "inclusion_rule_sha256": "0" * 64,
        "calendar_identity_sha256": "c" * 64,
        "source_identity": _source_row("d"),
    }
    with pytest.raises(RUNNER.InputBlockedError, match="inclusion rule"):
        RUNNER._snapshot(snapshot_row)

    observed: dict[str, object] = {}

    def core(portfolio, runtime_calendar, **kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            portfolio=portfolio,
            stage_hash="1" * 64,
            final_nav=40_000.0,
        )

    monkeypatch.setattr(RUNNER, "run_static_rebalance", core)
    point = RUNNER.Point(
        date(2021, 12, 31),
        decision_at,
        date(2022, 1, 3),
        calendar,
        None,
        execution,
        object(),
        _state(0, "spy"),
        False,
    )
    RUNNER._rebalance(RUNNER.Portfolio.us(40_000.0), point, 1.0, "0" * 64)
    propagated = observed["execution_inputs"][0]
    assert propagated.corporate_actions == (action,)
    assert observed["slippage_bps"] == 10.0
    assert observed["strategy_definition_sha256"] == RUNNER.DEFINITION_SHA256
    assert observed["strategy_adapter_sha256"] == RUNNER.ADAPTER_SHA256


def test_non_session_corporate_action_is_rejected() -> None:
    action = _action()
    with pytest.raises(
        RUNNER.InputBlockedError,
        match="corporate action effective date must be an accepted split session",
    ):
        RUNNER._require_action_sessions(
            (action,),
            (date(2021, 12, 31), date(2022, 1, 4)),
        )

    RUNNER._require_action_sessions(
        (action,),
        (date(2021, 12, 31), date(2022, 1, 3)),
    )


def test_publish_is_exclusive_and_nonreusable(tmp_path: Path) -> None:
    target = tmp_path / "private" / "claim.json"
    RUNNER._publish(target, {"claimed": True})
    with pytest.raises(RUNNER.InputBlockedError, match="must be absent"):
        RUNNER._publish(target, {"claimed": True})
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
