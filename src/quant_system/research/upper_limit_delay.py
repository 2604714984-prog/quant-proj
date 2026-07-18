"""Frozen upper-limit delayed-price-discovery target formation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math
from numbers import Real
from pathlib import Path
from statistics import median

from quant_system.data import AcceptedSessionCalendar

RESEARCH_ID = "A_SHARE_UPPER_LIMIT_DELAYED_PRICE_DISCOVERY_V1_20260718"
LINEAGE_ID = "A_SHARE_UPPER_LIMIT_DELAYED_PRICE_DISCOVERY_V1"
VARIANT_ID = "NON_ONE_PRICE_UPPER_LIMIT_HOLD_1_SESSION"
DEFINITION_PATH = Path("research/definitions/a_share_upper_limit_delayed_price_discovery_v1.json")
DEFINITION_SHA256 = "88db34392f9299a939bc63b81ff701c038b0a483cedd05d8f12dfbe7d21d22ad"
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
BENCHMARK_SYMBOL = "510300.SH"
MAX_POSITIONS, MIN_ELIGIBLE = 15, 500
MIN_LISTED_SESSIONS, MIN_MEDIAN_AMOUNT_CNY = 252, 20_000_000.0
COMMON_PREFIXES = {
    "SH": ("600", "601", "603", "605", "688"),
    "SZ": ("000", "001", "002", "003", "300", "301"),
}


class UpperLimitDelayContractError(ValueError): ...


def _finite(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise UpperLimitDelayContractError(f"{name} must be finite numeric")
    try:
        parsed = float(value)
    except (OverflowError, ValueError) as exc:
        raise UpperLimitDelayContractError(f"{name} must be finite numeric") from exc
    if not math.isfinite(parsed) or (positive and parsed <= 0.0):
        raise UpperLimitDelayContractError(f"{name} must be finite numeric")
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


@dataclass(frozen=True)
class DailySignal:
    symbol: str
    raw_low: float
    raw_up_limit: float
    is_limit_up: bool
    is_limit_down: bool
    trailing_amounts_cny: tuple[float, ...]
    accepted_sessions_since_listing: int
    listed: bool
    delisted: bool
    is_st: bool
    is_suspended: bool

    def __post_init__(self) -> None:
        if not common_a_symbol(self.symbol):
            raise UpperLimitDelayContractError("symbol must be a common A-share")
        low = _finite(self.raw_low, "raw_low", positive=True)
        limit = _finite(self.raw_up_limit, "raw_up_limit", positive=True)
        if low > limit:
            raise UpperLimitDelayContractError("raw_low cannot exceed raw_up_limit")
        if not isinstance(self.trailing_amounts_cny, tuple) or len(self.trailing_amounts_cny) != 20:
            raise UpperLimitDelayContractError("exactly twenty amount observations are required")
        if any(_finite(value, "amount") < 0.0 for value in self.trailing_amounts_cny):
            raise UpperLimitDelayContractError("amount must be nonnegative CNY")
        if (
            type(self.accepted_sessions_since_listing) is not int
            or self.accepted_sessions_since_listing < 0
        ):
            raise UpperLimitDelayContractError("listed-session count must be nonnegative int")
        if any(
            type(value) is not bool
            for value in (
                self.is_limit_up,
                self.is_limit_down,
                self.listed,
                self.delisted,
                self.is_st,
                self.is_suspended,
            )
        ):
            raise UpperLimitDelayContractError("status fields must be boolean")
        if self.is_limit_up and self.is_limit_down:
            raise UpperLimitDelayContractError("upper-limit and lower-limit states conflict")

    @property
    def median_amount_cny(self) -> float:
        return float(median(self.trailing_amounts_cny))

    @property
    def is_event(self) -> bool:
        return self.is_limit_up and self.raw_low < self.raw_up_limit


@dataclass(frozen=True)
class Target:
    decision_date: date
    entry_date: date
    scheduled_exit_date: date
    eligible_count: int
    event_count: int
    selected_symbols: tuple[str, ...]
    selected_median_amounts: tuple[tuple[str, float], ...]
    target_weights: tuple[tuple[str, float], ...]
    gross_target_exposure: float


@dataclass(frozen=True)
class IntervalAudit:
    decision_date: date
    split_id: str
    eligible_count: int
    event_count: int
    target_slot_count: int
    gross_target_exposure: float
    signal_panel_complete: bool
    entry_panel_complete: bool
    exit_panel_complete: bool
    mark_panel_complete: bool
    reference_panel_complete: bool
    signal_panel_missing_count: int = 0
    signal_panel_nonfinite_count: int = 0
    signal_panel_identity_failure_count: int = 0
    duplicate_key_count: int = 0
    nonfinite_required_value_count: int = 0
    split_boundary_violation_count: int = 0

    @property
    def valid(self) -> bool:
        return (
            self.eligible_count >= MIN_ELIGIBLE
            and self.signal_panel_complete
            and self.entry_panel_complete
            and self.exit_panel_complete
            and self.mark_panel_complete
            and self.reference_panel_complete
            and self.signal_panel_missing_count == 0
            and self.signal_panel_nonfinite_count == 0
            and self.signal_panel_identity_failure_count == 0
            and self.duplicate_key_count == 0
            and self.nonfinite_required_value_count == 0
            and self.split_boundary_violation_count == 0
        )


_SPLITS = (
    ("development_2020_2021", date(2020, 1, 1), date(2021, 12, 31)),
    ("validation_2022_2023", date(2022, 1, 1), date(2023, 12, 31)),
    ("retrospective_holdout_2024_2026h1", date(2024, 1, 1), date(2026, 6, 30)),
    ("embargo_2026h2", date(2026, 7, 1), date(2026, 12, 31)),
    ("prospective_forward_2027_2029", date(2027, 1, 1), date(2029, 12, 31)),
)


def split_id(day: date) -> str | None:
    if type(day) is not date:
        raise UpperLimitDelayContractError("split day must be a date")
    return next((name for name, start, end in _SPLITS if start <= day <= end), None)


def retained_triplet(decision: date, entry: date, exit_day: date) -> tuple[bool, str | None]:
    if any(type(day) is not date for day in (decision, entry, exit_day)):
        raise UpperLimitDelayContractError("triplet days must be dates")
    identities = (split_id(decision), split_id(entry), split_id(exit_day))
    return identities[0] is not None and len(set(identities)) == 1, identities[0]


def capacity_observation_session(
    calendar: AcceptedSessionCalendar, *, execution_date: date, decision_at: datetime
) -> date:
    """Return exactly t-1 for an open-t capacity check; same-session data is forbidden."""
    if not isinstance(calendar, AcceptedSessionCalendar):
        raise TypeError("calendar must be an AcceptedSessionCalendar")
    execution = calendar.session_on(execution_date, as_of=decision_at)
    if decision_at >= execution.open_at:
        raise UpperLimitDelayContractError("capacity decision must be strictly pre-open")
    try:
        position = calendar.session_dates.index(execution_date)
    except ValueError as exc:  # pragma: no cover - guarded by session_on
        raise UpperLimitDelayContractError("execution is not an accepted session") from exc
    if position == 0:
        raise UpperLimitDelayContractError("capacity t-1 session is unavailable")
    return calendar.session_on(calendar.session_dates[position - 1], as_of=decision_at).session_date


def _eligible(signal: DailySignal) -> bool:
    return (
        signal.accepted_sessions_since_listing >= MIN_LISTED_SESSIONS
        and signal.listed
        and not signal.delisted
        and not signal.is_st
        and not signal.is_suspended
        and signal.median_amount_cny >= MIN_MEDIAN_AMOUNT_CNY
    )


def build_daily_target(
    signals: Sequence[DailySignal],
    calendar: AcceptedSessionCalendar,
    *,
    decision_date: date,
    decision_at: datetime,
) -> Target:
    """Freeze one D/D+1/D+2 target without calculating any return."""
    if not isinstance(calendar, AcceptedSessionCalendar):
        raise TypeError("calendar must be an AcceptedSessionCalendar")
    rows = tuple(signals)
    if any(not isinstance(row, DailySignal) for row in rows):
        raise UpperLimitDelayContractError("signals must contain DailySignal values")
    if len({row.symbol for row in rows}) != len(rows):
        raise UpperLimitDelayContractError("signals contain duplicate symbols")
    signal_session = calendar.session_on(decision_date, as_of=decision_at)
    if decision_at != signal_session.close_at + timedelta(minutes=30):
        raise UpperLimitDelayContractError("decision_at must equal D close plus 30 minutes")
    entry = calendar.next_session(decision_date, as_of=decision_at)
    exit_session = calendar.next_session(entry.session_date, as_of=decision_at)
    retained, _ = retained_triplet(decision_date, entry.session_date, exit_session.session_date)
    if not retained:
        raise UpperLimitDelayContractError("D, D+1 and D+2 must remain in one split")
    eligible = tuple(row for row in rows if _eligible(row))
    ranked = tuple(
        sorted(
            ((row.symbol, row.median_amount_cny) for row in eligible if row.is_event),
            key=lambda item: (-item[1], item[0]),
        )
    )
    selected = ranked[:MAX_POSITIONS]
    symbols = tuple(symbol for symbol, _ in selected)
    return Target(
        decision_date,
        entry.session_date,
        exit_session.session_date,
        len(eligible),
        len(ranked),
        symbols,
        selected,
        tuple((symbol, 1.0 / MAX_POSITIONS) for symbol in symbols),
        len(symbols) / MAX_POSITIONS,
    )


def matched_reference_return(gross_target: float, d1_open: float, d2_open: float) -> float:
    """Return gross_target * (D+2/D+1 - 1), never an investable ETF account."""
    exposure = _finite(gross_target, "gross_target")
    entry, exit_price = (
        _finite(d1_open, "D+1 reference open", positive=True),
        _finite(d2_open, "D+2 reference open", positive=True),
    )
    if not 0.0 <= exposure <= 1.0:
        raise UpperLimitDelayContractError("gross_target must be in [0, 1]")
    result = exposure * (exit_price / entry - 1.0)
    if not math.isfinite(result):
        raise UpperLimitDelayContractError("reference return is nonfinite")
    return result


def qfq_execution_limits(
    qfq_open: float, raw_open: float, up_limit: float, down_limit: float
) -> tuple[float, float]:
    adjusted, raw = (
        _finite(qfq_open, "qfq_open", positive=True),
        _finite(raw_open, "raw_open", positive=True),
    )
    upper, lower = (
        _finite(up_limit, "up_limit", positive=True),
        _finite(down_limit, "down_limit", positive=True),
    )
    if lower > upper:
        raise UpperLimitDelayContractError("down_limit cannot exceed up_limit")
    ratio = adjusted / raw
    return upper * ratio, lower * ratio
