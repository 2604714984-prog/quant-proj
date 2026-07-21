"""One-hypothesis Employment Situation release-day SPY intraday adapter."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import fmean, stdev
from typing import Iterable, Sequence

from quant_system.data.reader import query, sha256_file


class ResearchInputError(ValueError):
    """Raised when a frozen input contract is not satisfied."""


@dataclass(frozen=True)
class DailyBar:
    trade_date: date
    open: float
    close: float


@dataclass(frozen=True)
class EventObservation:
    trade_date: date
    gross_return: float
    net_return: float
    non_event_month_mean: float
    net_premium: float


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def frozen_monthly_release_dates(
    text: str, *, start: date, end: date
) -> tuple[date, ...]:
    """Select the first ALFRED Employment Situation date in each month."""
    by_month: dict[tuple[int, int], list[date]] = defaultdict(list)
    for line in text.splitlines():
        try:
            item = date.fromisoformat(line.strip())
        except ValueError:
            continue
        if start <= item <= end:
            by_month[(item.year, item.month)].append(item)
    expected_months = (end.year - start.year) * 12 + end.month - start.month + 1
    if len(by_month) != expected_months:
        raise ResearchInputError("release list does not cover every frozen month")
    return tuple(min(by_month[key]) for key in sorted(by_month))


def _finite_positive(value: float, label: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ResearchInputError(f"{label} must be finite and positive")
    return number


def build_observations(
    bars: Iterable[DailyBar],
    event_dates: Sequence[date],
    *,
    expected_closed_dates: Sequence[date],
    round_trip_cost: float,
    minimum_non_event_sessions: int,
) -> tuple[tuple[EventObservation, ...], tuple[date, ...]]:
    """Build event observations without using the comparator as a trading signal."""
    cost = float(round_trip_cost)
    if not math.isfinite(cost) or cost < 0:
        raise ResearchInputError("round-trip cost must be finite and nonnegative")
    by_date: dict[date, DailyBar] = {}
    gross_by_month: dict[tuple[int, int], list[float]] = defaultdict(list)
    events = tuple(event_dates)
    if tuple(sorted(set(events))) != events:
        raise ResearchInputError("event dates must be unique and ordered")
    event_set = set(events)
    for bar in bars:
        if bar.trade_date in by_date:
            raise ResearchInputError("duplicate SPY trade date")
        open_price = _finite_positive(bar.open, "open")
        close_price = _finite_positive(bar.close, "close")
        normalized = DailyBar(bar.trade_date, open_price, close_price)
        by_date[bar.trade_date] = normalized
        if bar.trade_date not in event_set:
            gross_by_month[(bar.trade_date.year, bar.trade_date.month)].append(
                close_price / open_price - 1.0
            )

    expected_closed = set(expected_closed_dates)
    missing = tuple(item for item in events if item not in by_date)
    if set(missing) != expected_closed:
        raise ResearchInputError("missing event dates differ from frozen market closures")

    observations: list[EventObservation] = []
    for event_date in events:
        if event_date in expected_closed:
            continue
        bar = by_date[event_date]
        comparator = gross_by_month[(event_date.year, event_date.month)]
        if len(comparator) < minimum_non_event_sessions:
            raise ResearchInputError("insufficient non-event sessions in event month")
        gross = bar.close / bar.open - 1.0
        net = gross - cost
        baseline = fmean(comparator)
        observations.append(
            EventObservation(event_date, gross, net, baseline, net - baseline)
        )
    return tuple(observations), missing


def circular_block_lower_bound(
    values: Sequence[float],
    *,
    block_length: int,
    replications: int,
    seed: int,
    quantile: float,
) -> float:
    """Return a deterministic one-sided circular-block bootstrap lower bound."""
    sample = tuple(float(value) for value in values)
    if not sample or any(not math.isfinite(value) for value in sample):
        raise ResearchInputError("bootstrap sample must be finite and nonempty")
    if not 1 <= block_length <= len(sample):
        raise ResearchInputError("invalid block length")
    if replications < 100:
        raise ResearchInputError("too few bootstrap replications")
    if not 0 < quantile < 0.5:
        raise ResearchInputError("lower-bound quantile must be between zero and one half")
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(replications):
        drawn: list[float] = []
        while len(drawn) < len(sample):
            start = rng.randrange(len(sample))
            drawn.extend(
                sample[(start + offset) % len(sample)]
                for offset in range(block_length)
            )
        means.append(fmean(drawn[: len(sample)]))
    means.sort()
    position = (len(means) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(means) - 1)
    weight = position - lower
    return means[lower] * (1.0 - weight) + means[upper] * weight


def summarize_split(
    observations: Sequence[EventObservation],
    *,
    start: date,
    end: date,
    expected_count: int,
    bootstrap: dict[str, int | float],
) -> dict[str, object]:
    selected = tuple(item for item in observations if start <= item.trade_date <= end)
    if len(selected) != expected_count:
        raise ResearchInputError("observed event count differs from frozen split count")
    premiums = tuple(item.net_premium for item in selected)
    annual: dict[int, list[float]] = defaultdict(list)
    for item in selected:
        annual[item.trade_date.year].append(item.net_premium)
    lower_bound = circular_block_lower_bound(
        premiums,
        block_length=int(bootstrap["block_length"]),
        replications=int(bootstrap["replications"]),
        seed=int(bootstrap["seed"]),
        quantile=float(bootstrap["lower_quantile"]),
    )
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "event_count": len(selected),
        "mean_gross_intraday_return": fmean(item.gross_return for item in selected),
        "mean_net_intraday_return": fmean(item.net_return for item in selected),
        "mean_non_event_month_intraday_return": fmean(
            item.non_event_month_mean for item in selected
        ),
        "mean_net_premium": fmean(premiums),
        "net_premium_sample_std": stdev(premiums),
        "net_premium_positive_fraction": sum(value > 0 for value in premiums)
        / len(premiums),
        "annual_mean_net_premium": {
            str(year): fmean(values) for year, values in sorted(annual.items())
        },
        "one_sided_lower_bound": lower_bound,
        "gate_pass": lower_bound > 0.0,
    }


def _hash_observations(observations: Sequence[EventObservation]) -> str:
    lines = []
    for item in observations:
        lines.append(
            ",".join(
                [
                    item.trade_date.isoformat(),
                    format(item.gross_return, ".17g"),
                    format(item.net_return, ".17g"),
                    format(item.non_event_month_mean, ".17g"),
                    format(item.net_premium, ".17g"),
                ]
            )
        )
    return sha256_bytes(("\n".join(lines) + "\n").encode())


def execute(definition_path: Path, database_path: Path) -> dict[str, object]:
    definition_bytes = definition_path.read_bytes()
    definition = json.loads(definition_bytes)
    data = definition["data_contract"]
    actual_db_hash = sha256_file(database_path)
    if actual_db_hash != data["database_sha256"]:
        raise ResearchInputError("database hash differs from frozen definition")

    sql = (
        "SELECT trade_date, open, close, snapshot_id, source_document_sha256, "
        "source_url, price_adjustment_status, available_at "
        "FROM us_equity_research.sina_daily_bars "
        "WHERE symbol = ? AND trade_date BETWEEN ? AND ? ORDER BY trade_date"
    )
    response = query(
        database_path,
        sql,
        [definition["instrument"], data["start"], data["end"]],
        max_rows=int(data["expected_row_count"]) + 1,
    )
    if response.truncated or len(response.rows) != int(data["expected_row_count"]):
        raise ResearchInputError("SPY row count differs from frozen definition")

    bars: list[DailyBar] = []
    input_lines: list[str] = []
    for row in response.rows:
        trade_date, open_price, close_price, snapshot, document_hash, source_url, status, available = row
        if snapshot != data["snapshot_id"] or document_hash != data["source_document_sha256"]:
            raise ResearchInputError("source identity differs from frozen definition")
        if source_url != data["source_url"] or status != data["price_adjustment_status"]:
            raise ResearchInputError("source semantics differ from frozen definition")
        if available is not None:
            raise ResearchInputError("unexpected available_at semantics")
        bar = DailyBar(trade_date, float(open_price), float(close_price))
        bars.append(bar)
        input_lines.append(
            f"{trade_date.isoformat()},{format(float(open_price), '.17g')},"
            f"{format(float(close_price), '.17g')},{document_hash}"
        )

    event_dates = tuple(date.fromisoformat(value) for value in data["event_dates"])
    event_payload = "".join(f"{item.isoformat()}\n" for item in event_dates).encode()
    if sha256_bytes(event_payload) != data["event_dates_sha256"]:
        raise ResearchInputError("event-date identity differs from frozen definition")
    observations, excluded = build_observations(
        bars,
        event_dates,
        expected_closed_dates=tuple(
            date.fromisoformat(value) for value in data["expected_closed_release_dates"]
        ),
        round_trip_cost=float(definition["execution"]["round_trip_cost"]),
        minimum_non_event_sessions=int(
            definition["comparison"]["minimum_non_event_sessions_per_month"]
        ),
    )

    summaries: dict[str, object] = {}
    for name, split in definition["splits"].items():
        summaries[name] = summarize_split(
            observations,
            start=date.fromisoformat(split["start"]),
            end=date.fromisoformat(split["end"]),
            expected_count=int(split["expected_observed_events"]),
            bootstrap=split["bootstrap"],
        )
    passed = all(bool(value["gate_pass"]) for value in summaries.values())
    return {
        "schema_version": "compact-research-result-v1",
        "research_id": definition["research_id"],
        "status": "HISTORICAL_SCREEN_PASS" if passed else "HISTORICAL_SCREEN_FAIL",
        "definition_sha256": sha256_bytes(definition_bytes),
        "adapter_sha256": sha256_file(Path(__file__)),
        "database_sha256": actual_db_hash,
        "source_snapshot_id": data["snapshot_id"],
        "source_document_sha256": data["source_document_sha256"],
        "input_rows_sha256": sha256_bytes(("\n".join(input_lines) + "\n").encode()),
        "event_dates_sha256": data["event_dates_sha256"],
        "event_dates_total": len(event_dates),
        "observed_event_dates": len(observations),
        "excluded_market_closed_dates": [item.isoformat() for item in excluded],
        "observation_identity_sha256": _hash_observations(observations),
        "splits": summaries,
        "decision_rule": definition["decision_rule"],
        "input_classification": "RETROSPECTIVE_SECONDARY_PRICE_SOURCE_NOT_STRICT_PIT",
        "strategy_candidate_available": False,
        "limitations": definition["limitations"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--definition", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = execute(args.definition, args.database)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
