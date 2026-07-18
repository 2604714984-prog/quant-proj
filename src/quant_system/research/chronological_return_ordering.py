from __future__ import annotations

from calendar import monthrange
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
import math
from numbers import Real
import re
from statistics import median

from quant_system.backtest.permanent_portfolio import circular_block_start_indices
from quant_system.data import AcceptedSessionCalendar

RESEARCH_ID = "A_SHARE_CHRONOLOGICAL_RETURN_ORDERING_MONTHLY_V1_20260718"
DEFINITION_SHA256 = "882a7782e21c5a5e1cf41eb8eb0c7fd2fd167f4eaa706d56fc96e99429d43e5f"
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
MIN_FORMATION_SESSIONS, MIN_ELIGIBLE = 14, 1000
MIN_MEDIAN_AMOUNT_CNY, SELECTION_FRACTION = 50_000_000.0, 0.10
MIN_SELECTED, ROUNDTRIP_FRICTION = 100, 0.01
BOOTSTRAP_DRAWS, BONFERRONI_ALPHA = 10_000, 1.0 / 60.0
QUALITY = "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT"
COMMON_PREFIXES = {
    "SH": ("600", "601", "603", "605", "688"),
    "SZ": ("000", "001", "002", "003", "300", "301"),
}


class ChronologicalReturnOrderingError(ValueError): ...


