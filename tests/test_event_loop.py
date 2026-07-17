from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import hashlib
from zoneinfo import ZoneInfo

import pytest

from quant_system.backtest import (
    CapacityObservation,
    CapacityPolicy,
    ExecutionInput,
    Portfolio,
    TerminalAction,
    TransactionCostModel,
    blocked_exit_from_receipt,
    run_static_rebalance,
)
from quant_system.data import (
    AcceptedSession,
    AcceptedSessionCalendar,
    CorporateActionIdentity,
    SourceIdentity,
)
from quant_system.markets.common import MarketDataError
from quant_system.markets.universe import StatusEvidence
from quant_system.markets.us import CorporateActionValuationError

UTC = timezone.utc


def _source(label: str, available_at: datetime) -> SourceIdentity:
    return SourceIdentity(
        f"https://example.test/{label}",
        hashlib.sha256(label.encode()).hexdigest(),
        available_at,
        available_at + timedelta(minutes=1),
        label,
    )


def _session(day: date, timezone_name: str, label: str) -> AcceptedSession:
    zone = ZoneInfo(timezone_name)
    return AcceptedSession(
        day,
        datetime.combine(day, time(9, 30), zone),
        datetime.combine(day, time(16 if timezone_name == "America/New_York" else 15), zone),
        _source(f"calendar-{label}", datetime(2000, 1, 1, tzinfo=UTC)),
        timezone_name,
    )


def _calendar(days: tuple[date, ...], timezone_name: str) -> AcceptedSessionCalendar:
    return AcceptedSessionCalendar(
        tuple(_session(day, timezone_name, str(index)) for index, day in enumerate(days))
    )


def _statuses(
    symbol: str,
    timezone_name: str,
    *,
    suspended: bool = False,
    delisted: bool = False,
    available_at: datetime = datetime(2000, 1, 1, tzinfo=UTC),
) -> tuple[StatusEvidence, ...]:
    values = {"listed": True, "delisted": delisted, "st": False, "suspended": suspended}
    return tuple(
        StatusEvidence(
            f"{symbol}-{kind}",
            symbol,
            kind,
            value,
            date(1990, 1, 1),
            None,
            timezone_name,
            _source(f"status-{symbol}-{kind}", available_at),
        )
        for kind, value in values.items()
    )


def _input(
    symbol: str,
    market: str,
    execution: AcceptedSession,
    *,
    price: float | None = 10.0,
    suspended: bool = False,
    delisted: bool = False,
    action_types: tuple[str, ...] = (),
    corporate_actions: tuple[CorporateActionIdentity, ...] = (),
    capacity: CapacityObservation | None = None,
    terminal: TerminalAction | None = None,
    source_label: str | None = None,
) -> ExecutionInput:
    timezone_name = execution.exchange_timezone
    return ExecutionInput(
        symbol,
        market,  # type: ignore[arg-type]
        price,
        "USD" if market == "us" else "CNY",
        _source(source_label or f"bar-{symbol}", execution.open_at),
        _statuses(symbol, timezone_name, suspended=suspended, delisted=delisted),
        action_types,
        corporate_actions,
        suspended,
        None,
        None,
        capacity,
        terminal,
    )


def _listed_fund_portfolio(initial_cash: float = 10_000.0) -> Portfolio:
    return Portfolio(
        initial_cash,
        TransactionCostModel(sell_tax_rate=0.0),
        lot_size=100,
        share_t_plus_one=True,
        us_cash_settlement=False,
        a_share_stamp_tax_schedule=False,
    )


def _listed_fund_cash_action(
    symbol: str,
    action_id: str,
    action_type: str,
    execution: AcceptedSession,
    available_at: datetime,
    pay_date: date,
    *,
    currency: str = "CNY",
    unit: str = "per_share",
) -> CorporateActionIdentity:
    return CorporateActionIdentity(
        symbol,
        action_id,
        action_type,  # type: ignore[arg-type]
        execution.open_at,
        _source(f"{action_id}-source", available_at),
        "Asia/Shanghai",
        ex_date=execution.session_date,
        record_date=execution.session_date,
        pay_date=pay_date,
        cash_amount=Decimal("0.5"),
        currency=currency,
        unit=unit,
    )


