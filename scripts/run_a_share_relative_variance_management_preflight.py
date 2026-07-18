#!/usr/bin/env python3
"""Outcome-free aggregate preflight for the frozen relative-variance family."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from quant_system.research import relative_variance_management as rvm  # noqa: E402

DEFINITION = ROOT / "research/definitions/a_share_relative_variance_managed_liquid_equity_v1.json"
ORDINARY = r"((600|601|603|605|688)[0-9]{3}\.SH|(000|001|002|003|300|301)[0-9]{3}\.SZ)"
SPLITS = ("development_2020_2021", "validation_2022_2023", "holdout_2024_2026h1")


class PreflightError(ValueError):
    pass


@dataclass(frozen=True)
class IntervalAudit:
    decision_date: date
    split_id: str
    selected_count: int
    qualified_count: int
    excluded_count: int
    invalid_variance_count: int = 0
    invalid_execution_panel_count: int = 0
    capital: rvm.CapitalIntervalAudit | None = None

    def __post_init__(self) -> None:
        if type(self.decision_date) is not date or self.split_id not in SPLITS:
            raise PreflightError("interval identity is invalid")
        values = (
            self.selected_count,
            self.qualified_count,
            self.excluded_count,
            self.invalid_variance_count,
            self.invalid_execution_panel_count,
        )
        if any(type(value) is not int or value < 0 for value in values):
            raise PreflightError("interval aggregate is invalid")
        if self.capital is not None and not isinstance(
            self.capital, rvm.CapitalIntervalAudit
        ):
            raise PreflightError("capital interval aggregate is invalid")


def _capture(path: Path, label: str) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            raise OSError
        return path.read_bytes()
    except OSError as exc:
        raise PreflightError(f"{label} must be a readable regular file") from exc


def _strict_json(raw: bytes, label: str) -> dict[str, object]:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        output: dict[str, object] = {}
        for key, value in values:
            if key in output:
                raise PreflightError(f"{label} has duplicate keys")
            output[key] = value
        return output

    def constant(value: str) -> object:
        raise PreflightError(f"{label} has nonfinite {value}")

    try:
        value = json.loads(raw.decode(), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreflightError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise PreflightError(f"{label} must be an object")
    return value


def _definition() -> dict[str, object]:
    raw = _capture(DEFINITION, "definition")
    if hashlib.sha256(raw).hexdigest() != rvm.DEFINITION_SHA256:
        raise PreflightError("definition SHA-256 changed")
    return _strict_json(raw, "definition")


def _digest(path: Path) -> tuple[str, int, int]:
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    stat = path.stat()
    return digest, stat.st_size, stat.st_mtime_ns


def _report(
    audits: Sequence[IntervalAudit],
    *,
    input_failure_count: int = 0,
    duplicate_key_count: int = 0,
) -> dict[str, object]:
    rows = tuple(audits)
    if not rows or len({row.decision_date for row in rows}) != len(rows):
        raise PreflightError("preflight intervals are empty or duplicate")
    if any(
        type(value) is not int or value < 0 for value in (input_failure_count, duplicate_key_count)
    ):
        raise PreflightError("failure counts are invalid")
    if any(row.capital is None for row in rows):
        raise PreflightError("capital feasibility is required before outcomes")
    capital = tuple(row.capital for row in rows if row.capital is not None)
    counts = {split: sum(row.split_id == split for row in rows) for split in SPLITS}
    minimum_selected = {
        split: min((row.selected_count for row in rows if row.split_id == split), default=0)
        for split in SPLITS
    }
    invalid = {
        split: sum(row.split_id == split and row.selected_count != rvm.BASKET_SIZE for row in rows)
        for split in SPLITS
    }
    excluded = {
        split: sum(row.excluded_count for row in rows if row.split_id == split) for split in SPLITS
    }
    invalid_variance = {
        split: sum(row.invalid_variance_count for row in rows if row.split_id == split)
        for split in SPLITS
    }
    invalid_panels = {
        split: sum(row.invalid_execution_panel_count for row in rows if row.split_id == split)
        for split in SPLITS
    }
    blocked = (
        input_failure_count > 0
        or duplicate_key_count > 0
        or any(invalid_variance.values())
        or any(invalid_panels.values())
    )
    structural = any(invalid.values()) or counts != {
        "development_2020_2021": 23,
        "validation_2022_2023": 23,
        "holdout_2024_2026h1": 29,
    }
    invalid_capital = sum(not item.gate_pass for item in capital)
    minimum_faithful = max(
        max(
            item.managed.minimum_faithful_capital_cny,
            item.comparator.minimum_faithful_capital_cny,
        )
        for item in capital
    )
    minimum_managed_margin = min(
        item.managed.invested_ratio
        - max(0.80 * item.intended_exposure, item.intended_exposure - 0.10)
        for item in capital
    )
    capital_status = (
        "LIVE_FEASIBILITY_FAIL_NO_OUTCOME"
        if invalid_capital
        else "CAPITAL_FEASIBILITY_PASS_NO_OUTCOME"
    )
    status = (
        "INPUT_BLOCKED"
        if blocked
        else "STRUCTURAL_FAIL"
        if structural
        else capital_status
    )

    def metric(value: float) -> float:
        if not math.isfinite(value):
            raise PreflightError("capital aggregate must be finite")
        return round(float(value), 12)

    return {
        "schema_version": "a-share-relative-variance-preflight-v1",
        "research_id": rvm.RESEARCH_ID,
        "phase": "OUTCOME_FREE_PREFLIGHT",
        "status": status,
        "snapshot_id": rvm.SNAPSHOT_ID,
        "snapshot_digest": rvm.SNAPSHOT_DIGEST,
        "database_sha256": rvm.DATABASE_SHA256,
        "calendar_snapshot_id": rvm.CALENDAR_SNAPSHOT_ID,
        "calendar_digest": rvm.CALENDAR_DIGEST,
        "available_at_status": "UNKNOWN_NOT_PIT_QUALIFIED",
        "split_interval_counts": counts,
        "retained_interval_count_by_split": counts,
        "split_minimum_selected_counts": minimum_selected,
        "split_invalid_interval_counts": invalid,
        "candidate_excluded_counts": excluded,
        "split_invalid_variance_counts": invalid_variance,
        "split_invalid_execution_panel_counts": invalid_panels,
        "input_failure_count": input_failure_count,
        "duplicate_key_count": duplicate_key_count,
        "basket_size": rvm.BASKET_SIZE,
        "historical_initial_cash_cny": int(rvm.HISTORICAL_INITIAL_CASH_CNY),
        "lot_size_shares": rvm.LOT_SIZE_SHARES,
        "maximum_minimum_faithful_capital_cny": metric(minimum_faithful),
        "minimum_target_nonzero_managed_positions": min(
            item.managed.target_nonzero_positions for item in capital
        ),
        "minimum_target_nonzero_comparator_positions": min(
            item.comparator.target_nonzero_positions for item in capital
        ),
        "minimum_nonzero_managed_positions": min(
            item.managed.filled_positions for item in capital
        ),
        "minimum_nonzero_comparator_positions": min(
            item.comparator.filled_positions for item in capital
        ),
        "minimum_managed_invested_ratio": metric(
            min(item.managed.invested_ratio for item in capital)
        ),
        "minimum_comparator_invested_ratio": metric(
            min(item.comparator.invested_ratio for item in capital)
        ),
        "minimum_managed_invested_ratio_gate_margin": metric(minimum_managed_margin),
        "maximum_total_commission_drag_bps": metric(
            max(
                max(
                    item.managed.total_commission_drag_bps,
                    item.comparator.total_commission_drag_bps,
                )
                for item in capital
            )
        ),
        "maximum_minimum_commission_drag_bps": metric(
            max(
                max(
                    item.managed.minimum_commission_drag_bps,
                    item.comparator.minimum_commission_drag_bps,
                )
                for item in capital
            )
        ),
        "capacity_rejection_count": sum(
            item.managed.capacity_rejection_count
            + item.comparator.capacity_rejection_count
            for item in capital
        ),
        "capacity_rejection_count_by_path": {
            "managed": sum(item.managed.capacity_rejection_count for item in capital),
            "comparator": sum(item.comparator.capacity_rejection_count for item in capital),
        },
        "market_rule_rejection_count": sum(
            item.managed.market_rule_rejection_count
            + item.comparator.market_rule_rejection_count
            for item in capital
        ),
        "market_rule_rejection_count_by_path": {
            "managed": sum(item.managed.market_rule_rejection_count for item in capital),
            "comparator": sum(item.comparator.market_rule_rejection_count for item in capital),
        },
        "invalid_capital_interval_count": invalid_capital,
        "capital_feasibility_status": capital_status,
        "qfq_close_sessions_required": rvm.CLOSE_SESSIONS,
        "historical_outcome_authorized": False,
        "holding_returns_opened": False,
        "holdout_outcomes_opened": False,
        "forward_outcomes_opened": False,
        "security_identifiers_in_report": False,
        "strategy_candidate_available": False,
    }


SCAN_SQL = r"""
WITH cal AS (
 SELECT trade_date,row_number() OVER(ORDER BY trade_date) n
 FROM a_share.a_share_trade_calendar WHERE snapshot_id=? AND exchange=? AND source=?
 AND is_open=1 AND synthetic_data=false AND trade_date<='20260630'
), months AS (
 SELECT min(trade_date) first_d,max(trade_date) d FROM cal GROUP BY strftime(strptime(trade_date,'%Y%m%d'),'%Y%m')
), ints AS (
 SELECT d,lead(d) OVER(ORDER BY d) next_d,lead(first_d) OVER(ORDER BY d) entry_d,lead(first_d,2) OVER(ORDER BY d) exit_d FROM months
), scope AS (
 SELECT *,CASE WHEN entry_d BETWEEN '20200101' AND '20211231' AND exit_d<='20211231' THEN 'development_2020_2021'
 WHEN entry_d BETWEEN '20220101' AND '20231231' AND exit_d<='20231231' THEN 'validation_2022_2023'
 WHEN entry_d BETWEEN '20240101' AND '20260630' AND exit_d<='20260630' THEN 'holdout_2024_2026h1' END split_id
 FROM ints
), master AS (
 SELECT ts_code,market board,list_date FROM a_share.a_share_symbol_master
 WHERE regexp_full_match(ts_code,?) AND coalesce(regexp_full_match(list_date,'[0-9]{8}'),false) AND try_strptime(list_date,'%Y%m%d') IS NOT NULL QUALIFY row_number() OVER(PARTITION BY ts_code ORDER BY ingested_at DESC,snapshot_id DESC)=1
), bars AS (
 SELECT b.*,c.n,count(*) OVER(PARTITION BY ts_code,trade_date) key_n FROM a_share.a_share_canonical_daily_bars b JOIN cal c USING(trade_date)
 WHERE snapshot_id=? AND trade_date<='20260630'
), bu AS (SELECT * FROM bars WHERE key_n=1), windows AS (
 SELECT b.*,count(*) OVER w close_n,count(qfq_close) OVER w close_value_n,min(n) OVER w first_n,
 count(*) OVER w20 amount_n,count(amount) OVER w20 amount_value_n,median(amount) OVER w20 med_amount,
 bool_and(qfq_close IS NOT NULL AND isfinite(qfq_close) AND qfq_close>0 AND quality_status IS NOT DISTINCT FROM ?
 AND synthetic_data IS NOT DISTINCT FROM false AND coalesce(regexp_full_match(row_hash,'[0-9a-f]{64}'),false)) OVER w close_ok,
 bool_and(amount IS NOT NULL AND isfinite(amount) AND amount>=0) OVER w20 amount_ok
 FROM bu b WINDOW w AS(PARTITION BY ts_code ORDER BY n ROWS BETWEEN 273 PRECEDING AND CURRENT ROW),
 w20 AS(PARTITION BY ts_code ORDER BY n ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
), observed AS (
 SELECT m.* FROM master m JOIN (SELECT DISTINCT ts_code FROM bu) b USING(ts_code)
), qualified AS (
 SELECT s.d,s.next_d,s.entry_d,s.exit_d,s.split_id,m.ts_code,w.med_amount,w.n decision_n FROM scope s CROSS JOIN observed m JOIN windows w ON w.ts_code=m.ts_code AND w.trade_date=s.d
 WHERE s.split_id IS NOT NULL AND m.board IN (?,?,?) AND w.close_n=274 AND w.close_value_n=274 AND w.n-w.first_n=273
 AND m.list_date<=s.d
 AND w.amount_n=20 AND w.amount_value_n=20 AND w.close_ok AND w.amount_ok
 AND (SELECT count(*) FROM cal lc WHERE lc.trade_date>=m.list_date AND lc.trade_date<=s.d)>=274
), ranked AS (
 SELECT *,row_number() OVER(PARTITION BY d ORDER BY med_amount DESC,ts_code) rank FROM qualified
), selected AS (SELECT * FROM ranked WHERE rank<=30), stock_returns AS (
 SELECT ts_code,n,qfq_close/lag(qfq_close) OVER(PARTITION BY ts_code ORDER BY n)-1 daily_return FROM bu
), basket_returns AS (
 SELECT s.d,r.n,avg(r.daily_return) basket_return,count(r.daily_return) stock_count
 FROM selected s JOIN stock_returns r ON r.ts_code=s.ts_code AND r.n BETWEEN s.decision_n-272 AND s.decision_n
 GROUP BY s.d,r.n
), indexed_returns AS (
 SELECT *,row_number() OVER(PARTITION BY d ORDER BY n) return_n FROM basket_returns
), variance_audit AS (
 SELECT d,count(*) return_count,min(stock_count) minimum_stock_count,
 avg(basket_return*basket_return) FILTER(WHERE return_n<=252) baseline_variance,
 avg(basket_return*basket_return) FILTER(WHERE return_n>252) current_variance
 FROM indexed_returns GROUP BY d
), panel_points AS (
 SELECT d,ts_code,entry_d exec_d,d prior_d FROM selected UNION ALL SELECT d,ts_code,exit_d,next_d FROM selected
), panel_audit AS (
 SELECT x.d,count(e.ts_code) exec_count,count(p.ts_code) prior_count,bool_and(
 e.open IS NOT NULL AND isfinite(e.open) AND e.open>0 AND e.qfq_open IS NOT NULL AND isfinite(e.qfq_open) AND e.qfq_open>0
 AND e.adj_factor IS NOT NULL AND isfinite(e.adj_factor) AND e.adj_factor>0 AND e.quality_status IS NOT DISTINCT FROM ?
 AND e.synthetic_data IS NOT DISTINCT FROM false AND coalesce(regexp_full_match(e.row_hash,'[0-9a-f]{64}'),false)
 AND e.is_suspended IS NOT NULL AND e.is_st IS NOT NULL AND e.is_limit_up IS NOT NULL AND e.is_limit_down IS NOT NULL
 AND e.list_status IS NOT NULL AND e.up_limit IS NOT NULL AND e.down_limit IS NOT NULL
 AND p.vol IS NOT NULL AND isfinite(p.vol) AND p.vol>=0 AND p.amount IS NOT NULL AND isfinite(p.amount) AND p.amount>=0
 AND p.quality_status IS NOT DISTINCT FROM ? AND p.synthetic_data IS NOT DISTINCT FROM false
 AND coalesce(regexp_full_match(p.row_hash,'[0-9a-f]{64}'),false)) panel_ok
 FROM panel_points x LEFT JOIN bu e ON e.ts_code=x.ts_code AND e.trade_date=x.exec_d
 LEFT JOIN bu p ON p.ts_code=x.ts_code AND p.trade_date=x.prior_d GROUP BY x.d
), totals AS (
SELECT s.d,s.split_id,count(q.ts_code)::INTEGER qualified_count,
 count(q.ts_code) FILTER(WHERE q.rank<=30)::INTEGER selected_count,
 ((SELECT count(*) FROM observed)-count(q.ts_code))::INTEGER excluded_count,
 CASE WHEN v.return_count=273 AND v.minimum_stock_count=30 AND isfinite(v.baseline_variance) AND v.baseline_variance>0
 AND isfinite(v.current_variance) AND v.current_variance>0 AND least(1.0,v.baseline_variance/v.current_variance)>0 THEN 0 ELSE 1 END::INTEGER invalid_variance_count,
 CASE WHEN p.exec_count=60 AND p.prior_count=60 AND p.panel_ok THEN 0 ELSE 1 END::INTEGER invalid_execution_panel_count
 FROM scope s LEFT JOIN ranked q USING(d,split_id) LEFT JOIN variance_audit v USING(d) LEFT JOIN panel_audit p USING(d)
 WHERE s.split_id IS NOT NULL GROUP BY s.d,s.split_id,v.return_count,v.minimum_stock_count,v.baseline_variance,v.current_variance,p.exec_count,p.prior_count,p.panel_ok
), capital_payload AS (
 SELECT s.d,s.split_id,s.ts_code,
 least(1.0,v.baseline_variance/v.current_variance) exposure,
 e.open exec_open,e.is_suspended,e.is_st,e.up_limit,e.down_limit,e.list_status,
 p.vol prior_vol,p.amount prior_amount
 FROM selected s LEFT JOIN variance_audit v USING(d)
 LEFT JOIN bu e ON e.ts_code=s.ts_code AND e.trade_date=s.entry_d
 LEFT JOIN bu p ON p.ts_code=s.ts_code AND p.trade_date=s.d
)
SELECT t.d,t.split_id,t.selected_count,t.qualified_count,t.excluded_count,
t.invalid_variance_count,t.invalid_execution_panel_count,c.ts_code,c.exposure,c.exec_open,
c.is_suspended,c.is_st,c.up_limit,c.down_limit,c.list_status,c.prior_vol,c.prior_amount
FROM totals t LEFT JOIN capital_payload c USING(d,split_id) ORDER BY t.d,c.ts_code
"""


def run_read_only_preflight(database_path: str | Path) -> dict[str, object]:
    _definition()
    path = Path(database_path)
    before = _digest(path)
    if before[0] != rvm.DATABASE_SHA256:
        raise PreflightError("database SHA-256 changed")
    receipt = path.parent / "receipts" / rvm.SNAPSHOT_RECEIPT_FILENAME
    if (
        hashlib.sha256(_capture(receipt, "snapshot receipt")).hexdigest()
        != rvm.SNAPSHOT_RECEIPT_SHA256
    ):
        raise PreflightError("snapshot receipt SHA-256 changed")
    import duckdb

    connection = duckdb.connect(str(path), read_only=True)
    try:
        connection.execute("SET enable_external_access=false")
        parameters = [
            rvm.CALENDAR_SNAPSHOT_ID,
            "SSE",
            "AKSHARE_TOOL_TRADE_DATE_HIST_SINA",
            ORDINARY,
            rvm.SNAPSHOT_ID,
            rvm.CLASSIFICATION,
            *rvm.BOARD_LABELS,
            rvm.CLASSIFICATION,
            rvm.CLASSIFICATION,
        ]
        rows = connection.execute(SCAN_SQL, parameters).fetchall()
        grouped: dict[
            tuple[date, str],
            tuple[tuple[int, int, int, int, int], list[rvm.CapitalFormationRow], float],
        ] = {}
        for raw in rows:
            if len(raw) != 17:
                raise PreflightError("capital scan row shape is invalid")
            (
                day,
                split,
                selected,
                qualified,
                excluded,
                invalid_variance,
                invalid_panel,
                symbol,
                exposure,
                exec_open,
                is_suspended,
                is_st,
                up_limit,
                down_limit,
                list_status,
                prior_vol,
                prior_amount,
            ) = raw
            key = (datetime.strptime(str(day), "%Y%m%d").date(), str(split))
            totals = tuple(
                int(value)
                for value in (
                    selected,
                    qualified,
                    excluded,
                    invalid_variance,
                    invalid_panel,
                )
            )
            if symbol is None or exposure is None:
                raise PreflightError("capital scan payload is incomplete")
            if type(is_suspended) is not bool or type(is_st) is not bool:
                raise PreflightError("capital scan status flags are invalid")
            row = rvm.CapitalFormationRow(
                symbol=str(symbol),
                raw_open=float(exec_open),
                prior_volume_shares=float(prior_vol),
                prior_amount_cny=float(prior_amount),
                is_suspended=is_suspended,
                is_st=is_st,
                up_limit=float(up_limit),
                down_limit=float(down_limit),
                list_status=str(list_status),
            )
            if key not in grouped:
                grouped[key] = (totals, [row], float(exposure))
                continue
            prior_totals, formation_rows, prior_exposure = grouped[key]
            if prior_totals != totals or not math.isclose(
                prior_exposure, float(exposure), rel_tol=0.0, abs_tol=1e-15
            ):
                raise PreflightError("capital scan repeated aggregates disagree")
            formation_rows.append(row)

        audits = []
        for (day, split), (totals, formation_rows, exposure) in sorted(grouped.items()):
            selected, qualified, excluded, invalid_variance, invalid_panel = totals
            if len({row.symbol for row in formation_rows}) != len(formation_rows):
                raise PreflightError("capital scan has duplicate selected identifiers")
            capital = rvm.capital_interval_feasibility(
                formation_rows, intended_exposure=exposure
            )
            audits.append(
                IntervalAudit(
                    day,
                    split,
                    selected,
                    qualified,
                    excluded,
                    invalid_variance,
                    invalid_panel,
                    capital,
                )
            )
        duplicate = connection.execute(
            "SELECT coalesce(sum(n-1),0)::INTEGER FROM (SELECT count(*) n FROM a_share.a_share_canonical_daily_bars WHERE snapshot_id=? AND trade_date<='20260630' GROUP BY ts_code,trade_date HAVING count(*)>1)",
            [rvm.SNAPSHOT_ID],
        ).fetchone()[0]
        report = _report(tuple(audits), duplicate_key_count=duplicate)
    finally:
        connection.close()
    if _digest(path) != before:
        raise PreflightError("database changed during read-only preflight")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "DRY_RUN",
                    "database_opened": False,
                    "holding_returns_opened": False,
                    "strategy_candidate_available": False,
                },
                sort_keys=True,
            )
        )
        return 0
    if not args.database:
        raise PreflightError("--database is required with --execute")
    print(json.dumps(run_read_only_preflight(args.database), sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
