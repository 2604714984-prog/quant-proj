from datetime import date, datetime, timezone

import pytest

from quant_system.backtest.blocked_orders import BlockedExitOrder, advance_blocked_exit
from quant_system.backtest.capacity import (
    CapacityObservation,
    CapacityPolicy,
    assess_capacity,
)
from quant_system.markets.common import FillDecision, MarketDataError
from quant_system.markets.corporate_actions import CorporateAction, select_action_revision
from quant_system.markets.universe import StatusEvidence, evaluate_universe

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
UTC = timezone.utc


def test_capacity_uses_the_minimum_of_explicit_volume_and_amount_caps() -> None:
    observation = CapacityObservation(
        session_volume=100_000,
        volume_unit="shares",
        session_amount=500_000,
        amount_currency="CNY",
        source_id="bar:000001.SZ:20260713",
        source_sha256=SHA_A,
    )
    policy = CapacityPolicy(0.10, 0.05, "shares", "CNY")

    accepted = assess_capacity(2_000, 10.0, observation, policy)
    rejected = assess_capacity(3_000, 10.0, observation, policy)

    assert accepted.allowed is True
    assert accepted.binding_cap == "amount"
    assert accepted.max_volume == pytest.approx(2_500)
    assert accepted.max_amount == pytest.approx(25_000)
    assert rejected.reason == "exceeds_amount_cap"


def test_capacity_fails_closed_on_missing_identity_or_mismatched_units() -> None:
    with pytest.raises(MarketDataError, match="SHA-256"):
        CapacityObservation(100, "shares", 1_000, "CNY", "bar", "")
    observation = CapacityObservation(100, "shares", 1_000, "CNY", "bar", SHA_A)
    with pytest.raises(MarketDataError, match="volume units"):
        assess_capacity(1, 10, observation, CapacityPolicy(0.1, 0.1, "lots", "CNY"))
    with pytest.raises(MarketDataError, match="currencies"):
        assess_capacity(1, 10, observation, CapacityPolicy(0.1, 0.1, "shares", "USD"))
    with pytest.raises(MarketDataError, match="surrounding whitespace"):
        CapacityObservation(100, " shares", 1_000, "CNY", "bar", SHA_A)


def test_zero_observed_liquidity_is_valid_evidence_but_zero_capacity() -> None:
    observation = CapacityObservation(0, "shares", 0, "USD", "bar", SHA_A)
    decision = assess_capacity(1, 10, observation, CapacityPolicy(0.1, 0.1, "shares", "USD"))
    assert decision.allowed is False
    assert decision.max_volume == 0.0
    assert decision.binding_cap == "both"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0])
def test_capacity_rejects_nonfinite_or_negative_observations(bad: float) -> None:
    with pytest.raises(MarketDataError):
        CapacityObservation(bad, "shares", 1_000, "CNY", "bar", SHA_A)


def test_blocked_exit_persists_and_records_delay_until_first_fill() -> None:
    order = BlockedExitOrder("000001.SZ", 100, date(2026, 7, 13))
    order = advance_blocked_exit(
        order,
        session=date(2026, 7, 13),
        accepted_session_ordinal=0,
        session_identity_sha256=SHA_A,
        decision=FillDecision(False, None, "suspended"),
    )
    order = advance_blocked_exit(
        order,
        session=date(2026, 7, 14),
        accepted_session_ordinal=1,
        session_identity_sha256=SHA_B,
        decision=FillDecision(False, None, "limit_down_sell_rejected"),
    )
    order = advance_blocked_exit(
        order,
        session=date(2026, 7, 15),
        accepted_session_ordinal=2,
        session_identity_sha256=SHA_C,
        decision=FillDecision(True, 9.8, "filled"),
    )

    assert order.pending is False
    assert order.delay_sessions == 2
    assert order.executed_session == date(2026, 7, 15)
    assert tuple(attempt.reason for attempt in order.attempts) == (
        "suspended",
        "limit_down_sell_rejected",
        "filled",
    )
    with pytest.raises(ValueError, match="completed"):
        advance_blocked_exit(
            order,
            session=date(2026, 7, 16),
            accepted_session_ordinal=3,
            session_identity_sha256=SHA_A,
            decision=FillDecision(True, 9.9, "filled"),
        )


