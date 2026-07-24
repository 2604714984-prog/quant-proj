from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
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
from research.adapters.form4_aggregate_purchase_breadth import (
    Distribution,
    EXPECTED_INCLUSION_RULE_SHA256,
    InputContractError,
    SECONDARY_MONTHS,
    SignalRow,
    VALIDATION_MONTHS,
    adjudicate,
    apply_distribution,
    rebalance,
    rebalance_to_spy_weight,
    require_secondary_unsealed,
    risk_states,
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
    execution = calendar.next_session(
        signal.session_date, as_of=signal.close_at
    )
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


def _signal_rows() -> tuple[SignalRow, ...]:
    rows = []
    year, month = 2017, 1
    for index in range(60):
        rows.append(SignalRow(f"{year:04d}-{month:02d}", 20 + index % 7, 40))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return tuple(rows)


def test_signal_uses_prior_12_only_and_tie_is_cash() -> None:
    rows = tuple(SignalRow(f"2020-{month:02d}", 1, 3) for month in range(1, 13))
    rows += (SignalRow("2021-01", 1, 3),)
    assert risk_states(rows)["2021-01"] is False

    changed_current = rows[:-1] + (SignalRow("2021-01", 9, 1),)
    assert risk_states(changed_current)["2021-01"] is True


def test_signal_rows_require_unique_consecutive_nonzero_months() -> None:
    rows = list(_signal_rows()[:13])
    rows[5] = replace(rows[5], month=rows[4].month)
    with pytest.raises(InputContractError, match="unique"):
        risk_states(tuple(rows))
    with pytest.raises(InputContractError, match="positive"):
        SignalRow("2020-01", 0, 0)


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


def test_inclusion_rule_and_cost_mismatch_fail_before_core() -> None:
    calendar, signal, row, snapshot, decision_at = _execution_fixture()
    wrong = replace(snapshot, inclusion_rule_sha256="0" * 64)
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
            universe_snapshot=wrong,
            risk_on=True,
            strategy_definition_sha256=DEFINITION_SHA,
            strategy_adapter_sha256=ADAPTER_SHA,
            prior_stage_hash="0" * 64,
        )
    wrong_cost = Portfolio.us(40_000)
    with pytest.raises(InputContractError, match="10 bps"):
        rebalance(
            wrong_cost,
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


def test_rebalance_requires_first_next_month_session_at_exact_0830() -> None:
    calendar, signal, row, snapshot, decision_at = _execution_fixture()
    portfolio = Portfolio.us(
        40_000,
        costs=TransactionCostModel(commission_rate=0.001),
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

    same_month_calendar = _calendar()
    with pytest.raises(InputContractError, match="after month end"):
        rebalance(
            portfolio,
            same_month_calendar,
            signal_session=date(2020, 2, 3),
            decision_at=datetime(
                2020,
                2,
                4,
                8,
                30,
                tzinfo=ZoneInfo("America/New_York"),
            ),
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


def test_financial_inputs_reject_boolean_values() -> None:
    with pytest.raises(InputContractError, match="distribution amount"):
        Distribution("bad-dividend", date(2020, 1, 3), date(2020, 1, 6), True)
    nav = list(_nav(VALIDATION_MONTHS, 0.01))
    nav[3] = True
    with pytest.raises(InputContractError, match="real numbers"):
        adjudicate(
            strategy_nav=tuple(nav),
            fifty_fifty_nav=_nav(VALIDATION_MONTHS, 0.009),
            spy_buyhold_nav=_nav(VALIDATION_MONTHS, 0.011),
            states=(True,) * 21 + (False,) * 25,
            expected_months=VALIDATION_MONTHS,
        )


def test_adjudication_and_secondary_seal_are_mechanical() -> None:
    states = (True,) * 21 + (False,) * 25
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


def test_secondary_length_is_exact_and_each_state_needs_12() -> None:
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
