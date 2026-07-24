from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import hashlib
from zoneinfo import ZoneInfo

import pytest

from quant_system.backtest import (
    ExecutionInput,
    Portfolio,
    TransactionCostModel,
)
from quant_system.data import (
    AcceptedSession,
    AcceptedSessionCalendar,
    CalendarIdentity,
    SourceIdentity,
    calendar_identity_sha256,
    session_dates_sha256,
    session_rows_sha256,
)
from quant_system.markets.universe import (
    StatusEvidence,
    UniverseSnapshotIdentity,
    lifecycle_coverage_sha256,
    ordered_members_sha256,
)
from research.adapters.gdpnow_live_revision_impulse import (
    Distribution,
    EXPECTED_INCLUSION_RULE_SHA256,
    GDPNowRow,
    InputContractError,
    SECONDARY_MONTHS,
    VALIDATION_MONTHS,
    adjudicate,
    apply_distribution,
    monthly_signals,
    rebalance,
    rebalance_to_spy_weight,
    require_secondary_unsealed,
)


UTC = timezone.utc
DEFINITION_SHA = hashlib.sha256(b"definition").hexdigest()
ADAPTER_SHA = hashlib.sha256(b"adapter").hexdigest()


def _source(label: str, available: datetime) -> SourceIdentity:
    return SourceIdentity(
        f"https://example.test/{label}",
        hashlib.sha256(label.encode()).hexdigest(),
        available,
        available + timedelta(minutes=1),
        label,
    )


def _calendar() -> AcceptedSessionCalendar:
    zone = ZoneInfo("America/New_York")
    days = (date(2020, 1, 31), date(2020, 2, 3), date(2020, 2, 4))
    rows = tuple(
        AcceptedSession(
            day,
            datetime.combine(day, time(9, 30), zone),
            datetime.combine(day, time(16), zone),
            _source(f"calendar-{day}", datetime(2000, 1, 1, tzinfo=UTC)),
            "America/New_York",
            exchange_id="XNYS",
        )
        for day in days
    )
    identity = CalendarIdentity(
        "XNYS",
        "America/New_York",
        days[0],
        days[-1],
        len(days),
        session_dates_sha256(days),
        session_rows_sha256(rows),
        _source("calendar", datetime(2000, 1, 1, tzinfo=UTC)),
    )
    return AcceptedSessionCalendar(rows, identity=identity)


def _execution_fixture():
    calendar = _calendar()
    signal = calendar.session_on(
        date(2020, 1, 31), as_of=datetime(2020, 1, 31, 21, tzinfo=UTC)
    )
    execution = calendar.next_session(signal.session_date, as_of=signal.close_at)
    source = _source("status", datetime(2000, 1, 1, tzinfo=UTC))
    statuses = (
        StatusEvidence(
            "spy-listed",
            "SPY",
            "listed",
            True,
            date(1993, 1, 29),
            None,
            "America/New_York",
            source,
        ),
        StatusEvidence(
            "spy-not-delisted",
            "SPY",
            "delisted",
            False,
            date(1993, 1, 29),
            None,
            "America/New_York",
            source,
        ),
    )
    row = ExecutionInput(
        "SPY",
        "us",
        100.0,
        "USD",
        _source("open", execution.open_at),
        statuses,
        decision_price=100.0,
        decision_price_source=_source(
            "prior-close", datetime(2000, 1, 1, tzinfo=UTC)
        ),
        decision_price_basis="raw_pre_action_per_old_share",
        execution_price_effective_at=execution.open_at,
        execution_price_basis="retrospective_daily_bar_open_fill",
    )
    decision_at = datetime.combine(
        execution.session_date,
        time(8, 30),
        ZoneInfo("America/New_York"),
    )
    lifecycle_hash = lifecycle_coverage_sha256(
        ("SPY",),
        execution,
        decision_at,
        {"SPY": statuses},
        market="us",
    )
    snapshot = UniverseSnapshotIdentity(
        "us",
        "XNYS",
        execution.session_date,
        1,
        ordered_members_sha256(("SPY",)),
        lifecycle_hash,
        EXPECTED_INCLUSION_RULE_SHA256,
        calendar_identity_sha256(calendar.identity),
        _source("snapshot", datetime(2000, 1, 1, tzinfo=UTC)),
    )
    return calendar, signal, row, snapshot, decision_at


def _row(
    day: date,
    quarter: date,
    value: str,
    suffix: str,
) -> GDPNowRow:
    return GDPNowRow(day, quarter, Decimal(value), suffix * 64)