def test_static_rebalance_uses_frozen_callback_and_is_deterministic() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal, execution = (
        calendar.session_on(day, as_of=datetime(2026, 7, 13, 12, tzinfo=UTC)) for day in days
    )
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    inputs = (
        _input("AAA", "a_share", execution, price=10),
        _input("BBB", "a_share", execution, price=20),
    )
    seen = []

    def strategy(context):
        seen.append(context)
        assert context.signal_session == signal
        assert context.execution_session == execution
        assert context.eligible_symbols == ("AAA", "BBB")
        assert not hasattr(context, "open_price")
        return {"AAA": 0.5, "BBB": 0.5}

    before = deepcopy(portfolio.__dict__)
    first = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=inputs,
        target_weights=strategy,
    )
    second = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=inputs,
        target_weights=lambda _: {"BBB": 0.5, "AAA": 0.5},
    )

    assert [receipt.symbol for receipt in first.receipts] == ["AAA", "BBB"]
    assert first.portfolio.positions["AAA"].shares == 5_000
    assert first.portfolio.positions["BBB"].shares == 2_500
    assert first.stage_hash == second.stage_hash
    assert first.input_identity_hash == second.input_identity_hash
    assert portfolio.__dict__ == before
    assert len(seen) == 1


def test_timing_pit_and_target_weight_boundaries_fail_closed() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    input_row = _input("AAA", "a_share", execution)

    with pytest.raises(MarketDataError, match="between signal close"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at - timedelta(seconds=1),
            execution_inputs=(input_row,),
            target_weights=lambda _: {},
        )
    late = ExecutionInput(
        **{**input_row.__dict__, "source": _source("late", execution.open_at + timedelta(seconds=1))}
    )
    with pytest.raises(MarketDataError, match="unavailable at open"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(late,),
            target_weights=lambda _: {},
        )
    with pytest.raises(ValueError, match=r"in \[0, 1\]"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(input_row,),
            target_weights=lambda _: {"AAA": 1.1},
        )


def test_us_sells_before_buys_without_spending_unsettled_t_plus_three_cash() -> None:
    days = tuple(date(2016, 8, day) for day in range(1, 6))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2016, 8, 1, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(100, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("OLD", 10, 10, days[0])

    result = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("OLD", "us", execution),
            _input("NEW", "us", execution),
        ),
        target_weights=lambda _: {"NEW": 1.0},
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("sell", "OLD", "filled"),
        ("buy", "NEW", "insufficient_cash"),
    ]
    assert result.portfolio.positions == {}
    assert result.portfolio.available_cash == 0
    assert result.portfolio.pending_cash[0].settlement_date == days[4]
    assert result.receipts[0].cash_change == 100


def test_capacity_and_suspension_leave_blocked_exit_held_and_convertible() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])
    suspended = _input("AAA", "a_share", execution, price=None, suspended=True)

    result = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(suspended,),
        target_weights=lambda _: {},
    )
    assert result.receipts[0].reason == "suspended"
    assert result.portfolio.positions["AAA"].shares == 100
    blocked = blocked_exit_from_receipt(result.receipts[0], result.context, calendar)
    assert blocked.pending and len(blocked.attempts) == 1

    observation = CapacityObservation(
        "AAA",
        signal,
        500,
        5_000,
        "CNY",
        _source("capacity-AAA", signal.close_at),
    )
    capped = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(_input("AAA", "a_share", execution, capacity=observation),),
        target_weights=lambda _: {},
        capacity_policy=CapacityPolicy(0.1, 0.1, "CNY"),
    )
    assert capped.receipts[0].reason.startswith("capacity:")
    assert capped.portfolio.positions["AAA"].shares == 100


def test_max_positions_counts_a_blocked_exit_before_replacement_buy() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])

    result = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("AAA", "a_share", execution, price=None, suspended=True),
            _input("BBB", "a_share", execution),
        ),
        target_weights=lambda _: {"BBB": 0.5},
        max_positions=1,
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("sell", "AAA", "suspended"),
        ("buy", "BBB", "max_positions_after_blocked_exit"),
    ]
    assert set(result.portfolio.positions) == {"AAA"}
    assert result.receipts[1].filled_shares == 0
    assert result.receipts[1].cash_change == 0
    assert result.receipts[1].cash_after == result.receipts[0].cash_after


