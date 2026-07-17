"""Pure aggregate calculations for the read-only Macro Risk Shadow Phase 1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
import math
from numbers import Real
from pathlib import Path
from statistics import median
from typing import Any, Literal
from zoneinfo import ZoneInfo


RESEARCH_ID = "A_SHARE_MACRO_RISK_SHADOW_PHASE1_V1_20260718"
DEFINITION_PATH = Path("research/definitions/a_share_macro_risk_shadow_phase1_v1.json")
DEFINITION_SHA256 = "42c64bc1cf1b8244837df3c833f8997e167919c58a4697d4d725483ff1265df7"
SNAPSHOT_ID = "a_share_qfq_personal_research_20260716_v5"
DATABASE_SHA256 = "e636bb80e300f89e46831e91275c6f2167e370e81a00b21b300e253f6107bee0"
MAX_STALENESS_CALENDAR_DAYS = 7
SHANGHAI = ZoneInfo("Asia/Shanghai")
COMPONENTS = (
    "trend_120",
    "realized_volatility_20",
    "realized_volatility_60",
    "drawdown_120",
    "positive_return_breadth_60",
    "above_moving_average_breadth_60",
    "amount_breadth_20",
    "limit_down_share",
    "suspension_share",
)
class _MissingComponent(ValueError):
    pass


def _finite(value: object, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise _MissingComponent(name)
    try:
        parsed = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise _MissingComponent(name) from exc
    if not math.isfinite(parsed) or (positive and parsed <= 0.0):
        raise _MissingComponent(name)
    return parsed


def _series(
    values: tuple[float | None, ...],
    exact_length: int,
    name: str,
    *,
    positive: bool,
) -> tuple[float, ...]:
    if type(values) is not tuple or len(values) != exact_length:
        raise _MissingComponent(name)
    parsed = tuple(_finite(value, name, positive=positive) for value in values)
    if not positive and any(value < 0.0 for value in parsed):
        raise _MissingComponent(name)
    return parsed


def _clip(value: float, name: str) -> float:
    return _finite(min(1.0, max(0.0, value)), name)


def _log_change(current: float, prior: float, name: str) -> float:
    return _finite(math.log(current) - math.log(prior), name)


def _simple_return(current: float, prior: float, name: str) -> float:
    try:
        value = math.expm1(_log_change(current, prior, name))
    except OverflowError as exc:
        raise _MissingComponent(name) from exc
    return _finite(value, name)


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


@dataclass(frozen=True)
class MacroRiskInput:
    as_of: datetime
    generated_at: datetime
    snapshot_id: str
    database_sha256: str
    accepted_session_dates: tuple[date, ...]
    stock_price_session_dates: tuple[date, ...]
    stock_amount_session_dates: tuple[date, ...]
    flag_session_date: date
    ordered_universe_count: int
    price_universe_digest: str
    amount_universe_digest: str
    limit_down_universe_digest: str
    suspension_universe_digest: str
    benchmark_closes: tuple[float | None, ...]
    stock_closes: tuple[tuple[float | None, ...], ...]
    stock_amount_cny: tuple[tuple[float | None, ...], ...]
    limit_down_flags: tuple[bool | None, ...]
    suspension_flags: tuple[bool | None, ...]


@dataclass(frozen=True)
class ComponentContribution:
    component_id: str
    raw_value: float
    unit_risk: float
    contribution_points: float

@dataclass(frozen=True)
class ShadowAssessment:
    status: Literal["SHADOW_READY", "SHADOW_INPUT_BLOCKED"]
    risk_score: float | None
    risk_level: Literal["GREEN", "AMBER", "RED"] | None
    confidence: float
    component_contributions: tuple[ComponentContribution, ...]
    stale_components: tuple[str, ...]
    missing_components: tuple[str, ...]
    as_of: str
    generated_at: str
    input_snapshot_identity: tuple[tuple[str, str], ...]
    position_effect_enabled: bool = False
    strategy_selection_enabled: bool = False
    order_or_signal_enabled: bool = False
    strategy_candidate_available: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["input_snapshot_identity"] = dict(self.input_snapshot_identity)
        return payload


def _timestamp_text(value: object) -> str:
    return value.isoformat() if isinstance(value, datetime) else ""


def _contract_valid(data: MacroRiskInput) -> bool:
    if data.snapshot_id != SNAPSHOT_ID or data.database_sha256 != DATABASE_SHA256:
        return False
    if not isinstance(data.as_of, datetime) or not isinstance(data.generated_at, datetime):
        return False
    if (
        not isinstance(data.as_of.tzinfo, ZoneInfo)
        or data.as_of.tzinfo.key != "Asia/Shanghai"
        or data.generated_at.tzinfo is None
    ):
        return False
    if (data.as_of.hour, data.as_of.minute, data.as_of.second, data.as_of.microsecond) != (
        15,
        0,
        0,
        0,
    ):
        return False
    if data.generated_at < data.as_of:
        return False
    dates = data.accepted_session_dates
    if type(dates) is not tuple or len(dates) != 121:
        return False
    if any(type(day) is not date or day.weekday() >= 5 for day in dates):
        return False
    if any(left >= right for left, right in zip(dates, dates[1:])):
        return False
    if dates[-1] != data.as_of.date():
        return False
    if data.stock_price_session_dates != dates[-61:]:
        return False
    if data.stock_amount_session_dates != dates[-21:]:
        return False
    if type(data.flag_session_date) is not date or data.flag_session_date != dates[-1]:
        return False
    if type(data.ordered_universe_count) is not int or data.ordered_universe_count <= 0:
        return False
    containers = (
        data.benchmark_closes,
        data.stock_closes,
        data.stock_amount_cny,
        data.limit_down_flags,
        data.suspension_flags,
    )
    if any(type(value) is not tuple for value in containers):
        return False
    if not (
        len(data.stock_closes)
        == len(data.stock_amount_cny)
        == len(data.limit_down_flags)
        == len(data.suspension_flags)
        == data.ordered_universe_count
    ):
        return False
    digests = (
        data.price_universe_digest,
        data.amount_universe_digest,
        data.limit_down_universe_digest,
        data.suspension_universe_digest,
    )
    return all(_valid_digest(value) for value in digests) and len(set(digests)) == 1


def _realized_volatility(closes: tuple[float, ...], window: int, name: str) -> float:
    selected = closes[-(window + 1) :]
    returns = tuple(
        _log_change(selected[index], selected[index - 1], name)
        for index in range(1, len(selected))
    )
    mean = _finite(math.fsum(returns) / window, name)
    variance = _finite(
        math.fsum((value - mean) ** 2 for value in returns) / (window - 1), name
    )
    return _finite(math.sqrt(variance * 252.0), name)


def _price_breadth(data: MacroRiskInput, *, above_average: bool) -> float:
    selected = 0
    for values in data.stock_closes:
        closes = _series(values, 61, "stock_closes", positive=True)
        if above_average:
            baseline = _finite(
                math.fsum(value / 60.0 for value in closes[:-1]),
                "above_moving_average_breadth_60",
            )
            selected += closes[-1] > baseline
        else:
            selected += _log_change(
                closes[-1], closes[0], "positive_return_breadth_60"
            ) > 0.0
    return _finite(selected / data.ordered_universe_count, "price_breadth")


def _amount_breadth(data: MacroRiskInput) -> float:
    expanded = 0
    for values in data.stock_amount_cny:
        amounts = _series(values, 21, "stock_amount_cny", positive=False)
        if any(value <= 0.0 for value in amounts[:-1]):
            raise _MissingComponent("amount_breadth_20")
        expanded += amounts[-1] >= median(amounts[:-1])
    return _finite(
        expanded / data.ordered_universe_count, "amount_breadth_20"
    )


def _flag_share(data: MacroRiskInput, field: str, name: str) -> float:
    flags = getattr(data, field)
    if any(type(value) is not bool for value in flags):
        raise _MissingComponent(name)
    return _finite(sum(flags) / data.ordered_universe_count, name)


def _raw_components(data: MacroRiskInput) -> tuple[dict[str, float], tuple[str, ...]]:
    raw: dict[str, float] = {}
    missing: list[str] = []
    try:
        closes = _series(data.benchmark_closes, 121, "benchmark_closes", positive=True)
    except _MissingComponent:
        missing.extend(COMPONENTS[:4])
    else:
        benchmark_functions = {
            "trend_120": lambda: _simple_return(
                closes[-1], closes[0], "trend_120"
            ),
            "realized_volatility_20": lambda: _realized_volatility(
                closes, 20, "realized_volatility_20"
            ),
            "realized_volatility_60": lambda: _realized_volatility(
                closes, 60, "realized_volatility_60"
            ),
            "drawdown_120": lambda: _simple_return(
                closes[-1], max(closes), "drawdown_120"
            ),
        }
        for component, function in benchmark_functions.items():
            try:
                raw[component] = _finite(function(), component)
            except (OverflowError, _MissingComponent):
                missing.append(component)
    for component, function in (
        (
            "positive_return_breadth_60",
            lambda: _price_breadth(data, above_average=False),
        ),
        (
            "above_moving_average_breadth_60",
            lambda: _price_breadth(data, above_average=True),
        ),
        ("amount_breadth_20", lambda: _amount_breadth(data)),
        (
            "limit_down_share",
            lambda: _flag_share(data, "limit_down_flags", "limit_down_share"),
        ),
        (
            "suspension_share",
            lambda: _flag_share(data, "suspension_flags", "suspension_share"),
        ),
    ):
        try:
            raw[component] = _finite(function(), component)
        except (OverflowError, _MissingComponent):
            missing.append(component)
    missing_set = set(missing)
    return raw, tuple(name for name in COMPONENTS if name in missing_set)


def _unit_risk(component: str, value: float) -> float:
    if component == "trend_120":
        result = (0.10 - value) / 0.30
    elif component in {"realized_volatility_20", "realized_volatility_60"}:
        result = (value - 0.10) / 0.30
    elif component == "drawdown_120":
        result = -value / 0.30
    elif component in {
        "positive_return_breadth_60",
        "above_moving_average_breadth_60",
        "amount_breadth_20",
    }:
        result = 1.0 - value
    elif component == "limit_down_share":
        result = value / 0.10
    elif component == "suspension_share":
        result = value / 0.05
    else:
        raise _MissingComponent(component)
    return _clip(_finite(result, component), component)


def _blocked(
    data: MacroRiskInput,
    *,
    stale: tuple[str, ...] = (),
    missing: tuple[str, ...] = (),
) -> ShadowAssessment:
    return ShadowAssessment(
        "SHADOW_INPUT_BLOCKED",
        None,
        None,
        0.0,
        (),
        stale,
        missing,
        _timestamp_text(data.as_of),
        _timestamp_text(data.generated_at),
        (("snapshot_id", data.snapshot_id), ("database_sha256", data.database_sha256)),
    )


def compute_shadow(data: MacroRiskInput) -> ShadowAssessment:
    """Return one aggregate assessment, or fail closed without a score."""

    if not isinstance(data, MacroRiskInput):
        raise TypeError("data must be MacroRiskInput")
    if not _contract_valid(data):
        return _blocked(data, missing=COMPONENTS)
    local_generated = data.generated_at.astimezone(SHANGHAI)
    age_days = (local_generated.date() - data.as_of.date()).days
    raw, missing = _raw_components(data)
    stale = COMPONENTS if age_days > MAX_STALENESS_CALENDAR_DAYS else ()
    if stale or missing:
        return _blocked(data, stale=stale, missing=missing)
    try:
        contributions = tuple(
            ComponentContribution(
                component,
                _finite(raw[component], component),
                unit_risk := _unit_risk(component, raw[component]),
                _finite(100.0 * unit_risk / 9.0, component),
            )
            for component in COMPONENTS
        )
        score = round(
            _finite(
                math.fsum(item.contribution_points for item in contributions),
                "risk_score",
            ),
            6,
        )
        score = _finite(score, "risk_score")
    except (OverflowError, _MissingComponent):
        return _blocked(data, missing=COMPONENTS)
    level: Literal["GREEN", "AMBER", "RED"]
    if score < 33.333333:
        level = "GREEN"
    elif score < 66.666667:
        level = "AMBER"
    else:
        level = "RED"
    return ShadowAssessment(
        "SHADOW_READY",
        score,
        level,
        1.0,
        contributions,
        (),
        (),
        data.as_of.isoformat(),
        data.generated_at.isoformat(),
        (("snapshot_id", data.snapshot_id), ("database_sha256", data.database_sha256)),
    )
