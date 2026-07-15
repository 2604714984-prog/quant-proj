#!/usr/bin/env python3
"""Replay the four legacy US ETF formulas from the local database.

Status: FROZEN_ONE_OFF_EVIDENCE / NO_GENERALIZATION. This is a frozen one-off
evidence reproducer, not a new strategy experiment. It is not a general-purpose
runner. Do not import or generalize it into the runtime API. It matches the
arithmetic in legacy
``scripts/four_strategies.py``: constant close-to-close weights and a fixed
quarterly cost deduction.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
from typing import Any

from quant_system.config import load_settings
from quant_system.data.reader import query


SYMBOLS = ("SPY", "QQQ", "GLD")
START = date(2016, 1, 1)
END = date(2025, 12, 31)
INITIAL_CASH = 40_000.0
REBALANCE_SESSIONS = 63
COST_BPS = 5.0
LEGACY_BLOB = "0a015ace9ebb637598c857b46c21a911c13b2e96"
LEGACY_REPORT_BLOB = "2d1444b06c99923f855844b30d1d29ab90e886d4"
FROZEN_EXPECTED_ROW_COUNT = 7_542
FROZEN_EXPECTED_SESSION_COUNT = 2_514
FROZEN_EXPECTED_FIRST_SESSION = date(2016, 1, 4)
FROZEN_EXPECTED_LAST_SESSION = date(2025, 12, 31)
FROZEN_EXPECTED_SNAPSHOT_ID = "sina_us_etf_20160101_20251231_e4c60497095e76f9"
FROZEN_EXPECTED_SLICE_SHA256 = (
    "7183133d689717670d9b8b9caae9116e7822e5bb78ed8351ffe0f029875e8701"
)
ROW_SHA256 = re.compile(r"[0-9a-f]{64}")
STRATEGIES = {
    "US31_SPY_GLD_50_50": {"SPY": 0.5, "QQQ": 0.0, "GLD": 0.5},
    "US36_SPY_QQQ_50_50": {"SPY": 0.5, "QQQ": 0.5, "GLD": 0.0},
    "US41_SPY_QQQ_GLD_EQUAL": {"SPY": 1 / 3, "QQQ": 1 / 3, "GLD": 1 / 3},
    "US46_QQQ_GLD_50_50": {"SPY": 0.0, "QQQ": 0.5, "GLD": 0.5},
}
LEGACY_HEADLINES = {
    "US31_SPY_GLD_50_50": {"sharpe": 1.188, "total_return": 2.84, "max_drawdown": -0.205},
    "US36_SPY_QQQ_50_50": {"sharpe": 0.846, "total_return": 3.38, "max_drawdown": -0.311},
    "US41_SPY_QQQ_GLD_EQUAL": {"sharpe": 1.115, "total_return": 3.46, "max_drawdown": -0.235},
    "US46_QQQ_GLD_50_50": {"sharpe": 1.246, "total_return": 4.04, "max_drawdown": -0.238},
}


class ReplayError(RuntimeError):
    pass


@dataclass(frozen=True)
class MarketSlice:
    sessions: tuple[date, ...]
    closes: dict[str, tuple[float, ...]]
    snapshot_id: str
    row_count: int
    slice_sha256: str
    available_at_missing: int


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def load_market_slice(database: Path) -> MarketSlice:
    result = query(
        database,
        """
        SELECT symbol, trade_date, close, snapshot_id, row_sha256, available_at
        FROM us_equity_research.sina_daily_bars
        WHERE symbol IN ('SPY', 'QQQ', 'GLD')
          AND trade_date BETWEEN DATE '2016-01-01' AND DATE '2025-12-31'
        ORDER BY trade_date, symbol
        """,
        max_rows=8_000,
    )
    if result.truncated or not result.rows:
        raise ReplayError("Sina market slice is empty or truncated")
    by_symbol: dict[str, dict[date, float]] = {symbol: {} for symbol in SYMBOLS}
    snapshots: set[str] = set()
    identities: list[str] = []
    missing_available_at = 0
    for symbol, session, close, snapshot, row_sha256, available_at in result.rows:
        if symbol not in by_symbol or type(session) is not date:
            raise ReplayError("unexpected symbol or session in market slice")
        price = float(close)
        if not math.isfinite(price) or price <= 0 or session in by_symbol[symbol]:
            raise ReplayError("duplicate or invalid close in market slice")
        by_symbol[symbol][session] = price
        snapshots.add(str(snapshot))
        if not isinstance(row_sha256, str) or ROW_SHA256.fullmatch(row_sha256) is None:
            raise ReplayError("row_sha256 must be lowercase 64-hex SHA-256")
        identities.append(row_sha256)
        missing_available_at += available_at is None
    common = set.intersection(*(set(values) for values in by_symbol.values()))
    sessions = tuple(sorted(common))
    if any(set(values) != common for values in by_symbol.values()):
        raise ReplayError("SPY, QQQ and GLD do not have an exact common calendar")
    if len(snapshots) != 1 or len(sessions) < 2:
        raise ReplayError("market slice must have one snapshot and at least two sessions")
    closes = {
        symbol: tuple(by_symbol[symbol][session] for session in sessions)
        for symbol in SYMBOLS
    }
    identity_payload = "".join(identities).encode()
    return MarketSlice(
        sessions=sessions,
        closes=closes,
        snapshot_id=next(iter(snapshots)),
        row_count=len(result.rows),
        slice_sha256=hashlib.sha256(identity_payload).hexdigest(),
        available_at_missing=missing_available_at,
    )


def replay(closes: dict[str, tuple[float, ...]], weights: dict[str, float]) -> dict[str, float]:
    lengths = {len(closes[symbol]) for symbol in SYMBOLS}
    if len(lengths) != 1 or next(iter(lengths)) < 2:
        raise ReplayError("close series must have one common length of at least two")
    if set(weights) != set(SYMBOLS) or not math.isclose(sum(weights.values()), 1.0):
        raise ReplayError("strategy weights must cover SPY, QQQ and GLD and sum to one")
    if any(not math.isfinite(weight) or weight < 0 for weight in weights.values()):
        raise ReplayError("strategy weights must be finite and nonnegative")
    n = next(iter(lengths))
    equity = [INITIAL_CASH]
    active_assets = sum(weight > 0 for weight in weights.values())
    for index in range(1, n):
        daily_return = math.fsum(
            weights[symbol]
            * (closes[symbol][index] / closes[symbol][index - 1] - 1.0)
            for symbol in SYMBOLS
        )
        value = equity[-1] * (1.0 + daily_return)
        if index % REBALANCE_SESSIONS == 0:
            value -= equity[-1] * COST_BPS / 10_000.0 * active_assets * 2
        if not math.isfinite(value) or value <= 0:
            raise ReplayError("equity became nonpositive or nonfinite")
        equity.append(value)
    returns = [equity[i] / equity[i - 1] - 1.0 for i in range(1, n)]
    mean = statistics.fmean(returns)
    stdev = statistics.stdev(returns)
    peak = equity[0]
    max_drawdown = 0.0
    for value in equity:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value / peak - 1.0)
    total_return = equity[-1] / equity[0] - 1.0
    return {
        "cagr": (1.0 + total_return) ** (252.0 / n) - 1.0,
        "final_equity": equity[-1],
        "max_drawdown": max_drawdown,
        "sharpe": mean / stdev * math.sqrt(252.0),
        "total_return": total_return,
    }


def build_report(market: MarketSlice) -> dict[str, Any]:
    boundary_counts_exact = (
        market.row_count == FROZEN_EXPECTED_ROW_COUNT
        and len(market.sessions) == FROZEN_EXPECTED_SESSION_COUNT
        and market.sessions[0] == FROZEN_EXPECTED_FIRST_SESSION
        and market.sessions[-1] == FROZEN_EXPECTED_LAST_SESSION
    )
    input_slice_hash_exact = market.slice_sha256 == FROZEN_EXPECTED_SLICE_SHA256
    snapshot_id_exact = market.snapshot_id == FROZEN_EXPECTED_SNAPSHOT_ID
    mismatch_reasons: list[str] = []
    if not boundary_counts_exact:
        mismatch_reasons.append("boundary_counts_mismatch")
    if not input_slice_hash_exact:
        mismatch_reasons.append("input_slice_hash_mismatch")
    if not snapshot_id_exact:
        mismatch_reasons.append("snapshot_id_mismatch")

    report: dict[str, Any] = {
        "schema_version": "legacy-us-etf-migration-replay-v1.1",
        "classification": "RETROSPECTIVE_MIGRATION_CONSISTENCY_ONLY",
        "evidence_state": "FROZEN_ONE_OFF_EVIDENCE",
        "generalization_allowed": False,
        "generalization_policy": "NO_GENERALIZATION",
        "legacy_implementation": {
            "blob_oid": LEGACY_BLOB,
            "formula": "constant_weight_close_returns_with_63_session_cost_deduction",
            "headline_report_blob_oid": LEGACY_REPORT_BLOB,
        },
        "source": {
            "available_at_missing": market.available_at_missing,
            "first_session": market.sessions[0].isoformat(),
            "last_session": market.sessions[-1].isoformat(),
            "row_count": market.row_count,
            "session_count": len(market.sessions),
            "slice_sha256": market.slice_sha256,
            "snapshot_id": market.snapshot_id,
        },
        "boundary_counts_exact": boundary_counts_exact,
        "input_slice_hash_exact": input_slice_hash_exact,
        "snapshot_id_exact": snapshot_id_exact,
        "mismatch_reasons": mismatch_reasons,
        "limitations": [
            "replays legacy close-to-close arithmetic rather than next-open holdings",
            "uses raw Sina closes and does not establish strict PIT or corporate-action completeness",
            "US31/US36/US41/US46 remain rejected and are not reopened by this replay",
        ],
        "strict_pit_eligible": False,
        "strategy_evidence_eligible": False,
        "strategy_candidate_available": False,
        "recommendation_available": False,
    }
    if mismatch_reasons:
        report.update(
            {
                "headline_metrics_reproduced": None,
                "legacy_headline_drift": None,
                "results": None,
                "status": "INPUT_SLICE_MISMATCH",
            }
        )
        return report

    results = {name: replay(market.closes, weights) for name, weights in STRATEGIES.items()}
    drift = {
        name: {
            metric: results[name][metric] - expected
            for metric, expected in LEGACY_HEADLINES[name].items()
        }
        for name in STRATEGIES
    }
    headline_reproduced = all(
        abs(values["sharpe"]) <= 0.01
        and abs(values["total_return"]) <= 0.05
        and abs(values["max_drawdown"]) <= 0.01
        for values in drift.values()
    )
    report.update(
        {
            "headline_metrics_reproduced": headline_reproduced,
            "legacy_headline_drift": drift,
            "results": results,
            "status": (
                "REPLAY_COMPLETE_HEADLINES_REPRODUCED"
                if headline_reproduced
                else "REPLAY_COMPLETE_HEADLINES_NOT_REPRODUCED"
            ),
        }
    )
    return report


def main(argv: list[str] | None = None) -> int:
    settings = load_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=settings.paths.database)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = build_report(load_market_slice(args.database))
    payload = _canonical(report)
    if args.output is None:
        print(payload.decode(), end="")
        return 0
    if args.output.exists() or args.output.with_suffix(args.output.suffix + ".sha256").exists():
        raise ReplayError("output already exists")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    args.output.with_suffix(args.output.suffix + ".sha256").write_text(
        f"{digest}  {args.output.name}\n", encoding="ascii"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
