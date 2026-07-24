from dataclasses import replace
from datetime import date, datetime, time, timedelta
import hashlib
import json
import math
from pathlib import Path
import statistics
from zoneinfo import ZoneInfo

import pytest

from quant_system.backtest import Portfolio, TransactionCostModel
from quant_system.markets.us import cash_settlement_lag_sessions
from research.adapters import dts_nondebt_fiscal_impulse as adapter
from research.adapters.dts_nondebt_fiscal_impulse import (
    Distribution,
    InputContractError,
    MarketSession,
    MonthlyState,
    SegmentInputIdentity,
    Split,
    first_session_of_month,
    require_secondary_unsealed,
    run_secondary,
    run_validation,
    settlement_sessions,
)


DEFINITION = (
    Path(__file__).parents[1]
    / "research"
    / "definitions"
    / "us_eq_dts_nondebt_fiscal_impulse_yoy_4w_spy_cash_v1.json"
)
STATE_CYCLE = ("SPY", "CASH", "SPY", "SPY", "CASH", "CASH")
NY = ZoneInfo("America/New_York")
FISCAL_RECEIPT = hashlib.sha256(b"fiscal-receipt").hexdigest()
DEFINITION_ID = hashlib.sha256(b"definition-bytes").hexdigest()
ADAPTER_ID = hashlib.sha256(b"adapter-bytes").hexdigest()


def _next_month(value: date) -> date:
    return date(value.year + (value.month == 12), value.month % 12 + 1, 1)


def _months(start: date, count: int) -> tuple[date, ...]:
    output = [start]
    while len(output) < count:
        output.append(_next_month(output[-1]))
    return tuple(output)


def _history(count: int) -> tuple[str, ...]:
    return tuple(STATE_CYCLE[index % len(STATE_CYCLE)] for index in range(count))


def _previous_weekday(value: date) -> date:
    output = value - timedelta(days=1)
    while output.weekday() >= 5:
        output -= timedelta(days=1)
    return output


def _first_weekday(value: date) -> date:
    output = value
    while output.weekday() >= 5:
        output += timedelta(days=1)
    return output


def _market_sessions(
    months: tuple[date, ...],
    history: tuple[str, ...],
    terminal_month: date,
    *,
    up_factor: float = 1.08,
    down_factor: float = 0.92,
    initial_price: float = 100.0,
) -> tuple[MarketSession, ...]:
    first_execution = _first_weekday(months[0])
    first_date = _previous_weekday(first_execution)
    terminal_date = _first_weekday(terminal_month)
    dates = []
    current = first_date
    while current <= terminal_date:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)

    prices: dict[date, float] = {first_date: initial_price}
    boundary_price = initial_price
    for month, state in zip(months, history):
        month_dates = tuple(
            item
            for item in dates
            if (item.year, item.month)
            == (month.year, month.month)
        )
        assert len(month_dates) >= 2
        factor = up_factor if state == "SPY" else down_factor
        for index, session_date in enumerate(month_dates):
            fraction = index / (len(month_dates) - 1)
            prices[session_date] = boundary_price * factor**fraction
        boundary_price *= factor
    prices[terminal_date] = boundary_price
    return tuple(MarketSession(item, prices[item], prices[item]) for item in dates)


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _bundle(
    segment: str,
    *,
    history: tuple[str, ...] | None = None,
    up_factor: float = 1.08,
    down_factor: float = 0.92,
) -> tuple[
    tuple[MonthlyState, ...],
    tuple[MarketSession, ...],
    date,
    SegmentInputIdentity,
]:
    if segment == "validation":
        count = adapter.VALIDATION_INTERVALS
        start = adapter.VALIDATION_START_MONTH
        terminal = adapter.VALIDATION_TERMINAL_MONTH
    else:
        assert segment == "secondary"
        count = adapter.SECONDARY_INTERVALS
        start = adapter.SECONDARY_START_MONTH
        terminal = adapter.SECONDARY_TERMINAL_MONTH
    values = history or _history(count)
    months = _months(start, count)
    sessions = _market_sessions(
        months,
        values,
        terminal,
        up_factor=up_factor,
        down_factor=down_factor,
    )
    session_dates = tuple(item.session_date for item in sessions)
    states = []
    for index, (month, state) in enumerate(zip(months, values)):
        execution = first_session_of_month(month, sessions)
        execution_index = session_dates.index(execution)
        previous_session = session_dates[execution_index - 1]
        states.append(
            MonthlyState(
                month,
                state,
                datetime.combine(previous_session, time(20, 5), NY),
                datetime.combine(previous_session, time(16, 0), NY),
                _hash(f"{segment}-source-row-{index}"),
            )
        )
    frozen_states = tuple(states)
    identity = SegmentInputIdentity(
        segment,
        FISCAL_RECEIPT,
        adapter.fiscal_states_sha256(frozen_states),
        _hash(f"{segment}-market-receipt"),
        adapter.market_rows_sha256(sessions),
        adapter.calendar_sha256(sessions),
        DEFINITION_ID,
        ADAPTER_ID,
    )
    return frozen_states, sessions, terminal, identity