def _finite(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ChronologicalReturnOrderingError(f"{name} must be finite numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or (positive and parsed <= 0.0):
        raise ChronologicalReturnOrderingError(f"{name} must be finite numeric")
    return parsed


def common_a_symbol(symbol: str) -> bool:
    if not isinstance(symbol, str) or symbol.count(".") != 1:
        return False
    code, suffix = symbol.split(".")
    return (
        len(code) == 6
        and code.isdigit()
        and suffix in COMMON_PREFIXES
        and code.startswith(COMMON_PREFIXES[suffix])
    )


def chronological_return_ordering(closes: Sequence[object]) -> float | None:
    raw = tuple(closes)
    if len(raw) < MIN_FORMATION_SESSIONS + 1:
        return None
    try:
        prices = tuple(_finite(value, "qfq close", positive=True) for value in raw)
    except ChronologicalReturnOrderingError:
        return None
    returns = tuple(last / first - 1.0 for first, last in zip(prices[:-1], prices[1:], strict=True))
    count = len(returns)
    x_mean = (count + 1.0) / 2.0
    y_mean = math.fsum(returns) / count
    numerator = math.fsum((i - x_mean) * (value - y_mean) for i, value in enumerate(returns, 1))
    x_ss = math.fsum((i - x_mean) ** 2 for i in range(1, count + 1))
    y_ss = math.fsum((value - y_mean) ** 2 for value in returns)
    denominator = math.sqrt(x_ss * y_ss)
    if denominator == 0.0 or not math.isfinite(denominator):
        return None
    score = numerator / denominator
    return score if math.isfinite(score) else None


@dataclass(frozen=True)
class FormationRow:
    symbol: str
    qfq_closes: tuple[object, ...]
    formation_amounts_cny: tuple[object, ...]

    def __post_init__(self) -> None:
        if not common_a_symbol(self.symbol):
            raise ChronologicalReturnOrderingError("symbol is outside frozen ordinary boards")
        if not isinstance(self.qfq_closes, tuple) or not isinstance(
            self.formation_amounts_cny, tuple
        ):
            raise ChronologicalReturnOrderingError("formation inputs must be tuples")
        if len(self.qfq_closes) != len(self.formation_amounts_cny) + 1:
            raise ChronologicalReturnOrderingError(
                "formation close and amount windows do not align"
            )

    def screened_score(self) -> float | None:
        score = chronological_return_ordering(self.qfq_closes)
        if score is None:
            return None
        try:
            amounts = tuple(_finite(value, "amount") for value in self.formation_amounts_cny)
        except ChronologicalReturnOrderingError:
            return None
        if any(value < 0.0 for value in amounts) or median(amounts) < MIN_MEDIAN_AMOUNT_CNY:
            return None
        return score


@dataclass(frozen=True)
class Selection:
    eligible_symbols: tuple[str, ...]
    selected_symbols: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return (
            len(self.eligible_symbols) >= MIN_ELIGIBLE
            and len(self.selected_symbols) >= MIN_SELECTED
        )


def select_low_cro(rows: Sequence[FormationRow]) -> Selection:
    frozen = tuple(rows)
    if any(not isinstance(row, FormationRow) for row in frozen):
        raise ChronologicalReturnOrderingError("rows must contain FormationRow values")
    if len({row.symbol for row in frozen}) != len(frozen):
        raise ChronologicalReturnOrderingError("formation rows contain duplicate symbols")
    ranked = sorted(
        ((score, row.symbol) for row in frozen if (score := row.screened_score()) is not None),
        key=lambda item: (item[0], item[1]),
    )
    eligible = tuple(symbol for _, symbol in ranked)
    take = math.floor(SELECTION_FRACTION * len(eligible))
    selected = tuple(symbol for _, symbol in ranked[:take]) if take >= MIN_SELECTED else ()
    return Selection(eligible, selected)


def split_id(entry: date, exit_day: date) -> str | None:
    if type(entry) is not date or type(exit_day) is not date or entry > exit_day:
        raise ChronologicalReturnOrderingError("interval dates are invalid")
    splits = {
        "development_2020_2021": (date(2020, 1, 1), date(2021, 12, 31)),
        "validation_2022_2023": (date(2022, 1, 1), date(2023, 12, 31)),
        "retrospective_holdout_2024_2026m4": (date(2024, 1, 1), date(2026, 4, 30)),
        "forbidden_2026m5_2026m12": (date(2026, 5, 1), date(2026, 12, 31)),
        "prospective_forward_2027_2029": (date(2027, 1, 1), date(2029, 12, 31)),
    }
    return next(
        (name for name, (start, end) in splits.items() if start <= entry <= exit_day <= end), None
    )


def interval_dates(
    calendar: AcceptedSessionCalendar, *, decision_date: date, as_of: datetime
) -> tuple[date, date, str]:
    if not isinstance(calendar, AcceptedSessionCalendar):
        raise TypeError("calendar must be an AcceptedSessionCalendar")
    month_days = tuple(
        day
        for day in calendar.session_dates
        if (day.year, day.month) == (decision_date.year, decision_date.month)
    )
    if len(month_days) < MIN_FORMATION_SESSIONS or decision_date != month_days[-1]:
        raise ChronologicalReturnOrderingError("D must be last accepted and close a complete month")
    entry = calendar.next_session(decision_date, as_of=as_of).session_date
    year, month = (
        (decision_date.year + 1, 1)
        if decision_date.month == 12
        else (decision_date.year, decision_date.month + 1)
    )
    exit_day = calendar.next_session(date(year, month, monthrange(year, month)[1]), as_of=as_of)
    identity = split_id(entry, exit_day.session_date)
    if identity not in {
        "development_2020_2021",
        "validation_2022_2023",
        "retrospective_holdout_2024_2026m4",
    }:
        raise ChronologicalReturnOrderingError(
            "interval crosses or leaves an allowed historical split"
        )
    return entry, exit_day.session_date, identity


@dataclass(frozen=True)
class PricePanel:
    symbol: str
    entry_qfq_open: object
    exit_qfq_open: object
    entry_adj_factor: object
    exit_adj_factor: object
    entry_quality: str = QUALITY
    exit_quality: str = QUALITY
    entry_row_hash: str = "0" * 64
    exit_row_hash: str = "0" * 64
    entry_synthetic: bool = False
    exit_synthetic: bool = False

    def prices(self) -> tuple[float, float]:
        if not common_a_symbol(self.symbol):
            raise ChronologicalReturnOrderingError("panel symbol is invalid")
        values = tuple(
            _finite(value, "panel numeric", positive=True)
            for value in (
                self.entry_qfq_open,
                self.exit_qfq_open,
                self.entry_adj_factor,
                self.exit_adj_factor,
            )
        )
        hashes = (self.entry_row_hash, self.exit_row_hash)
        if (
            self.entry_quality != QUALITY
            or self.exit_quality != QUALITY
            or self.entry_synthetic is not False
            or self.exit_synthetic is not False
            or any(re.fullmatch(r"[0-9a-f]{64}", value) is None for value in hashes)
        ):
            raise ChronologicalReturnOrderingError("panel identity is invalid")
        return values[0], values[1]


def validate_price_panels(
    selection: Selection, panels: Sequence[PricePanel]
) -> tuple[PricePanel, ...]:
    if not isinstance(selection, Selection) or not selection.valid:
        raise ChronologicalReturnOrderingError("selection is not structurally valid")
    by_symbol: dict[str, PricePanel] = {}
    for panel in panels:
        if not isinstance(panel, PricePanel) or panel.symbol in by_symbol:
            raise ChronologicalReturnOrderingError("panels must be unique PricePanel values")
        by_symbol[panel.symbol] = panel
    if set(by_symbol) != set(selection.eligible_symbols):
        raise ChronologicalReturnOrderingError("every benchmark-eligible panel is required")
    ordered = tuple(by_symbol[symbol] for symbol in selection.eligible_symbols)
    for panel in ordered:
        panel.prices()
    return ordered


@dataclass(frozen=True)
class InferenceResult:
    observed_mean: float
    p_value: float
    lower_bound: float


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])


def bootstrap_mean(
    values: Sequence[object], *, seed: int, draws: int = BOOTSTRAP_DRAWS
) -> InferenceResult:
    frozen = tuple(_finite(value, "active return") for value in values)
    if len(frozen) < 3 or draws != BOOTSTRAP_DRAWS:
        raise ChronologicalReturnOrderingError(
            "bootstrap requires frozen draws and at least three intervals"
        )
    observed = math.fsum(frozen) / len(frozen)
    centered = tuple(value - observed for value in frozen)
    means: list[float] = []
    for starts in circular_block_start_indices(len(frozen), draws=draws, seed=seed):
        indices = tuple((start + offset) % len(frozen) for start in starts for offset in range(3))[
            : len(frozen)
        ]
        means.append(math.fsum(centered[index] for index in indices) / len(frozen))
    p_value = (1 + sum(value >= observed for value in means)) / (draws + 1)
    return InferenceResult(observed, p_value, observed - _quantile(means, 1 - BONFERRONI_ALPHA))