def test_max_positions_allows_replacement_after_successful_exit() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])

    result = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("AAA", "a_share", execution),
            _input("BBB", "a_share", execution),
        ),
        target_weights=lambda _: {"BBB": 0.5},
        max_positions=1,
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("sell", "AAA", "filled"),
        ("buy", "BBB", "filled"),
    ]
    assert set(result.portfolio.positions) == {"BBB"}


def test_max_positions_allows_existing_symbol_adjustment_at_the_cap() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])

    result = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("AAA", "a_share", execution),
            _input("BBB", "a_share", execution),
        ),
        target_weights=lambda _: {"AAA": 0.5, "BBB": 0.5},
        max_positions=1,
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("buy", "AAA", "filled"),
        ("buy", "BBB", "max_positions_after_blocked_exit"),
    ]
    assert result.portfolio.positions["AAA"].shares > 100
    assert "BBB" not in result.portfolio.positions


def test_max_positions_uses_sorted_new_symbol_order_deterministically() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("AAA", 100, 10, days[0])

    result = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input("CCC", "a_share", execution),
            _input("AAA", "a_share", execution, price=None, suspended=True),
            _input("BBB", "a_share", execution),
        ),
        target_weights=lambda _: {"CCC": 0.25, "BBB": 0.25},
        max_positions=2,
    )

    assert [(item.side, item.symbol, item.reason) for item in result.receipts] == [
        ("sell", "AAA", "suspended"),
        ("buy", "BBB", "filled"),
        ("buy", "CCC", "max_positions_after_blocked_exit"),
    ]
    assert set(result.portfolio.positions) == {"AAA", "BBB"}


@pytest.mark.parametrize("value", [True, 0, -1, 1.5])
def test_max_positions_validation_and_default_identity_compatibility(value) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 12, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(100_000, costs=TransactionCostModel())
    inputs = (_input("AAA", "a_share", execution),)
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "execution_inputs": inputs,
        "target_weights": lambda _: {"AAA": 0.5},
    }

    default = run_static_rebalance(portfolio, calendar, **arguments)
    explicit_none = run_static_rebalance(portfolio, calendar, max_positions=None, **arguments)
    nonbinding_cap = run_static_rebalance(portfolio, calendar, max_positions=10, **arguments)
    assert default.input_identity_hash == explicit_none.input_identity_hash
    assert default.stage_hash == explicit_none.stage_hash
    assert default.portfolio.__dict__ == nonbinding_cap.portfolio.__dict__
    assert default.input_identity_hash != nonbinding_cap.input_identity_hash
    with pytest.raises(ValueError, match="positive integer or None"):
        run_static_rebalance(portfolio, calendar, max_positions=value, **arguments)


def test_distribution_identity_credits_prior_holder_and_raw_label_is_rejected() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    action = CorporateActionIdentity(
        "ABC",
        "abc-dividend-v1",
        "cash_dividend",
        execution.open_at,
        _source("abc-dividend-source", signal.close_at),
        "America/New_York",
        ex_date=days[1],
        record_date=days[1],
        pay_date=days[2],
        cash_amount=Decimal("0.5"),
        currency="USD",
        unit="per_share",
    )
    result = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(_input("ABC", "us", execution, corporate_actions=(action,)),),
        target_weights=lambda _: {"ABC": 0.1},
    )
    assert result.receipts[0].side == "distribution"
    assert result.portfolio.pending_cash_total == pytest.approx(5)
    assert result.receipts[0].reason == "entitlement:5"

    with pytest.raises(CorporateActionValuationError, match="rich identity"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(_input("ABC", "us", execution, action_types=("dividend",)),),
            target_weights=lambda _: {},
        )


