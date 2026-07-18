from __future__ import annotations

from calendar import monthrange
from collections import defaultdict, namedtuple
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
import math
from numbers import Real
import re
from statistics import median

from quant_system.data import AcceptedSessionCalendar

RESEARCH_ID = "A_SHARE_POST_IPO_AGE_UNDERPERFORMANCE_AVOIDANCE_V1_20260718"
DEFINITION_SHA256 = "22ede826e4ce0dc3bf93fbdc902b9b9b6a4146c5d601a96cee2aab03bb6f8559"
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
EXPECTED_MASTER_ORDINARY, EXPECTED_OBSERVED_ORDINARY = 5208, 2909
EXPECTED_UNOBSERVED_ORDINARY = 2299
BOARD_LABELS = ("Main", "ChiNext", "STAR")
PAIR_COUNT, ROUNDTRIP_FRICTION = 50, 0.01


class PostIpoAgeContractError(ValueError): ...


def _finite(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise PostIpoAgeContractError(f"{name} must be finite numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or (positive and parsed <= 0.0):
        raise PostIpoAgeContractError(f"{name} must be finite numeric")
    return parsed


def anniversary(day: date, years: int) -> date:
    if type(day) is not date or type(years) is not int or years < 0:
        raise PostIpoAgeContractError("anniversary needs a date and nonnegative years")
    year = day.year + years
    return date(year, day.month, min(day.day, monthrange(year, day.month)[1]))


def age_side(list_date: date, decision_date: date) -> str | None:
    if type(list_date) is not date or type(decision_date) is not date:
        raise PostIpoAgeContractError("age classification needs dates")
    if list_date > decision_date:
        return None
    if decision_date < anniversary(list_date, 3):
        return "young"
    if decision_date >= anniversary(list_date, 5):
        return "seasoned"
    return None


@dataclass(frozen=True)
class CohortRow:
    symbol: str
    board: str
    list_date: date
    trailing_amounts_cny: tuple[float, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol:
            raise PostIpoAgeContractError("symbol must be an opaque nonempty identity")
        if self.board not in BOARD_LABELS or type(self.list_date) is not date:
            raise PostIpoAgeContractError("board or list_date is outside the frozen contract")
        if not isinstance(self.trailing_amounts_cny, tuple) or len(self.trailing_amounts_cny) != 20:
            raise PostIpoAgeContractError("exactly twenty amount rows are required")
        if any(_finite(value, "amount") < 0.0 for value in self.trailing_amounts_cny):
            raise PostIpoAgeContractError("amount must be nonnegative")

    @property
    def median_amount_cny(self) -> float:
        return float(median(self.trailing_amounts_cny))


MatchedPair = namedtuple(
    "MatchedPair", "young_symbol seasoned_symbol board young_median_amount seasoned_median_amount"
)


def build_pairs(rows: Sequence[CohortRow], *, decision_date: date) -> tuple[MatchedPair, ...]:
    frozen = tuple(rows)
    if any(not isinstance(row, CohortRow) for row in frozen):
        raise PostIpoAgeContractError("rows must contain CohortRow values")
    if len({row.symbol for row in frozen}) != len(frozen):
        raise PostIpoAgeContractError("cohort rows contain duplicate symbols")
    groups: dict[tuple[str, str], list[CohortRow]] = defaultdict(list)
    for row in frozen:
        side = age_side(row.list_date, decision_date)
        if side is not None:
            groups[(row.board, side)].append(row)
    for side in groups.values():
        side.sort(key=lambda row: (-row.median_amount_cny, row.symbol))
    pairs: list[MatchedPair] = []
    for board in BOARD_LABELS:
        for young, seasoned in zip(
            groups.get((board, "young"), ()), groups.get((board, "seasoned"), ())
        ):
            pairs.append(
                MatchedPair(
                    young.symbol,
                    seasoned.symbol,
                    board,
                    young.median_amount_cny,
                    seasoned.median_amount_cny,
                )
            )
    pairs.sort(
        key=lambda row: (
            -min(row.young_median_amount, row.seasoned_median_amount),
            row.young_symbol,
            row.seasoned_symbol,
        )
    )
    return tuple(pairs[:PAIR_COUNT])


def split_id(day: date) -> str | None:
    ranges = {
        "development_2020_2021": (date(2020, 1, 1), date(2021, 12, 31)),
        "validation_2022_2023": (date(2022, 1, 1), date(2023, 12, 31)),
        "retrospective_holdout_2024_2026h1": (date(2024, 1, 1), date(2026, 6, 30)),
    }
    return next((name for name, span in ranges.items() if span[0] <= day <= span[1]), None)


def interval_dates(
    calendar: AcceptedSessionCalendar, *, decision_date: date, as_of: datetime
) -> tuple[date, date, str]:
    if not isinstance(calendar, AcceptedSessionCalendar):
        raise TypeError("calendar must be an AcceptedSessionCalendar")
    same_month = tuple(
        day
        for day in calendar.session_dates
        if (day.year, day.month) == (decision_date.year, decision_date.month)
    )
    if not same_month or decision_date != same_month[-1]:
        raise PostIpoAgeContractError("D must be the last accepted session of its month")
    if decision_date >= date(2026, 5, 1):
        raise PostIpoAgeContractError("formation is forbidden from 2026-05")
    entry = calendar.next_session(decision_date, as_of=as_of).session_date
    year, month = (
        (decision_date.year + 1, 1)
        if decision_date.month == 12
        else (decision_date.year, decision_date.month + 1)
    )
    exit_day = calendar.next_session(
        date(year, month, monthrange(year, month)[1]), as_of=as_of
    ).session_date
    identity = split_id(entry)
    if identity is None or split_id(exit_day) != identity:
        raise PostIpoAgeContractError("entry and exit must remain in one split")
    return entry, exit_day, identity


@dataclass(frozen=True)
class SelectedPanel:
    symbol: str
    entry_qfq_open: float
    exit_qfq_open: float
    entry_adj_factor: float
    exit_adj_factor: float
    entry_hash: str
    exit_hash: str
    entry_quality: str
    exit_quality: str
    entry_synthetic: bool
    exit_synthetic: bool

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol:
            raise PostIpoAgeContractError("panel symbol must be opaque and nonempty")
        for name in ("entry_qfq_open", "exit_qfq_open", "entry_adj_factor", "exit_adj_factor"):
            _finite(getattr(self, name), name, positive=True)
        for value in (self.entry_hash, self.exit_hash):
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise PostIpoAgeContractError("selected panel row hash is invalid")
        quality = "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT"
        if (
            self.entry_quality != quality
            or self.exit_quality != quality
            or self.entry_synthetic is not False
            or self.exit_synthetic is not False
        ):
            raise PostIpoAgeContractError("selected panel identity is invalid")


IntervalReturn = namedtuple(
    "IntervalReturn", "seasoned_gross young_gross seasoned_net young_net active"
)


def synthetic_interval_return(
    pairs: Sequence[MatchedPair], panels: Mapping[str, SelectedPanel]
) -> IntervalReturn:
    frozen = tuple(pairs)
    if len(frozen) != PAIR_COUNT or any(not isinstance(pair, MatchedPair) for pair in frozen):
        raise PostIpoAgeContractError("exactly fifty MatchedPair values are required")
    young_ids = tuple(pair.young_symbol for pair in frozen)
    seasoned_ids = tuple(pair.seasoned_symbol for pair in frozen)
    if (
        len(set(young_ids)) != PAIR_COUNT
        or len(set(seasoned_ids)) != PAIR_COUNT
        or not set(young_ids).isdisjoint(seasoned_ids)
        or any(not isinstance(value, str) or not value for value in (*young_ids, *seasoned_ids))
        or any(pair.board not in BOARD_LABELS for pair in frozen)
        or any(
            _finite(value, "pair median amount") < 0.0
            for pair in frozen
            for value in (pair.young_median_amount, pair.seasoned_median_amount)
        )
    ):
        raise PostIpoAgeContractError("pair identity or metadata is invalid")

    def side(symbols: Sequence[str]) -> float:
        values = []
        for symbol in symbols:
            panel = panels.get(symbol)
            if not isinstance(panel, SelectedPanel) or panel.symbol != symbol:
                raise PostIpoAgeContractError("selected panel is missing")
            values.append(_finite(panel.exit_qfq_open / panel.entry_qfq_open - 1.0, "gross return"))
        return _finite(sum(values) / PAIR_COUNT, "side gross return")

    seasoned, young = side(seasoned_ids), side(young_ids)
    seasoned_net, young_net = seasoned - ROUNDTRIP_FRICTION, young - ROUNDTRIP_FRICTION
    result = (seasoned, young, seasoned_net, young_net, seasoned_net - young_net)
    if any(not math.isfinite(value) for value in result):
        raise PostIpoAgeContractError("interval return result must be finite")
    return IntervalReturn(*result)
