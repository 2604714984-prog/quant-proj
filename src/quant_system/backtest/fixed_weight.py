"""Clean-room fixed-weight backtest arithmetic over gross return factors."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
import math
from numbers import Real


@dataclass(frozen=True)
class GrossFactorRow:
    """One symbol's gross return factor for one accepted session."""

    session_date: date
    symbol: str
    gross_factor: float


@dataclass(frozen=True)
class FixedWeightSession:
    """Deterministic audit record for one portfolio return observation."""

    session_date: date
    session_index: int
    start_weights: tuple[tuple[str, float], ...]
    portfolio_gross_factor: float
    drifted_weights: tuple[tuple[str, float], ...]
    turnover: float
    cost_fraction: float
    net_factor: float
    end_weights: tuple[tuple[str, float], ...]
    wealth: float
    rebalanced: bool


@dataclass(frozen=True)
class FixedWeightResult:
    """Immutable result of a fixed-weight or buy-and-hold simulation."""

    target_weights: tuple[tuple[str, float], ...]
    rebalance_interval: int | None
    cost_bps: float
    sessions: tuple[FixedWeightSession, ...]
    final_wealth: float
    final_weights: tuple[tuple[str, float], ...]


def run_fixed_weight_backtest(
    rows: Sequence[GrossFactorRow],
    target_weights: Mapping[str, float],
    *,
    rebalance_interval: int | None = 63,
    cost_bps: float = 0.0,
) -> FixedWeightResult:
    """Apply close-to-close gross factors using the frozen 63-session contract.

    Session ``j`` first applies its asset factors to the weights effective at
    the start of the session.  When ``j`` is a rebalance boundary, turnover and
    multiplicative cost are computed from the resulting drifted weights before
    target weights become effective for session ``j + 1``.  ``None`` disables
    rebalancing and therefore implements the frozen buy-and-hold comparator.
    """

    targets = _validated_targets(target_weights)
    interval = _validated_interval(rebalance_interval)
    normalized_cost_bps = _validated_cost(cost_bps)
    symbols = tuple(symbol for symbol, _ in targets)
    sessions = _validated_sessions(rows, symbols)

    weights = targets
    wealth = 1.0
    audit: list[FixedWeightSession] = []
    for session_index, (session_date, factors) in enumerate(sessions, start=1):
        start_weights = weights
        numerators = tuple(
            (symbol, _finite(weight * factors[symbol], "weighted gross factor"))
            for symbol, weight in start_weights
        )
        portfolio_factor = _finite_sum(
            (value for _, value in numerators),
            "portfolio gross factor",
        )
        if portfolio_factor <= 0.0:
            raise ValueError("portfolio gross factor must be positive")
        drifted = tuple(
            (symbol, _finite(value / portfolio_factor, "drifted weight"))
            for symbol, value in numerators
        )
        wealth_after_return = _finite(
            wealth * portfolio_factor,
            "wealth after return",
        )

        rebalanced = interval is not None and session_index % interval == 0
        turnover = 0.0
        cost_fraction = 0.0
        end_weights = drifted
        if rebalanced:
            target_by_symbol = dict(targets)
            turnover = _finite_sum(
                (
                    abs(target_by_symbol[symbol] - weight)
                    for symbol, weight in drifted
                ),
                "turnover",
            )
            cost_fraction = _finite(
                normalized_cost_bps / 10_000.0 * turnover,
                "cost fraction",
            )
            if cost_fraction < 0.0 or cost_fraction >= 1.0:
                raise ValueError("cost fraction must be in [0, 1)")
            end_weights = targets

        net_factor = _finite(
            portfolio_factor * (1.0 - cost_fraction),
            "net factor",
        )
        if net_factor <= 0.0:
            raise ValueError("net factor must be positive")
        wealth = _finite(wealth_after_return * (1.0 - cost_fraction), "wealth")
        if wealth <= 0.0:
            raise ValueError("wealth must remain positive")
        audit.append(
            FixedWeightSession(
                session_date=session_date,
                session_index=session_index,
                start_weights=start_weights,
                portfolio_gross_factor=portfolio_factor,
                drifted_weights=drifted,
                turnover=turnover,
                cost_fraction=cost_fraction,
                net_factor=net_factor,
                end_weights=end_weights,
                wealth=wealth,
                rebalanced=rebalanced,
            )
        )
        weights = end_weights

    return FixedWeightResult(
        target_weights=targets,
        rebalance_interval=interval,
        cost_bps=normalized_cost_bps,
        sessions=tuple(audit),
        final_wealth=wealth,
        final_weights=weights,
    )


