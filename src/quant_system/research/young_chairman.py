"""Outcome-free PIT signal builder for the young-chairman historical replication."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
import math
from numbers import Real
from statistics import fmean
from typing import Literal

from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity


RESEARCH_ID = "A_SHARE_YOUNG_CHAIRMAN_LONG_HORIZON_PIT_REPLICATION_V1_20260716"
LINEAGE_TYPE = "HISTORICAL_PIT_REPLICATION"
BENCHMARK_SYMBOL = "510300.SH"
MARKET_CAP_MIN_CNY = 1_000_000_000.0
HORIZON_SESSIONS = (252, 756, 1260)
COST_BPS_PER_SIDE = 50.0
REQUIRED_COVERAGE_DOMAINS = frozenset(
    {
        "management",
        "market_cap",
        "raw_bars",
        "adjusted_bars",
        "accepted_calendar",
        "listing_delisting",
        "limit_status",
        "suspension_status",
        "corporate_actions",
    }
)


class YoungChairmanContractError(ValueError):
    """One input violates the frozen replication contract."""


def _finite_positive(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise YoungChairmanContractError(f"{field} must be positive finite numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise YoungChairmanContractError(f"{field} must be positive finite numeric")
    return parsed


def _text(value: object, field: str) -> str:
    parsed = str(value).strip()
    if not parsed:
        raise YoungChairmanContractError(f"{field} must be nonempty")
    return parsed


def _source(value: object, field: str) -> SourceIdentity:
    if not isinstance(value, SourceIdentity):
        raise YoungChairmanContractError(f"{field} must be a SourceIdentity")
    return value


@dataclass(frozen=True)
class ManagementRecord:
    symbol: str
    person_id: str
    title: str
    ann_date: date
    begin_date: date
    end_date: date | None
    birthday: date | None
    birthday_precision: Literal["day", "year", "unknown"]
    source: SourceIdentity

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _text(self.symbol, "symbol"))
        object.__setattr__(self, "person_id", _text(self.person_id, "person_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        if any(type(value) is not date for value in (self.ann_date, self.begin_date)):
            raise YoungChairmanContractError("management dates must be date values")
        if self.end_date is not None and (
            type(self.end_date) is not date or self.end_date < self.begin_date
        ):
            raise YoungChairmanContractError("end_date must not precede begin_date")
        if self.birthday_precision == "unknown":
            if self.birthday is not None:
                raise YoungChairmanContractError("unknown birthday precision requires no birthday")
        elif type(self.birthday) is not date:
            raise YoungChairmanContractError("known birthday precision requires a birthday")
        elif self.birthday_precision == "year":
            if (self.birthday.month, self.birthday.day) != (1, 1):
                raise YoungChairmanContractError("year-only birthday must use January 1 sentinel")
        elif self.birthday_precision != "day":
            raise YoungChairmanContractError("unsupported birthday_precision")
        _source(self.source, "management source")


@dataclass(frozen=True)
class MarketCapPoint:
    symbol: str
    session_date: date
    total_mv_cny: float
    source: SourceIdentity

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _text(self.symbol, "symbol"))
        if type(self.session_date) is not date:
            raise YoungChairmanContractError("market-cap session_date must be a date")
        object.__setattr__(
            self, "total_mv_cny", _finite_positive(self.total_mv_cny, "total_mv_cny")
        )
        _source(self.source, "market-cap source")


@dataclass(frozen=True)
class DailyBar:
    symbol: str
    session_date: date
    raw_open: float
    raw_close: float
    adjusted_open: float
    adjusted_close: float
    raw_source: SourceIdentity
    adjusted_source: SourceIdentity
    corporate_action_source: SourceIdentity

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _text(self.symbol, "symbol"))
        if type(self.session_date) is not date:
            raise YoungChairmanContractError("bar session_date must be a date")
        for field in ("raw_open", "raw_close", "adjusted_open", "adjusted_close"):
            object.__setattr__(self, field, _finite_positive(getattr(self, field), field))
        _source(self.raw_source, "raw_source")
        _source(self.adjusted_source, "adjusted_source")
        _source(self.corporate_action_source, "corporate_action_source")


@dataclass(frozen=True)
class SecurityState:
    symbol: str
    as_of_date: date
    list_date: date
    delist_date: date | None
    is_suspended: bool
    is_limit_up: bool
    listing_source: SourceIdentity
    suspension_source: SourceIdentity
    limit_source: SourceIdentity

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _text(self.symbol, "symbol"))
        if any(type(value) is not date for value in (self.as_of_date, self.list_date)):
            raise YoungChairmanContractError("security-state dates must be date values")
        if self.delist_date is not None and (
            type(self.delist_date) is not date or self.delist_date < self.list_date
        ):
            raise YoungChairmanContractError("delist_date must not precede list_date")
        if any(type(value) is not bool for value in (self.is_suspended, self.is_limit_up)):
            raise YoungChairmanContractError("security-state flags must be boolean")
        _source(self.listing_source, "listing_source")
        _source(self.suspension_source, "suspension_source")
        _source(self.limit_source, "limit_source")


@dataclass(frozen=True)
class PITDomainCoverage:
    domain: str
    start: date
    end: date
    complete: bool
    source: SourceIdentity

    def __post_init__(self) -> None:
        object.__setattr__(self, "domain", _text(self.domain, "domain"))
        if type(self.start) is not date or type(self.end) is not date or self.start > self.end:
            raise YoungChairmanContractError("coverage dates must form a closed interval")
        if type(self.complete) is not bool:
            raise YoungChairmanContractError("coverage complete must be boolean")
        _source(self.source, "coverage source")


SignalStatus = Literal["ELIGIBLE", "INELIGIBLE", "BLOCKED"]


@dataclass(frozen=True)
class SignalAssessment:
    symbol: str
    signal_date: date
    entry_date: date
    status: SignalStatus
    reasons: tuple[str, ...]
    conservative_age_upper: int | None = None
    weekly_close_mean_30: float | None = None


@dataclass(frozen=True)
class PlannedEvent:
    symbol: str
    signal_date: date
    entry_date: date
    exit_date: date
    horizon_sessions: int


@dataclass(frozen=True)
class HorizonPlan:
    horizon_sessions: int
    events: tuple[PlannedEvent, ...]
    incomplete_count: int
    overlap_excluded_count: int


def _blocked(symbol: str, signal: date, entry: date, *reasons: str) -> SignalAssessment:
    return SignalAssessment(symbol, signal, entry, "BLOCKED", tuple(sorted(set(reasons))))


def _qualifying_chairman(title: str) -> bool:
    normalized = "".join(title.split())
    return "董事长" in normalized and not any(
        marker in normalized for marker in ("副董事长", "名誉董事长", "荣誉董事长")
    )


def _age_upper(record: ManagementRecord, signal_date: date) -> int | None:
    if record.birthday is None or record.birthday_precision == "unknown":
        return None
    if record.birthday >= signal_date:
        raise YoungChairmanContractError("birthday must precede signal_date")
    if record.birthday_precision == "year":
        return signal_date.year - record.birthday.year
    birthday_passed = (signal_date.month, signal_date.day) >= (
        record.birthday.month,
        record.birthday.day,
    )
    return signal_date.year - record.birthday.year - (0 if birthday_passed else 1)


def _third_anniversary(list_date: date) -> date:
    try:
        return list_date.replace(year=list_date.year + 3)
    except ValueError:
        return date(list_date.year + 3, 2, 28)


def _coverage_reasons(
    rows: Sequence[PITDomainCoverage],
    *,
    history_start: date,
    signal_date: date,
    entry_date: date,
    cutoff,
) -> tuple[str, ...]:
    by_domain: dict[str, PITDomainCoverage] = {}
    reasons: list[str] = []
    for row in rows:
        if row.domain in by_domain:
            reasons.append(f"duplicate_coverage:{row.domain}")
        by_domain[row.domain] = row
    for domain in sorted(REQUIRED_COVERAGE_DOMAINS - by_domain.keys()):
        reasons.append(f"missing_coverage:{domain}")
    for domain in sorted(REQUIRED_COVERAGE_DOMAINS & by_domain.keys()):
        row = by_domain[domain]
        if not row.complete:
            reasons.append(f"incomplete_coverage:{domain}")
        if row.source.available_at > cutoff:
            reasons.append(f"late_coverage:{domain}")
        required_start = history_start if domain in {
            "raw_bars", "adjusted_bars", "accepted_calendar", "corporate_actions"
        } else signal_date
        required_end = entry_date if domain in {
            "accepted_calendar", "limit_status", "suspension_status"
        } else signal_date
        if row.start > required_start or row.end < required_end:
            reasons.append(f"coverage_range_gap:{domain}")
    return tuple(reasons)


def evaluate_signal(
    *,
    symbol: str,
    signal_date: date,
    entry_session: AcceptedSession,
    calendar: AcceptedSessionCalendar,
    managers: Sequence[ManagementRecord],
    market_cap: MarketCapPoint | None,
    security_state: SecurityState | None,
    bars: Sequence[DailyBar],
    coverage: Sequence[PITDomainCoverage],
) -> SignalAssessment:
    """Evaluate one signal only from bytes available before the next accepted open."""

    symbol = _text(symbol, "symbol")
    if type(signal_date) is not date or not isinstance(entry_session, AcceptedSession):
        raise YoungChairmanContractError("signal_date and entry_session are required")
    entry_date = entry_session.session_date
    cutoff = entry_session.open_at
    try:
        observed_entry = calendar.next_session(signal_date, as_of=cutoff)
    except (TypeError, ValueError) as exc:
        return _blocked(symbol, signal_date, entry_date, f"calendar:{type(exc).__name__}")
    if observed_entry != entry_session:
        return _blocked(symbol, signal_date, entry_date, "entry_not_next_accepted_open")

    frozen_bars = tuple(sorted(bars, key=lambda row: row.session_date))
    if not frozen_bars:
        return _blocked(symbol, signal_date, entry_date, "missing_bar_history")
    if any(row.symbol != symbol for row in frozen_bars):
        raise YoungChairmanContractError("all bars must match symbol")
    dates = tuple(row.session_date for row in frozen_bars)
    if len(dates) != len(set(dates)):
        raise YoungChairmanContractError("bar dates must be unique")
    if dates[-1] != signal_date or any(value > signal_date for value in dates):
        return _blocked(symbol, signal_date, entry_date, "bar_window_not_cut_at_signal")

    reasons = list(
        _coverage_reasons(
            coverage,
            history_start=dates[0],
            signal_date=signal_date,
            entry_date=entry_date,
            cutoff=cutoff,
        )
    )
    for row in frozen_bars:
        for source_name, source in (
            ("raw", row.raw_source),
            ("adjusted", row.adjusted_source),
            ("corporate_action", row.corporate_action_source),
        ):
            if source.available_at > cutoff:
                reasons.append(f"late_{source_name}_bar:{row.session_date.isoformat()}")
        try:
            calendar.session_on(row.session_date, as_of=cutoff)
        except (TypeError, ValueError):
            reasons.append(f"unaccepted_bar_session:{row.session_date.isoformat()}")
    if market_cap is None:
        reasons.append("missing_signal_date_market_cap")
    elif market_cap.symbol != symbol or market_cap.session_date != signal_date:
        reasons.append("market_cap_identity_mismatch")
    elif market_cap.source.available_at > cutoff:
        reasons.append("late_signal_date_market_cap")
    if security_state is None:
        reasons.append("missing_security_state")
    elif security_state.symbol != symbol or security_state.as_of_date != entry_date:
        reasons.append("security_state_identity_mismatch")
    else:
        for name, source in (
            ("listing", security_state.listing_source),
            ("suspension", security_state.suspension_source),
            ("limit", security_state.limit_source),
        ):
            if source.available_at > cutoff:
                reasons.append(f"late_{name}_state")
    if reasons:
        return _blocked(symbol, signal_date, entry_date, *reasons)

    known_managers = tuple(
        row
        for row in managers
        if row.symbol == symbol
        and row.ann_date <= signal_date
        and row.source.available_at <= cutoff
        and row.begin_date < signal_date
        and (row.end_date is None or row.end_date >= signal_date)
        and _qualifying_chairman(row.title)
    )
    if not known_managers:
        return SignalAssessment(
            symbol, signal_date, entry_date, "INELIGIBLE", ("no_active_qualifying_chairman",)
        )
    if len(known_managers) != 1:
        return _blocked(symbol, signal_date, entry_date, "ambiguous_active_chairmen")
    chairman = known_managers[0]
    age_upper = _age_upper(chairman, signal_date)
    if age_upper is None:
        return _blocked(symbol, signal_date, entry_date, "birthday_precision_unknown")

    assert market_cap is not None and security_state is not None
    ineligible: list[str] = []
    if age_upper >= 40:
        ineligible.append("chairman_age_upper_not_below_40")
    if not security_state.list_date <= signal_date < _third_anniversary(
        security_state.list_date
    ):
        ineligible.append("not_within_first_three_calendar_years")
    if security_state.delist_date is not None and entry_date > security_state.delist_date:
        ineligible.append("not_listed_at_entry")
    if security_state.is_suspended:
        ineligible.append("entry_session_suspended")
    if security_state.is_limit_up:
        ineligible.append("entry_session_limit_up_not_executable")
    if market_cap.total_mv_cny <= MARKET_CAP_MIN_CNY:
        ineligible.append("market_cap_not_above_1bn")

    if len(frozen_bars) < 11:
        return _blocked(symbol, signal_date, entry_date, "fewer_than_11_daily_closes")
    closes = tuple(row.adjusted_close for row in frozen_bars)
    ma5_now, ma10_now = fmean(closes[-5:]), fmean(closes[-10:])
    ma5_previous, ma10_previous = fmean(closes[-6:-1]), fmean(closes[-11:-1])
    if not (ma5_now > ma10_now and ma5_previous <= ma10_previous):
        ineligible.append("ma5_did_not_cross_above_ma10")

    current_week = signal_date.isocalendar()[:2]
    weekly_last: dict[tuple[int, int], DailyBar] = {}
    for row in frozen_bars:
        week = row.session_date.isocalendar()[:2]
        if week < current_week:
            weekly_last[week] = row
    completed_weeks = tuple(weekly_last[key].adjusted_close for key in sorted(weekly_last))
    if len(completed_weeks) < 30:
        return _blocked(symbol, signal_date, entry_date, "fewer_than_30_completed_weeks")
    weekly_mean = fmean(completed_weeks[-30:])
    if frozen_bars[-1].adjusted_close >= weekly_mean:
        ineligible.append("close_not_below_30week_mean")

    return SignalAssessment(
        symbol,
        signal_date,
        entry_date,
        "INELIGIBLE" if ineligible else "ELIGIBLE",
        tuple(ineligible),
        age_upper,
        weekly_mean,
    )


def plan_fixed_horizon_events(
    assessments: Sequence[SignalAssessment],
    session_dates: Sequence[date],
) -> tuple[HorizonPlan, ...]:
    """Apply fixed horizons and per-symbol non-overlap without reading returns."""

    frozen = tuple(sorted(assessments, key=lambda row: (row.symbol, row.entry_date)))
    if any(row.status != "ELIGIBLE" for row in frozen):
        raise YoungChairmanContractError("only ELIGIBLE assessments may be planned")
    identities = tuple((row.symbol, row.signal_date) for row in frozen)
    if len(identities) != len(set(identities)):
        raise YoungChairmanContractError("signal identities must be unique")
    sessions = tuple(session_dates)
    if not sessions or any(type(value) is not date for value in sessions):
        raise YoungChairmanContractError("session_dates must be nonempty dates")
    if any(left >= right for left, right in zip(sessions, sessions[1:])):
        raise YoungChairmanContractError("session_dates must be unique and increasing")
    positions = {value: index for index, value in enumerate(sessions)}
    if any(row.entry_date not in positions for row in frozen):
        raise YoungChairmanContractError("every entry_date must be an accepted session")

    plans: list[HorizonPlan] = []
    for horizon in HORIZON_SESSIONS:
        events: list[PlannedEvent] = []
        incomplete = 0
        overlaps = 0
        last_exit: dict[str, date] = {}
        for row in frozen:
            previous_exit = last_exit.get(row.symbol)
            if previous_exit is not None and row.signal_date <= previous_exit:
                overlaps += 1
                continue
            exit_position = positions[row.entry_date] + horizon
            if exit_position >= len(sessions):
                incomplete += 1
                last_exit[row.symbol] = date.max
                continue
            exit_date = sessions[exit_position]
            events.append(
                PlannedEvent(
                    row.symbol,
                    row.signal_date,
                    row.entry_date,
                    exit_date,
                    horizon,
                )
            )
            last_exit[row.symbol] = exit_date
        plans.append(HorizonPlan(horizon, tuple(events), incomplete, overlaps))
    return tuple(plans)


__all__ = [
    "BENCHMARK_SYMBOL",
    "COST_BPS_PER_SIDE",
    "DailyBar",
    "HORIZON_SESSIONS",
    "HorizonPlan",
    "LINEAGE_TYPE",
    "MARKET_CAP_MIN_CNY",
    "ManagementRecord",
    "MarketCapPoint",
    "PITDomainCoverage",
    "PlannedEvent",
    "REQUIRED_COVERAGE_DOMAINS",
    "RESEARCH_ID",
    "SecurityState",
    "SignalAssessment",
    "YoungChairmanContractError",
    "evaluate_signal",
    "plan_fixed_horizon_events",
]
