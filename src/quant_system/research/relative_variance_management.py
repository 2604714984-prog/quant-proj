from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math
from numbers import Real
from statistics import median, stdev

import numpy as np

RESEARCH_ID = "A_SHARE_RELATIVE_VARIANCE_MANAGED_LIQUID_EQUITY_V1_20260718"
DEFINITION_SHA256 = "e3d80a6d1febb8f88cfb2f341ddb0cb4b3e27ae7708d719df2c5229c7713219e"
SNAPSHOT_ID = "a_share_qfq_personal_research_20260716_v5"
SNAPSHOT_DIGEST = "da6160ddad3f5fcb21151dd0d3128ea7786be2a2014872a14f85635e783dba6b"
DATABASE_SHA256 = "e636bb80e300f89e46831e91275c6f2167e370e81a00b21b300e253f6107bee0"
SNAPSHOT_RECEIPT_FILENAME = "a_share_volume_unit_shares_v5_20260717.json"
SNAPSHOT_RECEIPT_SHA256 = "241be32158b9ab5cebbe92dfceeec2a889f3b56e681a1f764d7b6d257f21f17f"
CALENDAR_SNAPSHOT_ID = "akshare_sina_calendar_1d5ff82a6718fc4e19b95c98"
CALENDAR_DIGEST = "ea7557ee994893ab6719a20ef0de10c60c5087e8637c0771f11c1e6ddc4cee71"
CLASSIFICATION = "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT"
BOARD_LABELS = ("Main", "ChiNext", "STAR")
BASKET_SIZE, CLOSE_SESSIONS, RETURN_COUNT = 30, 274, 273
BASELINE_DAYS, CURRENT_DAYS = 252, 21
BOOTSTRAP_BLOCK_MONTHS = 3
HISTORICAL_INITIAL_CASH_CNY = 400_000.0
LOT_SIZE_SHARES = 100
COMMISSION_RATE = 0.0003
MINIMUM_COMMISSION_CNY = 5.0
CAPACITY_FRACTION = 0.01


class RelativeVarianceContractError(ValueError):
    pass