def _validated_targets(weights: Mapping[str, float]) -> tuple[tuple[str, float], ...]:
    if not isinstance(weights, Mapping) or not weights:
        raise ValueError("target_weights must be a nonempty mapping")
    normalized: list[tuple[str, float]] = []
    for symbol, weight in weights.items():
        if not isinstance(symbol, str) or not symbol or symbol != symbol.strip():
            raise ValueError("target weight symbols must be nonempty trimmed text")
        value = _number(weight, f"target weight for {symbol}")
        if value <= 0.0:
            raise ValueError("target weights must be strictly positive")
        normalized.append((symbol, value))
    normalized.sort(key=lambda item: item[0])
    total = _finite_sum((weight for _, weight in normalized), "target weight sum")
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("target weights must sum to one")
    return tuple(normalized)


def _validated_interval(value: int | None) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value <= 0:
        raise ValueError("rebalance_interval must be a positive integer or None")
    return value


def _validated_cost(value: float) -> float:
    normalized = _number(value, "cost_bps")
    if normalized < 0.0 or normalized >= 10_000.0:
        raise ValueError("cost_bps must be in [0, 10000)")
    return normalized


def _validated_sessions(
    rows: Sequence[GrossFactorRow],
    symbols: tuple[str, ...],
) -> tuple[tuple[date, dict[str, float]], ...]:
    frozen = tuple(rows)
    if not frozen:
        raise ValueError("at least one gross-factor row is required")

    sessions: list[tuple[date, dict[str, float]]] = []
    current_date: date | None = None
    current_symbols: list[str] = []
    current_factors: dict[str, float] = {}
    for row in frozen:
        if not isinstance(row, GrossFactorRow):
            raise TypeError("rows must contain GrossFactorRow values")
        if type(row.session_date) is not date:
            raise ValueError("session_date must be a date, not a datetime")
        if not isinstance(row.symbol, str) or not row.symbol or row.symbol != row.symbol.strip():
            raise ValueError("row symbol must be nonempty trimmed text")
        factor = _number(row.gross_factor, "gross_factor")
        if factor <= 0.0:
            raise ValueError("gross_factor must be positive")

        if current_date is None:
            current_date = row.session_date
        elif row.session_date != current_date:
            _append_session(
                sessions,
                current_date,
                current_symbols,
                current_factors,
                symbols,
            )
            if row.session_date <= current_date:
                raise ValueError("session dates must be strictly increasing and contiguous")
            current_date = row.session_date
            current_symbols = []
            current_factors = {}

        if row.symbol in current_factors:
            raise ValueError("duplicate symbol within a session")
        current_symbols.append(row.symbol)
        current_factors[row.symbol] = factor

    assert current_date is not None
    _append_session(
        sessions,
        current_date,
        current_symbols,
        current_factors,
        symbols,
    )
    return tuple(sessions)


def _append_session(
    sessions: list[tuple[date, dict[str, float]]],
    session_date: date,
    observed_symbols: list[str],
    factors: dict[str, float],
    expected_symbols: tuple[str, ...],
) -> None:
    observed = tuple(observed_symbols)
    observed_set = set(observed)
    expected_set = set(expected_symbols)
    if observed_set != expected_set:
        missing = sorted(expected_set - observed_set)
        unexpected = sorted(observed_set - expected_set)
        raise ValueError(
            f"session symbols do not match targets; missing={missing}, unexpected={unexpected}"
        )
    if observed != expected_symbols:
        raise ValueError("symbols within each session must be strictly sorted and unique")
    sessions.append((session_date, dict(factors)))


def _number(value: object, name: str) -> float:
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


def _finite_sum(values: Iterable[float], name: str) -> float:
    try:
        result = math.fsum(values)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite") from exc
    return _finite(result, name)