def _strict_json(raw: str) -> object:
    def reject_constant(value: str) -> None:
        raise ValueError(f"nonfinite JSON constant: {value}")

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        output: dict[str, object] = {}
        for key, value in pairs:
            if key in output:
                raise ValueError(f"duplicate JSON key: {key}")
            output[key] = value
        return output

    return json.loads(
        raw,
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicates,
    )


def test_frozen_definition_is_strict_outcome_free_and_exact() -> None:
    definition = _strict_json(DEFINITION.read_text(encoding="utf-8"))
    assert isinstance(definition, dict)
    assert (
        definition["research_id"]
        == "US_EQ_DTS_NONDEBT_FISCAL_IMPULSE_YOY_4W_SPY_CASH_V1"
    )
    assert definition["status"] == "PREREGISTERED_CODE_ONLY_OUTCOME_UNOPENED"
    assert (
        definition["mechanism"]["daily_formula_symbols"]
        == "open - close - redemptions + issues"
    )
    assert definition["mechanism"]["units"] == "USD millions"
    assert "28" in definition["mechanism"]["rolling_window"]
    assert "364" in definition["mechanism"]["seasonal_difference"]
    assert "strictly greater than zero" in definition["mechanism"]["state_direction"]
    assert "next observed DTS report date" in definition["mechanism"][
        "report_availability"
    ]
    assert definition["segments"]["validation"]["complete_intervals"] == 28
    assert definition["segments"]["validation"]["state_month_start"] == "2021-02-01"
    assert definition["segments"]["validation"]["state_month_end"] == "2023-05-01"
    assert definition["segments"]["validation"]["terminal_month"] == "2023-06-01"
    assert definition["segments"]["secondary"]["complete_intervals"] == 34
    assert definition["segments"]["secondary"]["state_month_start"] == "2023-08-01"
    assert definition["segments"]["secondary"]["state_month_end"] == "2026-05-01"
    assert definition["segments"]["secondary"]["terminal_month"] == "2026-06-01"
    assert len(definition["gates_per_segment"]) == 3
    assert definition["secondary_open_rule"]["required_gate_count"] == 3
    assert definition["secondary_open_rule"]["required_gate_passes"] == 3
    assert definition["secondary_open_rule"]["trust_caller_boolean"] is False
    assert definition["secondary_open_rule"]["mechanical_recomputation"] is True
    assert definition["secondary_open_rule"]["module_issued_validation_proof"] is True
    assert definition["implementation"]["shared_core_modified"] is False
    assert definition["implementation"]["new_framework"] is False
    assert definition["boundaries"]["network"] is False
    assert definition["boundaries"]["database_read"] is False
    assert definition["boundaries"]["real_market_values"] is False
    assert definition["boundaries"]["commit"] is False
    assert definition["boundaries"]["push"] is False
    with pytest.raises(ValueError, match="duplicate"):
        _strict_json('{"a": 1, "a": 2}')
    with pytest.raises(ValueError, match="nonfinite"):
        _strict_json('{"a": NaN}')