def _finite(value: object, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise RelativeVarianceContractError(f"{label} must be finite numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or (positive and parsed <= 0):
        raise RelativeVarianceContractError(f"{label} must be finite numeric")
    return parsed


@dataclass(frozen=True)
class QualifiedStock:
    symbol: str
    board: str
    accepted_session_count: int
    trailing_amounts_cny: tuple[float, ...]
    qfq_closes: tuple[float, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol or self.board not in BOARD_LABELS:
            raise RelativeVarianceContractError("stock identity or board is invalid")
        if (
            type(self.accepted_session_count) is not int
            or self.accepted_session_count < CLOSE_SESSIONS
        ):
            raise RelativeVarianceContractError("listing history is shorter than 274 sessions")
        if len(self.trailing_amounts_cny) != 20 or any(
            _finite(value, "amount") < 0 for value in self.trailing_amounts_cny
        ):
            raise RelativeVarianceContractError("exact finite 20-session amount window required")
        if len(self.qfq_closes) != CLOSE_SESSIONS:
            raise RelativeVarianceContractError("exactly 274 qfq closes are required")
        for value in self.qfq_closes:
            _finite(value, "qfq close", positive=True)

    @property
    def median_amount_cny(self) -> float:
        return float(median(self.trailing_amounts_cny))


@dataclass(frozen=True)
class CapitalFormationRow:
    symbol: str
    raw_open: float
    prior_volume_shares: float
    prior_amount_cny: float
    is_suspended: bool
    is_st: bool
    up_limit: float
    down_limit: float
    list_status: str

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol:
            raise RelativeVarianceContractError("capital row symbol is invalid")
        for value, label in (
            (self.raw_open, "raw open"),
            (self.up_limit, "up limit"),
            (self.down_limit, "down limit"),
        ):
            _finite(value, label, positive=True)
        volume = _finite(self.prior_volume_shares, "prior volume")
        if volume < 0 or not math.isclose(volume, round(volume), abs_tol=1e-6):
            raise RelativeVarianceContractError("prior volume must be nonnegative whole shares")
        if _finite(self.prior_amount_cny, "prior amount") < 0:
            raise RelativeVarianceContractError("prior amount must be nonnegative")
        if type(self.is_suspended) is not bool or type(self.is_st) is not bool:
            raise RelativeVarianceContractError("capital row status flags must be boolean")
        if not isinstance(self.list_status, str) or not self.list_status:
            raise RelativeVarianceContractError("capital row list status is invalid")


@dataclass(frozen=True)
class CapitalPathAudit:
    minimum_faithful_capital_cny: float
    target_nonzero_positions: int
    filled_positions: int
    invested_ratio: float
    total_commission_drag_bps: float
    minimum_commission_drag_bps: float
    capacity_rejection_count: int
    market_rule_rejection_count: int

    def __post_init__(self) -> None:
        faithful = _finite(
            self.minimum_faithful_capital_cny,
            "minimum faithful capital",
            positive=True,
        )
        invested = _finite(self.invested_ratio, "invested ratio")
        total_drag = _finite(self.total_commission_drag_bps, "commission drag")
        minimum_drag = _finite(
            self.minimum_commission_drag_bps, "minimum commission drag"
        )
        counts = (
            self.target_nonzero_positions,
            self.filled_positions,
            self.capacity_rejection_count,
            self.market_rule_rejection_count,
        )
        if (
            faithful <= 0
            or not 0 <= invested <= 1
            or total_drag < 0
            or minimum_drag < 0
            or minimum_drag > total_drag + 1e-12
            or any(type(value) is not int or not 0 <= value <= BASKET_SIZE for value in counts)
            or self.filled_positions > self.target_nonzero_positions
            or self.filled_positions
            + self.capacity_rejection_count
            + self.market_rule_rejection_count
            > self.target_nonzero_positions
        ):
            raise RelativeVarianceContractError("capital path audit is invalid")


@dataclass(frozen=True)
class CapitalIntervalAudit:
    intended_exposure: float
    managed: CapitalPathAudit
    comparator: CapitalPathAudit
    gate_pass: bool

    def __post_init__(self) -> None:
        exposure = _finite(self.intended_exposure, "intended exposure", positive=True)
        if (
            exposure > 1
            or not isinstance(self.managed, CapitalPathAudit)
            or not isinstance(self.comparator, CapitalPathAudit)
            or type(self.gate_pass) is not bool
        ):
            raise RelativeVarianceContractError("capital interval audit is invalid")


def _capital_path(
    rows: tuple[CapitalFormationRow, ...], total_exposure: float
) -> CapitalPathAudit:
    exposure = _finite(total_exposure, "capital path exposure", positive=True)
    if exposure > 1:
        raise RelativeVarianceContractError("capital path exposure cannot exceed one")
    target_weight = exposure / BASKET_SIZE
    cash = HISTORICAL_INITIAL_CASH_CNY
    faithful = gross_total = commission_total = minimum_excess = 0.0
    target_nonzero = filled_positions = capacity_rejections = market_rejections = 0
    for row in rows:
        price = float(row.raw_open)
        faithful = max(faithful, LOT_SIZE_SHARES * price / target_weight)
        requested = (
            math.floor(
                HISTORICAL_INITIAL_CASH_CNY
                * target_weight
                / price
                / LOT_SIZE_SHARES
            )
            * LOT_SIZE_SHARES
        )
        if requested <= 0:
            continue
        target_nonzero += 1
        market_rejected = (
            row.list_status != "L"
            or row.is_st
            or row.is_suspended
            or row.down_limit > row.up_limit
            or price < row.down_limit - 0.001
            or price > row.up_limit + 0.001
            or math.isclose(price, row.up_limit, rel_tol=1e-6, abs_tol=0.001)
        )
        if market_rejected:
            market_rejections += 1
            continue
        capacity_rejected = (
            requested > CAPACITY_FRACTION * row.prior_volume_shares
            or requested * price > CAPACITY_FRACTION * row.prior_amount_cny
        )
        if capacity_rejected:
            capacity_rejections += 1
            continue
        affordable = (
            math.floor(
                max(0.0, cash - MINIMUM_COMMISSION_CNY)
                / (1.0 + COMMISSION_RATE)
                / price
                / LOT_SIZE_SHARES
            )
            * LOT_SIZE_SHARES
        )
        filled = min(requested, affordable)
        if filled <= 0:
            continue
        gross = filled * price
        commission = max(MINIMUM_COMMISSION_CNY, COMMISSION_RATE * gross)
        cash -= gross + commission
        if cash < -1e-6:
            raise RelativeVarianceContractError("capital path cash became negative")
        gross_total += gross
        commission_total += commission
        minimum_excess += commission - COMMISSION_RATE * gross
        filled_positions += 1
    return CapitalPathAudit(
        minimum_faithful_capital_cny=faithful,
        target_nonzero_positions=target_nonzero,
        filled_positions=filled_positions,
        invested_ratio=gross_total / HISTORICAL_INITIAL_CASH_CNY,
        total_commission_drag_bps=(
            commission_total / HISTORICAL_INITIAL_CASH_CNY * 10_000
        ),
        minimum_commission_drag_bps=(
            minimum_excess / HISTORICAL_INITIAL_CASH_CNY * 10_000
        ),
        capacity_rejection_count=capacity_rejections,
        market_rule_rejection_count=market_rejections,
    )


def capital_interval_feasibility(
    rows: Sequence[CapitalFormationRow], *, intended_exposure: float
) -> CapitalIntervalAudit:
    frozen = tuple(rows)
    if (
        len(frozen) != BASKET_SIZE
        or any(not isinstance(row, CapitalFormationRow) for row in frozen)
        or len({row.symbol for row in frozen}) != BASKET_SIZE
    ):
        raise RelativeVarianceContractError("capital scan requires 30 unique formation rows")
    exposure = _finite(intended_exposure, "intended exposure", positive=True)
    if exposure > 1:
        raise RelativeVarianceContractError("intended exposure cannot exceed one")
    ordered = tuple(sorted(frozen, key=lambda row: row.symbol))
    managed = _capital_path(ordered, exposure)
    comparator = _capital_path(ordered, 1.0)
    managed_threshold = max(0.80 * exposure, exposure - 0.10)
    gate_pass = (
        comparator.filled_positions == BASKET_SIZE
        and comparator.invested_ratio >= 0.90
        and managed.filled_positions >= 24
        and managed.invested_ratio >= managed_threshold
    )
    return CapitalIntervalAudit(exposure, managed, comparator, gate_pass)


def select_basket(rows: Sequence[QualifiedStock]) -> tuple[QualifiedStock, ...]:
    frozen = tuple(rows)
    if any(not isinstance(row, QualifiedStock) for row in frozen):
        raise RelativeVarianceContractError("basket inputs must be qualified stocks")
    if len({row.symbol for row in frozen}) != len(frozen):
        raise RelativeVarianceContractError("duplicate stock identity")
    ranked = sorted(frozen, key=lambda row: (-row.median_amount_cny, row.symbol))
    if len(ranked) < BASKET_SIZE:
        raise RelativeVarianceContractError("fewer than 30 qualified stocks")
    return tuple(ranked[:BASKET_SIZE])


def basket_daily_returns(rows: Sequence[QualifiedStock]) -> tuple[float, ...]:
    basket = tuple(rows)
    if len(basket) != BASKET_SIZE or len({row.symbol for row in basket}) != BASKET_SIZE:
        raise RelativeVarianceContractError("same 30-stock basket is required")
    output = []
    for position in range(1, CLOSE_SESSIONS):
        values = tuple(
            _finite(row.qfq_closes[position] / row.qfq_closes[position - 1] - 1, "daily return")
            for row in basket
        )
        output.append(math.fsum(values) / BASKET_SIZE)
    if len(output) != RETURN_COUNT:
        raise RelativeVarianceContractError("exactly 273 basket returns are required")
    return tuple(output)


def variance_exposure(daily_returns: Sequence[float]) -> tuple[float, float, float]:
    values = tuple(_finite(value, "basket return") for value in daily_returns)
    if len(values) != RETURN_COUNT:
        raise RelativeVarianceContractError("variance input needs 273 returns")
    baseline = math.fsum(value * value for value in values[:BASELINE_DAYS]) / BASELINE_DAYS
    current = math.fsum(value * value for value in values[-CURRENT_DAYS:]) / CURRENT_DAYS
    if baseline <= 0 or current <= 0:
        raise RelativeVarianceContractError("baseline and current variance must be positive")
    exposure = min(1.0, baseline / current)
    return _finite(baseline, "baseline variance"), _finite(current, "current variance"), exposure


def annualized_net(values: Sequence[float]) -> float:
    frozen = tuple(_finite(value, "monthly net return") for value in values)
    if not frozen or any(value <= -1 for value in frozen):
        raise RelativeVarianceContractError(
            "monthly net returns are incomplete or at most minus one"
        )
    return math.exp(math.fsum(math.log1p(value) for value in frozen) * 12 / len(frozen)) - 1


def annualized_volatility(values: Sequence[float]) -> float:
    frozen = tuple(_finite(value, "monthly net return") for value in values)
    if len(frozen) < 2:
        raise RelativeVarianceContractError("sample volatility needs at least two returns")
    return _finite(stdev(frozen) * math.sqrt(12), "annualized volatility")


def _circular_block_start_indices(
    sample_size: int, *, draws: int, seed: int
) -> tuple[tuple[int, ...], ...]:
    if (
        type(sample_size) is not int
        or sample_size < BOOTSTRAP_BLOCK_MONTHS
        or type(draws) is not int
        or draws < 1
        or type(seed) is not int
        or seed < 0
    ):
        raise RelativeVarianceContractError("bootstrap index inputs are invalid")
    blocks = math.ceil(sample_size / BOOTSTRAP_BLOCK_MONTHS)
    generator = np.random.Generator(np.random.PCG64(seed))
    starts = generator.integers(0, sample_size, size=(draws, blocks), endpoint=False)
    return tuple(tuple(int(value) for value in row) for row in starts)


def centered_bootstrap(
    values: Sequence[float], *, seed: int, draws: int = 10_000, alpha: float = 1 / 60
) -> tuple[float, float, float]:
    frozen = tuple(_finite(value, "monthly active return") for value in values)
    if (
        not frozen
        or type(seed) is not int
        or seed < 0
        or type(draws) is not int
        or draws < 1
        or not 0 < alpha < 1
    ):
        raise RelativeVarianceContractError("bootstrap inputs are invalid")
    observed = math.fsum(frozen) / len(frozen)
    centered = tuple(value - observed for value in frozen)
    starts = _circular_block_start_indices(len(frozen), draws=draws, seed=seed)
    means = []
    for row in starts:
        sample = tuple(
            centered[(start + offset) % len(centered)]
            for start in row
            for offset in range(BOOTSTRAP_BLOCK_MONTHS)
        )[: len(centered)]
        means.append(math.fsum(sample) / len(sample))
    p_value = (1 + sum(value >= observed for value in means)) / (draws + 1)
    ordered = sorted(means)
    position = (len(ordered) - 1) * (1 - alpha)
    lower, upper = ordered[math.floor(position)], ordered[math.ceil(position)]
    quantile = lower + (upper - lower) * (position - math.floor(position))
    return observed, p_value, observed - quantile