@pytest.mark.parametrize("action_type", ["cash_dividend", "special_dividend"])
def test_a_share_listed_fund_distribution_full_event_loop_path(
    action_type: str,
) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 8, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = _listed_fund_portfolio()
    portfolio.start_session(days[0])
    portfolio.buy("510300.SH", 100, 10, days[0])
    action = _listed_fund_cash_action(
        "510300.SH",
        f"510300-{action_type}-v1",
        action_type,
        execution,
        signal.close_at,
        days[2],
    )

    result = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(
            _input(
                "510300.SH",
                "a_share",
                execution,
                corporate_actions=(action,),
            ),
        ),
        target_weights=lambda _: {},
    )

    assert [(item.side, item.symbol) for item in result.receipts] == [
        ("distribution", "510300.SH"),
        ("sell", "510300.SH"),
    ]
    assert result.receipts[0].reason == "entitlement:50"
    assert result.receipts[1].sell_tax == 0.0
    assert result.portfolio.positions == {}
    assert result.portfolio.pending_cash_total == pytest.approx(50.0)
    result.portfolio.start_session(days[2])
    cash_after_pay_date = result.portfolio.available_cash
    assert cash_after_pay_date == pytest.approx(10_050.0)
    result.portfolio.start_session(days[2])
    assert result.portfolio.available_cash == cash_after_pay_date


def test_a_share_action_set_is_prevalidated_before_any_distribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 8, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = _listed_fund_portfolio(20_000)
    portfolio.start_session(days[0])
    portfolio.buy("510300.SH", 100, 10, days[0])
    portfolio.buy("511010.SH", 100, 10, days[0])
    valid = _listed_fund_cash_action(
        "510300.SH", "510300-valid-v1", "cash_dividend", execution,
        signal.close_at, days[2],
    )
    late = _listed_fund_cash_action(
        "511010.SH", "511010-late-v1", "cash_dividend", execution,
        execution.open_at, days[2],
    )
    before = deepcopy(portfolio.__dict__)
    calls: list[str] = []
    original = Portfolio.apply_cash_distribution

    def observe(self, symbol, **kwargs):
        calls.append(symbol)
        return original(self, symbol, **kwargs)

    monkeypatch.setattr(Portfolio, "apply_cash_distribution", observe)
    with pytest.raises(MarketDataError, match="late"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(
                _input("510300.SH", "a_share", execution, corporate_actions=(valid,)),
                _input("511010.SH", "a_share", execution, corporate_actions=(late,)),
            ),
            target_weights=lambda _: {},
        )
    assert calls == []
    assert portfolio.__dict__ == before


def test_a_share_distribution_scope_and_identity_fail_closed() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 8, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    action = _listed_fund_cash_action(
        "510300.SH", "510300-cash-v1", "cash_dividend", execution,
        signal.close_at, days[2],
    )
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "target_weights": lambda _: {},
    }

    with pytest.raises(MarketDataError, match="zero-tax listed-fund"):
        run_static_rebalance(
            Portfolio.a_share(10_000, costs=TransactionCostModel()),
            calendar,
            execution_inputs=(
                _input("510300.SH", "a_share", execution, corporate_actions=(action,)),
            ),
            **arguments,
        )
    with pytest.raises(MarketDataError, match="for symbol"):
        run_static_rebalance(
            _listed_fund_portfolio(),
            calendar,
            execution_inputs=(
                _input("511010.SH", "a_share", execution, corporate_actions=(action,)),
            ),
            **arguments,
        )
    for currency, unit in (("USD", "per_share"), ("CNY", "per_unit")):
        incompatible = _listed_fund_cash_action(
            "510300.SH", f"bad-{currency}-{unit}", "cash_dividend", execution,
            signal.close_at, days[2], currency=currency, unit=unit,
        )
        with pytest.raises(MarketDataError, match="unit or currency"):
            run_static_rebalance(
                _listed_fund_portfolio(),
                calendar,
                execution_inputs=(
                    _input(
                        "510300.SH",
                        "a_share",
                        execution,
                        corporate_actions=(incompatible,),
                    ),
                ),
                **arguments,
            )

    split = CorporateActionIdentity(
        "510300.SH", "510300-split-v1", "split", execution.open_at,
        _source("510300-split-source", signal.close_at), "Asia/Shanghai",
        ex_date=days[1], split_ratio=Decimal("2"),
    )
    with pytest.raises(MarketDataError, match="only cash distributions"):
        run_static_rebalance(
            _listed_fund_portfolio(),
            calendar,
            execution_inputs=(
                _input("510300.SH", "a_share", execution, corporate_actions=(split,)),
            ),
            **arguments,
        )
    with pytest.raises(ValueError, match="effective_at.*ex_date"):
        CorporateActionIdentity(
            "510300.SH", "missing-ex-date", "cash_dividend", execution.open_at,
            _source("missing-ex-date-source", signal.close_at), "Asia/Shanghai",
            record_date=days[1], pay_date=days[2], cash_amount=Decimal("0.5"),
            currency="CNY", unit="per_share",
        )