def test_adapter_reuses_shared_primitives_without_closed_adapter_or_shared_clone() -> None:
    source = Path(adapter.__file__).read_text(encoding="utf-8")
    assert adapter.Portfolio is Portfolio
    assert adapter.TransactionCostModel is TransactionCostModel
    assert adapter.cash_settlement_lag_sessions is cash_settlement_lag_sessions
    assert "nport" not in source.casefold()
    assert "class Portfolio" not in source
    assert "class TransactionCostModel" not in source
    assert "duckdb" not in source.casefold()
    assert "requests" not in source.casefold()


@pytest.mark.parametrize("bad_price", [0.0, -1.0, float("nan"), float("inf")])
def test_market_input_rejects_nonpositive_or_nonfinite_prices(
    bad_price: float,
) -> None:
    with pytest.raises(InputContractError, match="spy_open"):
        MarketSession(date(2024, 1, 2), bad_price, 100.0)


def test_state_and_action_inputs_fail_closed() -> None:
    decision = datetime(2024, 1, 31, 20, 5, tzinfo=NY)
    available = datetime(2024, 1, 31, 16, 0, tzinfo=NY)
    row_hash = _hash("row")
    with pytest.raises(InputContractError, match="first calendar day"):
        MonthlyState(
            date(2024, 1, 2),
            "SPY",
            decision,
            available,
            row_hash,
        )
    with pytest.raises(InputContractError, match="exactly SPY or CASH"):
        MonthlyState(
            date(2024, 1, 1),
            "BONDS",
            decision,
            available,
            row_hash,
        )
    with pytest.raises(InputContractError, match="16:00"):
        MonthlyState(
            date(2024, 1, 1),
            "SPY",
            decision,
            available.replace(hour=15),
            row_hash,
        )
    with pytest.raises(InputContractError, match="cannot follow"):
        MonthlyState(
            date(2024, 1, 1),
            "SPY",
            decision,
            available + timedelta(days=1),
            row_hash,
        )
    with pytest.raises(InputContractError, match="pay_date"):
        Distribution(
            "SPY",
            "bad-pay",
            date(2024, 1, 5),
            date(2024, 1, 4),
            1.0,
        )
    with pytest.raises(InputContractError, match="finite and positive"):
        Split("SPY", "bad-split", date(2024, 1, 5), float("nan"))
    with pytest.raises(InputContractError, match="symbol"):
        Distribution(
            "QQQ",
            "wrong-symbol",
            date(2024, 1, 5),
            date(2024, 1, 8),
            1.0,
        )


def test_validation_requires_exact_count_consecutive_months_support_and_transitions() -> None:
    states, sessions, terminal, identity = _bundle("validation")
    with pytest.raises(InputContractError, match="exactly 28"):
        run_validation(
            states[:-1],
            sessions,
            terminal_month=terminal,
            input_identity=identity,
        )

    skipped = list(states)
    skipped[5] = replace(skipped[5], month=_next_month(skipped[5].month))
    with pytest.raises(InputContractError, match="exact frozen range"):
        run_validation(
            tuple(skipped),
            sessions,
            terminal_month=terminal,
            input_identity=identity,
        )
    with pytest.raises(InputContractError, match="terminal month"):
        run_validation(
            states,
            sessions,
            terminal_month=_next_month(terminal),
            input_identity=identity,
        )

    one_state, one_sessions, one_terminal, one_identity = _bundle(
        "validation",
        history=("SPY",) * adapter.VALIDATION_INTERVALS,
    )
    with pytest.raises(InputContractError, match="at least 4"):
        run_validation(
            one_state,
            one_sessions,
            terminal_month=one_terminal,
            input_identity=one_identity,
        )
    two_blocks, block_sessions, block_terminal, block_identity = _bundle(
        "validation",
        history=("SPY",) * 14 + ("CASH",) * 14,
    )
    with pytest.raises(InputContractError, match="transition direction"):
        run_validation(
            two_blocks,
            block_sessions,
            terminal_month=block_terminal,
            input_identity=block_identity,
        )

    result = run_validation(
        states,
        sessions,
        terminal_month=terminal,
        input_identity=identity,
    )
    assert result.observed_intervals == 28
    assert result.spy_intervals == result.state_history.count("SPY")
    assert result.cash_intervals == result.state_history.count("CASH")
    assert result.spy_intervals >= 4
    assert result.cash_intervals >= 4
    assert result.spy_to_cash_transitions >= 2
    assert result.cash_to_spy_transitions >= 2
    assert result.state_months[0] == date(2021, 2, 1)
    assert result.state_months[-1] == date(2023, 5, 1)
    assert result.terminal_month == date(2023, 6, 1)
    assert result.state_row_sha256s == tuple(
        item.source_row_sha256 for item in states
    )
    assert result.input_identity == identity


