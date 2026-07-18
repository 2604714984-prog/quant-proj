"""Aggregate-only read-only preflight for post-IPO lucky-code avoidance."""

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

from quant_system.research.post_ipo_numerology import (
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
    PAIR_COUNT,
    RESEARCH_ID,
    SNAPSHOT_DIGEST,
    SNAPSHOT_ID,
    SNAPSHOT_RECEIPT_FILENAME,
    SNAPSHOT_RECEIPT_SHA256,
    PostIpoNumerologyContractError,
)

CLASSIFICATION = "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT"
AVAILABLE_AT_STATUS = "UNKNOWN_NOT_PIT_QUALIFIED"
HISTORICAL_IS_ST_STATUS = "UNKNOWN_NOT_USED_AS_FILTER"
_DEFINITION_PATH = (
    Path(__file__).resolve().parents[1]
    / "research/definitions/a_share_post_ipo_numerological_overvaluation_avoidance_v1.json"
)
_ORDINARY = r"((600|601|603|605|688)[0-9]{3}\.SH|(000|001|002|003|300|301)[0-9]{3}\.SZ)"


def _capture(path: Path, label: str) -> tuple[bytes, tuple[int, int, int, int]]:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise PostIpoNumerologyContractError(f"{label} must be a readable regular file") from exc
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise PostIpoNumerologyContractError(f"{label} must be a regular file")
        raw = stream.read()
        after = os.fstat(stream.fileno())
    try:
        current = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise PostIpoNumerologyContractError(f"{label} changed during capture") from exc
    identity = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns)  # noqa: E731
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise PostIpoNumerologyContractError(f"{label} changed during capture")
    return raw, identity(after)


