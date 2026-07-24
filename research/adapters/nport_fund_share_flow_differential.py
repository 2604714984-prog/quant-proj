"""Disposable adapter for the frozen N-PORT SPY/QQQ flow differential."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
import math
import statistics
from zoneinfo import ZoneInfo

from quant_system.backtest import Portfolio, TransactionCostModel
from quant_system.backtest.portfolio import Trade
from quant_system.markets.us import cash_settlement_lag_sessions


RESEARCH_ID = "US_EQ_NPORT_FUND_SHARE_FLOW_DIFFERENTIAL_V1"
INITIAL_CAPITAL = 40_000.0
COMMISSION_RATE = 0.001
VALIDATION_INTERVALS = 12
SECONDARY_INTERVALS = 12
MINIMUM_STATE_INTERVALS = 3
SYMBOLS = ("SPY", "QQQ")
BUY_ORDER = ("QQQ", "SPY")
SELL_ORDER = ("SPY", "QQQ")
GATE_NAMES = (
    "exact_interval_count",
    "minimum_spy_state_support",
    "minimum_qqq_state_support",
    "terminal_wealth_above_fifty_fifty",
    "mean_return_above_fifty_fifty",
    "maximum_drawdown_no_worse_than_spy",
)
NY = ZoneInfo("America/New_York")


class InputContractError(ValueError):
    """Raised when inputs violate the frozen research contract."""


@dataclass(frozen=True)
class FlowPair:
    report_date: date
    pair_initial_available_at: datetime
    spy_external_net: Decimal
    spy_external_gross: Decimal
    qqq_external_net: Decimal
    qqq_external_gross: Decimal
    pair_sha256: str

    def __post_init__(self) -> None:
        if type(self.report_date) is not date:
            raise InputContractError("report_date must be a date")
        if self.report_date.month not in {3, 6, 9, 12}:
            raise InputContractError("report_date must be a calendar quarter end")
        next_day = self.report_date.replace(day=28)
        while True:
            try:
                next_day = next_day.replace(day=next_day.day + 1)
            except ValueError:
                break
        if self.report_date.day != next_day.day:
            raise InputContractError("report_date must be a calendar quarter end")
        _require_aware(self.pair_initial_available_at, "pair_initial_available_at")
        for net_name, gross_name in (
            ("spy_external_net", "spy_external_gross"),
            ("qqq_external_net", "qqq_external_gross"),
        ):
            net = getattr(self, net_name)
            gross = getattr(self, gross_name)
            if type(net) is not Decimal or not net.is_finite():
                raise InputContractError(f"{net_name} must be a finite Decimal")
            if type(gross) is not Decimal or not gross.is_finite() or gross < 0:
                raise InputContractError(
                    f"{gross_name} must be a nonnegative Decimal"
                )
            if gross == 0 and net != 0:
                raise InputContractError(
                    f"{net_name} must be zero when external gross flow is zero"
                )
            if abs(net) > gross:
                raise InputContractError(f"{net_name} cannot exceed external gross flow")
        _require_sha256(self.pair_sha256, "pair_sha256")

    @property
    def spy_imbalance(self) -> Decimal | None:
        if self.spy_external_gross == 0:
            return None
        return self.spy_external_net / self.spy_external_gross

    @property
    def qqq_imbalance(self) -> Decimal | None:
        if self.qqq_external_gross == 0:
            return None
        return self.qqq_external_net / self.qqq_external_gross

    @property
    def selected_symbol(self) -> str:
        if self.spy_external_gross == 0 or self.qqq_external_gross == 0:
            return "SPY"
        assert self.qqq_imbalance is not None
        assert self.spy_imbalance is not None
        return "QQQ" if self.qqq_imbalance > self.spy_imbalance else "SPY"


@dataclass(frozen=True)
class MarketSession:
    session_date: date
    spy_open: float
    spy_close: float
    qqq_open: float
    qqq_close: float

    def __post_init__(self) -> None:
        if type(self.session_date) is not date:
            raise InputContractError("session_date must be a date")
        for name in ("spy_open", "spy_close", "qqq_open", "qqq_close"):
            _require_positive(getattr(self, name), name)

    def opens(self) -> dict[str, float]:
        return {"SPY": self.spy_open, "QQQ": self.qqq_open}

    def closes(self) -> dict[str, float]:
        return {"SPY": self.spy_close, "QQQ": self.qqq_close}


@dataclass(frozen=True)
class Distribution:
    symbol: str
    event_id: str
    ex_date: date
    pay_date: date
    amount_per_share: float

    def __post_init__(self) -> None:
        _require_symbol(self.symbol)
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
        _require_symbol(self.symbol)
        _require_identity(self.event_id, "event_id")
        if type(self.effective_date) is not date:
            raise InputContractError("effective_date must be a date")
        _require_positive(self.ratio, "ratio")


@dataclass(frozen=True)
class TradeAudit:
    phase: str
    symbol: str
    side: str
    trade_date: date
    shares: int
    price: float
    commission: float


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
    qqq_intervals: int
    strategy: Performance
    fifty_fifty: Performance
    spy_buyhold: Performance
    gates: tuple[tuple[str, bool], ...]
    all_gates_pass: bool


@dataclass(frozen=True)
class _PendingPhaseB:
    decision_date: date
    settlement_date: date
    targets: tuple[tuple[str, int], ...]

    def as_dict(self) -> dict[str, int]:
        return dict(self.targets)


@dataclass
class _Account:
    name: str
    portfolio: Portfolio
    boundaries: list[float] = field(default_factory=list)
    daily_nav: list[tuple[date, float]] = field(default_factory=list)
    trades: list[TradeAudit] = field(default_factory=list)
    pending: _PendingPhaseB | None = None


def select_symbol(pair: FlowPair) -> str:
    if not isinstance(pair, FlowPair):
        raise InputContractError("pair must be a FlowPair")
    return pair.selected_symbol


def decision_session(
    pair: FlowPair,
    sessions: tuple[MarketSession, ...],
) -> date:
    """Return the first accepted session whose 08:30 cutoff is strictly later."""

    _validate_sessions(sessions)
    if not isinstance(pair, FlowPair):
        raise InputContractError("pair must be a FlowPair")
    available = pair.pair_initial_available_at.astimezone(NY)
    for session in sessions:
        cutoff = datetime.combine(session.session_date, time(8, 30), NY)
        if cutoff > available:
            return session.session_date
    raise InputContractError("no accepted decision session follows pair availability")


def settlement_sessions(
    trade_date: date,
    accepted_session_dates: tuple[date, ...],
) -> tuple[date, ...]:
    """Return the exact accepted-session settlement path for a US sale."""

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


def run_validation(
    pairs: tuple[FlowPair, ...],
    sessions: tuple[MarketSession, ...],
    *,
    distributions: tuple[Distribution, ...] = (),
    splits: tuple[Split, ...] = (),
) -> SegmentDecision:
    return _run_segment(
        pairs,
        sessions,
        distributions=distributions,
        splits=splits,
        expected_intervals=VALIDATION_INTERVALS,
        segment="validation",
    )


def run_secondary(
    pairs: tuple[FlowPair, ...],
    sessions: tuple[MarketSession, ...],
    *,
    validation: SegmentDecision,
    distributions: tuple[Distribution, ...] = (),
    splits: tuple[Split, ...] = (),
) -> SegmentDecision:
    require_secondary_unsealed(validation)
    return _run_segment(
        pairs,
        sessions,
        distributions=distributions,
        splits=splits,
        expected_intervals=SECONDARY_INTERVALS,
        segment="secondary",
    )


def require_secondary_unsealed(validation: SegmentDecision) -> None:
    if not isinstance(validation, SegmentDecision):
        raise InputContractError("secondary segment remains sealed")
    if validation.segment != "validation":
        raise InputContractError("secondary requires a validation-segment decision")
    if validation.observed_intervals != VALIDATION_INTERVALS:
        raise InputContractError("secondary requires the frozen validation result")
    if (
        type(validation.spy_intervals) is not int
        or type(validation.qqq_intervals) is not int
        or validation.spy_intervals + validation.qqq_intervals
        != VALIDATION_INTERVALS
        or validation.spy_intervals < MINIMUM_STATE_INTERVALS
        or validation.qqq_intervals < MINIMUM_STATE_INTERVALS
    ):
        raise InputContractError("secondary requires exact validation state support")
    recomputed_values = _gate_values(
        observed_intervals=validation.observed_intervals,
        expected_intervals=VALIDATION_INTERVALS,
        spy_count=validation.spy_intervals,
        qqq_count=validation.qqq_intervals,
        strategy=validation.strategy,
        fifty_fifty=validation.fifty_fifty,
        spy_buyhold=validation.spy_buyhold,
    )
    recomputed_gates = tuple(zip(GATE_NAMES, recomputed_values))
    if (
        type(validation.gates) is not tuple
        or tuple(name for name, _ in validation.gates) != GATE_NAMES
        or any(type(value) is not bool for _, value in validation.gates)
        or validation.gates != recomputed_gates
    ):
        raise InputContractError("secondary requires all exact validation gates")
    recomputed_pass = all(recomputed_values)
    if (
        type(validation.all_gates_pass) is not bool
        or validation.all_gates_pass is not recomputed_pass
    ):
        raise InputContractError("secondary validation gate summary is inconsistent")
    if not recomputed_pass:
        raise InputContractError("secondary segment remains sealed")


def _run_segment(
    pairs: tuple[FlowPair, ...],
    sessions: tuple[MarketSession, ...],
    *,
    distributions: tuple[Distribution, ...],
    splits: tuple[Split, ...],
    expected_intervals: int,
    segment: str,
) -> SegmentDecision:
    if segment not in {"validation", "secondary"}:
        raise InputContractError("segment must be validation or secondary")
    _validate_pairs(pairs, expected_intervals)
    _validate_sessions(sessions)
    _validate_actions(distributions, splits)
    session_dates = tuple(item.session_date for item in sessions)
    decision_dates = tuple(decision_session(pair, sessions) for pair in pairs)
    if decision_dates != tuple(sorted(decision_dates)):
        raise InputContractError("pair decision sessions must be chronological")
    if len(set(decision_dates)) != len(decision_dates):
        raise InputContractError("pair decisions must occur on unique sessions")
    session_index = {item.session_date: index for index, item in enumerate(sessions)}
    if any(session_index[item] == 0 for item in decision_dates):
        raise InputContractError("each decision requires a preceding accepted session")

    pairs_by_decision = dict(zip(decision_dates, pairs))
    terminal_date = decision_dates[-1]
    distributions_by_date = _group_distributions(distributions)
    splits_by_date = _group_splits(splits)
    accounts = (
        _new_account("strategy"),
        _new_account("fifty_fifty"),
        _new_account("spy_buyhold"),
    )
    selected_history: list[str] = []

    first_decision_index = session_index[decision_dates[0]]
    for index in range(first_decision_index, session_index[terminal_date] + 1):
        session = sessions[index]
        for account in accounts:
            account.portfolio.start_session(session.session_date)

        pair = pairs_by_decision.get(session.session_date)
        if pair is not None:
            prior_closes = sessions[index - 1].closes()
            for account in accounts:
                account.boundaries.append(account.portfolio.nav(prior_closes))
            if session.session_date == terminal_date:
                break

        todays_splits = splits_by_date.get(session.session_date, ())
        if todays_splits and any(
            account.pending is not None
            and account.pending.decision_date < session.session_date
            and session.session_date <= account.pending.settlement_date
            for account in accounts
        ):
            raise InputContractError("split between Phase A and Phase B fails closed")

        for account in accounts:
            _apply_actions(
                account.portfolio,
                distributions_by_date.get(session.session_date, ()),
                todays_splits,
            )
            if (
                account.pending is not None
                and account.pending.settlement_date == session.session_date
            ):
                _phase_b(account, session)

        if pair is not None:
            selected = select_symbol(pair)
            selected_history.append(selected)
            prior_closes = sessions[index - 1].closes()
            strategy_nav = accounts[0].boundaries[-1]
            fifty_nav = accounts[1].boundaries[-1]
            strategy_targets = {
                "SPY": (
                    math.floor(strategy_nav / prior_closes["SPY"])
                    if selected == "SPY"
                    else 0
                ),
                "QQQ": (
                    math.floor(strategy_nav / prior_closes["QQQ"])
                    if selected == "QQQ"
                    else 0
                ),
            }
            fifty_targets = {
                symbol: math.floor(0.5 * fifty_nav / prior_closes[symbol])
                for symbol in SYMBOLS
            }
            _phase_a(
                accounts[0],
                session,
                strategy_targets,
                session_dates,
            )
            _phase_a(
                accounts[1],
                session,
                fifty_targets,
                session_dates,
            )
            if len(accounts[2].boundaries) == 1:
                buyhold_nav = accounts[2].boundaries[-1]
                _phase_a(
                    accounts[2],
                    session,
                    {
                        "SPY": math.floor(buyhold_nav / prior_closes["SPY"]),
                        "QQQ": 0,
                    },
                    session_dates,
                )

        for account in accounts:
            account.daily_nav.append(
                (session.session_date, account.portfolio.nav(session.opens()))
            )

    if any(account.pending is not None for account in accounts):
        raise InputContractError("terminal boundary arrived before Phase B completed")
    performances = tuple(
        _performance(account, expected_intervals) for account in accounts
    )
    spy_count = selected_history.count("SPY")
    qqq_count = selected_history.count("QQQ")
    gate_values = _gate_values(
        observed_intervals=len(selected_history),
        expected_intervals=expected_intervals,
        spy_count=spy_count,
        qqq_count=qqq_count,
        strategy=performances[0],
        fifty_fifty=performances[1],
        spy_buyhold=performances[2],
    )
    gates = tuple(zip(GATE_NAMES, gate_values))
    return SegmentDecision(
        segment,
        expected_intervals,
        spy_count,
        qqq_count,
        performances[0],
        performances[1],
        performances[2],
        gates,
        all(value for _, value in gates),
    )


def _new_account(name: str) -> _Account:
    return _Account(
        name,
        Portfolio.us(
            INITIAL_CAPITAL,
            costs=TransactionCostModel(commission_rate=COMMISSION_RATE),
        ),
    )


def _gate_values(
    *,
    observed_intervals: int,
    expected_intervals: int,
    spy_count: int,
    qqq_count: int,
    strategy: Performance,
    fifty_fifty: Performance,
    spy_buyhold: Performance,
) -> tuple[bool, ...]:
    if (
        type(observed_intervals) is not int
        or type(expected_intervals) is not int
        or type(spy_count) is not int
        or type(qqq_count) is not int
        or not isinstance(strategy, Performance)
        or not isinstance(fifty_fifty, Performance)
        or not isinstance(spy_buyhold, Performance)
    ):
        raise InputContractError("gate inputs do not match the frozen contract")
    return (
        observed_intervals == expected_intervals,
        spy_count >= MINIMUM_STATE_INTERVALS,
        qqq_count >= MINIMUM_STATE_INTERVALS,
        strategy.terminal_wealth > fifty_fifty.terminal_wealth,
        strategy.arithmetic_mean_return > fifty_fifty.arithmetic_mean_return,
        strategy.maximum_drawdown >= spy_buyhold.maximum_drawdown,
    )


def _phase_a(
    account: _Account,
    session: MarketSession,
    targets: dict[str, int],
    accepted_session_dates: tuple[date, ...],
) -> None:
    if account.pending is not None:
        raise InputContractError("a new decision cannot overlap pending Phase B")
    _validate_targets(targets)
    current = _current_shares(account.portfolio)
    sale_required = any(current[symbol] > targets[symbol] for symbol in SYMBOLS)
    if sale_required:
        settlement_path = settlement_sessions(
            session.session_date,
            accepted_session_dates,
        )
        for symbol in SELL_ORDER:
            excess = current[symbol] - targets[symbol]
            if excess > 0:
                trade = account.portfolio.sell(
                    symbol,
                    excess,
                    session.opens()[symbol],
                    session.session_date,
                    settlement_date=settlement_path[-1],
                    accepted_settlement_sessions=settlement_path,
                )
                _record_trade(account, "A", trade)
        remaining = _current_shares(account.portfolio)
        if any(remaining[symbol] < targets[symbol] for symbol in SYMBOLS):
            account.pending = _PendingPhaseB(
                session.session_date,
                settlement_path[-1],
                tuple((symbol, targets[symbol]) for symbol in SYMBOLS),
            )
        return
    _buy_deficits(account, session, targets, phase="A")


def _phase_b(account: _Account, session: MarketSession) -> None:
    pending = account.pending
    if pending is None or pending.settlement_date != session.session_date:
        raise InputContractError("Phase B must occur on its frozen settlement session")
    _buy_deficits(account, session, pending.as_dict(), phase="B")
    account.pending = None


def _buy_deficits(
    account: _Account,
    session: MarketSession,
    targets: dict[str, int],
    *,
    phase: str,
) -> None:
    current = _current_shares(account.portfolio)
    prices = session.opens()
    for symbol in BUY_ORDER:
        deficit = targets[symbol] - current[symbol]
        if deficit <= 0:
            continue
        affordable = math.floor(
            (account.portfolio.available_cash + 1e-9)
            / (prices[symbol] * (1.0 + COMMISSION_RATE))
        )
        shares = min(deficit, affordable)
        if shares <= 0:
            continue
        trade = account.portfolio.buy(
            symbol,
            shares,
            prices[symbol],
            session.session_date,
        )
        _record_trade(account, phase, trade)
        current[symbol] += shares


def _apply_actions(
    portfolio: Portfolio,
    distributions: tuple[Distribution, ...],
    splits: tuple[Split, ...],
) -> None:
    for event in distributions:
        portfolio.apply_cash_distribution(
            event.symbol,
            event_id=event.event_id,
            amount_per_share=event.amount_per_share,
            ex_date=event.ex_date,
            pay_date=event.pay_date,
        )
    for event in splits:
        portfolio.apply_split(
            event.symbol,
            event.ratio,
            event_id=event.event_id,
        )


def _record_trade(account: _Account, phase: str, trade: Trade) -> None:
    account.trades.append(
        TradeAudit(
            phase,
            trade.symbol,
            trade.side,
            trade.trade_date,
            int(trade.shares),
            trade.price,
            trade.costs.commission,
        )
    )


def _performance(account: _Account, expected_intervals: int) -> Performance:
    if len(account.boundaries) != expected_intervals + 1:
        raise InputContractError("pre-trade boundary count is not frozen")
    interval_returns = tuple(
        later / earlier - 1.0
        for earlier, later in zip(account.boundaries, account.boundaries[1:])
    )
    if len(interval_returns) != expected_intervals:
        raise InputContractError("interval return count is not frozen")
    if any(not math.isfinite(item) for item in interval_returns):
        raise InputContractError("interval returns must be finite")
    path = (INITIAL_CAPITAL,) + tuple(value for _, value in account.daily_nav)
    peak = path[0]
    maximum_drawdown = 0.0
    for value in path:
        _require_positive(value, "daily opening NAV")
        peak = max(peak, value)
        maximum_drawdown = min(maximum_drawdown, value / peak - 1.0)
    return Performance(
        account.boundaries[-1],
        statistics.fmean(interval_returns),
        maximum_drawdown,
        interval_returns,
        tuple(account.boundaries),
        tuple(account.daily_nav),
        tuple(account.trades),
    )


def _current_shares(portfolio: Portfolio) -> dict[str, int]:
    output: dict[str, int] = {}
    for symbol in SYMBOLS:
        position = portfolio.positions.get(symbol)
        shares = 0.0 if position is None else position.shares
        if not math.isfinite(shares) or shares < 0 or not shares.is_integer():
            raise InputContractError("portfolio shares must be nonnegative whole shares")
        output[symbol] = int(shares)
    return output


def _validate_pairs(pairs: tuple[FlowPair, ...], expected_intervals: int) -> None:
    if type(pairs) is not tuple or len(pairs) != expected_intervals + 1:
        raise InputContractError(
            f"segment requires exactly {expected_intervals + 1} flow pairs"
        )
    if any(not isinstance(pair, FlowPair) for pair in pairs):
        raise InputContractError("flow pairs have invalid types")
    report_dates = tuple(pair.report_date for pair in pairs)
    if report_dates != tuple(sorted(report_dates)):
        raise InputContractError("flow pairs must be sorted")
    if len(set(report_dates)) != len(report_dates):
        raise InputContractError("flow pair report dates must be unique")
    if len({pair.pair_sha256 for pair in pairs}) != len(pairs):
        raise InputContractError("flow pair hashes must be unique")


def _validate_sessions(sessions: tuple[MarketSession, ...]) -> None:
    if type(sessions) is not tuple or len(sessions) < 2:
        raise InputContractError("sessions must be a tuple with coverage")
    if any(not isinstance(session, MarketSession) for session in sessions):
        raise InputContractError("sessions have invalid types")
    dates = tuple(session.session_date for session in sessions)
    if dates != tuple(sorted(dates)):
        raise InputContractError("sessions must be sorted")
    if len(set(dates)) != len(dates):
        raise InputContractError("session dates must be unique")


def _validate_actions(
    distributions: tuple[Distribution, ...],
    splits: tuple[Split, ...],
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


def _validate_targets(targets: dict[str, int]) -> None:
    if set(targets) != set(SYMBOLS):
        raise InputContractError("targets must contain exactly SPY and QQQ")
    if any(type(value) is not int or value < 0 for value in targets.values()):
        raise InputContractError("target shares must be nonnegative integers")


def _group_distributions(
    events: tuple[Distribution, ...],
) -> dict[date, tuple[Distribution, ...]]:
    output: dict[date, list[Distribution]] = {}
    for event in events:
        output.setdefault(event.ex_date, []).append(event)
    return {key: tuple(value) for key, value in output.items()}


def _group_splits(events: tuple[Split, ...]) -> dict[date, tuple[Split, ...]]:
    output: dict[date, list[Split]] = {}
    for event in events:
        output.setdefault(event.effective_date, []).append(event)
    return {key: tuple(value) for key, value in output.items()}


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
        or value <= 0
    ):
        raise InputContractError(f"{label} must be finite and positive")
    return float(value)


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


def _require_symbol(value: object) -> str:
    if value not in SYMBOLS:
        raise InputContractError("symbol must be SPY or QQQ")
    return str(value)