def test_signal_uses_latest_two_same_quarter_and_reset_is_cash() -> None:
    rows = (
        _row(date(2020, 1, 2), date(2020, 3, 31), "1.0", "1"),
        _row(date(2020, 1, 15), date(2020, 3, 31), "1.2", "2"),
        _row(date(2020, 2, 4), date(2020, 3, 31), "1.2", "3"),
        _row(date(2020, 4, 15), date(2020, 6, 30), "2.0", "4"),
    )
    signals = monthly_signals(rows, ("2020-01", "2020-02", "2020-03", "2020-04"))
    assert tuple(signal.risk_on for signal in signals) == (
        True,
        False,
        False,
        False,
    )
    assert signals[0].revision_impulse == Decimal("0.2")
    assert signals[1].revision_impulse == Decimal("0.0")
    assert signals[3].pair_status == "INSUFFICIENT_SAME_QUARTER_PAIR"
    assert signals[3].previous_row_sha256 is None


def test_signal_rejects_cross_month_gaps_unsorted_rows_and_duplicate_hashes() -> None:
    first = _row(date(2020, 1, 2), date(2020, 3, 31), "1.0", "1")
    second = _row(date(2020, 1, 15), date(2020, 3, 31), "1.2", "2")
    with pytest.raises(InputContractError, match="consecutive"):
        monthly_signals((first, second), ("2020-01", "2020-03"))
    with pytest.raises(InputContractError, match="sorted"):
        monthly_signals((second, first), ("2020-01",))
    with pytest.raises(InputContractError, match="hashes"):
        monthly_signals((first, replace(second, row_sha256=first.row_sha256)), ("2020-01",))


def test_signal_row_requires_quarter_end_finite_decimal_and_sha256() -> None:
    with pytest.raises(InputContractError, match="quarter end"):
        _row(date(2020, 1, 2), date(2020, 3, 30), "1.0", "1")
    with pytest.raises(InputContractError, match="finite"):
        _row(date(2020, 1, 2), date(2020, 3, 31), "NaN", "1")
    with pytest.raises(InputContractError, match="SHA-256"):
        GDPNowRow(
            date(2020, 1, 2),
            date(2020, 3, 31),
            Decimal("1.0"),
            "not-a-hash",
        )


def test_rebalance_uses_shared_core_and_charges_10_bps_once() -> None:
    calendar, signal, row, snapshot, decision_at = _execution_fixture()
    portfolio = Portfolio.us(
        40_000,
        costs=TransactionCostModel(commission_rate=0.001),
    )
    result = rebalance(
        portfolio,
        calendar,
        signal_session=signal.session_date,
        decision_at=decision_at,
        execution_inputs=(row,),
        universe_snapshot=snapshot,
        risk_on=True,
        strategy_definition_sha256=DEFINITION_SHA,
        strategy_adapter_sha256=ADAPTER_SHA,
        prior_stage_hash="0" * 64,
    )
    receipt = result.receipts[0]
    assert receipt.filled_shares == 399
    assert receipt.commission == pytest.approx(39.9)
    assert receipt.cash_after == pytest.approx(60.1)
    assert portfolio.positions == {}


def test_monthly_fifty_fifty_uses_same_core_and_cost_contract() -> None:
    calendar, signal, row, snapshot, decision_at = _execution_fixture()
    portfolio = Portfolio.us(
        40_000,
        costs=TransactionCostModel(commission_rate=0.001),
    )
    result = rebalance_to_spy_weight(
        portfolio,
        calendar,
        signal_session=signal.session_date,
        decision_at=decision_at,
        execution_inputs=(row,),
        universe_snapshot=snapshot,
        spy_weight=0.5,
        strategy_definition_sha256=DEFINITION_SHA,
        strategy_adapter_sha256=ADAPTER_SHA,
        prior_stage_hash="0" * 64,
    )
    receipt = result.receipts[0]
    assert receipt.filled_shares == 200
    assert receipt.commission == pytest.approx(20.0)
    assert receipt.cash_after == pytest.approx(19_980.0)


def test_inclusion_rule_cost_and_decision_time_fail_closed() -> None:
    calendar, signal, row, snapshot, decision_at = _execution_fixture()
    portfolio = Portfolio.us(
        40_000,
        costs=TransactionCostModel(commission_rate=0.001),
    )
    with pytest.raises(InputContractError, match="inclusion-rule"):
        rebalance(
            portfolio,
            calendar,
            signal_session=signal.session_date,
            decision_at=decision_at,
            execution_inputs=(row,),
            universe_snapshot=replace(snapshot, inclusion_rule_sha256="0" * 64),
            risk_on=True,
            strategy_definition_sha256=DEFINITION_SHA,
            strategy_adapter_sha256=ADAPTER_SHA,
            prior_stage_hash="0" * 64,
        )
    with pytest.raises(InputContractError, match="10 bps"):
        rebalance(
            Portfolio.us(40_000),
            calendar,
            signal_session=signal.session_date,
            decision_at=decision_at,
            execution_inputs=(row,),
            universe_snapshot=snapshot,
            risk_on=True,
            strategy_definition_sha256=DEFINITION_SHA,
            strategy_adapter_sha256=ADAPTER_SHA,
            prior_stage_hash="0" * 64,
        )
    with pytest.raises(InputContractError, match="08:30"):
        rebalance(
            portfolio,
            calendar,
            signal_session=signal.session_date,
            decision_at=decision_at + timedelta(minutes=30),
            execution_inputs=(row,),
            universe_snapshot=snapshot,
            risk_on=True,
            strategy_definition_sha256=DEFINITION_SHA,
            strategy_adapter_sha256=ADAPTER_SHA,
            prior_stage_hash="0" * 64,
        )


def test_distribution_is_entitled_on_ex_date_and_applied_once() -> None:
    portfolio = Portfolio.us(1_000)
    portfolio.start_session(date(2020, 1, 2))
    portfolio.buy("SPY", 5, 100, date(2020, 1, 2))
    event = Distribution("spy-div-1", date(2020, 1, 3), date(2020, 1, 6), 2.0)
    assert apply_distribution(portfolio, event) == 10.0
    assert portfolio.pending_cash_total == 10.0
    with pytest.raises(ValueError, match="already"):
        apply_distribution(portfolio, event)
    portfolio.start_session(date(2020, 1, 6))
    assert portfolio.pending_cash_total == 0.0
    assert portfolio.available_cash == 510.0


def _nav(months: int, growth: float) -> tuple[float, ...]:
    return tuple(40_000 * (1 + growth) ** index for index in range(months + 1))


def test_adjudication_and_secondary_seal_are_mechanical() -> None:
    states = (True,) * 13 + (False,) * 33
    decision = adjudicate(
        strategy_nav=_nav(VALIDATION_MONTHS, 0.012),
        fifty_fifty_nav=_nav(VALIDATION_MONTHS, 0.009),
        spy_buyhold_nav=_nav(VALIDATION_MONTHS, 0.011),
        states=states,
        expected_months=VALIDATION_MONTHS,
    )
    assert decision.all_gates_pass
    require_secondary_unsealed(decision)

    failed = adjudicate(
        strategy_nav=_nav(VALIDATION_MONTHS, 0.008),
        fifty_fifty_nav=_nav(VALIDATION_MONTHS, 0.009),
        spy_buyhold_nav=_nav(VALIDATION_MONTHS, 0.011),
        states=states,
        expected_months=VALIDATION_MONTHS,
    )
    assert not failed.all_gates_pass
    with pytest.raises(InputContractError, match="sealed"):
        require_secondary_unsealed(failed)


def test_secondary_length_and_each_state_minimum_are_exact() -> None:
    with pytest.raises(InputContractError, match="state count"):
        adjudicate(
            strategy_nav=_nav(SECONDARY_MONTHS, 0.01),
            fifty_fifty_nav=_nav(SECONDARY_MONTHS, 0.009),
            spy_buyhold_nav=_nav(SECONDARY_MONTHS, 0.011),
            states=(True,) * (SECONDARY_MONTHS - 1),
            expected_months=SECONDARY_MONTHS,
        )
    decision = adjudicate(
        strategy_nav=_nav(SECONDARY_MONTHS, 0.012),
        fifty_fifty_nav=_nav(SECONDARY_MONTHS, 0.009),
        spy_buyhold_nav=_nav(SECONDARY_MONTHS, 0.011),
        states=(True,) * 42 + (False,) * 11,
        expected_months=SECONDARY_MONTHS,
    )
    assert dict(decision.gates)["minimum_12_cash_months"] is False

    passing_secondary = adjudicate(
        strategy_nav=_nav(SECONDARY_MONTHS, 0.012),
        fifty_fifty_nav=_nav(SECONDARY_MONTHS, 0.009),
        spy_buyhold_nav=_nav(SECONDARY_MONTHS, 0.011),
        states=(True,) * 12 + (False,) * 41,
        expected_months=SECONDARY_MONTHS,
    )
    assert passing_secondary.all_gates_pass
    with pytest.raises(InputContractError, match="sealed"):
        require_secondary_unsealed(passing_secondary)


def test_financial_inputs_reject_booleans() -> None:
    with pytest.raises(InputContractError, match="distribution amount"):
        Distribution("bad-dividend", date(2020, 1, 3), date(2020, 1, 6), True)
    nav = list(_nav(VALIDATION_MONTHS, 0.01))
    nav[3] = True
    with pytest.raises(InputContractError, match="real numbers"):
        adjudicate(
            strategy_nav=tuple(nav),
            fifty_fifty_nav=_nav(VALIDATION_MONTHS, 0.009),
            spy_buyhold_nav=_nav(VALIDATION_MONTHS, 0.011),
            states=(True,) * 13 + (False,) * 33,
            expected_months=VALIDATION_MONTHS,
        )
