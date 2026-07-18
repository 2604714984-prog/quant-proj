from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math
from numbers import Real
from statistics import median, stdev

import numpy as np

RESEARCH_ID = "A_SHARE_RELATIVE_VARIANCE_MANAGED_LIQUID_EQUITY_V1_20260718"
DEFINITION_SHA256 = "a4c29d96b3baa5820e8860e53a4e692bff6a3a2b3bd3c479ba100c720f6a7e07"
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
