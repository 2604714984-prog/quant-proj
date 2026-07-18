"""Frozen post-IPO lucky-code avoidance research primitives."""

from __future__ import annotations

from bisect import bisect_left
from calendar import monthrange
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
import math
from numbers import Real
from statistics import median

from quant_system.backtest.permanent_portfolio import circular_block_start_indices
from quant_system.data import AcceptedSessionCalendar

RESEARCH_ID = "A_SHARE_POST_IPO_NUMEROLOGICAL_OVERVALUATION_AVOIDANCE_V1_20260718"
DEFINITION_SHA256 = "6e6e61ec0d8487582fad27aa0079d3b3dc54a8493402aeb442e7da907aecdac2"
SNAPSHOT_ID = "a_share_qfq_personal_research_20260716_v5"
SNAPSHOT_DIGEST = "da6160ddad3f5fcb21151dd0d3128ea7786be2a2014872a14f85635e783dba6b"
DATABASE_SHA256 = "e636bb80e300f89e46831e91275c6f2167e370e81a00b21b300e253f6107bee0"
SNAPSHOT_RECEIPT_FILENAME = "a_share_volume_unit_shares_v5_20260717.json"
SNAPSHOT_RECEIPT_SHA256 = "241be32158b9ab5cebbe92dfceeec2a889f3b56e681a1f764d7b6d257f21f17f"
CALENDAR_SNAPSHOT_ID = "akshare_sina_calendar_1d5ff82a6718fc4e19b95c98"
CALENDAR_EXCHANGE = "SSE"
CALENDAR_SOURCE = "AKSHARE_TOOL_TRADE_DATE_HIST_SINA"
CALENDAR_ROW_COUNT = 2058
CALENDAR_DIGEST = "ea7557ee994893ab6719a20ef0de10c60c5087e8637c0771f11c1e6ddc4cee71"
COVERAGE_START, HISTORICAL_CUTOFF = date(2018, 1, 2), date(2026, 6, 30)
EXPECTED_MASTER_ORDINARY = 5208
EXPECTED_OBSERVED_ORDINARY = 2909
EXPECTED_UNOBSERVED_ORDINARY = 2299
PAIR_COUNT, IPO_AGE_MIN, IPO_AGE_MAX = 15, 60, 756
ROUNDTRIP_FRICTION = 0.01
BOOTSTRAP_DRAWS, BONFERRONI_ALPHA = 10_000, 1.0 / 60.0
BOARD_PREFIXES = {
    "SH_MAIN": ("SH", ("600", "601", "603", "605")),
    "STAR": ("SH", ("688",)),
    "SZ_MAIN": ("SZ", ("000", "001", "002", "003")),
    "CHINEXT": ("SZ", ("300", "301")),
}


class PostIpoNumerologyContractError(ValueError): ...