def test_blocked_exit_rejects_skipped_sessions_and_unrecognized_blocks() -> None:
    order = BlockedExitOrder("ABC", 1, date(2026, 7, 13))
    with pytest.raises(ValueError, match="cannot be skipped"):
        advance_blocked_exit(
            order,
            session=date(2026, 7, 13),
            accepted_session_ordinal=1,
            session_identity_sha256=SHA_A,
            decision=FillDecision(False, None, "suspended"),
        )
    with pytest.raises(MarketDataError, match="recognized reason"):
        advance_blocked_exit(
            order,
            session=date(2026, 7, 13),
            accepted_session_ordinal=0,
            session_identity_sha256=SHA_A,
            decision=FillDecision(False, None, "unknown_gap"),
        )
    with pytest.raises(MarketDataError, match="SHA-256"):
        advance_blocked_exit(
            order,
            session=date(2026, 7, 13),
            accepted_session_ordinal=0,
            session_identity_sha256="",
            decision=FillDecision(False, None, "suspended"),
        )


def _status_records(*, st: bool = False, suspended: bool = False) -> list[StatusEvidence]:
    known = datetime(2026, 7, 12, 12, tzinfo=UTC)
    return [
        StatusEvidence(
            "000001.SZ", "listed", True, date(1991, 4, 3), None, known, "list", SHA_A
        ),
        StatusEvidence(
            "000001.SZ",
            "delisted",
            False,
            date(1991, 4, 3),
            None,
            known,
            "delist",
            SHA_B,
        ),
        StatusEvidence(
            "000001.SZ", "st", st, date(2026, 1, 1), None, known, "st", SHA_C
        ),
        StatusEvidence(
            "000001.SZ",
            "suspended",
            suspended,
            date(2026, 7, 13),
            date(2026, 7, 14),
            known,
            "suspension",
            "d" * 64,
        ),
    ]


def test_universe_predicate_requires_all_effective_identities_before_cutoff() -> None:
    cutoff = datetime(2026, 7, 13, 9, tzinfo=UTC)
    eligible = evaluate_universe("000001.SZ", date(2026, 7, 13), cutoff, _status_records())
    excluded = evaluate_universe(
        "000001.SZ", date(2026, 7, 13), cutoff, _status_records(st=True)
    )

    assert eligible.eligible is True
    assert tuple(kind for kind, _, _ in eligible.evidence) == (
        "listed",
        "delisted",
        "st",
        "suspended",
    )
    assert excluded.eligible is False
    assert excluded.reasons == ("st",)


def test_universe_predicate_fails_on_late_missing_or_ambiguous_status() -> None:
    cutoff = datetime(2026, 7, 13, 9, tzinfo=UTC)
    records = _status_records()
    records[2] = StatusEvidence(
        "000001.SZ",
        "st",
        False,
        date(2026, 1, 1),
        None,
        datetime(2026, 7, 13, 10, tzinfo=UTC),
        "late-st",
        SHA_C,
    )
    with pytest.raises(MarketDataError, match="missing effective st"):
        evaluate_universe("000001.SZ", date(2026, 7, 13), cutoff, records)

    records = _status_records()
    records.append(records[2])
    with pytest.raises(MarketDataError, match="ambiguous effective st"):
        evaluate_universe("000001.SZ", date(2026, 7, 13), cutoff, records)

    with pytest.raises(MarketDataError, match="timezone-aware"):
        evaluate_universe(
            "000001.SZ",
            date(2026, 7, 13),
            datetime(2026, 7, 13, 9),
            _status_records(),
        )
    with pytest.raises(MarketDataError, match="missing effective suspended"):
        evaluate_universe(
            "000001.SZ", date(2026, 7, 13), cutoff, _status_records()[:-1]
        )


