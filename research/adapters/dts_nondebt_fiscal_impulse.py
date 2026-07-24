"""Outcome-free disposable adapter for the frozen DTS fiscal-impulse state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
import hashlib
import math
import statistics
from zoneinfo import ZoneInfo

from quant_system.backtest import Portfolio, TransactionCostModel
from quant_system.backtest.portfolio import Trade
from quant_system.markets.us import cash_settlement_lag_sessions


RESEARCH_ID = "US_EQ_DTS_NONDEBT_FISCAL_IMPULSE_YOY_4W_SPY_CASH_V1"
INITIAL_CAPITAL = 40_000.0
COMMISSION_RATE = 0.001
VALIDATION_INTERVALS = 28
SECONDARY_INTERVALS = 34
MINIMUM_STATE_INTERVALS = 4
MINIMUM_DIRECTIONAL_TRANSITIONS = 2
VALIDATION_START_MONTH = date(2021, 2, 1)
VALIDATION_END_MONTH = date(2023, 5, 1)
VALIDATION_TERMINAL_MONTH = date(2023, 6, 1)
SECONDARY_START_MONTH = date(2023, 8, 1)
SECONDARY_END_MONTH = date(2026, 5, 1)
SECONDARY_TERMINAL_MONTH = date(2026, 6, 1)
SYMBOL = "SPY"
STATES = ("SPY", "CASH")
NY = ZoneInfo("America/New_York")
GATE_NAMES = (
    "terminal_wealth_above_fifty_fifty",
    "paired_mean_active_return_above_zero",
    "maximum_drawdown_no_worse_than_spy",
)


class InputContractError(ValueError):
    """Raised when an input violates the frozen research contract."""


@dataclass(frozen=True)
class MonthlyState:
    month: date
    state: str
    decision_at: datetime
    source_available_at: datetime
    source_row_sha256: str

    def __post_init__(self) -> None:
        if type(self.month) is not date or self.month.day != 1:
            raise InputContractError("month must be the first calendar day")
        if self.state not in STATES:
            raise InputContractError("state must be exactly SPY or CASH")
        _require_aware(self.decision_at, "decision_at")
        _require_aware(self.source_available_at, "source_available_at")
        available_et = self.source_available_at.astimezone(NY)
        if available_et.timetz().replace(tzinfo=None) != time(16, 0):
            raise InputContractError("source_available_at must be 16:00 America/New_York")
        if self.source_available_at > self.decision_at:
            raise InputContractError("source_available_at cannot follow decision_at")
        _require_sha256(self.source_row_sha256, "source_row_sha256")


@dataclass(frozen=True)
class SegmentInputIdentity:
    segment: str
    fiscal_receipt_sha256: str
    fiscal_states_sha256: str
    market_receipt_sha256: str
    market_rows_sha256: str
    calendar_sha256: str
    definition_sha256: str
    adapter_sha256: str

    def __post_init__(self) -> None:
        if self.segment not in {"validation", "secondary"}:
            raise InputContractError("identity segment must be validation or secondary")
        for name in (
            "fiscal_receipt_sha256",
            "fiscal_states_sha256",
            "market_receipt_sha256",
            "market_rows_sha256",
            "calendar_sha256",
            "definition_sha256",
            "adapter_sha256",
        ):
            _require_sha256(getattr(self, name), name)


@dataclass(frozen=True)
class MarketSession:
    session_date: date
    spy_open: float
    spy_close: float

    def __post_init__(self) -> None:
        if type(self.session_date) is not date:
            raise InputContractError("session_date must be a date")
        _require_positive(self.spy_open, "spy_open")
        _require_positive(self.spy_close, "spy_close")

    def open_mark(self) -> dict[str, float]:
        return {SYMBOL: self.spy_open}

    def close_mark(self) -> dict[str, float]:
        return {SYMBOL: self.spy_close}


@dataclass(frozen=True)
class Distribution:
    symbol: str
    event_id: str
    ex_date: date
    pay_date: date
    amount_per_share: float

    def __post_init__(self) -> None:
        _require_spy(self.symbol)
        _require_identity(self.event_id, "event_id")
        if type(self.ex_date) is not date or type(self.pay_date) is not date:
            raise InputContractError("distribution dates must be dates")
        if self.pay_date < self.ex_date:
            raise InputContractError("pay_date cannot precede ex_date")
        _require_positive(self.amount_per_share, "amount_per_share")


@dataclass(frozen=True)
class Split:
    symbol: str
    event_id: str
    effective_date: date
    ratio: float

    def __post_init__(self) -> None:
        _require_spy(self.symbol)
        _require_identity(self.event_id, "event_id")
        if type(self.effective_date) is not date:
            raise InputContractError("effective_date must be a date")
        _require_positive(self.ratio, "ratio")


@dataclass(frozen=True)
class TradeAudit:
    side: str
    trade_date: date
    shares: int
    price: float
    commission: float
    settlement_date: date | None


@dataclass(frozen=True)
class Performance:
    terminal_wealth: float
    arithmetic_mean_return: float
    maximum_drawdown: float
    interval_returns: tuple[float, ...]
    pretrade_boundaries: tuple[float, ...]
    daily_open_nav: tuple[tuple[date, float], ...]
    trades: tuple[TradeAudit, ...]


@dataclass(frozen=True)
class SegmentDecision:
    segment: str
    observed_intervals: int
    spy_intervals: int
    cash_intervals: int
    spy_to_cash_transitions: int
    cash_to_spy_transitions: int
    state_history: tuple[str, ...]
    state_months: tuple[date, ...]
    terminal_month: date
    state_row_sha256s: tuple[str, ...]
    input_identity: SegmentInputIdentity
    strategy: Performance
    fifty_fifty: Performance
    spy_buyhold: Performance
    paired_mean_active_return: float
    gates: tuple[tuple[str, bool], ...]
    all_gates_pass: bool
    _module_proof: object = field(repr=False, compare=False)


@dataclass
class _Account:
    portfolio: Portfolio
    boundaries: list[float] = field(default_factory=list)
    daily_nav: list[tuple[date, float]] = field(default_factory=list)
    trades: list[TradeAudit] = field(default_factory=list)


_ISSUED_VALIDATIONS: dict[object, SegmentDecision] = {}


def first_session_of_month(
    month: date,
    sessions: tuple[MarketSession, ...],
) -> date:
    """Return the first caller-accepted XNYS session in ``month``."""

    if type(month) is not date or month.day != 1:
        raise InputContractError("month must be the first calendar day")
    _validate_sessions(sessions)
    for session in sessions:
        if (session.session_date.year, session.session_date.month) == (
            month.year,
            month.month,
        ):
            return session.session_date
    raise InputContractError("accepted sessions do not cover a required month")


def settlement_sessions(
    trade_date: date,
    accepted_session_dates: tuple[date, ...],
) -> tuple[date, ...]:
    """Return the exact accepted-session path required by the shared US primitive."""

    if type(trade_date) is not date:
        raise InputContractError("trade_date must be a date")
    if (
        type(accepted_session_dates) is not tuple
        or any(type(item) is not date for item in accepted_session_dates)
    ):
        raise InputContractError("accepted_session_dates must be a tuple of dates")
    if accepted_session_dates != tuple(sorted(accepted_session_dates)):
        raise InputContractError("accepted_session_dates must be sorted")
    if len(set(accepted_session_dates)) != len(accepted_session_dates):
        raise InputContractError("accepted_session_dates must be unique")
    following = tuple(item for item in accepted_session_dates if item > trade_date)
    lag = cash_settlement_lag_sessions(trade_date)
    if len(following) < lag:
        raise InputContractError("accepted calendar does not cover sale settlement")
    return following[:lag]


def fiscal_states_sha256(states: tuple[MonthlyState, ...]) -> str:
    """Bind exact ordered monthly state rows without opening any outcome."""

    if type(states) is not tuple or any(
        not isinstance(item, MonthlyState) for item in states
    ):
        raise InputContractError("states must be a tuple of MonthlyState")
    rows = tuple(
        "|".join(
            (
                item.month.isoformat(),
                item.state,
                item.decision_at.isoformat(),
                item.source_available_at.isoformat(),
                item.source_row_sha256,
            )
        )
        for item in states
    )
    return _rows_sha256(rows)


def market_rows_sha256(sessions: tuple[MarketSession, ...]) -> str:
    """Bind exact ordered synthetic or qualified raw-open/raw-close rows."""

    _validate_sessions(sessions)
    rows = tuple(
        "|".join(
            (
                item.session_date.isoformat(),
                item.spy_open.hex(),
                item.spy_close.hex(),
            )
        )
        for item in sessions
    )
    return _rows_sha256(rows)


def calendar_sha256(sessions: tuple[MarketSession, ...]) -> str:
    """Bind the exact ordered accepted-session calendar."""

    _validate_sessions(sessions)
    return _rows_sha256(tuple(item.session_date.isoformat() for item in sessions))


def run_validation(
    states: tuple[MonthlyState, ...],
    sessions: tuple[MarketSession, ...],
    *,
    terminal_month: date,
    input_identity: SegmentInputIdentity,
    distributions: tuple[Distribution, ...] = (),
    splits: tuple[Split, ...] = (),
) -> SegmentDecision:
    return _run_segment(
        states,
        sessions,
        terminal_month=terminal_month,
        input_identity=input_identity,
        distributions=distributions,
        splits=splits,
        expected_intervals=VALIDATION_INTERVALS,
        segment="validation",
    )


def run_secondary(
    states: tuple[MonthlyState, ...],
    sessions: tuple[MarketSession, ...],
    *,
    terminal_month: date,
    validation: SegmentDecision,
    input_identity: SegmentInputIdentity,
    distributions: tuple[Distribution, ...] = (),
    splits: tuple[Split, ...] = (),
) -> SegmentDecision:
    require_secondary_unsealed(validation)
    return _run_segment(
        states,
        sessions,
        terminal_month=terminal_month,
        input_identity=input_identity,
        validation_identity=validation.input_identity,
        distributions=distributions,
        splits=splits,
        expected_intervals=SECONDARY_INTERVALS,
        segment="secondary",
    )


def require_secondary_unsealed(validation: SegmentDecision) -> None:
    """Mechanically recompute validation support and all three gates."""

    if not isinstance(validation, SegmentDecision):
        raise InputContractError("secondary segment remains sealed")
    if (
        type(validation._module_proof) is not object
        or _ISSUED_VALIDATIONS.get(validation._module_proof) is not validation
    ):
        raise InputContractError(
            "secondary requires this module's exact run_validation proof"
        )
    if validation.segment != "validation":
        raise InputContractError("secondary requires a validation-segment decision")
    if validation.observed_intervals != VALIDATION_INTERVALS:
        raise InputContractError("secondary requires the frozen validation interval count")
    if (
        validation.state_months
        != _month_range(VALIDATION_START_MONTH, VALIDATION_END_MONTH)
        or validation.terminal_month != VALIDATION_TERMINAL_MONTH
        or type(validation.state_row_sha256s) is not tuple
        or len(validation.state_row_sha256s) != VALIDATION_INTERVALS
        or any(
            _require_sha256(item, "state_row_sha256") != item
            for item in validation.state_row_sha256s
        )
        or not isinstance(validation.input_identity, SegmentInputIdentity)
        or validation.input_identity.segment != "validation"
    ):
        raise InputContractError("secondary requires exact validation input binding")
    support = _state_support(validation.state_history, VALIDATION_INTERVALS)
    recorded_support = (
        validation.spy_intervals,
        validation.cash_intervals,
        validation.spy_to_cash_transitions,
        validation.cash_to_spy_transitions,
    )
    if any(type(item) is not int for item in recorded_support) or recorded_support != support:
        raise InputContractError("secondary requires exact validation state support")

    gate_values, paired_mean = _gate_values(
        validation.strategy,
        validation.fifty_fifty,
        validation.spy_buyhold,
        VALIDATION_INTERVALS,
    )
    recomputed_gates = tuple(zip(GATE_NAMES, gate_values))
    if (
        type(validation.gates) is not tuple
        or tuple(name for name, _ in validation.gates) != GATE_NAMES
        or any(type(value) is not bool for _, value in validation.gates)
        or validation.gates != recomputed_gates
    ):
        raise InputContractError("secondary requires all exact validation gates")
    if (
        not _is_finite_number(validation.paired_mean_active_return)
        or validation.paired_mean_active_return != paired_mean
    ):
        raise InputContractError("secondary validation active-return summary is inconsistent")
    recomputed_pass = all(gate_values)
    if (
        type(validation.all_gates_pass) is not bool
        or validation.all_gates_pass is not recomputed_pass
    ):
        raise InputContractError("secondary validation gate summary is inconsistent")
    if not recomputed_pass:
        raise InputContractError("secondary segment remains sealed")


def _run_segment(
    states: tuple[MonthlyState, ...],
    sessions: tuple[MarketSession, ...],
    *,
    terminal_month: date,
    input_identity: SegmentInputIdentity,
    validation_identity: SegmentInputIdentity | None = None,
    distributions: tuple[Distribution, ...],
    splits: tuple[Split, ...],
    expected_intervals: int,
    segment: str,
) -> SegmentDecision:
    if segment not in {"validation", "secondary"}:
        raise InputContractError("segment must be validation or secondary")
    history = _validate_state_contract(
        states,
        terminal_month,
        expected_intervals,
        segment,
    )
    _validate_sessions(sessions)

    months = tuple(item.month for item in states) + (terminal_month,)
    decision_dates = tuple(first_session_of_month(month, sessions) for month in months)
    session_dates = tuple(item.session_date for item in sessions)
    session_index = {item: index for index, item in enumerate(session_dates)}
    first_index = session_index[decision_dates[0]]
    terminal_index = session_index[decision_dates[-1]]
    if first_index != 1 or terminal_index != len(sessions) - 1:
        raise InputContractError(
            "segment sessions require exactly one accepted preceding session "
            "and no rows after terminal execution"
        )
    _validate_state_timing(states, decision_dates[:-1], session_dates)
    _validate_input_identity(
        input_identity,
        segment=segment,
        states=states,
        sessions=sessions,
        validation_identity=validation_identity,
    )
    terminal_date = decision_dates[-1]
    _validate_actions(
        distributions,
        splits,
        session_dates=session_dates,
        first_decision=decision_dates[0],
        terminal_date=terminal_date,
    )

    state_by_decision = dict(zip(decision_dates[:-1], history))
    distributions_by_date = _group_distributions(distributions)
    splits_by_date = _group_splits(splits)
    accounts = (_new_account(), _new_account(), _new_account())

    for index in range(first_index, terminal_index + 1):
        session = sessions[index]
        for account in accounts:
            account.portfolio.start_session(session.session_date)

        state = state_by_decision.get(session.session_date)
        is_boundary = state is not None or session.session_date == terminal_date
        if is_boundary:
            prior_close = sessions[index - 1].spy_close
            for account in accounts:
                account.boundaries.append(account.portfolio.nav({SYMBOL: prior_close}))
            if session.session_date == terminal_date:
                break

        todays_distributions = distributions_by_date.get(session.session_date, ())
        todays_splits = splits_by_date.get(session.session_date, ())
        _apply_actions(accounts, todays_distributions, todays_splits)

        if state is not None:
            split_ratio = _combined_split_ratio(todays_splits)
            strategy_target = _target_shares(
                accounts[0].boundaries[-1],
                sessions[index - 1].spy_close,
                1.0 if state == "SPY" else 0.0,
                split_ratio,
            )
            fifty_target = _target_shares(
                accounts[1].boundaries[-1],
                sessions[index - 1].spy_close,
                0.5,
                split_ratio,
            )
            _rebalance(
                accounts[0],
                strategy_target,
                session,
                session_dates,
            )
            _rebalance(
                accounts[1],
                fifty_target,
                session,
                session_dates,
            )
            if len(accounts[2].boundaries) == 1:
                buyhold_target = _target_shares(
                    accounts[2].boundaries[-1],
                    sessions[index - 1].spy_close,
                    1.0,
                    split_ratio,
                )
                _rebalance(
                    accounts[2],
                    buyhold_target,
                    session,
                    session_dates,
                )

        for account in accounts:
            account.daily_nav.append(
                (session.session_date, account.portfolio.nav(session.open_mark()))
            )

    performances = tuple(
        _performance(account, expected_intervals) for account in accounts
    )
    gate_values, paired_mean = _gate_values(
        performances[0],
        performances[1],
        performances[2],
        expected_intervals,
    )
    gates = tuple(zip(GATE_NAMES, gate_values))
    support = _state_support(history, expected_intervals)
    proof = object()
    decision = SegmentDecision(
        segment,
        expected_intervals,
        support[0],
        support[1],
        support[2],
        support[3],
        history,
        tuple(item.month for item in states),
        terminal_month,
        tuple(item.source_row_sha256 for item in states),
        input_identity,
        performances[0],
        performances[1],
        performances[2],
        paired_mean,
        gates,
        all(gate_values),
        proof,
    )
    if segment == "validation":
        _ISSUED_VALIDATIONS[proof] = decision
    return decision


def _new_account() -> _Account:
    return _Account(
        Portfolio.us(
            INITIAL_CAPITAL,
            costs=TransactionCostModel(commission_rate=COMMISSION_RATE),
        )
    )


def _rebalance(
    account: _Account,
    target_shares: int,
    session: MarketSession,
    accepted_session_dates: tuple[date, ...],
) -> None:
    if type(target_shares) is not int or target_shares < 0:
        raise InputContractError("target shares must be a nonnegative integer")
    current = _current_shares(account.portfolio)
    if current > target_shares:
        path = settlement_sessions(session.session_date, accepted_session_dates)
        trade = account.portfolio.sell(
            SYMBOL,
            current - target_shares,
            session.spy_open,
            session.session_date,
            settlement_date=path[-1],
            accepted_settlement_sessions=path,
        )
        _record_trade(account, trade, path[-1])
        return
    deficit = target_shares - current
    if deficit <= 0:
        return
    unit_cash = session.spy_open * (1.0 + COMMISSION_RATE)
    if not _is_finite_number(unit_cash) or unit_cash <= 0.0:
        raise InputContractError("buy unit cash must be finite and positive")
    affordable = math.floor((account.portfolio.available_cash + 1e-9) / unit_cash)
    shares = min(deficit, affordable)
    if shares <= 0:
        return
    trade = account.portfolio.buy(
        SYMBOL,
        shares,
        session.spy_open,
        session.session_date,
    )
    _record_trade(account, trade, None)


def _apply_actions(
    accounts: tuple[_Account, ...],
    distributions: tuple[Distribution, ...],
    splits: tuple[Split, ...],
) -> None:
    if type(accounts) is not tuple or any(
        not isinstance(account, _Account) for account in accounts
    ):
        raise InputContractError("accounts must be an internal account tuple")
    for event in distributions:
        for account in accounts:
            account.portfolio.apply_cash_distribution(
                event.symbol,
                event_id=event.event_id,
                amount_per_share=event.amount_per_share,
                ex_date=event.ex_date,
                pay_date=event.pay_date,
            )
    for event in splits:
        for account in accounts:
            adjusted = _current_shares(account.portfolio) * event.ratio
            if not _is_finite_number(adjusted) or not float(adjusted).is_integer():
                raise InputContractError(
                    "split must preserve nonnegative whole-share holdings"
                )
        for account in accounts:
            account.portfolio.apply_split(
                event.symbol,
                event.ratio,
                event_id=event.event_id,
            )


def _record_trade(
    account: _Account,
    trade: Trade,
    settlement_date: date | None,
) -> None:
    if not float(trade.shares).is_integer():
        raise InputContractError("executed shares must be whole shares")
    account.trades.append(
        TradeAudit(
            trade.side,
            trade.trade_date,
            int(trade.shares),
            trade.price,
            trade.costs.commission,
            settlement_date,
        )
    )


def _performance(account: _Account, expected_intervals: int) -> Performance:
    if len(account.boundaries) != expected_intervals + 1:
        raise InputContractError("pretrade boundary count is not frozen")
    interval_returns = tuple(
        later / earlier - 1.0
        for earlier, later in zip(account.boundaries, account.boundaries[1:])
    )
    if len(interval_returns) != expected_intervals or any(
        not _is_finite_number(item) or item <= -1.0 for item in interval_returns
    ):
        raise InputContractError("interval returns must be finite and above negative one")
    maximum_drawdown = _maximum_drawdown(
        (INITIAL_CAPITAL,) + tuple(value for _, value in account.daily_nav)
    )
    return Performance(
        account.boundaries[-1],
        statistics.fmean(interval_returns),
        maximum_drawdown,
        interval_returns,
        tuple(account.boundaries),
        tuple(account.daily_nav),
        tuple(account.trades),
    )


def _gate_values(
    strategy: Performance,
    fifty_fifty: Performance,
    spy_buyhold: Performance,
    expected_intervals: int,
) -> tuple[tuple[bool, bool, bool], float]:
    strategy_metrics = _verified_metrics(strategy, expected_intervals)
    fifty_metrics = _verified_metrics(fifty_fifty, expected_intervals)
    spy_metrics = _verified_metrics(spy_buyhold, expected_intervals)
    active_returns = tuple(
        strategy_return - comparator_return
        for strategy_return, comparator_return in zip(
            strategy_metrics[3],
            fifty_metrics[3],
        )
    )
    if len(active_returns) != expected_intervals or any(
        not _is_finite_number(item) for item in active_returns
    ):
        raise InputContractError("paired active returns must be finite and complete")
    paired_mean = statistics.fmean(active_returns)
    return (
        (
            strategy_metrics[0] > fifty_metrics[0],
            paired_mean > 0.0,
            strategy_metrics[2] >= spy_metrics[2],
        ),
        paired_mean,
    )


def _verified_metrics(
    performance: Performance,
    expected_intervals: int,
) -> tuple[float, float, float, tuple[float, ...]]:
    if not isinstance(performance, Performance):
        raise InputContractError("gate performance must use the frozen result type")
    if (
        type(performance.pretrade_boundaries) is not tuple
        or len(performance.pretrade_boundaries) != expected_intervals + 1
        or any(
            not _is_finite_number(item) or item <= 0.0
            for item in performance.pretrade_boundaries
        )
    ):
        raise InputContractError("gate boundaries must be finite, positive, and complete")
    recomputed_returns = tuple(
        later / earlier - 1.0
        for earlier, later in zip(
            performance.pretrade_boundaries,
            performance.pretrade_boundaries[1:],
        )
    )
    if (
        type(performance.interval_returns) is not tuple
        or len(performance.interval_returns) != expected_intervals
        or any(
            not _is_finite_number(item) or item <= -1.0
            for item in performance.interval_returns
        )
        or any(
            not math.isclose(recorded, recomputed, rel_tol=1e-12, abs_tol=1e-12)
            for recorded, recomputed in zip(
                performance.interval_returns,
                recomputed_returns,
            )
        )
    ):
        raise InputContractError("gate interval returns are inconsistent")
    terminal_wealth = performance.pretrade_boundaries[-1]
    arithmetic_mean = statistics.fmean(recomputed_returns)
    if (
        not _is_finite_number(performance.terminal_wealth)
        or performance.terminal_wealth <= 0.0
        or not math.isclose(
            performance.terminal_wealth,
            terminal_wealth,
            rel_tol=1e-12,
            abs_tol=1e-9,
        )
        or not _is_finite_number(performance.arithmetic_mean_return)
        or not math.isclose(
            performance.arithmetic_mean_return,
            arithmetic_mean,
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
    ):
        raise InputContractError("gate terminal or mean performance is inconsistent")
    if (
        type(performance.daily_open_nav) is not tuple
        or not performance.daily_open_nav
        or any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not date
            or not _is_finite_number(item[1])
            or item[1] <= 0.0
            for item in performance.daily_open_nav
        )
    ):
        raise InputContractError("gate daily opening NAV path is invalid")
    daily_dates = tuple(item[0] for item in performance.daily_open_nav)
    if daily_dates != tuple(sorted(daily_dates)) or len(set(daily_dates)) != len(
        daily_dates
    ):
        raise InputContractError("gate daily opening NAV dates must be ordered")
    maximum_drawdown = _maximum_drawdown(
        (INITIAL_CAPITAL,) + tuple(item[1] for item in performance.daily_open_nav)
    )
    if (
        not _is_finite_number(performance.maximum_drawdown)
        or not math.isclose(
            performance.maximum_drawdown,
            maximum_drawdown,
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
    ):
        raise InputContractError("gate maximum drawdown is inconsistent")
    if type(performance.trades) is not tuple or any(
        not isinstance(item, TradeAudit) for item in performance.trades
    ):
        raise InputContractError("gate trade audit is invalid")
    return terminal_wealth, arithmetic_mean, maximum_drawdown, recomputed_returns


def _maximum_drawdown(path: tuple[float, ...]) -> float:
    if type(path) is not tuple or not path:
        raise InputContractError("drawdown path must be a nonempty tuple")
    peak = 0.0
    drawdown = 0.0
    for value in path:
        _require_positive(value, "daily opening NAV")
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - 1.0)
    return drawdown


def _target_shares(
    nav: float,
    decision_close: float,
    weight: float,
    split_ratio: float,
) -> int:
    _require_positive(nav, "pretrade NAV")
    _require_positive(decision_close, "decision close")
    if weight not in {0.0, 0.5, 1.0}:
        raise InputContractError("weight is outside the frozen contract")
    _require_positive(split_ratio, "split ratio")
    pre_split_target = math.floor(weight * nav / decision_close)
    adjusted = pre_split_target * split_ratio
    if not _is_finite_number(adjusted) or adjusted < 0.0 or not adjusted.is_integer():
        raise InputContractError("split-adjusted target must be whole shares")
    return int(adjusted)


def _combined_split_ratio(splits: tuple[Split, ...]) -> float:
    ratio = 1.0
    for event in splits:
        ratio *= event.ratio
        if not _is_finite_number(ratio) or ratio <= 0.0:
            raise InputContractError("combined split ratio must be finite and positive")
    return ratio


def _current_shares(portfolio: Portfolio) -> int:
    position = portfolio.positions.get(SYMBOL)
    shares = 0.0 if position is None else position.shares
    if (
        not _is_finite_number(shares)
        or shares < 0.0
        or not float(shares).is_integer()
    ):
        raise InputContractError("portfolio shares must be nonnegative whole shares")
    return int(shares)


def _validate_state_contract(
    states: tuple[MonthlyState, ...],
    terminal_month: date,
    expected_intervals: int,
    segment: str,
) -> tuple[str, ...]:
    if type(states) is not tuple or len(states) != expected_intervals:
        raise InputContractError(
            f"segment requires exactly {expected_intervals} monthly states"
        )
    if any(not isinstance(item, MonthlyState) for item in states):
        raise InputContractError("monthly states have invalid types")
    months = tuple(item.month for item in states)
    if segment == "validation":
        expected_months = _month_range(
            VALIDATION_START_MONTH,
            VALIDATION_END_MONTH,
        )
        expected_terminal = VALIDATION_TERMINAL_MONTH
    elif segment == "secondary":
        expected_months = _month_range(
            SECONDARY_START_MONTH,
            SECONDARY_END_MONTH,
        )
        expected_terminal = SECONDARY_TERMINAL_MONTH
    else:
        raise InputContractError("segment must be validation or secondary")
    if len(expected_months) != expected_intervals:
        raise InputContractError("internal frozen month count is inconsistent")
    if months != expected_months:
        raise InputContractError(
            f"{segment} months must match the exact frozen range without "
            "overlap, subset, or reorder"
        )
    if terminal_month != expected_terminal:
        raise InputContractError(f"{segment} terminal month is not frozen")
    history = tuple(item.state for item in states)
    _state_support(history, expected_intervals)
    return history


def _validate_state_timing(
    states: tuple[MonthlyState, ...],
    decision_dates: tuple[date, ...],
    session_dates: tuple[date, ...],
) -> None:
    if len(states) != len(decision_dates):
        raise InputContractError("state timing rows are incomplete")
    session_index = {item: index for index, item in enumerate(session_dates)}
    normalized_decisions: list[datetime] = []
    normalized_available: list[datetime] = []
    source_rows: list[str] = []
    for state, execution_date in zip(states, decision_dates):
        index = session_index[execution_date]
        if index == 0:
            raise InputContractError("monthly decision requires a preceding session")
        expected_decision_date = session_dates[index - 1]
        decision_et = state.decision_at.astimezone(NY)
        if (
            decision_et.date() != expected_decision_date
            or decision_et.timetz().replace(tzinfo=None) != time(20, 5)
        ):
            raise InputContractError(
                "decision_at must be 20:05 America/New_York on the accepted "
                "session preceding execution"
            )
        available_et = state.source_available_at.astimezone(NY)
        if available_et > decision_et:
            raise InputContractError("source row is late for its monthly decision")
        normalized_decisions.append(decision_et)
        normalized_available.append(available_et)
        source_rows.append(state.source_row_sha256)
    if normalized_decisions != sorted(normalized_decisions) or len(
        set(normalized_decisions)
    ) != len(normalized_decisions):
        raise InputContractError("monthly decisions must be strictly ordered")
    if normalized_available != sorted(normalized_available) or len(
        set(normalized_available)
    ) != len(normalized_available):
        raise InputContractError("source availability rows must be strictly ordered")
    if len(set(source_rows)) != len(source_rows):
        raise InputContractError("source row identities must be unique")


def _validate_input_identity(
    identity: SegmentInputIdentity,
    *,
    segment: str,
    states: tuple[MonthlyState, ...],
    sessions: tuple[MarketSession, ...],
    validation_identity: SegmentInputIdentity | None,
) -> None:
    if not isinstance(identity, SegmentInputIdentity) or identity.segment != segment:
        raise InputContractError("segment input identity does not match the run")
    if identity.fiscal_states_sha256 != fiscal_states_sha256(states):
        raise InputContractError("fiscal state-row identity mismatch")
    if identity.market_rows_sha256 != market_rows_sha256(sessions):
        raise InputContractError("market row identity mismatch")
    if identity.calendar_sha256 != calendar_sha256(sessions):
        raise InputContractError("accepted calendar identity mismatch")
    if segment == "validation":
        if validation_identity is not None:
            raise InputContractError("validation cannot inherit another segment identity")
        return
    if (
        not isinstance(validation_identity, SegmentInputIdentity)
        or validation_identity.segment != "validation"
    ):
        raise InputContractError("secondary requires the validation input identity")
    if (
        identity.fiscal_receipt_sha256
        != validation_identity.fiscal_receipt_sha256
        or identity.definition_sha256 != validation_identity.definition_sha256
        or identity.adapter_sha256 != validation_identity.adapter_sha256
    ):
        raise InputContractError("secondary fiscal/code identity mismatch")
    if identity.fiscal_states_sha256 == validation_identity.fiscal_states_sha256:
        raise InputContractError("secondary fiscal state rows must be segment-specific")
    if (
        identity.market_receipt_sha256
        == validation_identity.market_receipt_sha256
        or identity.market_rows_sha256 == validation_identity.market_rows_sha256
        or identity.calendar_sha256 == validation_identity.calendar_sha256
    ):
        raise InputContractError("secondary market segment identity is not independent")


def _state_support(
    history: tuple[str, ...],
    expected_intervals: int,
) -> tuple[int, int, int, int]:
    if (
        type(history) is not tuple
        or len(history) != expected_intervals
        or any(item not in STATES for item in history)
    ):
        raise InputContractError("state history does not match the frozen interval count")
    spy_count = history.count("SPY")
    cash_count = history.count("CASH")
    spy_to_cash = sum(
        earlier == "SPY" and later == "CASH"
        for earlier, later in zip(history, history[1:])
    )
    cash_to_spy = sum(
        earlier == "CASH" and later == "SPY"
        for earlier, later in zip(history, history[1:])
    )
    if spy_count < MINIMUM_STATE_INTERVALS or cash_count < MINIMUM_STATE_INTERVALS:
        raise InputContractError("each state requires at least 4 intervals")
    if (
        spy_to_cash < MINIMUM_DIRECTIONAL_TRANSITIONS
        or cash_to_spy < MINIMUM_DIRECTIONAL_TRANSITIONS
    ):
        raise InputContractError("each transition direction requires at least 2 events")
    return spy_count, cash_count, spy_to_cash, cash_to_spy


def _validate_sessions(sessions: tuple[MarketSession, ...]) -> None:
    if type(sessions) is not tuple or len(sessions) < 2:
        raise InputContractError("sessions must be a tuple with coverage")
    if any(not isinstance(item, MarketSession) for item in sessions):
        raise InputContractError("sessions have invalid types")
    dates = tuple(item.session_date for item in sessions)
    if dates != tuple(sorted(dates)):
        raise InputContractError("sessions must be sorted")
    if len(set(dates)) != len(dates):
        raise InputContractError("session dates must be unique")


def _validate_actions(
    distributions: tuple[Distribution, ...],
    splits: tuple[Split, ...],
    *,
    session_dates: tuple[date, ...],
    first_decision: date,
    terminal_date: date,
) -> None:
    if type(distributions) is not tuple or any(
        not isinstance(item, Distribution) for item in distributions
    ):
        raise InputContractError("distributions must be a tuple of Distribution")
    if type(splits) is not tuple or any(not isinstance(item, Split) for item in splits):
        raise InputContractError("splits must be a tuple of Split")
    event_ids = tuple(item.event_id for item in distributions + splits)
    if len(set(event_ids)) != len(event_ids):
        raise InputContractError("corporate-action event IDs must be unique")
    accepted = set(session_dates)
    event_dates = tuple(item.ex_date for item in distributions) + tuple(
        item.effective_date for item in splits
    )
    if any(
        item not in accepted or item < first_decision or item >= terminal_date
        for item in event_dates
    ):
        raise InputContractError(
            "corporate-action effective dates must be covered preterminal sessions"
        )


def _group_distributions(
    events: tuple[Distribution, ...],
) -> dict[date, tuple[Distribution, ...]]:
    grouped: dict[date, list[Distribution]] = {}
    for event in events:
        grouped.setdefault(event.ex_date, []).append(event)
    return {key: tuple(value) for key, value in grouped.items()}


def _group_splits(events: tuple[Split, ...]) -> dict[date, tuple[Split, ...]]:
    grouped: dict[date, list[Split]] = {}
    for event in events:
        grouped.setdefault(event.effective_date, []).append(event)
    return {key: tuple(value) for key, value in grouped.items()}


def _next_month(value: date) -> date:
    return date(value.year + (value.month == 12), value.month % 12 + 1, 1)


def _month_range(start: date, end: date) -> tuple[date, ...]:
    output = [start]
    while output[-1] < end:
        output.append(_next_month(output[-1]))
    if output[-1] != end:
        raise InputContractError("month range endpoints are inconsistent")
    return tuple(output)


def _rows_sha256(rows: tuple[str, ...]) -> str:
    if type(rows) is not tuple or any(type(item) is not str for item in rows):
        raise InputContractError("identity rows must be a string tuple")
    payload = "".join(f"{item}\n" for item in rows).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_spy(value: object) -> str:
    if value != SYMBOL:
        raise InputContractError("corporate-action symbol must be SPY")
    return str(value)


def _require_identity(value: object, label: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > 256
    ):
        raise InputContractError(f"{label} must be a stable nonempty identity")
    return value


def _require_sha256(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise InputContractError(f"{label} must be lowercase SHA-256")
    return value


def _require_aware(value: object, label: str) -> datetime:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InputContractError(f"{label} must be timezone-aware")
    return value


def _require_positive(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0.0
    ):
        raise InputContractError(f"{label} must be finite and positive")
    return float(value)


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )
