from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

from quant_system.research.chronological_return_ordering import (
    CALENDAR_DIGEST,
    CALENDAR_EXCHANGE,
    CALENDAR_ROW_COUNT,
    CALENDAR_SNAPSHOT_ID,
    CALENDAR_SOURCE,
    COVERAGE_START,
    DATABASE_SHA256,
    DEFINITION_SHA256,
    EXPECTED_MASTER_ORDINARY,
    EXPECTED_OBSERVED_ORDINARY,
    EXPECTED_UNOBSERVED_ORDINARY,
    HISTORICAL_CUTOFF,
    MIN_ELIGIBLE,
    MIN_FORMATION_SESSIONS,
    MIN_SELECTED,
    QUALITY,
    RESEARCH_ID,
    SNAPSHOT_DIGEST,
    SNAPSHOT_ID,
    SNAPSHOT_RECEIPT_FILENAME,
    SNAPSHOT_RECEIPT_SHA256,
    ChronologicalReturnOrderingError,
)

CLASSIFICATION = QUALITY
AVAILABLE_AT_STATUS = "UNKNOWN_NOT_PIT_QUALIFIED"
HISTORICAL_IS_ST_STATUS = "UNKNOWN_NOT_USED_AS_FILTER"
_DEFINITION_PATH = (
    Path(__file__).resolve().parents[1]
    / "research/definitions/a_share_chronological_return_ordering_monthly_v1.json"
)
_ORDINARY = r"((600|601|603|605|688)[0-9]{3}\.SH|(000|001|002|003|300|301)[0-9]{3}\.SZ)"


def _capture(path: Path, label: str) -> tuple[bytes, tuple[int, int, int, int]]:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise ChronologicalReturnOrderingError(f"{label} must be a readable regular file") from exc
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ChronologicalReturnOrderingError(f"{label} must be a regular file")
        raw = stream.read()
        after = os.fstat(stream.fileno())
    try:
        current = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise ChronologicalReturnOrderingError(f"{label} changed during capture") from exc
    identity = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns)  # noqa: E731
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise ChronologicalReturnOrderingError(f"{label} changed during capture")
    return raw, identity(after)


def _strict_json(raw: bytes, label: str) -> dict[str, object]:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            if key in result:
                raise ChronologicalReturnOrderingError(f"{label} has duplicate JSON keys")
            result[key] = value
        return result

    def constant(value: str) -> object:
        raise ChronologicalReturnOrderingError(f"{label} has nonfinite JSON {value}")

    try:
        value = json.loads(raw.decode(), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ChronologicalReturnOrderingError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise ChronologicalReturnOrderingError(f"{label} must be a JSON object")
    return value


def _frozen_json(path: Path, label: str, expected_sha256: str) -> dict[str, object]:
    raw, _ = _capture(path, label)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ChronologicalReturnOrderingError(f"{label} SHA-256 is not frozen")
    return _strict_json(raw, label)


def _definition(path: Path | None = None) -> dict[str, object]:
    return _frozen_json(path or _DEFINITION_PATH, "strategy definition", DEFINITION_SHA256)


def _digest(path: Path) -> tuple[str, tuple[int, int, int, int]]:
    raw, identity = _capture(path, "database")
    return hashlib.sha256(raw).hexdigest(), identity


def _parse_day(value: object) -> date:
    return datetime.strptime(str(value), "%Y%m%d").date()


def _validated_calendar(connection: Any) -> None:
    rows = connection.execute(
        "SELECT snapshot_id,exchange,trade_date,is_open,pretrade_date,source,ingested_at,"
        "row_hash,synthetic_data FROM a_share.a_share_trade_calendar WHERE trade_date<=? "
        "ORDER BY exchange,trade_date,row_hash",
        [HISTORICAL_CUTOFF.strftime("%Y%m%d")],
    ).fetchall()
    if len(rows) != CALENDAR_ROW_COUNT:
        raise ChronologicalReturnOrderingError("calendar row count is not frozen")
    days: list[str] = []
    previous: str | None = None
    for row in rows:
        if not isinstance(row, (tuple, list)) or len(row) != 9:
            raise ChronologicalReturnOrderingError("calendar row shape is invalid")
        snapshot, exchange, day, opened, predecessor, source, ingested, row_hash, synthetic = row
        _parse_day(day)
        if (
            (snapshot, exchange, source, opened, synthetic)
            != (CALENDAR_SNAPSHOT_ID, CALENDAR_EXCHANGE, CALENDAR_SOURCE, 1, False)
            or type(opened) is not int
            or not isinstance(ingested, str)
            or not ingested
            or re.fullmatch(r"[0-9a-f]{64}", str(row_hash)) is None
            or (previous is None and predecessor not in (None, ""))
            or (previous is not None and predecessor != previous)
        ):
            raise ChronologicalReturnOrderingError("calendar row identity is invalid")
        previous = str(day)
        days.append(previous)
    digest = hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
    if (
        days[0] != COVERAGE_START.strftime("%Y%m%d")
        or days[-1] != HISTORICAL_CUTOFF.strftime("%Y%m%d")
        or days != sorted(set(days))
        or digest != CALENDAR_DIGEST
    ):
        raise ChronologicalReturnOrderingError("calendar coverage or digest is not frozen")
    bar_days = tuple(
        str(row[0])
        for row in connection.execute(
            "SELECT trade_date FROM a_share.a_share_canonical_daily_bars WHERE snapshot_id=? "
            "AND trade_date<=? GROUP BY trade_date ORDER BY trade_date",
            [SNAPSHOT_ID, HISTORICAL_CUTOFF.strftime("%Y%m%d")],
        ).fetchall()
    )
    if bar_days != tuple(days):
        raise ChronologicalReturnOrderingError("calendar and snapshot dates differ")


def _cohort_counts(connection: Any) -> tuple[int, int, int, int]:
    row = connection.execute(
        "WITH m AS (SELECT ts_code,source,snapshot_id,row_hash,synthetic_data FROM "
        "a_share.a_share_symbol_master QUALIFY row_number() OVER(PARTITION BY ts_code ORDER BY "
        "ingested_at DESC,snapshot_id DESC)=1), o AS (SELECT * FROM m WHERE "
        "regexp_full_match(ts_code,?)), s AS (SELECT DISTINCT b.ts_code FROM "
        "a_share.a_share_canonical_daily_bars b JOIN o USING(ts_code) WHERE b.snapshot_id=?) "
        "SELECT (SELECT count(*) FROM o),(SELECT count(*) FROM s),(SELECT count(*) FROM o WHERE "
        "NOT EXISTS(SELECT 1 FROM s WHERE s.ts_code=o.ts_code)),(SELECT count(*) FROM o WHERE "
        "synthetic_data IS DISTINCT FROM false OR row_hash IS DISTINCT FROM "
        "source||'|'||snapshot_id||'|symbol_master|'||ts_code||'|')",
        [_ORDINARY, SNAPSHOT_ID],
    ).fetchone()
    if row is None or len(row) != 4 or any(type(value) is not int or value < 0 for value in row):
        raise ChronologicalReturnOrderingError("cohort count audit is invalid")
    master, observed, unobserved, failures = row
    if (master, observed, unobserved) != (
        EXPECTED_MASTER_ORDINARY,
        EXPECTED_OBSERVED_ORDINARY,
        EXPECTED_UNOBSERVED_ORDINARY,
    ):
        failures += 1
    return master, observed, unobserved, failures


_SCAN_SQL = r"""
WITH cb AS (
 SELECT trade_date,row_number() OVER(ORDER BY trade_date) si FROM a_share.a_share_trade_calendar WHERE snapshot_id=? AND exchange=? AND source=? AND is_open=1 AND synthetic_data=false AND trade_date<=?
), mo AS (
 SELECT min(trade_date) first_d,max(trade_date) d,min(si) first_si,max(si) d_si,count(*) formation_n FROM cb GROUP BY strftime(strptime(trade_date,'%Y%m%d'),'%Y%m')
), mi AS (
 SELECT *,lead(first_d,1) OVER(ORDER BY d) entry_d,lead(first_d,2) OVER(ORDER BY d) exit_d FROM mo
), intervals AS (
 SELECT *,CASE WHEN entry_d BETWEEN '20200101' AND '20211231' AND exit_d<='20211231' THEN 'development_2020_2021'
   WHEN entry_d BETWEEN '20220101' AND '20231231' AND exit_d<='20231231' THEN 'validation_2022_2023' WHEN entry_d BETWEEN '20240101' AND '20260430' AND exit_d<='20260430' THEN 'retrospective_holdout_2024_2026m4'
 END split_id FROM mi WHERE entry_d IS NOT NULL AND exit_d IS NOT NULL
), purges AS (
 SELECT count(*)::BIGINT purge_n FROM intervals
 WHERE entry_d BETWEEN '20200101' AND '20260430' AND split_id IS NULL
), bc AS (
 SELECT b.*,count(*) OVER(PARTITION BY ts_code,trade_date) key_n FROM a_share.a_share_canonical_daily_bars b
 WHERE snapshot_id=? AND trade_date<=?
), bu AS (SELECT * FROM bc WHERE key_n=1),
 universe AS (SELECT DISTINCT ts_code FROM bu WHERE regexp_full_match(ts_code,?)),
 expected AS (
 SELECT i.d,i.entry_d,i.exit_d,i.split_id,i.first_si,i.d_si,i.formation_n,u.ts_code,c.si,c.trade_date,
   c.si=i.first_si-1 prior_row FROM intervals i CROSS JOIN universe u
 JOIN cb c ON c.si BETWEEN i.first_si-1 AND i.d_si WHERE i.split_id IS NOT NULL
), joined AS (
 SELECT e.*,b.ts_code matched_code,b.qfq_close,b.amount,b.adj_factor,b.quality_status,b.row_hash,b.synthetic_data
 FROM expected e LEFT JOIN bu b ON b.ts_code=e.ts_code AND b.trade_date=e.trade_date
), daily AS (
 SELECT *,CASE WHEN NOT prior_row THEN qfq_close/lag(qfq_close) OVER(PARTITION BY d,ts_code ORDER BY si)-1 END ret FROM joined
), formed AS (
 SELECT d,entry_d,exit_d,split_id,formation_n,ts_code,count(matched_code) matched_n,
   count(qfq_close) close_n,count(adj_factor) adj_n,count(amount) FILTER(NOT prior_row) amount_n,count(ret) return_n,
   sum(CASE WHEN matched_code IS NOT NULL AND ((qfq_close IS NOT NULL AND (NOT isfinite(qfq_close) OR qfq_close<=0)) OR
     (amount IS NOT NULL AND (NOT isfinite(amount) OR amount<0)) OR (adj_factor IS NOT NULL AND
     (NOT isfinite(adj_factor) OR adj_factor<=0))) THEN 1 ELSE 0 END) nonfinite_n,
   sum(CASE WHEN matched_code IS NOT NULL AND (quality_status IS DISTINCT FROM ? OR synthetic_data IS DISTINCT FROM false
     OR NOT coalesce(regexp_full_match(row_hash,'[0-9a-f]{64}'),false)) THEN 1 ELSE 0 END) identity_n,
   stddev_pop(ret) return_sd,corr(ret,si) cro,median(amount) FILTER(NOT prior_row) med_amount
 FROM daily GROUP BY d,entry_d,exit_d,split_id,formation_n,ts_code
), classified AS (
 SELECT *,matched_n<>formation_n+1 OR close_n<>formation_n+1 OR adj_n<>formation_n+1 OR amount_n<>formation_n formation_missing,
   nonfinite_n>0 formation_nonfinite,identity_n>0 formation_identity,return_n<>formation_n OR return_sd IS NULL
   OR return_sd=0 OR cro IS NULL OR NOT isfinite(cro) bad_cro,med_amount IS NULL OR med_amount<50000000 below_liquidity FROM formed
), eligible AS (
 SELECT * FROM classified WHERE NOT formation_missing AND NOT formation_nonfinite AND NOT formation_identity
   AND NOT bad_cro AND NOT below_liquidity
), ranked AS (
 SELECT *,row_number() OVER(PARTITION BY d ORDER BY cro,ts_code) rn,count(*) OVER(PARTITION BY d) eligible_n FROM eligible
), selection_counts AS (
 SELECT d,max(eligible_n)::BIGINT eligible_n,sum(CASE WHEN rn<=floor(eligible_n*0.10) THEN 1 ELSE 0 END)::BIGINT selected_n FROM ranked GROUP BY d
), panels AS (
 SELECT e.d,e.ts_code,en.qfq_open entry_open,en.adj_factor entry_adj,en.quality_status entry_quality,
   en.row_hash entry_hash,en.synthetic_data entry_synth,ex.qfq_open exit_open,ex.adj_factor exit_adj,
   ex.quality_status exit_quality,ex.row_hash exit_hash,ex.synthetic_data exit_synth FROM eligible e
 LEFT JOIN bu en ON en.ts_code=e.ts_code AND en.trade_date=e.entry_d
 LEFT JOIN bu ex ON ex.ts_code=e.ts_code AND ex.trade_date=e.exit_d
), panel_audit AS (
 SELECT d,count(*)::BIGINT panel_n,sum(CASE WHEN entry_open IS NULL OR exit_open IS NULL OR entry_adj IS NULL
   OR exit_adj IS NULL THEN 1 ELSE 0 END)::BIGINT panel_missing,sum(CASE WHEN (entry_open IS NOT NULL AND
   (NOT isfinite(entry_open) OR entry_open<=0)) OR (exit_open IS NOT NULL AND (NOT isfinite(exit_open) OR exit_open<=0))
   OR (entry_adj IS NOT NULL AND (NOT isfinite(entry_adj) OR entry_adj<=0)) OR (exit_adj IS NOT NULL AND
   (NOT isfinite(exit_adj) OR exit_adj<=0)) THEN 1 ELSE 0 END)::BIGINT panel_nonfinite,
   sum(CASE WHEN entry_quality IS DISTINCT FROM ? OR exit_quality IS DISTINCT FROM ? OR entry_synth IS DISTINCT FROM false
   OR exit_synth IS DISTINCT FROM false OR NOT coalesce(regexp_full_match(entry_hash,'[0-9a-f]{64}'),false)
   OR NOT coalesce(regexp_full_match(exit_hash,'[0-9a-f]{64}'),false) THEN 1 ELSE 0 END)::BIGINT panel_identity FROM panels GROUP BY d
), exclusions AS (
 SELECT d,sum(formation_missing)::BIGINT formation_missing,sum(formation_nonfinite)::BIGINT formation_nonfinite,
   sum(formation_identity)::BIGINT formation_identity,sum(bad_cro)::BIGINT bad_cro,
   sum(CASE WHEN NOT formation_missing AND NOT formation_nonfinite AND NOT formation_identity
     AND NOT bad_cro AND below_liquidity THEN 1 ELSE 0 END)::BIGINT below_liquidity FROM classified GROUP BY d
)
SELECT i.d,i.split_id,i.formation_n,coalesce(s.eligible_n,0)::BIGINT,coalesce(s.selected_n,0)::BIGINT,
 coalesce(x.formation_missing,0)::BIGINT,coalesce(x.formation_nonfinite,0)::BIGINT,
 coalesce(x.formation_identity,0)::BIGINT,coalesce(x.bad_cro,0)::BIGINT,coalesce(x.below_liquidity,0)::BIGINT,
 coalesce(p.panel_n,0)::BIGINT,coalesce(p.panel_missing,0)::BIGINT,coalesce(p.panel_nonfinite,0)::BIGINT,
 coalesce(p.panel_identity,0)::BIGINT,z.purge_n FROM intervals i LEFT JOIN selection_counts s USING(d)
 LEFT JOIN exclusions x USING(d) LEFT JOIN panel_audit p USING(d) CROSS JOIN purges z
 WHERE i.split_id IS NOT NULL ORDER BY i.d
"""


@dataclass(frozen=True)
class IntervalAudit:
    decision_date: date
    split_id: str
    formation_sessions: int
    eligible_count: int
    selected_count: int
    formation_missing: int = 0
    formation_nonfinite: int = 0
    formation_identity: int = 0
    bad_cro: int = 0
    below_liquidity: int = 0
    panel_count: int = 0
    panel_missing: int = 0
    panel_nonfinite: int = 0
    panel_identity: int = 0
    cross_boundary_purged: int = 0


def _database_audits(connection: Any) -> tuple[IntervalAudit, ...]:
    parameters = [
        CALENDAR_SNAPSHOT_ID,
        CALENDAR_EXCHANGE,
        CALENDAR_SOURCE,
        HISTORICAL_CUTOFF.strftime("%Y%m%d"),
        SNAPSHOT_ID,
        HISTORICAL_CUTOFF.strftime("%Y%m%d"),
        _ORDINARY,
        QUALITY,
        QUALITY,
        QUALITY,
    ]
    rows = connection.execute(_SCAN_SQL, parameters).fetchall()
    audits: list[IntervalAudit] = []
    for row in rows:
        if len(row) != 15:
            raise ChronologicalReturnOrderingError("preflight interval shape is invalid")
        day, split, *counts = row
        if type(split) is not str or any(type(value) is not int or value < 0 for value in counts):
            raise ChronologicalReturnOrderingError("preflight interval counts are invalid")
        audits.append(IntervalAudit(_parse_day(day), split, *counts))
    return tuple(audits)


def _duplicate_keys(connection: Any) -> int:
    row = connection.execute(
        "SELECT coalesce(sum(n-1),0) FROM (SELECT count(*) n FROM "
        "a_share.a_share_canonical_daily_bars WHERE snapshot_id=? AND trade_date<=? "
        "GROUP BY ts_code,trade_date HAVING count(*)>1)",
        [SNAPSHOT_ID, HISTORICAL_CUTOFF.strftime("%Y%m%d")],
    ).fetchone()
    if row is None or type(row[0]) is not int or row[0] < 0:
        raise ChronologicalReturnOrderingError("duplicate-key count is invalid")
    return row[0]


def _report(
    audits: Sequence[IntervalAudit],
    cohort: tuple[int, int, int, int],
    coverage: tuple[date, date],
    *,
    duplicate_keys: int = 0,
) -> dict[str, object]:
    rows = tuple(audits)
    split_ids = (
        "development_2020_2021",
        "validation_2022_2023",
        "retrospective_holdout_2024_2026m4",
    )
    if not rows or any(row.split_id not in split_ids for row in rows):
        raise ChronologicalReturnOrderingError("preflight requires historical interval audits")
    if len({row.decision_date for row in rows}) != len(rows):
        raise ChronologicalReturnOrderingError("duplicate interval audit")
    all_counts = tuple(
        value for row in rows for value in row.__dict__.values() if type(value) is int
    )
    if any(value < 0 for value in (*all_counts, *cohort, duplicate_keys)):
        raise ChronologicalReturnOrderingError("preflight aggregate count is invalid")
    master, observed, unobserved, master_failures = cohort
    purge_counts = {row.cross_boundary_purged for row in rows}
    if len(purge_counts) != 1:
        raise ChronologicalReturnOrderingError("cross-boundary purge count is inconsistent")
    split_counts = {name: sum(row.split_id == name for row in rows) for name in split_ids}
    minimum = lambda name, field: min(  # noqa: E731
        getattr(row, field) for row in rows if row.split_id == name
    )
    maximum = lambda name, field: max(  # noqa: E731
        getattr(row, field) for row in rows if row.split_id == name
    )
    min_eligible = {name: minimum(name, "eligible_count") for name in split_ids}
    max_eligible = {name: maximum(name, "eligible_count") for name in split_ids}
    min_selected = {name: minimum(name, "selected_count") for name in split_ids}
    max_selected = {name: maximum(name, "selected_count") for name in split_ids}
    invalid = {
        name: sum(
            row.split_id == name
            and (
                row.formation_sessions < MIN_FORMATION_SESSIONS
                or row.eligible_count < MIN_ELIGIBLE
                or row.selected_count < MIN_SELECTED
                or row.panel_count != row.eligible_count
                or row.panel_missing + row.panel_nonfinite + row.panel_identity > 0
            )
            for row in rows
        )
        for name in split_ids
    }
    counts = {
        "formation_missing_count": sum(row.formation_missing for row in rows),
        "formation_nonfinite_count": sum(row.formation_nonfinite for row in rows),
        "formation_identity_failure_count": sum(row.formation_identity for row in rows),
        "zero_variance_or_nonfinite_cro_count": sum(row.bad_cro for row in rows),
        "below_liquidity_floor_count": sum(row.below_liquidity for row in rows),
        "benchmark_panel_missing_count": sum(row.panel_missing for row in rows),
        "benchmark_panel_nonfinite_count": sum(row.panel_nonfinite for row in rows),
        "benchmark_panel_identity_failure_count": sum(row.panel_identity for row in rows),
    }
    blocked = (
        master_failures > 0
        or duplicate_keys > 0
        or any(
            counts[name] > 0
            for name in (
                "benchmark_panel_missing_count",
                "benchmark_panel_nonfinite_count",
                "benchmark_panel_identity_failure_count",
            )
        )
    )
    split_structure = (
        20 <= split_counts["validation_2022_2023"] <= 23
        and split_counts["retrospective_holdout_2024_2026m4"] >= 24
    )
    report: dict[str, object] = {
        "schema_version": "a-share-chronological-return-ordering-preflight-v1",
        "research_id": RESEARCH_ID,
        "phase": "OUTCOME_FREE_PREFLIGHT",
        "status": "INPUT_BLOCKED"
        if blocked
        else "STRUCTURAL_FAIL"
        if any(invalid.values()) or not split_structure
        else "PREFLIGHT_PASS",
        "snapshot_id": SNAPSHOT_ID,
        "database_sha256": DATABASE_SHA256,
        "snapshot_digest": SNAPSHOT_DIGEST,
        "snapshot_receipt_sha256": SNAPSHOT_RECEIPT_SHA256,
        "calendar_snapshot_id": CALENDAR_SNAPSHOT_ID,
        "calendar_digest": CALENDAR_DIGEST,
        "classification": CLASSIFICATION,
        "available_at_status": AVAILABLE_AT_STATUS,
        "historical_is_st_status": HISTORICAL_IS_ST_STATUS,
        "coverage_start": coverage[0].isoformat(),
        "coverage_end": coverage[1].isoformat(),
        "master_ordinary_count": master,
        "observed_ordinary_count": observed,
        "unobserved_ordinary_count": unobserved,
        "split_interval_counts": split_counts,
        "split_minimum_eligible_counts": min_eligible,
        "split_maximum_eligible_counts": max_eligible,
        "split_minimum_selected_counts": min_selected,
        "split_maximum_selected_counts": max_selected,
        "split_invalid_interval_counts": invalid,
        "split_minimum_formation_session_counts": {
            name: minimum(name, "formation_sessions") for name in split_ids
        },
        "cross_boundary_purged_interval_count": purge_counts.pop(),
        **counts,
        "duplicate_key_count": duplicate_keys,
        "unexpected_exception_count": 0,
        "post_entry_outcomes_opened": False,
        "forbidden_or_prospective_data_accessed": False,
        "security_identifiers_in_report": False,
        "strategy_candidate_available": False,
    }
    frozen = _definition()
    try:
        allowed = frozen["outcome_free_preflight"]["allowed_fields"]  # type: ignore[index]
    except (KeyError, TypeError) as exc:
        raise ChronologicalReturnOrderingError("definition preflight allowlist is invalid") from exc
    if (
        not isinstance(allowed, list)
        or set(report) != set(allowed)
        or len(allowed) != len(set(allowed))
    ):
        raise ChronologicalReturnOrderingError("preflight report differs from frozen allowlist")
    return report


def run_read_only_preflight(database_path: str | Path) -> dict[str, object]:
    path = Path(database_path)
    before = _digest(path)
    if before[0] != DATABASE_SHA256:
        raise ChronologicalReturnOrderingError("database SHA-256 is not frozen")
    receipt = _frozen_json(
        path.parent / "receipts" / SNAPSHOT_RECEIPT_FILENAME,
        "snapshot receipt",
        SNAPSHOT_RECEIPT_SHA256,
    )
    expected = {
        "post_db_sha256": DATABASE_SHA256,
        "target_snapshot": SNAPSHOT_ID,
        "v5_digest": SNAPSHOT_DIGEST,
        "date_start": COVERAGE_START.strftime("%Y%m%d"),
        "date_end": HISTORICAL_CUTOFF.strftime("%Y%m%d"),
        "volume_unit": "SHARES",
        "amount_unit": "CNY",
        "status": "PUBLISHED_V5_VOLUME_UNIT_SHARES_VERIFIED",
        "strategy_candidate_available": False,
        "strategy_outcomes_opened": False,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ChronologicalReturnOrderingError("receipt does not bind the frozen snapshot")
    import duckdb

    connection = duckdb.connect(str(path), read_only=True)
    try:
        connection.execute("SET enable_external_access=false")
        snapshot = connection.execute(
            "SELECT count(*),min(trade_date),max(trade_date),count(DISTINCT quality_status),"
            "min(quality_status),bool_and(not synthetic_data) FROM "
            "a_share.a_share_canonical_daily_bars WHERE snapshot_id=? AND trade_date<=?",
            [SNAPSHOT_ID, HISTORICAL_CUTOFF.strftime("%Y%m%d")],
        ).fetchone()
        if (
            snapshot is None
            or snapshot[0] <= 0
            or receipt.get("target_rows") != snapshot[0]
            or snapshot[3:] != (1, CLASSIFICATION, True)
        ):
            raise ChronologicalReturnOrderingError("snapshot identity is invalid")
        coverage = (_parse_day(snapshot[1]), _parse_day(snapshot[2]))
        if coverage != (COVERAGE_START, HISTORICAL_CUTOFF):
            raise ChronologicalReturnOrderingError("snapshot coverage is not frozen")
        _validated_calendar(connection)
        report = _report(
            _database_audits(connection),
            _cohort_counts(connection),
            coverage,
            duplicate_keys=_duplicate_keys(connection),
        )
    finally:
        connection.close()
    if _digest(path) != before:
        raise ChronologicalReturnOrderingError("database changed during read-only preflight")
    return report