def _finite(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise PostIpoNumerologyContractError(f"{name} must be finite numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or (positive and parsed <= 0.0):
        raise PostIpoNumerologyContractError(f"{name} must be finite numeric")
    return parsed


def board_id(symbol: str) -> str | None:
    if not isinstance(symbol, str) or symbol.count(".") != 1:
        return None
    code, exchange = symbol.split(".")
    if len(code) != 6 or not code.isdigit():
        return None
    for board, (suffix, prefixes) in BOARD_PREFIXES.items():
        if exchange == suffix and code.startswith(prefixes):
            return board
    return None


def lucky_code(symbol: str) -> bool:
    board = board_id(symbol)
    if board is None:
        raise PostIpoNumerologyContractError("symbol is outside the frozen ordinary boards")
    code, exchange = symbol.split(".")
    digits = code[-3:] if exchange == "SH" else code[-4:]
    return "4" not in digits and any(value in digits for value in "689")


def list_quarter(list_date: date) -> str:
    if type(list_date) is not date:
        raise PostIpoNumerologyContractError("list_date must be a date")
    return f"{list_date.year:04d}Q{(list_date.month - 1) // 3 + 1}"


def accepted_session_age(
    calendar: AcceptedSessionCalendar,
    *,
    list_date: date,
    decision_date: date,
    as_of: datetime,
) -> int:
    if not isinstance(calendar, AcceptedSessionCalendar):
        raise TypeError("calendar must be an AcceptedSessionCalendar")
    if type(list_date) is not date or type(decision_date) is not date:
        raise PostIpoNumerologyContractError("age dates must be dates")
    dates = calendar.session_dates
    position = bisect_left(dates, list_date)
    if position == len(dates) or (dates[0] - list_date).days > 7:
        raise PostIpoNumerologyContractError("first accepted listing session is unavailable")
    end = bisect_left(dates, decision_date)
    if end == len(dates) or dates[end] != decision_date or position > end:
        raise PostIpoNumerologyContractError("decision session is unavailable")
    calendar.session_on(dates[position], as_of=as_of)
    calendar.session_on(decision_date, as_of=as_of)
    return end - position + 1


@dataclass(frozen=True)
class CohortRow:
    symbol: str
    list_date: date
    ipo_age_sessions: int
    trailing_amounts_cny: tuple[float, ...]

    def __post_init__(self) -> None:
        if board_id(self.symbol) is None:
            raise PostIpoNumerologyContractError("cohort symbol is outside frozen boards")
        list_quarter(self.list_date)
        if type(self.ipo_age_sessions) is not int or self.ipo_age_sessions < 0:
            raise PostIpoNumerologyContractError("IPO age must be nonnegative int")
        if not isinstance(self.trailing_amounts_cny, tuple) or len(self.trailing_amounts_cny) != 20:
            raise PostIpoNumerologyContractError("exactly twenty amount rows are required")
        if any(_finite(value, "amount") < 0.0 for value in self.trailing_amounts_cny):
            raise PostIpoNumerologyContractError("amount must be nonnegative")

    @property
    def median_amount_cny(self) -> float:
        return float(median(self.trailing_amounts_cny))

    @property
    def eligible(self) -> bool:
        return IPO_AGE_MIN <= self.ipo_age_sessions <= IPO_AGE_MAX


@dataclass(frozen=True)
class MatchedPair:
    not_lucky_symbol: str
    lucky_symbol: str
    board: str
    absolute_list_quarter: str
    not_lucky_median_amount: float
    lucky_median_amount: float


def build_pairs(rows: Sequence[CohortRow]) -> tuple[MatchedPair, ...]:
    frozen = tuple(rows)
    if any(not isinstance(row, CohortRow) for row in frozen):
        raise PostIpoNumerologyContractError("rows must contain CohortRow values")
    if len({row.symbol for row in frozen}) != len(frozen):
        raise PostIpoNumerologyContractError("cohort rows contain duplicate symbols")
    groups: dict[tuple[str, str, bool], list[CohortRow]] = defaultdict(list)
    for row in frozen:
        if row.eligible:
            groups[
                (board_id(row.symbol) or "", list_quarter(row.list_date), lucky_code(row.symbol))
            ].append(row)
    for side in groups.values():
        side.sort(key=lambda row: (-row.median_amount_cny, row.symbol))
    pairs: list[MatchedPair] = []
    cohorts = sorted({(board, quarter) for board, quarter, _ in groups})
    for board, quarter in cohorts:
        unlucky = groups.get((board, quarter, False), [])
        lucky = groups.get((board, quarter, True), [])
        for left, right in zip(unlucky, lucky):
            pairs.append(
                MatchedPair(
                    left.symbol,
                    right.symbol,
                    board,
                    quarter,
                    left.median_amount_cny,
                    right.median_amount_cny,
                )
            )
    pairs.sort(
        key=lambda row: (
            -min(row.not_lucky_median_amount, row.lucky_median_amount),
            row.not_lucky_symbol,
            row.lucky_symbol,
        )
    )
    return tuple(pairs[:PAIR_COUNT])


def split_id(day: date) -> str | None:
    if type(day) is not date:
        raise PostIpoNumerologyContractError("split day must be a date")
    splits = {
        "development_2020_2021": (date(2020, 1, 1), date(2021, 12, 31)),
        "validation_2022_2023": (date(2022, 1, 1), date(2023, 12, 31)),
        "retrospective_holdout_2024_2026h1": (date(2024, 1, 1), date(2026, 6, 30)),
        "embargo_2026h2": (date(2026, 7, 1), date(2026, 12, 31)),
        "prospective_forward_2027_2029": (date(2027, 1, 1), date(2029, 12, 31)),
    }
    return next((name for name, (start, end) in splits.items() if start <= day <= end), None)


def interval_dates(
    calendar: AcceptedSessionCalendar, *, decision_date: date, as_of: datetime
) -> tuple[date, date, str]:
    if not isinstance(calendar, AcceptedSessionCalendar):
        raise TypeError("calendar must be an AcceptedSessionCalendar")
    dates = calendar.session_dates
    same_month = tuple(
        day for day in dates if (day.year, day.month) == (decision_date.year, decision_date.month)
    )
    if not same_month or decision_date != same_month[-1]:
        raise PostIpoNumerologyContractError("D must be the last accepted session of its month")
    entry = calendar.next_session(decision_date, as_of=as_of).session_date
    year, month = (
        (decision_date.year + 1, 1)
        if decision_date.month == 12
        else (decision_date.year, decision_date.month + 1)
    )
    next_month_end = date(year, month, monthrange(year, month)[1])
    exit_day = calendar.next_session(next_month_end, as_of=as_of).session_date
    identity = split_id(entry)
    if identity is None or split_id(exit_day) != identity:
        raise PostIpoNumerologyContractError("entry and exit must remain in one split")
    return entry, exit_day, identity


@dataclass(frozen=True)
class IntervalReturn:
    strategy_gross: float
    benchmark_gross: float
    strategy_net: float
    benchmark_net: float
    active: float


def synthetic_interval_return(
    pairs: Sequence[MatchedPair],
    prices: Mapping[str, tuple[float, float]],
) -> IntervalReturn:
    frozen = tuple(pairs)
    if len(frozen) != PAIR_COUNT or len({p.not_lucky_symbol for p in frozen}) != PAIR_COUNT:
        raise PostIpoNumerologyContractError("exactly fifteen unique matched pairs are required")
    if len({p.lucky_symbol for p in frozen}) != PAIR_COUNT:
        raise PostIpoNumerologyContractError("lucky pair symbols must be unique")

    def side(symbols: Sequence[str]) -> float:
        values: list[float] = []
        for symbol in symbols:
            try:
                entry, exit_price = prices[symbol]
            except (KeyError, TypeError) as exc:
                raise PostIpoNumerologyContractError("pair price is missing") from exc
            first = _finite(entry, "entry qfq open", positive=True)
            last = _finite(exit_price, "exit qfq open", positive=True)
            values.append(last / first - 1.0)
        return math.fsum(values) / PAIR_COUNT

    strategy = side(tuple(pair.not_lucky_symbol for pair in frozen))
    benchmark = side(tuple(pair.lucky_symbol for pair in frozen))
    strategy_net, benchmark_net = strategy - ROUNDTRIP_FRICTION, benchmark - ROUNDTRIP_FRICTION
    return IntervalReturn(
        strategy, benchmark, strategy_net, benchmark_net, strategy_net - benchmark_net
    )


def annualized_net_return(values: Sequence[float]) -> float:
    frozen = tuple(_finite(value, "net return") for value in values)
    if not frozen or any(value <= -1.0 for value in frozen):
        raise PostIpoNumerologyContractError("annualization needs finite returns above -1")
    result = math.exp(math.fsum(math.log1p(value) for value in frozen) * 12.0 / len(frozen)) - 1.0
    return _finite(result, "annualized net return")


def _linear_quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(_finite(value, "bootstrap mean") for value in values)
    if not ordered or not 0.0 <= probability <= 1.0:
        raise PostIpoNumerologyContractError("quantile requires values and p in [0,1]")
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])


@dataclass(frozen=True)
class InferenceResult:
    observed_mean: float
    p_value: float
    lower_bound: float
    draws: int
    seed: int


def bootstrap_mean(values: Sequence[float], *, draws: int, seed: int) -> InferenceResult:
    frozen = tuple(_finite(value, "active return") for value in values)
    if len(frozen) < 3:
        raise PostIpoNumerologyContractError("bootstrap requires at least three intervals")
    observed = math.fsum(frozen) / len(frozen)
    starts = circular_block_start_indices(len(frozen), draws=draws, seed=seed)
    centered = tuple(value - observed for value in frozen)
    means: list[float] = []
    for blocks in starts:
        indices = tuple((start + offset) % len(frozen) for start in blocks for offset in range(3))[
            : len(frozen)
        ]
        means.append(math.fsum(centered[index] for index in indices) / len(frozen))
    p_value = (1 + sum(value >= observed for value in means)) / (len(means) + 1)
    lower = observed - _linear_quantile(means, 1.0 - BONFERRONI_ALPHA)
    return InferenceResult(observed, p_value, lower, draws, seed)