def test_pit_timing_is_exact_and_late_or_reordered_state_rows_fail_closed() -> None:
    states, sessions, terminal, identity = _bundle("validation")
    session_dates = tuple(item.session_date for item in sessions)
    first_execution = first_session_of_month(states[0].month, sessions)
    previous_session = session_dates[session_dates.index(first_execution) - 1]
    assert states[0].decision_at.astimezone(NY) == datetime.combine(
        previous_session,
        time(20, 5),
        NY,
    )
    assert states[0].source_available_at.astimezone(NY).time() == time(16, 0)
    assert states[0].source_available_at <= states[0].decision_at

    wrong_decision = list(states)
    wrong_decision[0] = replace(
        wrong_decision[0],
        decision_at=wrong_decision[0].decision_at + timedelta(minutes=1),
    )
    wrong_decision_states = tuple(wrong_decision)
    wrong_decision_identity = replace(
        identity,
        fiscal_states_sha256=adapter.fiscal_states_sha256(wrong_decision_states),
    )
    with pytest.raises(InputContractError, match="20:05"):
        run_validation(
            wrong_decision_states,
            sessions,
            terminal_month=terminal,
            input_identity=wrong_decision_identity,
        )

    with pytest.raises(InputContractError, match="cannot follow"):
        replace(
            states[0],
            source_available_at=datetime.combine(
                states[0].decision_at.date() + timedelta(days=1),
                time(16, 0),
                NY,
            ),
        )

    reordered = list(states)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    reordered_states = tuple(reordered)
    reordered_identity = replace(
        identity,
        fiscal_states_sha256=adapter.fiscal_states_sha256(reordered_states),
    )
    with pytest.raises(InputContractError, match="overlap, subset, or reorder"):
        run_validation(
            reordered_states,
            sessions,
            terminal_month=terminal,
            input_identity=reordered_identity,
        )


def test_secondary_overlap_and_identity_mismatches_fail_closed() -> None:
    validation_states, validation_sessions, validation_terminal, validation_id = (
        _bundle("validation")
    )
    validation = run_validation(
        validation_states,
        validation_sessions,
        terminal_month=validation_terminal,
        input_identity=validation_id,
    )
    secondary_states, secondary_sessions, secondary_terminal, secondary_id = _bundle(
        "secondary"
    )

    overlap = list(secondary_states)
    overlap[0] = replace(overlap[0], month=adapter.VALIDATION_END_MONTH)
    overlap_states = tuple(overlap)
    overlap_id = replace(
        secondary_id,
        fiscal_states_sha256=adapter.fiscal_states_sha256(overlap_states),
    )
    with pytest.raises(InputContractError, match="overlap, subset, or reorder"):
        run_secondary(
            overlap_states,
            secondary_sessions,
            terminal_month=secondary_terminal,
            validation=validation,
            input_identity=overlap_id,
        )

    with pytest.raises(InputContractError, match="fiscal state-row identity mismatch"):
        run_validation(
            validation_states,
            validation_sessions,
            terminal_month=validation_terminal,
            input_identity=replace(
                validation_id,
                fiscal_states_sha256=_hash("wrong-fiscal-states"),
            ),
        )
    with pytest.raises(InputContractError, match="market row identity mismatch"):
        run_validation(
            validation_states,
            validation_sessions,
            terminal_month=validation_terminal,
            input_identity=replace(
                validation_id,
                market_rows_sha256=_hash("wrong-market-rows"),
            ),
        )
    with pytest.raises(InputContractError, match="fiscal/code identity mismatch"):
        run_secondary(
            secondary_states,
            secondary_sessions,
            terminal_month=secondary_terminal,
            validation=validation,
            input_identity=replace(
                secondary_id,
                fiscal_receipt_sha256=_hash("different-fiscal-receipt"),
            ),
        )
    with pytest.raises(InputContractError, match="fiscal/code identity mismatch"):
        run_secondary(
            secondary_states,
            secondary_sessions,
            terminal_month=secondary_terminal,
            validation=validation,
            input_identity=replace(
                secondary_id,
                adapter_sha256=_hash("different-adapter"),
            ),
        )
    with pytest.raises(InputContractError, match="market segment identity"):
        run_secondary(
            secondary_states,
            secondary_sessions,
            terminal_month=secondary_terminal,
            validation=validation,
            input_identity=replace(
                secondary_id,
                market_receipt_sha256=validation_id.market_receipt_sha256,
            ),
        )


