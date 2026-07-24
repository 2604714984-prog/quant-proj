"""Disposable one-shot adapter for the frozen SEC Form D SPY/cash mechanism."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import statistics
from typing import Any

from quant_system.backtest import Portfolio, TransactionCostModel
from quant_system.markets.us import cash_settlement_lag_sessions


RESEARCH_ID = "US_EQ_SEC_FORMD_PRIVATE_CAPITAL_FORMATION_YOY_SPY_CASH_V1"
INITIAL_CAPITAL = 40_000.0
COMMISSION_RATE = 0.001
SYMBOL = "SPY"
VALIDATION_MONTHS = (date(2021, 2, 1), date(2023, 5, 1))
SECONDARY_MONTHS = (date(2023, 8, 1), date(2026, 5, 1))
TERMINAL_MONTHS = {
    "validation": date(2023, 6, 1),
    "secondary": date(2026, 6, 1),
}
INTERVALS = {"validation": 28, "secondary": 34}
GATE_NAMES = (
    "terminal_wealth_above_fifty_fifty",
    "paired_mean_active_return_above_zero",
    "maximum_drawdown_no_worse_than_spy",
)


class ContractError(RuntimeError):
    """The exact frozen input or execution contract was not satisfied."""


@dataclass(frozen=True)
class State:
    month: date
    state: str
    source_row_sha256: str


@dataclass(frozen=True)
class Session:
    session_date: date
    raw_open: float
    raw_close: float


@dataclass(frozen=True)
class Distribution:
    event_id: str
    ex_date: date
    pay_date: date
    amount_per_share: float


@dataclass(frozen=True)
class Performance:
    terminal_wealth: float
    interval_returns: tuple[float, ...]
    maximum_drawdown: float
    boundaries: tuple[float, ...]
    daily_open_nav: tuple[float, ...]
    trade_count: int


@dataclass
class Account:
    portfolio: Portfolio
    boundaries: list[float] = field(default_factory=list)
    daily_open_nav: list[float] = field(default_factory=list)
    trade_count: int = 0


@dataclass(frozen=True)
class SegmentResult:
    segment: str
    states: tuple[State, ...]
    support: dict[str, int | bool]
    strategy: Performance
    fifty_fifty: Performance
    spy_buyhold: Performance
    paired_mean_active_return: float
    gates: tuple[tuple[str, bool], ...]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ContractError(f"{path.name} is not a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
        ):
            raise ContractError(f"{path.name} changed while hashing")
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def exact_bytes(path: Path, expected_sha256: str) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ContractError(f"{path.name} is not a regular file")
        chunks: list[bytes] = []
        digest = hashlib.sha256()
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            while chunk := handle.read(1024 * 1024):
                chunks.append(chunk)
                digest.update(chunk)
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
        ):
            raise ContractError(f"{path.name} changed while reading")
    finally:
        os.close(descriptor)
    if digest.hexdigest() != expected_sha256:
        raise ContractError(f"{path.name} SHA256 mismatch")
    return b"".join(chunks)


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key {key}")
        result[key] = value
    return result


def strict_json(payload: bytes) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ContractError(f"nonfinite JSON constant {value}")

    value = json.loads(
        payload,
        parse_constant=reject_constant,
        object_pairs_hook=unique_object,
    )
    if not isinstance(value, dict):
        raise ContractError("JSON root must be an object")
    return value


def strict_jsonl(payload: bytes) -> list[dict[str, Any]]:
    if not payload or not payload.endswith(b"\n"):
        raise ContractError("JSONL must be nonempty and newline terminated")
    rows: list[dict[str, Any]] = []
    for line in payload.splitlines():
        if not line:
            raise ContractError("JSONL contains a blank row")
        rows.append(strict_json(line))
    return rows


def parse_sha256(value: str) -> str:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise argparse.ArgumentTypeError("expected lowercase SHA256")
    return value


def parse_month(value: object) -> date:
    if not isinstance(value, str):
        raise ContractError("month must be a string")
    parsed = date.fromisoformat(value)
    if parsed.day != 1:
        raise ContractError("month must be its first calendar day")
    return parsed


def parse_date(value: object, name: str) -> date:
    if not isinstance(value, str):
        raise ContractError(f"{name} must be a date string")
    return date.fromisoformat(value)


def require_positive(value: object, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ContractError(f"{name} must be numeric") from error
    if not math.isfinite(number) or number <= 0:
        raise ContractError(f"{name} must be finite and positive")
    return number


def quarter_index(year: int, quarter: int) -> int:
    if quarter not in {1, 2, 3, 4}:
        raise ContractError("quarter out of range")
    return year * 4 + quarter - 1


def quarter_label(index: int) -> str:
    year, offset = divmod(index, 4)
    return f"{year}:Q{offset + 1}"


def expected_months(segment: str) -> tuple[date, ...]:
    if segment not in INTERVALS:
        raise ContractError("segment must be validation or secondary")
    start, end = VALIDATION_MONTHS if segment == "validation" else SECONDARY_MONTHS
    months: list[date] = []
    current = start
    while current <= end:
        months.append(current)
        current = (
            date(current.year + 1, 1, 1)
            if current.month == 12
            else date(current.year, current.month + 1, 1)
        )
    if len(months) != INTERVALS[segment]:
        raise ContractError("internal month contract drift")
    return tuple(months)


def derive_states(
    counts_rows: list[dict[str, Any]],
    state_rows: list[dict[str, Any]],
    segment: str,
) -> tuple[State, ...]:
    counts: dict[int, int] = {}
    for row in counts_rows:
        label = row.get("quarter")
        count = row.get("nonfund_initial_offerings")
        if not isinstance(label, str) or not isinstance(count, int) or isinstance(count, bool):
            raise ContractError("quarterly count row has invalid types")
        match = __import__("re").fullmatch(r"(\d{4}):Q([1-4])", label)
        if match is None or count < 0:
            raise ContractError("quarterly count row is invalid")
        index = quarter_index(int(match.group(1)), int(match.group(2)))
        if index in counts:
            raise ContractError("duplicate quarterly count")
        counts[index] = count

    months = expected_months(segment)
    if len(state_rows) != len(months):
        raise ContractError("state row count differs from frozen split")
    states: list[State] = []
    for month, recorded in zip(months, state_rows):
        execution_quarter = quarter_index(month.year, (month.month - 1) // 3 + 1)
        latest_index, earlier_index = execution_quarter - 2, execution_quarter - 6
        if latest_index not in counts or earlier_index not in counts:
            raise ContractError("quarterly count coverage is incomplete")
        latest, earlier = counts[latest_index], counts[earlier_index]
        canonical = {
            "execution_quarter": quarter_label(execution_quarter),
            "latest_nonfund_initial_offerings": latest,
            "latest_source_quarter": quarter_label(latest_index),
            "month": month.isoformat(),
            "state": "SPY" if latest > earlier else "CASH",
            "year_earlier_nonfund_initial_offerings": earlier,
            "year_earlier_source_quarter": quarter_label(earlier_index),
        }
        row_hash = sha256_bytes(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("ascii")
        )
        expected = dict(canonical, source_row_sha256=row_hash)
        if recorded != expected:
            raise ContractError("recorded state is not mechanically derived")
        states.append(State(month, canonical["state"], row_hash))
    return tuple(states)


def state_support(states: tuple[State, ...]) -> dict[str, int | bool]:
    labels = tuple(state.state for state in states)
    spy_to_cash = sum(
        left == "SPY" and right == "CASH"
        for left, right in zip(labels, labels[1:])
    )
    cash_to_spy = sum(
        left == "CASH" and right == "SPY"
        for left, right in zip(labels, labels[1:])
    )
    support: dict[str, int | bool] = {
        "intervals": len(labels),
        "spy_months": labels.count("SPY"),
        "cash_months": labels.count("CASH"),
        "spy_to_cash_transitions": spy_to_cash,
        "cash_to_spy_transitions": cash_to_spy,
    }
    support["passes"] = (
        support["spy_months"] >= 4
        and support["cash_months"] >= 4
        and spy_to_cash >= 1
        and cash_to_spy >= 1
    )
    return support


def load_sessions(
    market_payload: bytes,
    calendar_payload: bytes,
) -> tuple[Session, ...]:
    market_rows = strict_jsonl(market_payload)
    calendar_rows = strict_jsonl(calendar_payload)
    if len(market_rows) != len(calendar_rows):
        raise ContractError("market and calendar row counts differ")
    sessions: list[Session] = []
    previous: date | None = None
    for market, calendar in zip(market_rows, calendar_rows):
        market_date = parse_date(market.get("session_date"), "market session_date")
        calendar_date = parse_date(calendar.get("session_date"), "calendar session_date")
        if market_date != calendar_date or (previous is not None and market_date <= previous):
            raise ContractError("market/calendar dates are not exact and ordered")
        if (
            market.get("symbol") != SYMBOL
            or market.get("currency") != "USD"
            or market.get("price_basis") != "unadjusted_raw_open_close"
            or calendar.get("exchange") != "XNYS"
            or market.get("calendar_row_sha256") != calendar.get("row_identity_sha256")
        ):
            raise ContractError("market/calendar identity drift")
        open_at = datetime.fromisoformat(str(calendar.get("open_at")))
        close_at = datetime.fromisoformat(str(calendar.get("close_at")))
        if open_at.tzinfo is None or close_at.tzinfo is None or close_at <= open_at:
            raise ContractError("calendar timestamp identity is invalid")
        sessions.append(
            Session(
                market_date,
                require_positive(market.get("raw_open"), "raw_open"),
                require_positive(market.get("raw_close"), "raw_close"),
            )
        )
        previous = market_date
    return tuple(sessions)


def load_distributions(payload: bytes) -> tuple[Distribution, ...]:
    rows = strict_jsonl(payload)
    result: list[Distribution] = []
    identities: set[str] = set()
    for row in rows:
        event_id = row.get("event_id")
        if (
            row.get("symbol") != SYMBOL
            or row.get("action_type") != "cash_distribution"
            or row.get("currency") != "USD"
            or row.get("unit") != "per_share"
            or not isinstance(event_id, str)
            or not event_id
            or event_id in identities
        ):
            raise ContractError("distribution identity drift")
        ex_date = parse_date(row.get("ex_date"), "ex_date")
        pay_date = parse_date(row.get("pay_date"), "pay_date")
        if pay_date < ex_date:
            raise ContractError("distribution pay_date precedes ex_date")
        result.append(
            Distribution(
                event_id,
                ex_date,
                pay_date,
                require_positive(row.get("amount_per_share"), "amount_per_share"),
            )
        )
        identities.add(event_id)
    return tuple(sorted(result, key=lambda item: (item.ex_date, item.event_id)))


def first_session(month: date, sessions: tuple[Session, ...]) -> date:
    for session in sessions:
        if (session.session_date.year, session.session_date.month) == (
            month.year,
            month.month,
        ):
            return session.session_date
    raise ContractError("market packet does not cover a required month")


def current_shares(portfolio: Portfolio) -> int:
    position = portfolio.positions.get(SYMBOL)
    shares = 0.0 if position is None else position.shares
    if not math.isfinite(shares) or shares < 0 or not float(shares).is_integer():
        raise ContractError("portfolio shares are not nonnegative whole shares")
    return int(shares)


def target_shares(nav: float, decision_close: float, weight: float) -> int:
    if weight not in {0.0, 0.5, 1.0}:
        raise ContractError("target weight is outside the frozen set")
    if not math.isfinite(nav) or nav <= 0:
        raise ContractError("pretrade NAV is invalid")
    return math.floor(weight * nav / require_positive(decision_close, "decision_close"))


def rebalance(
    account: Account,
    target: int,
    session: Session,
    accepted_dates: tuple[date, ...],
) -> None:
    current = current_shares(account.portfolio)
    if current > target:
        lag = cash_settlement_lag_sessions(session.session_date)
        following = tuple(day for day in accepted_dates if day > session.session_date)
        if len(following) < lag:
            raise ContractError("calendar does not cover US cash settlement")
        account.portfolio.sell(
            SYMBOL,
            current - target,
            session.raw_open,
            session.session_date,
            settlement_date=following[lag - 1],
            accepted_settlement_sessions=following[:lag],
        )
        account.trade_count += 1
    elif current < target:
        affordable = math.floor(
            (account.portfolio.available_cash + 1e-9)
            / (session.raw_open * (1.0 + COMMISSION_RATE))
        )
        shares = min(target - current, affordable)
        if shares > 0:
            account.portfolio.buy(
                SYMBOL,
                shares,
                session.raw_open,
                session.session_date,
            )
            account.trade_count += 1


def performance(account: Account, expected_intervals: int) -> Performance:
    if len(account.boundaries) != expected_intervals + 1:
        raise ContractError("boundary count differs from frozen interval count")
    returns = tuple(
        right / left - 1.0
        for left, right in zip(account.boundaries, account.boundaries[1:])
    )
    if any(not math.isfinite(value) or value <= -1.0 for value in returns):
        raise ContractError("interval return is invalid")
    peak = INITIAL_CAPITAL
    drawdown = 0.0
    for value in account.daily_open_nav:
        if not math.isfinite(value) or value <= 0:
            raise ContractError("daily NAV is invalid")
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - 1.0)
    return Performance(
        account.boundaries[-1],
        returns,
        drawdown,
        tuple(account.boundaries),
        tuple(account.daily_open_nav),
        account.trade_count,
    )


def run_segment(
    segment: str,
    states: tuple[State, ...],
    sessions: tuple[Session, ...],
    distributions: tuple[Distribution, ...],
) -> SegmentResult:
    expected = INTERVALS.get(segment)
    if expected is None or len(states) != expected or tuple(s.month for s in states) != expected_months(segment):
        raise ContractError("state split differs from frozen contract")
    support = state_support(states)
    if support["passes"] is not True:
        raise ContractError("state support preflight failed")
    decision_dates = tuple(first_session(state.month, sessions) for state in states)
    terminal_date = first_session(TERMINAL_MONTHS[segment], sessions)
    dates = tuple(session.session_date for session in sessions)
    index_by_date = {day: index for index, day in enumerate(dates)}
    first_index = index_by_date[decision_dates[0]]
    terminal_index = index_by_date[terminal_date]
    if first_index != 1 or terminal_index != len(sessions) - 1:
        raise ContractError("market packet boundary coverage is not exact")
    state_by_date = dict(zip(decision_dates, states))
    actions_by_date: dict[date, list[Distribution]] = {}
    for action in distributions:
        if action.ex_date not in index_by_date or action.ex_date >= terminal_date:
            raise ContractError("distribution lies outside the active segment")
        actions_by_date.setdefault(action.ex_date, []).append(action)

    accounts = tuple(
        Account(
            Portfolio.us(
                INITIAL_CAPITAL,
                costs=TransactionCostModel(commission_rate=COMMISSION_RATE),
            )
        )
        for _ in range(3)
    )
    prior_strategy_state: str | None = None
    for index in range(first_index, terminal_index + 1):
        session = sessions[index]
        for account in accounts:
            account.portfolio.start_session(session.session_date)
        state = state_by_date.get(session.session_date)
        if state is not None or session.session_date == terminal_date:
            prior_close = sessions[index - 1].raw_close
            for account in accounts:
                account.boundaries.append(account.portfolio.nav({SYMBOL: prior_close}))
            if session.session_date == terminal_date:
                break
        for action in actions_by_date.get(session.session_date, []):
            for account in accounts:
                account.portfolio.apply_cash_distribution(
                    SYMBOL,
                    event_id=action.event_id,
                    amount_per_share=action.amount_per_share,
                    ex_date=action.ex_date,
                    pay_date=action.pay_date,
                )
        if state is not None:
            prior_close = sessions[index - 1].raw_close
            if prior_strategy_state is None or state.state != prior_strategy_state:
                rebalance(
                    accounts[0],
                    target_shares(
                        accounts[0].boundaries[-1],
                        prior_close,
                        1.0 if state.state == "SPY" else 0.0,
                    ),
                    session,
                    dates,
                )
            rebalance(
                accounts[1],
                target_shares(accounts[1].boundaries[-1], prior_close, 0.5),
                session,
                dates,
            )
            if prior_strategy_state is None:
                rebalance(
                    accounts[2],
                    target_shares(accounts[2].boundaries[-1], prior_close, 1.0),
                    session,
                    dates,
                )
            prior_strategy_state = state.state
        for account in accounts:
            account.daily_open_nav.append(
                account.portfolio.nav({SYMBOL: session.raw_open})
            )
    strategy, fifty, buyhold = (
        performance(account, expected) for account in accounts
    )
    active = tuple(
        left - right
        for left, right in zip(strategy.interval_returns, fifty.interval_returns)
    )
    paired_mean = statistics.fmean(active)
    gates = tuple(
        zip(
            GATE_NAMES,
            (
                strategy.terminal_wealth > fifty.terminal_wealth,
                paired_mean > 0.0,
                strategy.maximum_drawdown >= buyhold.maximum_drawdown,
            ),
        )
    )
    return SegmentResult(
        segment,
        states,
        support,
        strategy,
        fifty,
        buyhold,
        paired_mean,
        gates,
    )


def atomic_json(path: Path, value: dict[str, Any]) -> str:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("ascii")
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return sha256_bytes(payload)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--segment", choices=("validation", "secondary"), required=True)
    for name in (
        "definition",
        "counts",
        "states",
        "input-receipt",
        "market",
        "calendar",
        "actions",
        "lifecycle",
        "central-db",
        "claim",
        "result",
    ):
        result.add_argument(f"--{name}", required=True, type=Path)
    for name in (
        "definition",
        "counts",
        "states",
        "input-receipt",
        "market",
        "calendar",
        "actions",
        "lifecycle",
        "central-db",
        "expected-adapter",
    ):
        result.add_argument(f"--{name}-sha256", required=True, type=parse_sha256)
    result.add_argument("--accepted-validation-result", type=Path)
    result.add_argument("--accepted-validation-result-sha256", type=parse_sha256)
    return result


def metric(performance_value: Performance) -> dict[str, float | int]:
    return {
        "terminal_wealth": performance_value.terminal_wealth,
        "arithmetic_mean_interval_return": statistics.fmean(
            performance_value.interval_returns
        ),
        "maximum_drawdown": performance_value.maximum_drawdown,
        "trade_count": performance_value.trade_count,
    }


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.claim.exists() or args.result.exists():
        raise ContractError("one-use claim or result already exists")
    adapter_sha = sha256_file(Path(__file__))
    if adapter_sha != args.expected_adapter_sha256:
        raise ContractError("adapter SHA256 mismatch")
    exact_bytes(args.definition, args.definition_sha256)
    input_receipt = strict_json(
        exact_bytes(args.input_receipt, args.input_receipt_sha256)
    )
    if (
        input_receipt.get("research_id") != RESEARCH_ID
        or input_receipt.get("status") != "INPUT_ACCEPTED_STATE_SUPPORT_PASS"
    ):
        raise ContractError("Form D input receipt is not accepted")
    normalized = input_receipt.get("normalized")
    if not isinstance(normalized, dict):
        raise ContractError("Form D normalized identity is missing")
    expected_counts = normalized.get("quarterly_counts_sha256")
    expected_states = normalized.get(f"{args.segment}_states_sha256")
    if (
        expected_counts != args.counts_sha256
        or expected_states != args.states_sha256
    ):
        raise ContractError("Form D CLI/input receipt hash binding drift")
    counts_rows = strict_jsonl(exact_bytes(args.counts, args.counts_sha256))
    state_rows = strict_jsonl(exact_bytes(args.states, args.states_sha256))
    states = derive_states(counts_rows, state_rows, args.segment)
    support = state_support(states)
    receipt_support = input_receipt.get("support")
    if (
        not isinstance(receipt_support, dict)
        or receipt_support.get(args.segment) != support
        or support["passes"] is not True
    ):
        raise ContractError("state support receipt does not reproduce")

    expected_market_hashes = {
        args.market: args.market_sha256,
        args.calendar: args.calendar_sha256,
        args.actions: args.actions_sha256,
        args.lifecycle: args.lifecycle_sha256,
    }
    for path, expected in expected_market_hashes.items():
        if sha256_file(path) != expected:
            raise ContractError(f"{path.name} preclaim SHA256 mismatch")
    if sha256_file(args.central_db) != args.central_db_sha256:
        raise ContractError("central DB preclaim SHA256 mismatch")
    if Path(str(args.central_db) + ".wal").exists():
        raise ContractError("central DB WAL is present")

    validation_identity: dict[str, Any] | None = None
    if args.segment == "secondary":
        if (
            args.accepted_validation_result is None
            or args.accepted_validation_result_sha256 is None
        ):
            raise ContractError("secondary requires accepted validation result")
        validation_identity = strict_json(
            exact_bytes(
                args.accepted_validation_result,
                args.accepted_validation_result_sha256,
            )
        )
        if (
            validation_identity.get("research_id") != RESEARCH_ID
            or validation_identity.get("status")
            != "VALIDATION_PASS_SECONDARY_ELIGIBLE"
            or validation_identity.get("adapter_sha256") != adapter_sha
            or validation_identity.get("definition_sha256")
            != args.definition_sha256
        ):
            raise ContractError("accepted validation identity drift")
        recorded_gates = validation_identity.get("gates")
        if (
            not isinstance(recorded_gates, dict)
            or set(recorded_gates) != set(GATE_NAMES)
            or any(recorded_gates[name] is not True for name in GATE_NAMES)
        ):
            raise ContractError("accepted validation gates are not exact PASS")
    elif (
        args.accepted_validation_result is not None
        or args.accepted_validation_result_sha256 is not None
    ):
        raise ContractError("validation cannot accept a prior result")

    claim = {
        "schema_version": "formd-private-capital-one-use-claim-v1",
        "claimed_at_utc": datetime.now().astimezone().isoformat(),
        "research_id": RESEARCH_ID,
        "segment": args.segment,
        "adapter_sha256": adapter_sha,
        "definition_sha256": args.definition_sha256,
        "input_receipt_sha256": args.input_receipt_sha256,
        "counts_sha256": args.counts_sha256,
        "states_sha256": args.states_sha256,
        "market_sha256": args.market_sha256,
        "calendar_sha256": args.calendar_sha256,
        "actions_sha256": args.actions_sha256,
        "lifecycle_sha256": args.lifecycle_sha256,
        "central_db_sha256": args.central_db_sha256,
        "accepted_validation_result_sha256": (
            args.accepted_validation_result_sha256
            if args.segment == "secondary"
            else None
        ),
        "market_values_opened_before_claim": False,
        "strategy_execution_performed_before_claim": False,
    }
    claim_sha = atomic_json(args.claim, claim)

    market_payload = exact_bytes(args.market, args.market_sha256)
    calendar_payload = exact_bytes(args.calendar, args.calendar_sha256)
    actions_payload = exact_bytes(args.actions, args.actions_sha256)
    exact_bytes(args.lifecycle, args.lifecycle_sha256)
    sessions = load_sessions(market_payload, calendar_payload)
    distributions = load_distributions(actions_payload)
    decision = run_segment(args.segment, states, sessions, distributions)
    if sha256_file(args.central_db) != args.central_db_sha256:
        raise ContractError("central DB changed during execution")
    if Path(str(args.central_db) + ".wal").exists():
        raise ContractError("central DB WAL appeared during execution")

    gates = {name: value for name, value in decision.gates}
    passed = all(gates.values())
    status_value = (
        "VALIDATION_PASS_SECONDARY_ELIGIBLE"
        if args.segment == "validation" and passed
        else "VALIDATION_FAIL_CLOSED"
        if args.segment == "validation"
        else "RETROSPECTIVE_SECONDARY_PASS_PENDING_USER_REVIEW"
        if passed
        else "HOLDOUT_FAIL_CLOSED"
    )
    result = {
        "schema_version": "formd-private-capital-result-v1",
        "created_at_utc": datetime.now().astimezone().isoformat(),
        "research_id": RESEARCH_ID,
        "segment": args.segment,
        "status": status_value,
        "claim_sha256": claim_sha,
        "adapter_sha256": adapter_sha,
        "definition_sha256": args.definition_sha256,
        "input_receipt_sha256": args.input_receipt_sha256,
        "counts_sha256": args.counts_sha256,
        "states_sha256": args.states_sha256,
        "market_sha256": args.market_sha256,
        "calendar_sha256": args.calendar_sha256,
        "actions_sha256": args.actions_sha256,
        "lifecycle_sha256": args.lifecycle_sha256,
        "central_db_sha256_before_after": args.central_db_sha256,
        "support": decision.support,
        "gates": gates,
        "strategy": metric(decision.strategy),
        "fifty_fifty": metric(decision.fifty_fifty),
        "spy_buyhold": metric(decision.spy_buyhold),
        "paired_mean_active_return": decision.paired_mean_active_return,
        "confirmatory_p_value": None,
        "boundaries": {
            "classification": "RETROSPECTIVE_SECONDARY_REVISION_LIMITED",
            "database_write": False,
            "strategy_candidate_available": False,
            "rerun": False,
            "shadow": False,
            "paper": False,
            "broker": False,
            "live": False,
        },
    }
    result_sha = atomic_json(args.result, result)
    print(
        json.dumps(
            {
                "result_sha256": result_sha,
                "segment": args.segment,
                "status": status_value,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