def _strict_json(raw: bytes, label: str) -> dict[str, object]:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            if key in result:
                raise PostIpoNumerologyContractError(f"{label} has duplicate JSON keys")
            result[key] = value
        return result

    def constant(value: str) -> object:
        raise PostIpoNumerologyContractError(f"{label} has nonfinite JSON {value}")

    try:
        value = json.loads(raw.decode(), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PostIpoNumerologyContractError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise PostIpoNumerologyContractError(f"{label} must be a JSON object")
    return value


def _definition(path: Path | None = None) -> dict[str, object]:
    raw, _ = _capture(path or _DEFINITION_PATH, "strategy definition")
    if hashlib.sha256(raw).hexdigest() != DEFINITION_SHA256:
        raise PostIpoNumerologyContractError("strategy definition SHA-256 is not frozen")
    return _strict_json(raw, "strategy definition")


def _digest(path: Path) -> tuple[str, tuple[int, int, int, int]]:
    raw, identity = _capture(path, "database")
    return hashlib.sha256(raw).hexdigest(), identity


def _receipt(path: Path) -> dict[str, object]:
    raw, _ = _capture(path, "snapshot receipt")
    if hashlib.sha256(raw).hexdigest() != SNAPSHOT_RECEIPT_SHA256:
        raise PostIpoNumerologyContractError("snapshot receipt SHA-256 is not frozen")
    return _strict_json(raw, "snapshot receipt")


def _parse_day(value: object) -> date:
    try:
        return datetime.strptime(str(value), "%Y%m%d").date()
    except ValueError as exc:
        raise PostIpoNumerologyContractError("database contains an invalid date") from exc


def _validated_calendar(connection: Any) -> tuple[tuple[str, ...], str]:
    rows = connection.execute(
        "SELECT snapshot_id,exchange,trade_date,is_open,pretrade_date,source,ingested_at,"
        "row_hash,synthetic_data FROM a_share.a_share_trade_calendar WHERE trade_date<=? "
        "ORDER BY exchange,trade_date,row_hash",
        [HISTORICAL_CUTOFF.strftime("%Y%m%d")],
    ).fetchall()
    if len(rows) != CALENDAR_ROW_COUNT:
        raise PostIpoNumerologyContractError("calendar row count is not frozen")
    days: list[str] = []
    previous: str | None = None
    for row in rows:
        if not isinstance(row, (tuple, list)) or len(row) != 9:
            raise PostIpoNumerologyContractError("calendar row shape is invalid")
        snapshot, exchange, day, opened, predecessor, source, ingested, row_hash, synthetic = row
        _parse_day(day)
        if (
            snapshot != CALENDAR_SNAPSHOT_ID
            or exchange != CALENDAR_EXCHANGE
            or source != CALENDAR_SOURCE
            or type(opened) is not int
            or opened != 1
            or synthetic is not False
            or not isinstance(ingested, str)
            or not ingested
            or re.fullmatch(r"[0-9a-f]{64}", str(row_hash)) is None
            or (previous is None and predecessor not in (None, ""))
            or (previous is not None and predecessor != previous)
        ):
            raise PostIpoNumerologyContractError("calendar row identity is invalid")
        previous = str(day)
        days.append(previous)
    digest = hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
    if (
        days[0] != COVERAGE_START.strftime("%Y%m%d")
        or days[-1] != HISTORICAL_CUTOFF.strftime("%Y%m%d")
        or len(days) != len(set(days))
        or days != sorted(days)
        or digest != CALENDAR_DIGEST
    ):
        raise PostIpoNumerologyContractError("calendar coverage or digest is not frozen")
    bar_days = tuple(
        str(row[0])
        for row in connection.execute(
            "SELECT trade_date FROM a_share.a_share_canonical_daily_bars WHERE snapshot_id=? "
            "AND trade_date<=? GROUP BY trade_date ORDER BY trade_date",
            [SNAPSHOT_ID, HISTORICAL_CUTOFF.strftime("%Y%m%d")],
        ).fetchall()
    )
    if bar_days != tuple(days):
        raise PostIpoNumerologyContractError("calendar and snapshot dates differ")
    return tuple(days), digest


def _cohort_counts(connection: Any) -> tuple[int, int, int, int]:
    row = connection.execute(
        "WITH m AS (SELECT ts_code,source,snapshot_id,row_hash,synthetic_data,list_date FROM "
        "a_share.a_share_symbol_master QUALIFY row_number() OVER (PARTITION BY ts_code ORDER BY "
        "ingested_at DESC,snapshot_id DESC)=1), ordinary AS (SELECT * FROM m WHERE "
        "regexp_full_match(ts_code,?)), observed AS (SELECT DISTINCT b.ts_code FROM "
        "a_share.a_share_canonical_daily_bars b JOIN ordinary o USING(ts_code) WHERE "
        "b.snapshot_id=?) SELECT (SELECT count(*) FROM ordinary),(SELECT count(*) FROM observed),"
        "(SELECT count(*) FROM ordinary o WHERE NOT EXISTS (SELECT 1 FROM observed s WHERE "
        "s.ts_code=o.ts_code)),(SELECT count(*) FROM ordinary WHERE list_date IS NULL OR "
        "NOT regexp_full_match(list_date,'[0-9]{8}') OR synthetic_data IS DISTINCT FROM false OR "
        "row_hash IS DISTINCT FROM source||'|'||snapshot_id||'|symbol_master|'||ts_code||'|')",
        [_ORDINARY, SNAPSHOT_ID],
    ).fetchone()
    if row is None or len(row) != 4 or any(type(value) is not int or value < 0 for value in row):
        raise PostIpoNumerologyContractError("cohort count audit is invalid")
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
 SELECT trade_date,row_number() OVER(ORDER BY trade_date) si
 FROM a_share.a_share_trade_calendar
 WHERE snapshot_id=? AND exchange=? AND source=? AND is_open=1 AND synthetic_data=false
   AND trade_date<=?
), mo AS (
 SELECT min(trade_date) first_d,max(trade_date) d
 FROM cb GROUP BY strftime(strptime(trade_date,'%Y%m%d'),'%Y%m')
), mi AS (
 SELECT d,lead(first_d,1) OVER(ORDER BY d) entry_d,lead(first_d,2) OVER(ORDER BY d) exit_d
 FROM mo
), intervals AS (
 SELECT d,entry_d,exit_d,CASE
   WHEN entry_d BETWEEN '20200101' AND '20211231' AND exit_d<='20211231' THEN 'development_2020_2021'
   WHEN entry_d BETWEEN '20220101' AND '20231231' AND exit_d<='20231231' THEN 'validation_2022_2023'
   WHEN entry_d BETWEEN '20240101' AND '20260630' AND exit_d<='20260630' THEN 'retrospective_holdout_2024_2026h1'
 END split_id FROM mi WHERE entry_d IS NOT NULL AND exit_d IS NOT NULL
), master AS (
 SELECT ts_code,list_date,CASE
   WHEN regexp_full_match(ts_code,'(600|601|603|605)[0-9]{3}\.SH') THEN 'SH_MAIN'
   WHEN regexp_full_match(ts_code,'688[0-9]{3}\.SH') THEN 'STAR'
   WHEN regexp_full_match(ts_code,'(000|001|002|003)[0-9]{3}\.SZ') THEN 'SZ_MAIN'
   WHEN regexp_full_match(ts_code,'(300|301)[0-9]{3}\.SZ') THEN 'CHINEXT' END board,
   substr(list_date,1,4)||'Q'||cast(ceil(cast(substr(list_date,5,2) AS INTEGER)/3.0) AS INTEGER) list_q
 FROM a_share.a_share_symbol_master WHERE regexp_full_match(ts_code,?)
 QUALIFY row_number() OVER(PARTITION BY ts_code ORDER BY ingested_at DESC,snapshot_id DESC)=1
), observed AS (
 SELECT DISTINCT b.ts_code FROM a_share.a_share_canonical_daily_bars b JOIN master m USING(ts_code)
 WHERE b.snapshot_id=?
), lm AS (
 SELECT m.*,min(c.si) first_si FROM master m JOIN observed o USING(ts_code)
 LEFT JOIN cb c ON c.trade_date>=m.list_date GROUP BY ALL
), bc AS (
 SELECT b.*,count(*) OVER(PARTITION BY ts_code,trade_date) key_n
 FROM a_share.a_share_canonical_daily_bars b WHERE snapshot_id=? AND trade_date<=?
), bu AS (SELECT * FROM bc WHERE key_n=1),
 bw AS (
 SELECT b.*,c.si,count(*) OVER w n,count(amount) OVER w amount_n,min(c.si) OVER w first_w,
   median(amount) OVER w med_amount,
   bool_and(amount IS NOT NULL AND isfinite(amount) AND amount>=0) OVER w amount_ok,
   bool_and(adj_factor IS NOT NULL AND isfinite(adj_factor) AND adj_factor>0
     AND quality_status IS NOT DISTINCT FROM ? AND synthetic_data IS NOT DISTINCT FROM false
     AND coalesce(regexp_full_match(row_hash,'[0-9a-f]{64}'),false)) OVER w identity_ok
 FROM bu b JOIN cb c USING(trade_date)
 WINDOW w AS(PARTITION BY ts_code ORDER BY c.si ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
), scope AS (
 SELECT i.*,m.ts_code,m.board,m.list_q,d.si d_si,m.first_si,
   CASE WHEN m.list_date>=? THEN d.si-m.first_si+1 END age,
   CASE WHEN m.list_date<? AND d.si<=756 THEN 1 ELSE 0 END age_unknown
 FROM intervals i CROSS JOIN lm m JOIN cb d ON d.trade_date=i.d
 WHERE i.split_id IS NOT NULL AND ((m.list_date>=? AND d.si-m.first_si+1 BETWEEN 60 AND 756)
   OR (m.list_date<? AND d.si<=756))
), classified AS (
 SELECT s.*,b.med_amount,
   CASE WHEN age_unknown=1 OR b.ts_code IS NULL OR b.n<>20 OR b.amount_n<>20
     OR b.si-b.first_w<>19 THEN 1 ELSE 0 END win_missing,
   CASE WHEN b.ts_code IS NOT NULL AND b.amount_ok IS DISTINCT FROM true THEN 1 ELSE 0 END win_nonfinite,
   CASE WHEN b.ts_code IS NOT NULL AND b.identity_ok IS DISTINCT FROM true THEN 1 ELSE 0 END win_identity,
   CASE WHEN right(split_part(s.ts_code,'.',1),CASE WHEN ends_with(s.ts_code,'.SH') THEN 3 ELSE 4 END)
     LIKE '%4%' THEN false
     WHEN regexp_matches(right(split_part(s.ts_code,'.',1),CASE WHEN ends_with(s.ts_code,'.SH')
       THEN 3 ELSE 4 END),'[689]') THEN true ELSE false END lucky
 FROM scope s LEFT JOIN bw b ON b.ts_code=s.ts_code AND b.trade_date=s.d
), valid AS (SELECT * FROM classified WHERE win_missing=0 AND win_nonfinite=0 AND win_identity=0),
 ranked AS (
 SELECT *,row_number() OVER(PARTITION BY d,board,list_q,lucky ORDER BY med_amount DESC,ts_code) rn
 FROM valid
), pairs AS (
 SELECT n.d,n.entry_d,n.exit_d,n.split_id,n.board,n.list_q,n.ts_code not_code,l.ts_code lucky_code,
   least(n.med_amount,l.med_amount) pair_liq
 FROM ranked n JOIN ranked l ON n.d=l.d AND n.board=l.board AND n.list_q=l.list_q
   AND n.rn=l.rn WHERE n.lucky=false AND l.lucky=true
), selected AS (
 SELECT * FROM pairs QUALIFY row_number() OVER(PARTITION BY d ORDER BY pair_liq DESC,not_code,lucky_code)<=15
), symbols AS (
 SELECT d,entry_d,exit_d,not_code ts_code FROM selected UNION ALL
 SELECT d,entry_d,exit_d,lucky_code FROM selected
), panels AS (
 SELECT s.*,e.qfq_open entry_qfq,e.adj_factor entry_adj,e.quality_status entry_quality,
   e.synthetic_data entry_synth,e.row_hash entry_hash,
   x.qfq_open exit_qfq,x.adj_factor exit_adj,x.quality_status exit_quality,
   x.synthetic_data exit_synth,x.row_hash exit_hash
 FROM symbols s LEFT JOIN bu e ON e.ts_code=s.ts_code AND e.trade_date=s.entry_d
 LEFT JOIN bu x ON x.ts_code=s.ts_code AND x.trade_date=s.exit_d
), pa AS (
 SELECT d,count(*) panel_n,
   sum(CASE WHEN entry_qfq IS NULL OR exit_qfq IS NULL OR entry_adj IS NULL OR exit_adj IS NULL
     THEN 1 ELSE 0 END)::BIGINT qfq_missing,
   sum(CASE WHEN (entry_qfq IS NOT NULL AND (NOT isfinite(entry_qfq) OR entry_qfq<=0))
     OR (exit_qfq IS NOT NULL AND (NOT isfinite(exit_qfq) OR exit_qfq<=0))
     OR (entry_adj IS NOT NULL AND (NOT isfinite(entry_adj) OR entry_adj<=0))
     OR (exit_adj IS NOT NULL AND (NOT isfinite(exit_adj) OR exit_adj<=0)) THEN 1 ELSE 0 END)::BIGINT qfq_nonfinite,
   sum(CASE WHEN entry_quality IS DISTINCT FROM ? OR exit_quality IS DISTINCT FROM ?
     OR entry_synth IS DISTINCT FROM false OR exit_synth IS DISTINCT FROM false
     OR NOT coalesce(regexp_full_match(entry_hash,'[0-9a-f]{64}'),false)
     OR NOT coalesce(regexp_full_match(exit_hash,'[0-9a-f]{64}'),false) THEN 1 ELSE 0 END)::BIGINT panel_identity
 FROM panels GROUP BY d
), pc AS (SELECT d,count(*)::BIGINT pair_n FROM pairs GROUP BY d),
 errors AS (
 SELECT d,sum(win_missing)::BIGINT win_missing,sum(win_nonfinite)::BIGINT win_nonfinite,
   sum(win_identity)::BIGINT win_identity FROM classified GROUP BY d
), daily AS (
 SELECT i.d,i.split_id,coalesce(pc.pair_n,0)::BIGINT pair_n,
   coalesce(e.win_missing,0)::BIGINT win_missing,
   coalesce(e.win_nonfinite,0)::BIGINT win_nonfinite,
   coalesce(e.win_identity,0)::BIGINT win_identity
 FROM intervals i LEFT JOIN pc USING(d) LEFT JOIN errors e USING(d) WHERE i.split_id IS NOT NULL
)
SELECT d.d,d.split_id,d.pair_n,d.win_missing,d.win_nonfinite,d.win_identity,
 coalesce(pa.panel_n,0)::BIGINT panel_n,coalesce(pa.qfq_missing,0)::BIGINT qfq_missing,
 coalesce(pa.qfq_nonfinite,0)::BIGINT qfq_nonfinite,coalesce(pa.panel_identity,0)::BIGINT panel_identity
FROM daily d LEFT JOIN pa USING(d) ORDER BY d.d
"""


@dataclass(frozen=True)
class IntervalAudit:
    decision_date: date
    split_id: str
    pair_count: int
    window_missing: int = 0
    window_nonfinite: int = 0
    window_identity: int = 0
    panel_count: int = 0
    qfq_missing: int = 0
    qfq_nonfinite: int = 0
    panel_identity: int = 0


def _database_audits(connection: Any) -> tuple[IntervalAudit, ...]:
    quality = CLASSIFICATION
    parameters = [
        CALENDAR_SNAPSHOT_ID,
        CALENDAR_EXCHANGE,
        CALENDAR_SOURCE,
        HISTORICAL_CUTOFF.strftime("%Y%m%d"),
        _ORDINARY,
        SNAPSHOT_ID,
        SNAPSHOT_ID,
        HISTORICAL_CUTOFF.strftime("%Y%m%d"),
        quality,
        COVERAGE_START.strftime("%Y%m%d"),
        COVERAGE_START.strftime("%Y%m%d"),
        COVERAGE_START.strftime("%Y%m%d"),
        COVERAGE_START.strftime("%Y%m%d"),
        quality,
        quality,
    ]
    rows = connection.execute(_SCAN_SQL, parameters).fetchall()
    audits: list[IntervalAudit] = []
    for row in rows:
        if len(row) != 10:
            raise PostIpoNumerologyContractError("preflight interval shape is invalid")
        decision, split, *counts = row
        if type(split) is not str or any(type(value) is not int or value < 0 for value in counts):
            raise PostIpoNumerologyContractError("preflight interval counts are invalid")
        audits.append(IntervalAudit(_parse_day(decision), split, *counts))
    return tuple(audits)


def _duplicate_keys(connection: Any) -> int:
    row = connection.execute(
        "SELECT coalesce(sum(n-1),0) FROM (SELECT count(*) n FROM "
        "a_share.a_share_canonical_daily_bars WHERE snapshot_id=? AND trade_date<=? "
        "GROUP BY ts_code,trade_date HAVING count(*)>1)",
        [SNAPSHOT_ID, HISTORICAL_CUTOFF.strftime("%Y%m%d")],
    ).fetchone()
    if row is None or type(row[0]) is not int or row[0] < 0:
        raise PostIpoNumerologyContractError("duplicate-key count is invalid")
    return row[0]


def _report(
    audits: Sequence[IntervalAudit],
    cohort: tuple[int, int, int, int],
    coverage: tuple[date, date],
    *,
    duplicate_keys: int = 0,
    unexpected: int = 0,
    definition: dict[str, object] | None = None,
) -> dict[str, object]:
    rows = tuple(audits)
    split_ids = (
        "development_2020_2021",
        "validation_2022_2023",
        "retrospective_holdout_2024_2026h1",
    )
    if not rows or any(row.split_id not in split_ids for row in rows):
        raise PostIpoNumerologyContractError("preflight requires historical interval audits")
    if len({row.decision_date for row in rows}) != len(rows):
        raise PostIpoNumerologyContractError("duplicate interval audit")
    if any(
        type(value) is not int or value < 0
        for row in rows
        for value in (
            row.pair_count,
            row.window_missing,
            row.window_nonfinite,
            row.window_identity,
            row.panel_count,
            row.qfq_missing,
            row.qfq_nonfinite,
            row.panel_identity,
        )
    ):
        raise PostIpoNumerologyContractError("interval audit count is invalid")
    master, observed, unobserved, master_failures = cohort
    if any(type(value) is not int or value < 0 for value in (*cohort, duplicate_keys, unexpected)):
        raise PostIpoNumerologyContractError("preflight aggregate count is invalid")
    split_counts = {name: sum(row.split_id == name for row in rows) for name in split_ids}
    minimum_pairs = {
        name: min(row.pair_count for row in rows if row.split_id == name) for name in split_ids
    }
    maximum_pairs = {
        name: max(row.pair_count for row in rows if row.split_id == name) for name in split_ids
    }
    incomplete = {
        name: sum(row.split_id == name and row.pair_count < PAIR_COUNT for row in rows)
        for name in split_ids
    }
    counts = {
        "master_identity_failure_count": master_failures,
        "window_missing_count": sum(row.window_missing for row in rows),
        "window_nonfinite_count": sum(row.window_nonfinite for row in rows),
        "window_identity_failure_count": sum(row.window_identity for row in rows),
        "qfq_panel_missing_count": sum(row.qfq_missing for row in rows),
        "qfq_panel_nonfinite_count": sum(row.qfq_nonfinite for row in rows),
        "qfq_panel_identity_failure_count": sum(row.panel_identity for row in rows),
        "duplicate_key_count": duplicate_keys,
    }
    expected_panels = all(row.panel_count == min(row.pair_count, PAIR_COUNT) * 2 for row in rows)
    blocked = any(counts.values()) or not expected_panels or unexpected > 0
    selected_panels_complete = expected_panels and not any(
        value for name, value in counts.items() if name.startswith("qfq_panel_")
    )
    structural = (
        any(incomplete.values())
        or split_counts["validation_2022_2023"] < 20
        or split_counts["retrospective_holdout_2024_2026h1"] < 24
    )
    report: dict[str, object] = {
        "schema_version": "a-share-post-ipo-numerology-preflight-v1",
        "research_id": RESEARCH_ID,
        "phase": "OUTCOME_FREE_PREFLIGHT",
        "status": "INPUT_BLOCKED"
        if blocked
        else "STRUCTURAL_FAIL"
        if structural
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
        "split_minimum_pair_counts": minimum_pairs,
        "split_maximum_pair_counts": maximum_pairs,
        "split_incomplete_interval_counts": incomplete,
        "window_panels_complete": counts["window_missing_count"] == 0
        and counts["window_nonfinite_count"] == 0
        and counts["window_identity_failure_count"] == 0,
        "qfq_panels_complete": selected_panels_complete,
        "adj_factor_panels_complete": selected_panels_complete,
        **counts,
        "unexpected_exception_count": unexpected,
        "post_entry_outcomes_opened": False,
        "embargo_or_prospective_data_accessed": False,
        "security_identifiers_in_report": False,
        "strategy_candidate_available": False,
    }
    frozen = definition if definition is not None else _definition()
    try:
        allowed = frozen["outcome_free_preflight"]["allowed_fields"]  # type: ignore[index]
    except (KeyError, TypeError) as exc:
        raise PostIpoNumerologyContractError("definition preflight allowlist is invalid") from exc
    if not isinstance(allowed, list) or any(not isinstance(field, str) for field in allowed):
        raise PostIpoNumerologyContractError("definition preflight allowlist is invalid")
    if len(allowed) != len(set(allowed)) or set(report) != set(allowed):
        raise PostIpoNumerologyContractError("preflight report differs from frozen allowlist")
    return report


def run_read_only_preflight(database_path: str | Path) -> dict[str, object]:
    definition = _definition()
    path = Path(database_path)
    before = _digest(path)
    if before[0] != DATABASE_SHA256:
        raise PostIpoNumerologyContractError("database SHA-256 is not frozen")
    receipt = _receipt(path.parent / "receipts" / SNAPSHOT_RECEIPT_FILENAME)
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
        raise PostIpoNumerologyContractError("receipt does not bind the frozen snapshot")
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
            or snapshot[3:]
            != (
                1,
                CLASSIFICATION,
                True,
            )
        ):
            raise PostIpoNumerologyContractError("snapshot identity is invalid")
        coverage = (_parse_day(snapshot[1]), _parse_day(snapshot[2]))
        if coverage != (COVERAGE_START, HISTORICAL_CUTOFF):
            raise PostIpoNumerologyContractError("snapshot coverage is not frozen")
        _validated_calendar(connection)
        cohort = _cohort_counts(connection)
        audits = _database_audits(connection)
        report = _report(
            audits,
            cohort,
            coverage,
            duplicate_keys=_duplicate_keys(connection),
            definition=definition,
        )
    finally:
        connection.close()
    if _digest(path) != before:
        raise PostIpoNumerologyContractError("database changed during read-only preflight")
    return report