def test_segment_session_coverage_is_exact_before_hash_or_outcome_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validation_states, validation_sessions, validation_terminal, validation_id = (
        _bundle("validation")
    )
    secondary_states, secondary_sessions, secondary_terminal, secondary_id = _bundle(
        "secondary"
    )
    validation = run_validation(
        validation_states,
        validation_sessions,
        terminal_month=validation_terminal,
        input_identity=validation_id,
    )
    secondary = run_secondary(
        secondary_states,
        secondary_sessions,
        terminal_month=secondary_terminal,
        validation=validation,
        input_identity=secondary_id,
    )
    assert validation.observed_intervals == 28
    assert secondary.observed_intervals == 34

    combined_sessions = validation_sessions + secondary_sessions

    def unexpected_market_hash(_: object) -> str:
        pytest.fail("overcovered segment reached market hash or outcome path")

    monkeypatch.setattr(adapter, "market_rows_sha256", unexpected_market_hash)
    with pytest.raises(InputContractError, match="no rows after terminal execution"):
        run_validation(
            validation_states,
            combined_sessions,
            terminal_month=validation_terminal,
            input_identity=validation_id,
        )


def test_first_accepted_session_prior_raw_close_raw_open_whole_shares_and_cost() -> None:
    states, frozen_sessions, terminal, identity = _bundle("validation")
    sessions = list(frozen_sessions)
    first_decision = first_session_of_month(states[0].month, tuple(sessions))
    first_index = next(
        index
        for index, item in enumerate(sessions)
        if item.session_date == first_decision
    )
    sessions[first_index - 1] = replace(sessions[first_index - 1], spy_close=200.0)
    sessions[first_index] = replace(sessions[first_index], spy_open=100.0)
    changed_sessions = tuple(sessions)
    identity = replace(
        identity,
        market_rows_sha256=adapter.market_rows_sha256(changed_sessions),
    )

    result = run_validation(
        states,
        changed_sessions,
        terminal_month=terminal,
        input_identity=identity,
    )
    first_trade = result.strategy.trades[0]
    benchmark_trade = result.fifty_fifty.trades[0]
    assert first_trade.trade_date == first_decision
    assert first_trade.side == "buy"
    assert first_trade.shares == 200
    assert type(first_trade.shares) is int
    assert first_trade.price == 100.0
    assert first_trade.commission == pytest.approx(20.0)
    assert benchmark_trade.shares == 100
    assert benchmark_trade.commission == pytest.approx(10.0)


def test_cash_settlement_uses_historical_lag_and_never_reuses_sale_cash() -> None:
    old_dates = (
        date(2024, 5, 24),
        date(2024, 5, 28),
        date(2024, 5, 29),
        date(2024, 5, 30),
    )
    new_dates = (
        date(2024, 5, 28),
        date(2024, 5, 29),
        date(2024, 5, 30),
    )
    assert settlement_sessions(old_dates[0], old_dates) == old_dates[1:3]
    assert settlement_sessions(new_dates[0], new_dates) == (new_dates[1],)

    states, sessions, terminal, identity = _bundle("validation")
    dates = tuple(item.session_date for item in sessions)
    result = run_validation(
        states,
        sessions,
        terminal_month=terminal,
        input_identity=identity,
    )
    sale = next(item for item in result.strategy.trades if item.side == "sell")
    lag = cash_settlement_lag_sessions(sale.trade_date)
    expected_settlement = tuple(item for item in dates if item > sale.trade_date)[
        lag - 1
    ]
    assert sale.settlement_date == expected_settlement
    assert not any(
        item.side == "buy" and item.trade_date == sale.trade_date
        for item in result.strategy.trades
    )
    next_buy = next(
        item
        for item in result.strategy.trades
        if item.side == "buy" and item.trade_date > sale.trade_date
    )
    assert next_buy.trade_date > sale.settlement_date