def test_ordinary_a_share_input_remains_receipt_equivalent() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "Asia/Shanghai")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 8, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.a_share(10_000, costs=TransactionCostModel())
    row = _input("600000.SH", "a_share", execution)
    explicit_empty = ExecutionInput(**{**row.__dict__, "corporate_actions": ()})
    arguments = {
        "signal_session": days[0],
        "decision_at": signal.close_at,
        "target_weights": lambda _: {"600000.SH": 1.0},
    }

    default = run_static_rebalance(
        portfolio, calendar, execution_inputs=(row,), **arguments,
    )
    explicit = run_static_rebalance(
        portfolio, calendar, execution_inputs=(explicit_empty,), **arguments,
    )
    assert default.receipts == explicit.receipts
    assert default.receipt_hashes == explicit.receipt_hashes
    assert default.input_identity_hash == explicit.input_identity_hash
    assert default.portfolio.__dict__ == explicit.portfolio.__dict__


def test_terminal_action_is_timed_ineligible_and_cannot_be_repurchased() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("DEAD", 10, 10, days[0])
    terminal = TerminalAction(
        "dead-delisting-v1",
        "delisting",
        execution.open_at,
        2.5,
        _source("dead-delisting-source", signal.close_at),
    )
    row = _input(
        "DEAD",
        "us",
        execution,
        price=None,
        delisted=True,
        action_types=("delisting",),
        terminal=terminal,
    )
    result = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(row,),
        target_weights=lambda _: {},
    )
    assert result.portfolio.positions == {}
    assert result.receipts[0].cash_change == pytest.approx(25)
    assert result.receipts[0].reason == "terminal_delisting"

    eligible_row = ExecutionInput(
        **{**row.__dict__, "status_records": _statuses("DEAD", "America/New_York")}
    )
    with pytest.raises(MarketDataError, match="PIT ineligible"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(eligible_row,),
            target_weights=lambda _: {"DEAD": 1.0},
        )

    empty = run_static_rebalance(
        Portfolio.us(1_000, costs=TransactionCostModel()),
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(row,),
        target_weights=lambda _: {},
    )
    assert empty.receipts == () and empty.portfolio.positions == {}

    mistimed = TerminalAction(
        terminal.event_id,
        terminal.action_type,
        signal.open_at,
        terminal.recovery_per_share,
        terminal.source,
    )
    with pytest.raises(MarketDataError, match="effective date"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(ExecutionInput(**{**row.__dict__, "terminal_action": mistimed}),),
            target_weights=lambda _: {},
        )

    intraday_future = TerminalAction(
        "dead-delisting-close-v1",
        terminal.action_type,
        execution.close_at,
        terminal.recovery_per_share,
        terminal.source,
    )
    before = deepcopy(portfolio.__dict__)
    with pytest.raises(MarketDataError, match="follows execution open"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(
                ExecutionInput(**{**row.__dict__, "terminal_action": intraday_future}),
            ),
            target_weights=lambda _: {},
        )
    assert portfolio.__dict__ == before