def _dividend(**overrides: object) -> CorporateAction:
    values: dict[str, object] = {
        "action_id": "SPY:2026Q2:dividend",
        "action_type": "cash_dividend",
        "symbol": "SPY",
        "source_url": "https://example.test/distribution.pdf",
        "source_sha256": SHA_A,
        "revision": 1,
        "supersedes_sha256": None,
        "available_at": datetime(2026, 6, 1, 12, tzinfo=UTC),
        "effective_at": datetime(2026, 6, 20, 0, tzinfo=UTC),
        "ex_date": date(2026, 6, 20),
        "record_date": date(2026, 6, 21),
        "pay_date": date(2026, 6, 25),
        "cash_amount": 1.25,
        "currency": "USD",
    }
    values.update(overrides)
    return CorporateAction(**values)


def test_corporate_action_validates_dates_fields_and_source_identity() -> None:
    action = _dividend()
    assert action.cash_amount == pytest.approx(1.25)
    with pytest.raises(MarketDataError, match="ex_date <= record_date"):
        _dividend(record_date=date(2026, 6, 19))
    with pytest.raises(MarketDataError, match="uncredentialed HTTPS"):
        _dividend(source_url="https://user:secret@example.test/file")
    with pytest.raises(MarketDataError, match="uppercase"):
        _dividend(currency="usd")
    with pytest.raises(MarketDataError, match="timezone-aware"):
        _dividend(available_at=datetime(2026, 6, 1, 12))
    with pytest.raises(MarketDataError, match="not a datetime"):
        _dividend(ex_date=datetime(2026, 6, 20, tzinfo=UTC))


def test_corporate_action_revision_selection_is_point_in_time_and_contiguous() -> None:
    original = _dividend()
    revised = _dividend(
        source_sha256=SHA_B,
        revision=2,
        supersedes_sha256=SHA_A,
        available_at=datetime(2026, 6, 10, 12, tzinfo=UTC),
        cash_amount=1.30,
    )

    assert select_action_revision(
        [revised, original], datetime(2026, 6, 5, tzinfo=UTC)
    ) is original
    assert select_action_revision(
        [original, revised], datetime(2026, 6, 11, tzinfo=UTC)
    ) is revised
    broken = _dividend(
        source_sha256=SHA_C,
        revision=2,
        supersedes_sha256="d" * 64,
        available_at=datetime(2026, 6, 10, 12, tzinfo=UTC),
    )
    with pytest.raises(MarketDataError, match="chain is broken"):
        select_action_revision([original, broken], datetime(2026, 6, 11, tzinfo=UTC))


def test_split_and_symbol_change_have_distinct_strict_fields() -> None:
    split = CorporateAction(
        "ABC:split",
        "split",
        "ABC",
        "https://example.test/split",
        SHA_A,
        1,
        None,
        datetime(2026, 6, 1, tzinfo=UTC),
        datetime(2026, 7, 1, tzinfo=UTC),
        ex_date=date(2026, 7, 1),
        split_ratio=2.0,
    )
    change = CorporateAction(
        "ABC:symbol",
        "symbol_change",
        "ABC",
        "https://example.test/symbol",
        SHA_B,
        1,
        None,
        datetime(2026, 6, 1, tzinfo=UTC),
        datetime(2026, 7, 1, tzinfo=UTC),
        new_symbol="XYZ",
    )
    assert (split.split_ratio, change.new_symbol) == (2.0, "XYZ")
    with pytest.raises(MarketDataError, match="cannot contain split"):
        CorporateAction(
            "ABC:bad-symbol",
            "symbol_change",
            "ABC",
            "https://example.test/symbol",
            SHA_C,
            1,
            None,
            datetime(2026, 6, 1, tzinfo=UTC),
            datetime(2026, 7, 1, tzinfo=UTC),
            split_ratio=2.0,
            new_symbol="XYZ",
        )
