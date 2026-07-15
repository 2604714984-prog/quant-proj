"""Small deterministic monthly dual-momentum and open/close backtest primitives."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
import math
from numbers import Integral, Real


@dataclass(frozen=True)
class OpenCloseBar:
    """One accepted common-session open/close observation."""

    session_date: date
    symbol: str
    open_price: float
    close_price: float


@dataclass(frozen=True)
class MonthlyTarget:
    """Target weights decided at one close and executable at the next open."""

    decision_date: date
    execution_date: date
    weights: tuple[tuple[str, float], ...]
    selected_symbols: tuple[str, ...]
    momentum_by_symbol: tuple[tuple[str, float], ...]
    volatility_by_symbol: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class AllocationSession:
    """One close-to-close audit row, including any trade at the session open."""

    session_date: date
    net_factor: float
    wealth: float
    overnight_factor: float
    intraday_factor: float
    turnover: float
    cost_fraction: float
    rebalanced: bool
    decision_date: date | None
    close_weights: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class MonthlyAllocationResult:
    """Immutable result from a target schedule and a common-session panel."""

    targets: tuple[MonthlyTarget, ...]
    sessions: tuple[AllocationSession, ...]
    final_wealth: float


def build_dual_momentum_targets(
    rows: Sequence[OpenCloseBar],
    risky_symbols: Sequence[str],
    cash_like_symbol: str,
    *,
    lookback_sessions: int = 252,
    skip_sessions: int = 21,
    volatility_sessions: int = 60,
    top_count: int = 2,
    single_risky_cap: float = 0.6,
) -> tuple[MonthlyTarget, ...]:
    """Create month-end targets using the frozen 12-1 and inverse-volatility rules.

    Ties retain ``risky_symbols`` order. Volatility is sample standard deviation
    (``ddof=1``) over the latest 60 common-session close returns ending at the
    decision close. Inverse-volatility weights are clipped directly at the cap
    without redistribution; the remainder goes to the cash-like symbol.
    """

    risky = _symbols(risky_symbols, name="risky_symbols")
    cash = _symbol(cash_like_symbol, name="cash_like_symbol")
    if cash in risky:
        raise ValueError("cash_like_symbol must not also be risky")
    all_symbols = tuple(sorted((*risky, cash)))
    panel = _validated_panel(rows, all_symbols)
    lookback = _integer(lookback_sessions, name="lookback_sessions", minimum=2)
    skip = _integer(skip_sessions, name="skip_sessions", minimum=1)
    volatility_window = _integer(
        volatility_sessions,
        name="volatility_sessions",
        minimum=2,
    )
    count = _integer(top_count, name="top_count", minimum=1)
    cap = _number(single_risky_cap, name="single_risky_cap")
    if lookback <= skip:
        raise ValueError("lookback_sessions must exceed skip_sessions")
    if count > len(risky):
        raise ValueError("top_count cannot exceed the risky universe")
    if not 0.0 < cap <= 1.0:
        raise ValueError("single_risky_cap must be in (0, 1]")
    first_decision = max(lookback, volatility_window)
    if len(panel) <= first_decision + 1:
        raise ValueError("panel is too short for a decision and next-open execution")

    risky_order = {symbol: index for index, symbol in enumerate(risky)}
    targets: list[MonthlyTarget] = []
    for index in range(first_decision, len(panel) - 1):
        session_date = panel[index][0]
        next_date = panel[index + 1][0]
        if (session_date.year, session_date.month) == (next_date.year, next_date.month):
            continue
        momenta = {
            symbol: _finite(
                panel[index - skip][1][symbol][1]
                / panel[index - lookback][1][symbol][1]
                - 1.0,
                "momentum",
            )
            for symbol in (*risky, cash)
        }
        cash_momentum = momenta[cash]
        eligible = tuple(
            symbol
            for symbol in risky
            if momenta[symbol] > 0.0 and momenta[symbol] > cash_momentum
        )
        selected = tuple(
            sorted(
                eligible,
                key=lambda symbol: (-momenta[symbol], risky_order[symbol]),
            )[:count]
        )

        volatilities: dict[str, float] = {}
        for symbol in selected:
            returns = tuple(
                panel[offset][1][symbol][1] / panel[offset - 1][1][symbol][1] - 1.0
                for offset in range(index - volatility_window + 1, index + 1)
            )
            volatility = _sample_standard_deviation(returns)
            if volatility <= 0.0:
                raise ValueError("selected risky volatility must be strictly positive")
            volatilities[symbol] = volatility

        target_by_symbol = {symbol: 0.0 for symbol in all_symbols}
        if selected:
            inverse = {symbol: 1.0 / volatilities[symbol] for symbol in selected}
            inverse_total = math.fsum(inverse.values())
            for symbol in selected:
                target_by_symbol[symbol] = min(inverse[symbol] / inverse_total, cap)
        risky_total = math.fsum(target_by_symbol[symbol] for symbol in risky)
        target_by_symbol[cash] = _finite(1.0 - risky_total, "cash-like target weight")
        targets.append(
            MonthlyTarget(
                decision_date=session_date,
                execution_date=next_date,
                weights=_validated_weights(target_by_symbol, all_symbols),
                selected_symbols=selected,
                momentum_by_symbol=tuple((symbol, momenta[symbol]) for symbol in (*risky, cash)),
                volatility_by_symbol=tuple(
                    (symbol, volatilities[symbol]) for symbol in selected
                ),
            )
        )
    if not targets:
        raise ValueError("panel produced no executable monthly targets")
    return tuple(targets)


def build_static_targets(
    schedule: Sequence[MonthlyTarget],
    target_weights: Mapping[str, float],
) -> tuple[MonthlyTarget, ...]:
    """Copy a decision/execution schedule with one fixed comparator allocation."""

    frozen_schedule = tuple(schedule)
    if not frozen_schedule:
        raise ValueError("schedule must be nonempty")
    expected_symbols = tuple(symbol for symbol, _ in frozen_schedule[0].weights)
    weights = _validated_weights(target_weights, expected_symbols)
    selected = tuple(symbol for symbol, weight in weights if weight > 0.0)
    return tuple(
        MonthlyTarget(
            decision_date=item.decision_date,
            execution_date=item.execution_date,
            weights=weights,
            selected_symbols=selected,
            momentum_by_symbol=(),
            volatility_by_symbol=(),
        )
        for item in frozen_schedule
    )


def run_monthly_open_close_backtest(
    rows: Sequence[OpenCloseBar],
    targets: Sequence[MonthlyTarget],
    *,
    cash_like_symbol: str,
    cost_bps_per_turnover_side: float,
    initial_close_date: date | None = None,
) -> MonthlyAllocationResult:
    """Apply targets at next-session opens and drift holdings between rebalances.

    The initial state is 100% in the cash-like ETF at the close preceding the
    first execution. Each daily factor includes old holdings' overnight return,
    full-L1 turnover cost at the open, and new holdings' intraday return.
    """

    frozen_targets = tuple(targets)
    if not frozen_targets:
        raise ValueError("targets must be nonempty")
    cash = _symbol(cash_like_symbol, name="cash_like_symbol")
    symbols = tuple(symbol for symbol, _ in frozen_targets[0].weights)
    if cash not in symbols:
        raise ValueError("cash_like_symbol is missing from target weights")
    panel = _validated_panel(rows, symbols)
    cost_bps = _number(cost_bps_per_turnover_side, name="cost_bps_per_turnover_side")
    if cost_bps < 0.0 or cost_bps >= 10_000.0:
        raise ValueError("cost_bps_per_turnover_side must be in [0, 10000)")

    date_to_index = {session_date: index for index, (session_date, _) in enumerate(panel)}
    target_by_execution: dict[date, MonthlyTarget] = {}
    previous_execution: date | None = None
    for target in frozen_targets:
        if not isinstance(target, MonthlyTarget):
            raise TypeError("targets must contain MonthlyTarget values")
        _validated_weights(dict(target.weights), symbols)
        if target.execution_date in target_by_execution:
            raise ValueError("duplicate execution date")
        if previous_execution is not None and target.execution_date <= previous_execution:
            raise ValueError("execution dates must be strictly increasing")
        previous_execution = target.execution_date
        execution_index = date_to_index.get(target.execution_date)
        decision_index = date_to_index.get(target.decision_date)
        if execution_index is None or decision_index is None or execution_index != decision_index + 1:
            raise ValueError("each target must execute on the session immediately after decision")
        target_by_execution[target.execution_date] = target

    first_execution_index = date_to_index[frozen_targets[0].execution_date]
    if initial_close_date is None:
        first_index = first_execution_index
    else:
        if type(initial_close_date) is not date or initial_close_date not in date_to_index:
            raise ValueError("initial_close_date must be an accepted common-session date")
        anchor_index = date_to_index[initial_close_date]
        if anchor_index >= first_execution_index:
            raise ValueError("initial_close_date must precede first target execution")
        first_index = anchor_index + 1
    if first_index == 0:
        raise ValueError("return ledger needs a preceding close")
    close_weights = {symbol: (1.0 if symbol == cash else 0.0) for symbol in symbols}
    wealth = 1.0
    audit: list[AllocationSession] = []
    for index in range(first_index, len(panel)):
        session_date, prices = panel[index]
        previous_prices = panel[index - 1][1]
        overnight_numerators = {
            symbol: close_weights[symbol]
            * prices[symbol][0]
            / previous_prices[symbol][1]
            for symbol in symbols
        }
        overnight_factor = _positive_sum(overnight_numerators.values(), "overnight factor")
        open_weights = {
            symbol: overnight_numerators[symbol] / overnight_factor for symbol in symbols
        }

        target = target_by_execution.get(session_date)
        turnover = 0.0
        cost_fraction = 0.0
        trade_weights = open_weights
        if target is not None:
            target_weights = dict(target.weights)
            turnover = _finite(
                math.fsum(abs(target_weights[symbol] - open_weights[symbol]) for symbol in symbols),
                "turnover",
            )
            cost_fraction = _finite(cost_bps / 10_000.0 * turnover, "cost fraction")
            if cost_fraction < 0.0 or cost_fraction >= 1.0:
                raise ValueError("cost fraction must be in [0, 1)")
            trade_weights = target_weights

        intraday_numerators = {
            symbol: trade_weights[symbol] * prices[symbol][1] / prices[symbol][0]
            for symbol in symbols
        }
        intraday_factor = _positive_sum(intraday_numerators.values(), "intraday factor")
        close_weights = {
            symbol: intraday_numerators[symbol] / intraday_factor for symbol in symbols
        }
        net_factor = _finite(
            overnight_factor * (1.0 - cost_fraction) * intraday_factor,
            "net factor",
        )
        if net_factor <= 0.0:
            raise ValueError("net factor must be positive")
        wealth = _finite(wealth * net_factor, "wealth")
        if wealth <= 0.0:
            raise ValueError("wealth must remain positive")
        audit.append(
            AllocationSession(
                session_date=session_date,
                net_factor=net_factor,
                wealth=wealth,
                overnight_factor=overnight_factor,
                intraday_factor=intraday_factor,
                turnover=turnover,
                cost_fraction=cost_fraction,
                rebalanced=target is not None,
                decision_date=None if target is None else target.decision_date,
                close_weights=tuple((symbol, close_weights[symbol]) for symbol in symbols),
            )
        )
    return MonthlyAllocationResult(
        targets=frozen_targets,
        sessions=tuple(audit),
        final_wealth=wealth,
    )


def _validated_panel(
    rows: Sequence[OpenCloseBar],
    expected_symbols: tuple[str, ...],
) -> tuple[tuple[date, dict[str, tuple[float, float]]], ...]:
    frozen = tuple(rows)
    if not frozen:
        raise ValueError("rows must be nonempty")
    expected = tuple(sorted(expected_symbols))
    if expected != expected_symbols or len(set(expected)) != len(expected):
        raise ValueError("expected symbols must be sorted and unique")
    grouped: list[tuple[date, dict[str, tuple[float, float]]]] = []
    current_date: date | None = None
    current: dict[str, tuple[float, float]] = {}
    observed_order: list[str] = []
    for row in frozen:
        if not isinstance(row, OpenCloseBar):
            raise TypeError("rows must contain OpenCloseBar values")
        if type(row.session_date) is not date:
            raise ValueError("session_date must be a date")
        symbol = _symbol(row.symbol, name="row symbol")
        open_price = _number(row.open_price, name="open_price")
        close_price = _number(row.close_price, name="close_price")
        if open_price <= 0.0 or close_price <= 0.0:
            raise ValueError("open_price and close_price must be positive")
        if current_date is None:
            current_date = row.session_date
        elif row.session_date != current_date:
            _append_panel_session(grouped, current_date, current, observed_order, expected)
            if row.session_date <= current_date:
                raise ValueError("session dates must be strictly increasing")
            current_date = row.session_date
            current = {}
            observed_order = []
        if symbol in current:
            raise ValueError("duplicate symbol within a session")
        current[symbol] = (open_price, close_price)
        observed_order.append(symbol)
    assert current_date is not None
    _append_panel_session(grouped, current_date, current, observed_order, expected)
    return tuple(grouped)


def _append_panel_session(
    grouped: list[tuple[date, dict[str, tuple[float, float]]]],
    session_date: date,
    values: dict[str, tuple[float, float]],
    observed_order: list[str],
    expected: tuple[str, ...],
) -> None:
    if tuple(observed_order) != expected:
        missing = sorted(set(expected) - set(values))
        unexpected = sorted(set(values) - set(expected))
        raise ValueError(
            "session symbols must equal the sorted common panel; "
            f"missing={missing}, unexpected={unexpected}"
        )
    grouped.append((session_date, dict(values)))


def _validated_weights(
    weights: Mapping[str, float],
    expected_symbols: tuple[str, ...],
) -> tuple[tuple[str, float], ...]:
    if not isinstance(weights, Mapping):
        raise ValueError("weights must be a mapping")
    if set(weights) != set(expected_symbols):
        raise ValueError("weights must contain exactly the common-panel symbols")
    normalized = tuple(
        (symbol, _number(weights[symbol], name=f"weight for {symbol}"))
        for symbol in expected_symbols
    )
    if any(value < 0.0 or value > 1.0 for _, value in normalized):
        raise ValueError("weights must be in [0, 1]")
    if not math.isclose(
        math.fsum(value for _, value in normalized),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("weights must sum to one")
    return normalized


def _symbols(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    frozen = tuple(_symbol(value, name=name) for value in values)
    if not frozen or len(set(frozen)) != len(frozen):
        raise ValueError(f"{name} must be nonempty and unique")
    return frozen


def _symbol(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be nonempty trimmed text")
    return value


def _integer(value: object, *, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer >= {minimum}")
    normalized = int(value)
    if normalized < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return normalized


def _number(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{name} must be a finite number")
    return normalized


def _finite(value: float, name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _positive_sum(values: Iterable[float], name: str) -> float:
    try:
        result = math.fsum(values)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be finite and positive") from exc
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return result


def _sample_standard_deviation(values: Sequence[float]) -> float:
    frozen = tuple(_number(value, name="return") for value in values)
    if len(frozen) < 2:
        raise ValueError("sample standard deviation needs at least two values")
    mean = math.fsum(frozen) / len(frozen)
    variance = math.fsum((value - mean) ** 2 for value in frozen) / (len(frozen) - 1)
    return _finite(math.sqrt(variance), "sample standard deviation")


__all__ = [
    "AllocationSession",
    "MonthlyAllocationResult",
    "MonthlyTarget",
    "OpenCloseBar",
    "build_dual_momentum_targets",
    "build_static_targets",
    "run_monthly_open_close_backtest",
]