def test_distribution_freezes_ex_date_entitlement_and_settles_on_pay_date() -> None:
    account = adapter._new_account()
    purchase_date = date(2026, 1, 2)
    ex_date = date(2026, 1, 5)
    pay_date = date(2026, 1, 7)
    account.portfolio.start_session(purchase_date)
    account.portfolio.buy("SPY", 10, 100.0, purchase_date)
    account.portfolio.start_session(ex_date)
    cash_before = account.portfolio.available_cash

    event = Distribution("SPY", "spy-dividend-1", ex_date, pay_date, 0.5)
    adapter._apply_actions((account,), (event,), ())
    assert account.portfolio.pending_cash_total == pytest.approx(5.0)
    assert account.portfolio.available_cash == cash_before
    account.portfolio.start_session(date(2026, 1, 6))
    assert account.portfolio.available_cash == cash_before
    account.portfolio.start_session(pay_date)
    assert account.portfolio.pending_cash_total == 0.0
    assert account.portfolio.available_cash == pytest.approx(cash_before + 5.0)

    buyer = adapter._new_account()
    buyer.portfolio.start_session(ex_date)
    buyer.portfolio.buy("SPY", 10, 100.0, ex_date)
    buyer_event = Distribution("SPY", "spy-dividend-buyer", ex_date, pay_date, 0.5)
    adapter._apply_actions((buyer,), (buyer_event,), ())
    assert buyer.portfolio.pending_cash_total == 0.0


def test_ordinary_split_is_supported_and_fractional_result_fails_before_mutation() -> None:
    account = adapter._new_account()
    trade_date = date(2026, 1, 2)
    split_date = date(2026, 1, 5)
    account.portfolio.start_session(trade_date)
    account.portfolio.buy("SPY", 10, 100.0, trade_date)
    account.portfolio.start_session(split_date)
    adapter._apply_actions(
        (account,),
        (),
        (Split("SPY", "spy-split-2", split_date, 2.0),),
    )
    assert account.portfolio.positions["SPY"].shares == 20
    assert account.portfolio.positions["SPY"].average_cost == pytest.approx(50.05)

    fractional = adapter._new_account()
    fractional.portfolio.start_session(trade_date)
    fractional.portfolio.buy("SPY", 3, 100.0, trade_date)
    fractional.portfolio.start_session(split_date)
    before = fractional.portfolio.positions["SPY"].shares
    with pytest.raises(InputContractError, match="whole-share"):
        adapter._apply_actions(
            (fractional,),
            (),
            (Split("SPY", "spy-reverse-split", split_date, 0.5),),
        )
    assert fractional.portfolio.positions["SPY"].shares == before


def test_intervals_paired_gates_and_daily_open_drawdown_are_mechanical() -> None:
    states, sessions, terminal, identity = _bundle("validation")
    result = run_validation(
        states,
        sessions,
        terminal_month=terminal,
        input_identity=identity,
    )
    assert len(result.strategy.pretrade_boundaries) == 29
    assert len(result.strategy.interval_returns) == 28
    assert result.strategy.pretrade_boundaries[0] == 40_000.0
    assert result.strategy.interval_returns[0] == pytest.approx(
        result.strategy.pretrade_boundaries[1] / 40_000.0 - 1.0
    )
    expected_active_mean = statistics.fmean(
        strategy_return - benchmark_return
        for strategy_return, benchmark_return in zip(
            result.strategy.interval_returns,
            result.fifty_fifty.interval_returns,
        )
    )
    assert result.paired_mean_active_return == pytest.approx(expected_active_mean)
    assert tuple(name for name, _ in result.gates) == adapter.GATE_NAMES
    assert len(result.gates) == 3
    assert result.all_gates_pass is True
    assert all(value for _, value in result.gates)
    first_daily_nav = result.strategy.daily_open_nav[0][1]
    assert first_daily_nav < 40_000.0
    assert result.strategy.maximum_drawdown <= first_daily_nav / 40_000.0 - 1.0