def test_missing_halt_mark_fails_and_identity_or_prior_stage_changes_hash() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    base = _input("ABC", "us", execution)
    first = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(base,),
        target_weights=lambda _: {},
    )
    changed = _input("ABC", "us", execution, source_label="different-partition")
    second = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(changed,),
        target_weights=lambda _: {},
        prior_stage_hash="1" * 64,
    )
    assert first.receipts == () and second.receipts == ()
    assert first.input_identity_hash != second.input_identity_hash
    assert first.stage_hash != second.stage_hash

    numeric_change = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(_input("ABC", "us", execution, price=11),),
        target_weights=lambda _: {},
    )
    assert numeric_change.input_identity_hash != first.input_identity_hash
    with pytest.raises(ValueError, match="slippage_bps"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(base,),
            target_weights=lambda _: {},
            slippage_bps=-1,
        )

    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    portfolio.positions["ABC"].last_accepted_mark = None
    halted = _input("ABC", "us", execution, price=None, action_types=("trading_halt",))
    with pytest.raises(Exception, match="prior accepted valuation"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(halted,),
            target_weights=lambda _: {},
        )


def test_same_day_distribution_receipt_reconciles_immediate_cash() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    action = CorporateActionIdentity(
        "ABC", "same-day-dividend", "cash_dividend", execution.open_at,
        _source("same-day-source", signal.close_at), "America/New_York",
        ex_date=days[1], record_date=days[1], pay_date=days[1],
        cash_amount=Decimal("0.5"), currency="USD", unit="per_share",
    )
    result = run_static_rebalance(
        portfolio,
        calendar,
        signal_session=days[0],
        decision_at=signal.close_at,
        execution_inputs=(_input("ABC", "us", execution, corporate_actions=(action,)),),
        target_weights=lambda _: {"ABC": 0.1},
    )
    assert result.receipts[0].cash_change == pytest.approx(5)
    assert result.receipts[0].cash_after == pytest.approx(905)


def test_invalid_weights_and_late_or_duplicate_actions_leave_caller_unchanged() -> None:
    days = (date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15))
    calendar = _calendar(days, "America/New_York")
    signal = calendar.session_on(days[0], as_of=datetime(2026, 7, 13, 22, tzinfo=UTC))
    execution = calendar.session_on(days[1], as_of=signal.close_at)
    portfolio = Portfolio.us(1_000, costs=TransactionCostModel())
    portfolio.start_session(days[0])
    portfolio.buy("ABC", 10, 10, days[0])
    before = deepcopy(portfolio.__dict__)
    late = CorporateActionIdentity(
        "ABC", "late-dividend", "cash_dividend", execution.open_at,
        _source("late-action-source", execution.open_at), "America/New_York",
        ex_date=days[1], record_date=days[1], pay_date=days[2],
        cash_amount=Decimal("0.5"), currency="USD", unit="per_share",
    )
    late_row = _input("ABC", "us", execution, corporate_actions=(late,))

    with pytest.raises(MarketDataError, match="late"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(late_row,),
            target_weights=lambda _: {},
        )
    with pytest.raises(MarketDataError, match="globally unique"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(
                ExecutionInput(**{**late_row.__dict__, "corporate_actions": (late, late)}),
            ),
            target_weights=lambda _: {},
        )
    with pytest.raises(ValueError, match="numeric"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(_input("ABC", "us", execution),),
            target_weights=lambda _: {"ABC": True},
        )
    future_action = CorporateActionIdentity(
        "ABC", "future-intraday-dividend", "cash_dividend", execution.close_at,
        _source("future-intraday-source", signal.close_at), "America/New_York",
        ex_date=days[1], record_date=days[1], pay_date=days[2],
        cash_amount=Decimal("0.5"), currency="USD", unit="per_share",
    )
    with pytest.raises(MarketDataError, match="after execution open"):
        run_static_rebalance(
            portfolio,
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(
                _input("ABC", "us", execution, corporate_actions=(future_action,)),
            ),
            target_weights=lambda _: {},
        )
    with pytest.raises(MarketDataError, match="unknown US action"):
        run_static_rebalance(
            Portfolio.us(1_000, costs=TransactionCostModel()),
            calendar,
            signal_session=days[0],
            decision_at=signal.close_at,
            execution_inputs=(_input("ABC", "us", execution, action_types=("mystery",)),),
            target_weights=lambda _: {},
        )
    assert portfolio.__dict__ == before