def test_secondary_is_sealed_and_recomputes_gates_instead_of_trusting_booleans() -> None:
    states, flat_sessions, terminal, flat_identity = _bundle(
        "validation",
        up_factor=1.0,
        down_factor=1.0,
    )
    flat = run_validation(
        states,
        flat_sessions,
        terminal_month=terminal,
        input_identity=flat_identity,
    )
    assert flat.all_gates_pass is False
    with pytest.raises(InputContractError, match="sealed"):
        require_secondary_unsealed(flat)
    with pytest.raises(InputContractError, match="run_validation proof"):
        require_secondary_unsealed(replace(flat, all_gates_pass=True))
    forged_gates = replace(
        flat,
        gates=tuple((name, True) for name in adapter.GATE_NAMES),
        all_gates_pass=True,
    )
    with pytest.raises(InputContractError, match="run_validation proof"):
        require_secondary_unsealed(forged_gates)

    states, sessions, terminal, identity = _bundle("validation")
    passing = run_validation(
        states,
        sessions,
        terminal_month=terminal,
        input_identity=identity,
    )
    require_secondary_unsealed(passing)
    with pytest.raises(InputContractError, match="run_validation proof"):
        require_secondary_unsealed(replace(passing, _module_proof=object()))
    nonfinite = replace(
        passing,
        strategy=replace(passing.strategy, terminal_wealth=float("nan")),
    )
    with pytest.raises(InputContractError, match="run_validation proof"):
        require_secondary_unsealed(nonfinite)
    negative = replace(
        passing,
        strategy=replace(
            passing.strategy,
            pretrade_boundaries=(-1.0,) + passing.strategy.pretrade_boundaries[1:],
        ),
    )
    with pytest.raises(InputContractError, match="run_validation proof"):
        require_secondary_unsealed(negative)


def test_secondary_requires_exactly_34_intervals_and_opens_only_after_three_of_three() -> None:
    (
        validation_states,
        validation_sessions,
        validation_terminal,
        validation_identity,
    ) = _bundle("validation")
    validation = run_validation(
        validation_states,
        validation_sessions,
        terminal_month=validation_terminal,
        input_identity=validation_identity,
    )
    (
        secondary_states,
        secondary_sessions,
        secondary_terminal,
        secondary_identity,
    ) = _bundle("secondary")
    with pytest.raises(InputContractError, match="exactly 34"):
        run_secondary(
            secondary_states[:-1],
            secondary_sessions,
            terminal_month=secondary_terminal,
            validation=validation,
            input_identity=secondary_identity,
        )
    result = run_secondary(
        secondary_states,
        secondary_sessions,
        terminal_month=secondary_terminal,
        validation=validation,
        input_identity=secondary_identity,
    )
    assert result.segment == "secondary"
    assert result.observed_intervals == 34
    assert len(result.strategy.interval_returns) == 34
    assert len(result.gates) == 3
    assert result.state_months[0] == date(2023, 8, 1)
    assert result.state_months[-1] == date(2026, 5, 1)
    assert result.terminal_month == date(2026, 6, 1)


def test_run_does_not_mutate_caller_owned_synthetic_inputs() -> None:
    states, sessions, terminal, identity = _bundle("validation")
    ex_date = sessions[10].session_date
    pay_date = sessions[12].session_date
    distributions = (
        Distribution("SPY", "immutability-dividend", ex_date, pay_date, 0.25),
    )
    states_before = tuple(states)
    sessions_before = tuple(sessions)
    distributions_before = tuple(distributions)
    run_validation(
        states,
        sessions,
        terminal_month=terminal,
        input_identity=identity,
        distributions=distributions,
    )
    assert states == states_before
    assert sessions == sessions_before
    assert distributions == distributions_before
    assert all(math.isfinite(item.spy_open) for item in sessions)
