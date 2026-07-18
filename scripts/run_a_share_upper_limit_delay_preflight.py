"""Aggregate-only read-only preflight for the frozen upper-limit-delay study."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import stat
from typing import Any

from quant_system.research.upper_limit_delay import (
    CALENDAR_DIGEST,
    CALENDAR_EXCHANGE,
    CALENDAR_ROW_COUNT,
    CALENDAR_SNAPSHOT_ID,
    CALENDAR_SOURCE,
    COVERAGE_START,
    DATABASE_SHA256,
    DEFINITION_SHA256,
    HISTORICAL_CUTOFF,
    MAX_POSITIONS,
    MIN_ELIGIBLE,
    RESEARCH_ID,
    SNAPSHOT_DIGEST,
    SNAPSHOT_ID,
    SNAPSHOT_RECEIPT_FILENAME,
    SNAPSHOT_RECEIPT_SHA256,
    IntervalAudit,
    UpperLimitDelayContractError,
    common_a_symbol,
)

CLASSIFICATION = "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT"
AVAILABLE_AT_STATUS = "UNKNOWN_NOT_PIT_QUALIFIED"
HISTORICAL_IS_ST_STATUS = "ALL_FALSE_NOT_HISTORICALLY_QUALIFIED"
_DEFINITION_PATH = (
    Path(__file__).resolve().parents[1]
    / "research"
    / "definitions"
    / "a_share_upper_limit_delayed_price_discovery_v1.json"
)


def _captured_regular_bytes(path: Path, label: str) -> bytes:
    """Read one immutable regular-file identity and reject link/replacement drift."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise UpperLimitDelayContractError(f"{label} must be a readable regular file") from exc
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise UpperLimitDelayContractError(f"{label} must be a readable regular file")
        raw = stream.read()
        after = os.fstat(stream.fileno())
    try:
        path_state = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise UpperLimitDelayContractError(f"{label} changed during capture") from exc
    identity = lambda value: (  # noqa: E731 - compact immutable identity projection
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
    )
    if identity(before) != identity(after) or identity(after) != identity(path_state):
        raise UpperLimitDelayContractError(f"{label} changed during capture")
    return raw


def _strict_json_object(raw: bytes, label: str) -> dict[str, object]:
    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise UpperLimitDelayContractError(f"{label} contains a duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise UpperLimitDelayContractError(f"{label} contains nonfinite JSON: {value}")

    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=object_pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpperLimitDelayContractError(f"{label} is not strict JSON") from exc
    if not isinstance(payload, dict):
        raise UpperLimitDelayContractError(f"{label} must be a JSON object")
    return payload


def _definition_payload(path: Path | None = None) -> dict[str, object]:
    raw = _captured_regular_bytes(path or _DEFINITION_PATH, "strategy definition")
    if hashlib.sha256(raw).hexdigest() != DEFINITION_SHA256:
        raise UpperLimitDelayContractError("strategy definition SHA-256 is not frozen")
    return _strict_json_object(raw, "strategy definition")


def _digest(path: Path) -> tuple[str, tuple[int, int, int]]:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise UpperLimitDelayContractError("database path must be a readable regular file") from exc
    with os.fdopen(descriptor, "rb") as stream:
        stat = os.fstat(stream.fileno())
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest(), (stat.st_dev, stat.st_ino, stat.st_size)


def _receipt(path: Path) -> dict[str, object]:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise UpperLimitDelayContractError("snapshot receipt is unreadable") from exc
    with os.fdopen(descriptor, "rb") as stream:
        raw = stream.read()
    if hashlib.sha256(raw).hexdigest() != SNAPSHOT_RECEIPT_SHA256:
        raise UpperLimitDelayContractError("snapshot receipt SHA-256 is not frozen")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpperLimitDelayContractError("snapshot receipt is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise UpperLimitDelayContractError("snapshot receipt must be an object")
    return payload


def _parse_day(value: object) -> date:
    try:
        return datetime.strptime(str(value), "%Y%m%d").date()
    except ValueError as exc:
        raise UpperLimitDelayContractError("database contains an invalid date") from exc


def _valid_hash(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _legacy_symbol_master_identity(
    value: object, *, source: object, snapshot_id: object, symbol: object
) -> None:
    components = (source, snapshot_id, symbol)
    if any(
        not isinstance(component, str) or not component or "|" in component
        for component in components
    ):
        raise UpperLimitDelayContractError("legacy symbol-master components are invalid")
    expected = f"{source}|{snapshot_id}|symbol_master|{symbol}|"
    if not isinstance(value, str) or value.count("|") != 4 or value != expected:
        raise UpperLimitDelayContractError("legacy symbol-master row identity differs")


def _validate_master(connection: Any) -> None:
    rows = connection.execute(
        "SELECT ts_code,nullif(list_date,''),source,snapshot_id,row_hash,synthetic_data "
        "FROM a_share.a_share_symbol_master QUALIFY row_number() OVER "
        "(PARTITION BY ts_code ORDER BY ingested_at DESC,snapshot_id DESC)=1"
    ).fetchall()
    accepted: set[str] = set()
    for symbol, listed, source, snapshot_id, row_hash, synthetic in rows:
        if not common_a_symbol(symbol):
            continue
        if not listed or synthetic is not False:
            raise UpperLimitDelayContractError("symbol-master identity is incomplete")
        _parse_day(listed)
        _legacy_symbol_master_identity(
            row_hash,
            source=source,
            snapshot_id=snapshot_id,
            symbol=symbol,
        )
        if symbol in accepted:
            raise UpperLimitDelayContractError("symbol-master contains a duplicate symbol")
        accepted.add(symbol)
    if len(accepted) < MIN_ELIGIBLE:
        raise UpperLimitDelayContractError("symbol-master common-share coverage is incomplete")


def _calendar_digest(rows: Sequence[Sequence[object]]) -> str:
    encoded = json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validated_calendar(connection: Any) -> tuple[tuple[str, ...], str]:
    """Capture the exact accepted calendar rows and prove bar/reference date parity."""
    rows = connection.execute(
        "SELECT snapshot_id,exchange,trade_date,is_open,pretrade_date,source,"
        "ingested_at,row_hash,synthetic_data FROM a_share.a_share_trade_calendar "
        "WHERE trade_date<=? ORDER BY exchange,trade_date,row_hash",
        [HISTORICAL_CUTOFF.strftime("%Y%m%d")],
    ).fetchall()
    if len(rows) != CALENDAR_ROW_COUNT:
        raise UpperLimitDelayContractError("calendar row count is not frozen")
    days: list[str] = []
    seen: dict[tuple[str, str], int] = {}
    previous: str | None = None
    for row in rows:
        if not isinstance(row, (tuple, list)) or len(row) != 9:
            raise UpperLimitDelayContractError("calendar row shape is invalid")
        snapshot, exchange, trade_day, is_open, pretrade, source, ingested, row_hash, synthetic = (
            row
        )
        _parse_day(trade_day)
        key = (str(exchange), str(trade_day))
        if key in seen:
            if seen[key] != is_open:
                raise UpperLimitDelayContractError("calendar has conflicting exchange-date flags")
            raise UpperLimitDelayContractError("calendar has duplicate exchange-date rows")
        seen[key] = is_open
        if (
            snapshot != CALENDAR_SNAPSHOT_ID
            or exchange != CALENDAR_EXCHANGE
            or source != CALENDAR_SOURCE
            or type(is_open) is not int
            or is_open != 1
            or synthetic is not False
            or not isinstance(ingested, str)
            or not ingested
            or not _valid_hash(row_hash)
        ):
            raise UpperLimitDelayContractError("calendar row identity is invalid")
        if previous is None:
            if pretrade not in (None, ""):
                raise UpperLimitDelayContractError("calendar first predecessor is invalid")
        elif pretrade != previous:
            raise UpperLimitDelayContractError("calendar predecessor chain is invalid")
        previous = str(trade_day)
        days.append(previous)
    if (
        not days
        or days != sorted(days)
        or days[0] != COVERAGE_START.strftime("%Y%m%d")
        or days[-1] != HISTORICAL_CUTOFF.strftime("%Y%m%d")
    ):
        raise UpperLimitDelayContractError("calendar coverage is not frozen")
    digest = _calendar_digest(rows)
    if digest != CALENDAR_DIGEST:
        raise UpperLimitDelayContractError("calendar digest is not frozen")

    def accepted_dates(where: str, parameters: list[object]) -> tuple[str, ...]:
        values = connection.execute(
            "SELECT trade_date,count(*) FROM a_share.a_share_canonical_daily_bars WHERE "
            + where
            + " AND trade_date<=? GROUP BY trade_date ORDER BY trade_date",
            [*parameters, HISTORICAL_CUTOFF.strftime("%Y%m%d")],
        ).fetchall()
        if any(
            not isinstance(value, (tuple, list))
            or len(value) != 2
            or type(value[1]) is not int
            or value[1] <= 0
            for value in values
        ):
            raise UpperLimitDelayContractError("calendar parity rows are invalid")
        return tuple(str(value[0]) for value in values)

    snapshot_days = accepted_dates("snapshot_id=?", [SNAPSHOT_ID])
    reference_days = accepted_dates(
        "snapshot_id=? AND ts_code=?",
        [SNAPSHOT_ID, "510300.SH"],
    )
    frozen_days = tuple(days)
    if snapshot_days != frozen_days or reference_days != frozen_days:
        raise UpperLimitDelayContractError("calendar and accepted bar dates differ")
    return frozen_days, digest


_SCAN_SQL = r"""
WITH calendar_base AS (
  SELECT trade_date,
         row_number() OVER (ORDER BY trade_date) AS session_index
  FROM a_share.a_share_trade_calendar
  WHERE snapshot_id=? AND exchange=? AND source=? AND is_open=1
    AND synthetic_data=false AND trade_date<=?
), calendar AS (
  SELECT trade_date,session_index,
         lead(trade_date,1) OVER (ORDER BY trade_date) AS d1,
         lead(trade_date,2) OVER (ORDER BY trade_date) AS d2
  FROM calendar_base
), triplets AS (
  SELECT trade_date AS d,d1,d2,
         CASE
           WHEN trade_date BETWEEN '20200101' AND '20211231' AND d2<='20211231'
             THEN 'development_2020_2021'
           WHEN trade_date BETWEEN '20220101' AND '20231231' AND d2<='20231231'
             THEN 'validation_2022_2023'
           WHEN trade_date BETWEEN '20240101' AND '20260630' AND d2<='20260630'
             THEN 'retrospective_holdout_2024_2026h1'
           ELSE NULL
         END AS split_id
  FROM calendar
  WHERE d1 IS NOT NULL AND d2 IS NOT NULL
), masters AS (
  SELECT ts_code,nullif(list_date,'') AS list_date,nullif(delist_date,'') AS delist_date
  FROM a_share.a_share_symbol_master
  QUALIFY row_number() OVER (
    PARTITION BY ts_code ORDER BY ingested_at DESC,snapshot_id DESC
  )=1
), master_sessions AS (
  SELECT m.ts_code,m.list_date,m.delist_date,min(c.session_index) AS list_session_index
  FROM masters m JOIN calendar_base c ON c.trade_date>=m.list_date
  WHERE m.list_date IS NOT NULL
  GROUP BY m.ts_code,m.list_date,m.delist_date
), bars_counted AS (
  SELECT b.*,
         count(*) OVER (PARTITION BY b.ts_code,b.trade_date) AS key_count
  FROM a_share.a_share_canonical_daily_bars b
  WHERE b.snapshot_id=? AND b.trade_date<=?
), bars_unique AS (
  SELECT * FROM bars_counted WHERE key_count=1
), bars_windowed AS (
  SELECT b.*,c.session_index,m.list_session_index,m.delist_date,
         count(*) OVER w AS history_rows,
         count(b.amount) OVER w AS history_amount_rows,
         min(c.session_index) OVER w AS history_first_index,
         median(b.amount) OVER w AS median_amount_20,
         bool_and(b.amount IS NOT NULL AND isfinite(b.amount) AND b.amount>=0) OVER w
           AS history_amounts_valid,
         bool_and(
           b.quality_status IS NOT DISTINCT FROM ?
           AND b.synthetic_data IS NOT DISTINCT FROM false
           AND coalesce(regexp_full_match(b.row_hash,'[0-9a-f]{64}'),false)
         ) OVER w AS history_identity_valid
  FROM bars_unique b
  JOIN calendar_base c USING (trade_date)
  JOIN master_sessions m USING (ts_code)
  WINDOW w AS (
    PARTITION BY b.ts_code ORDER BY c.session_index ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
  )
), scope AS (
  SELECT t.d,t.d1,t.d2,t.split_id,m.ts_code
  FROM triplets t CROSS JOIN master_sessions m
  JOIN calendar_base c ON c.trade_date=t.d
  WHERE t.split_id IS NOT NULL
    AND (regexp_full_match(m.ts_code,'(600|601|603|605|688)[0-9]{3}\.SH') OR
         regexp_full_match(m.ts_code,'(000|001|002|003|300|301)[0-9]{3}\.SZ'))
    AND c.session_index-m.list_session_index+1>=252
    AND (m.delist_date IS NULL OR m.delist_date>t.d)
), signal_classified AS (
  SELECT s.*,q.median_amount_20,q.qfq_close,q.low,q.up_limit,q.is_limit_up,q.is_limit_down,
         q.list_status,q.is_st,q.is_suspended,
    CASE WHEN q.ts_code IS NULL OR q.low IS NULL OR q.up_limit IS NULL
           OR q.qfq_close IS NULL OR q.vol IS NULL OR q.amount IS NULL
           OR q.is_limit_up IS NULL OR q.is_limit_down IS NULL
           OR q.list_status IS NULL OR q.is_st IS NULL
           OR q.is_suspended IS NULL OR q.history_rows<>20 OR q.history_amount_rows<>20
           OR q.session_index-q.history_first_index<>19
         THEN 1 ELSE 0 END AS signal_missing,
    CASE WHEN q.ts_code IS NOT NULL AND (
           NOT coalesce(isfinite(q.low),false) OR q.low<=0
           OR NOT coalesce(isfinite(q.up_limit),false) OR q.up_limit<=0
           OR q.low>q.up_limit
           OR NOT coalesce(isfinite(q.qfq_close),false) OR q.qfq_close<=0
           OR NOT coalesce(isfinite(q.vol),false) OR q.vol<0 OR q.vol<>trunc(q.vol)
           OR NOT coalesce(isfinite(q.amount),false) OR q.amount<0
           OR q.history_amounts_valid IS DISTINCT FROM true)
         THEN 1 ELSE 0 END AS signal_nonfinite,
    CASE WHEN q.ts_code IS NOT NULL AND (
           q.quality_status IS DISTINCT FROM ?
           OR q.synthetic_data IS DISTINCT FROM false
           OR NOT coalesce(regexp_full_match(q.row_hash,'[0-9a-f]{64}'),false)
           OR q.history_identity_valid IS DISTINCT FROM true
           OR (q.is_limit_up=true AND q.is_limit_down=true)
           OR q.list_status NOT IN ('L','D','P'))
         THEN 1 ELSE 0 END AS signal_identity_failure
  FROM scope s LEFT JOIN bars_windowed q ON q.ts_code=s.ts_code AND q.trade_date=s.d
), signal_evaluated AS (
  SELECT *,
    (signal_missing=0 AND signal_nonfinite=0 AND signal_identity_failure=0
     AND list_status='L' AND is_st=false AND is_suspended=false
     AND median_amount_20>=20000000) AS is_eligible
  FROM signal_classified
), daily AS (
  SELECT d,d1,d2,split_id,
         count(ts_code) FILTER (WHERE is_eligible) AS eligible_count,
         count(ts_code) FILTER (
           WHERE is_eligible AND is_limit_up=true AND low<up_limit
         ) AS event_count,
         sum(signal_missing)::BIGINT AS signal_missing_count,
         sum(signal_nonfinite)::BIGINT AS signal_nonfinite_count,
         sum(signal_identity_failure)::BIGINT AS signal_identity_failure_count
  FROM signal_evaluated
  GROUP BY d,d1,d2,split_id
), ranked AS (
  SELECT q.ts_code,q.d AS trade_date,q.median_amount_20,q.qfq_close,
         row_number() OVER (
           PARTITION BY q.d ORDER BY q.median_amount_20 DESC,q.ts_code ASC
         ) AS event_rank
  FROM signal_evaluated q
  WHERE q.is_eligible AND q.is_limit_up=true AND q.low<q.up_limit
), selected AS (
  SELECT * FROM ranked WHERE event_rank<=15
), selected_panels AS (
  SELECT d.d,d.split_id,s.ts_code,
         s.qfq_close AS signal_mark,
         e1.qfq_open AS entry_qfq_open,e1.open AS entry_raw_open,
         e1.up_limit AS entry_up,e1.down_limit AS entry_down,
         e1.vol AS entry_volume,e1.amount AS entry_amount,
         e1.is_st AS entry_st,e1.is_suspended AS entry_suspended,
         e1.is_limit_up AS entry_limit_up,e1.is_limit_down AS entry_limit_down,
         e1.list_status AS entry_status,e1.row_hash AS entry_hash,
         e1.quality_status AS entry_quality,e1.synthetic_data AS entry_synthetic,
         e2.qfq_open AS exit_qfq_open,e2.open AS exit_raw_open,
         e2.up_limit AS exit_up,e2.down_limit AS exit_down,
         e2.is_st AS exit_st,e2.is_suspended AS exit_suspended,
         e2.is_limit_up AS exit_limit_up,e2.is_limit_down AS exit_limit_down,
         e2.list_status AS exit_status,e2.row_hash AS exit_hash,
         e2.quality_status AS exit_quality,e2.synthetic_data AS exit_synthetic
  FROM daily d LEFT JOIN selected s ON s.trade_date=d.d
  LEFT JOIN bars_unique e1 ON e1.ts_code=s.ts_code AND e1.trade_date=d.d1
  LEFT JOIN bars_unique e2 ON e2.ts_code=s.ts_code AND e2.trade_date=d.d2
), panel_aggregates AS (
  SELECT d,count(ts_code)::BIGINT AS matched_selected_row_count,
    count(*) FILTER (WHERE ts_code IS NOT NULL AND
      CASE WHEN
        entry_qfq_open IS NOT NULL AND isfinite(entry_qfq_open) AND entry_qfq_open>0 AND
        entry_raw_open IS NOT NULL AND isfinite(entry_raw_open) AND entry_raw_open>0 AND
        entry_up IS NOT NULL AND isfinite(entry_up) AND entry_up>0 AND
        entry_down IS NOT NULL AND isfinite(entry_down) AND entry_down>0 AND
        entry_down<=entry_up AND entry_st IS NOT NULL AND entry_suspended IS NOT NULL AND
        (entry_raw_open<=entry_up OR abs(entry_raw_open-entry_up)<=
          greatest(0.001,0.000001*greatest(abs(entry_raw_open),abs(entry_up)))) AND
        (entry_raw_open>=entry_down OR abs(entry_raw_open-entry_down)<=
          greatest(0.001,0.000001*greatest(abs(entry_raw_open),abs(entry_down)))) AND
        entry_limit_up IS NOT NULL AND entry_limit_down IS NOT NULL AND
        NOT (entry_limit_up=true AND entry_limit_down=true) AND
        entry_status IN ('L','D','P') AND
        coalesce(regexp_full_match(entry_hash,'[0-9a-f]{64}'),false) AND
        entry_quality IS NOT DISTINCT FROM ? AND entry_synthetic IS NOT DISTINCT FROM false
      THEN true ELSE false END) AS entry_complete_row_count,
    count(*) FILTER (WHERE ts_code IS NOT NULL AND
      CASE WHEN
        exit_qfq_open IS NOT NULL AND isfinite(exit_qfq_open) AND exit_qfq_open>0 AND
        exit_raw_open IS NOT NULL AND isfinite(exit_raw_open) AND exit_raw_open>0 AND
        exit_up IS NOT NULL AND isfinite(exit_up) AND exit_up>0 AND
        exit_down IS NOT NULL AND isfinite(exit_down) AND exit_down>0 AND
        exit_down<=exit_up AND exit_st IS NOT NULL AND exit_suspended IS NOT NULL AND
        (exit_raw_open<=exit_up OR abs(exit_raw_open-exit_up)<=
          greatest(0.001,0.000001*greatest(abs(exit_raw_open),abs(exit_up)))) AND
        (exit_raw_open>=exit_down OR abs(exit_raw_open-exit_down)<=
          greatest(0.001,0.000001*greatest(abs(exit_raw_open),abs(exit_down)))) AND
        exit_limit_up IS NOT NULL AND exit_limit_down IS NOT NULL AND
        NOT (exit_limit_up=true AND exit_limit_down=true) AND
        entry_volume IS NOT NULL AND isfinite(entry_volume) AND entry_volume>=0 AND
        entry_volume=trunc(entry_volume) AND entry_amount IS NOT NULL AND
        isfinite(entry_amount) AND entry_amount>=0 AND
        exit_status IN ('L','D','P') AND
        coalesce(regexp_full_match(exit_hash,'[0-9a-f]{64}'),false) AND
        exit_quality IS NOT DISTINCT FROM ? AND exit_synthetic IS NOT DISTINCT FROM false
      THEN true ELSE false END) AS exit_complete_row_count,
    count(*) FILTER (WHERE ts_code IS NOT NULL AND
      CASE WHEN
        signal_mark IS NOT NULL AND isfinite(signal_mark) AND signal_mark>0 AND
        entry_qfq_open IS NOT NULL AND isfinite(entry_qfq_open) AND entry_qfq_open>0 AND
        exit_qfq_open IS NOT NULL AND isfinite(exit_qfq_open) AND exit_qfq_open>0
      THEN true ELSE false END) AS mark_complete_row_count,
    coalesce(sum(
      CASE WHEN ts_code IS NOT NULL AND
        (signal_mark IS NULL OR NOT coalesce(isfinite(signal_mark),false)) THEN 1 ELSE 0 END +
      CASE WHEN ts_code IS NOT NULL AND
        (entry_qfq_open IS NULL OR NOT coalesce(isfinite(entry_qfq_open),false)) THEN 1 ELSE 0 END +
      CASE WHEN ts_code IS NOT NULL AND
        (entry_raw_open IS NULL OR NOT coalesce(isfinite(entry_raw_open),false)) THEN 1 ELSE 0 END +
      CASE WHEN ts_code IS NOT NULL AND
        (exit_qfq_open IS NULL OR NOT coalesce(isfinite(exit_qfq_open),false)) THEN 1 ELSE 0 END +
      CASE WHEN ts_code IS NOT NULL AND
        (exit_raw_open IS NULL OR NOT coalesce(isfinite(exit_raw_open),false)) THEN 1 ELSE 0 END
      + CASE WHEN ts_code IS NOT NULL AND
        (entry_volume IS NULL OR NOT coalesce(isfinite(entry_volume),false)) THEN 1 ELSE 0 END
      + CASE WHEN ts_code IS NOT NULL AND
        (entry_amount IS NULL OR NOT coalesce(isfinite(entry_amount),false)) THEN 1 ELSE 0 END
    ),0) AS selected_nonfinite_count
  FROM selected_panels GROUP BY d
), reference_panels AS (
  SELECT d.d,
    CASE WHEN r1.qfq_open IS NOT NULL AND isfinite(r1.qfq_open) AND r1.qfq_open>0 AND
     r2.qfq_open IS NOT NULL AND isfinite(r2.qfq_open) AND r2.qfq_open>0 AND
     r1.quality_status IS NOT DISTINCT FROM ? AND
     r2.quality_status IS NOT DISTINCT FROM ? AND
     r1.synthetic_data IS NOT DISTINCT FROM false AND
     r2.synthetic_data IS NOT DISTINCT FROM false AND
     coalesce(regexp_full_match(r1.row_hash,'[0-9a-f]{64}'),false) AND
     coalesce(regexp_full_match(r2.row_hash,'[0-9a-f]{64}'),false)
     THEN true ELSE false END AS reference_complete,
    (CASE WHEN r1.qfq_open IS NULL OR NOT coalesce(isfinite(r1.qfq_open),false)
      THEN 1 ELSE 0 END +
     CASE WHEN r2.qfq_open IS NULL OR NOT coalesce(isfinite(r2.qfq_open),false)
      THEN 1 ELSE 0 END) AS reference_nonfinite_count
  FROM daily d
  LEFT JOIN bars_unique r1 ON r1.ts_code='510300.SH' AND r1.trade_date=d.d1
  LEFT JOIN bars_unique r2 ON r2.ts_code='510300.SH' AND r2.trade_date=d.d2
)
SELECT d.d,d.split_id,d.eligible_count,d.event_count,
       least(d.event_count,15) AS target_slot_count,
       least(d.event_count,15)::DOUBLE/15.0 AS gross_target_exposure,
       (d.signal_missing_count=0 AND d.signal_nonfinite_count=0
        AND d.signal_identity_failure_count=0) AS signal_complete,
       d.signal_missing_count,d.signal_nonfinite_count,d.signal_identity_failure_count,
       (p.matched_selected_row_count=least(d.event_count,15)
        AND p.entry_complete_row_count=least(d.event_count,15)) AS entry_complete,
       (p.matched_selected_row_count=least(d.event_count,15)
        AND p.exit_complete_row_count=least(d.event_count,15)) AS exit_complete,
       (p.matched_selected_row_count=least(d.event_count,15)
        AND p.mark_complete_row_count=least(d.event_count,15)) AS mark_complete,
       r.reference_complete,
       p.selected_nonfinite_count+r.reference_nonfinite_count AS nonfinite_count
FROM daily d JOIN panel_aggregates p USING (d) JOIN reference_panels r USING (d)
ORDER BY d
"""


def _duplicate_key_count(connection: Any) -> int:
    row = connection.execute(
        "SELECT coalesce(sum(n-1),0) FROM (SELECT count(*) n FROM "
        "a_share.a_share_canonical_daily_bars WHERE snapshot_id=? AND trade_date<=? "
        "GROUP BY ts_code,trade_date HAVING count(*)>1)",
        [SNAPSHOT_ID, HISTORICAL_CUTOFF.strftime("%Y%m%d")],
    ).fetchone()
    if row is None or type(row[0]) is not int or row[0] < 0:
        raise UpperLimitDelayContractError("duplicate-key audit is invalid")
    return row[0]


def _database_audits(connection: Any) -> tuple[IntervalAudit, ...]:
    parameters = [
        CALENDAR_SNAPSHOT_ID,
        CALENDAR_EXCHANGE,
        CALENDAR_SOURCE,
        HISTORICAL_CUTOFF.strftime("%Y%m%d"),
        SNAPSHOT_ID,
        HISTORICAL_CUTOFF.strftime("%Y%m%d"),
        CLASSIFICATION,
        CLASSIFICATION,
        CLASSIFICATION,
        CLASSIFICATION,
        CLASSIFICATION,
        CLASSIFICATION,
    ]
    rows = connection.execute(_SCAN_SQL, parameters).fetchall()
    duplicate_count = _duplicate_key_count(connection)
    audits: list[IntervalAudit] = []
    for row in rows:
        (
            decision,
            split,
            eligible,
            events,
            slots,
            exposure,
            signal_complete,
            signal_missing,
            signal_nonfinite,
            signal_identity,
            entry_complete,
            exit_complete,
            mark_complete,
            reference_complete,
            nonfinite,
        ) = row
        values = (
            eligible,
            events,
            slots,
            signal_missing,
            signal_nonfinite,
            signal_identity,
            nonfinite,
        )
        if any(type(value) is not int or value < 0 for value in values):
            raise UpperLimitDelayContractError("preflight count is invalid")
        if (
            type(split) is not str
            or type(exposure) not in (int, float)
            or not math.isfinite(exposure)
        ):
            raise UpperLimitDelayContractError("preflight interval identity is invalid")
        flags = (signal_complete, entry_complete, exit_complete, mark_complete, reference_complete)
        if any(type(value) is not bool for value in flags):
            raise UpperLimitDelayContractError("preflight panel flag is invalid")
        audits.append(
            IntervalAudit(
                _parse_day(decision),
                split,
                eligible,
                events,
                slots,
                float(exposure),
                *flags,
                signal_panel_missing_count=signal_missing,
                signal_panel_nonfinite_count=signal_nonfinite,
                signal_panel_identity_failure_count=signal_identity,
                duplicate_key_count=duplicate_count,
                nonfinite_required_value_count=nonfinite,
            )
        )
    return tuple(audits)


def _preflight_report(
    audits: Sequence[IntervalAudit],
    coverage: tuple[date, date],
    *,
    definition: dict[str, object] | None = None,
    calendar_digest: str = CALENDAR_DIGEST,
    unexpected: int = 0,
) -> dict[str, object]:
    rows = tuple(audits)
    if not rows or any(not isinstance(row, IntervalAudit) for row in rows):
        raise UpperLimitDelayContractError("preflight audit identity is invalid")
    if len({row.decision_date for row in rows}) != len(rows):
        raise UpperLimitDelayContractError("duplicate interval audit")
    if type(unexpected) is not int or unexpected < 0:
        raise UpperLimitDelayContractError("unexpected exception count is invalid")
    split_ids = (
        "development_2020_2021",
        "validation_2022_2023",
        "retrospective_holdout_2024_2026h1",
    )
    if any(row.split_id not in split_ids for row in rows):
        raise UpperLimitDelayContractError("preflight contains a forbidden split")
    split_ranges = {
        "development_2020_2021": (date(2020, 1, 1), date(2021, 12, 31)),
        "validation_2022_2023": (date(2022, 1, 1), date(2023, 12, 31)),
        "retrospective_holdout_2024_2026h1": (date(2024, 1, 1), date(2026, 6, 30)),
    }
    for row in rows:
        integer_counts = (
            row.eligible_count,
            row.event_count,
            row.target_slot_count,
            row.signal_panel_missing_count,
            row.signal_panel_nonfinite_count,
            row.signal_panel_identity_failure_count,
            row.duplicate_key_count,
            row.nonfinite_required_value_count,
            row.split_boundary_violation_count,
        )
        flags = (
            row.signal_panel_complete,
            row.entry_panel_complete,
            row.exit_panel_complete,
            row.mark_panel_complete,
            row.reference_panel_complete,
        )
        start, end = split_ranges[row.split_id]
        if (
            any(type(value) is not int or value < 0 for value in integer_counts)
            or any(type(value) is not bool for value in flags)
            or row.target_slot_count != min(row.event_count, MAX_POSITIONS)
            or not isinstance(row.gross_target_exposure, float)
            or not math.isfinite(row.gross_target_exposure)
            or not math.isclose(
                row.gross_target_exposure,
                row.target_slot_count / MAX_POSITIONS,
                rel_tol=0.0,
                abs_tol=1e-15,
            )
            or not start <= row.decision_date <= end
        ):
            raise UpperLimitDelayContractError("preflight audit semantics are invalid")
    split_counts = {split: sum(row.split_id == split for row in rows) for split in split_ids}
    structural = any(row.eligible_count < MIN_ELIGIBLE for row in rows) or any(
        split_counts[split] < 400
        for split in ("validation_2022_2023", "retrospective_holdout_2024_2026h1")
    )
    panels = {
        "signal_panels_complete": all(
            row.signal_panel_complete
            and row.signal_panel_missing_count == 0
            and row.signal_panel_nonfinite_count == 0
            and row.signal_panel_identity_failure_count == 0
            for row in rows
        ),
        "entry_panels_complete": all(row.entry_panel_complete for row in rows),
        "exit_panels_complete": all(row.exit_panel_complete for row in rows),
        "mark_panels_complete": all(row.mark_panel_complete for row in rows),
        "reference_panels_complete": all(row.reference_panel_complete for row in rows),
    }
    counts = {
        "signal_panel_missing_count": sum(row.signal_panel_missing_count for row in rows),
        "signal_panel_nonfinite_count": sum(row.signal_panel_nonfinite_count for row in rows),
        "signal_panel_identity_failure_count": sum(
            row.signal_panel_identity_failure_count for row in rows
        ),
        "duplicate_key_count": max(row.duplicate_key_count for row in rows),
        "nonfinite_required_value_count": sum(row.nonfinite_required_value_count for row in rows),
        "split_boundary_violation_count": sum(row.split_boundary_violation_count for row in rows),
    }
    blocked = not all(panels.values()) or any(counts.values()) or unexpected > 0
    report: dict[str, object] = {
        "schema_version": "a-share-upper-limit-delay-preflight-v1",
        "research_id": RESEARCH_ID,
        "phase": "OUTCOME_FREE_PREFLIGHT",
        "status": (
            "PREFLIGHT_PASS"
            if not structural and not blocked
            else "INPUT_BLOCKED"
            if blocked
            else "STRUCTURAL_FAIL"
        ),
        "snapshot_id": SNAPSHOT_ID,
        "calendar_snapshot_id": CALENDAR_SNAPSHOT_ID,
        "calendar_digest": calendar_digest,
        "database_sha256": DATABASE_SHA256,
        "snapshot_digest": SNAPSHOT_DIGEST,
        "snapshot_receipt_sha256": SNAPSHOT_RECEIPT_SHA256,
        "classification": CLASSIFICATION,
        "available_at_status": AVAILABLE_AT_STATUS,
        "historical_is_st_status": HISTORICAL_IS_ST_STATUS,
        "coverage_start": coverage[0].isoformat(),
        "coverage_end": coverage[1].isoformat(),
        "split_interval_counts": split_counts,
        "split_event_counts": {
            split: sum(row.event_count for row in rows if row.split_id == split)
            for split in split_ids
        },
        "split_zero_event_counts": {
            split: sum(row.split_id == split and row.event_count == 0 for row in rows)
            for split in split_ids
        },
        "minimum_eligible_count": min(row.eligible_count for row in rows),
        "maximum_eligible_count": max(row.eligible_count for row in rows),
        "minimum_target_slot_count": min(row.target_slot_count for row in rows),
        "maximum_target_slot_count": max(row.target_slot_count for row in rows),
        "minimum_gross_target_exposure": min(row.gross_target_exposure for row in rows),
        "maximum_gross_target_exposure": max(row.gross_target_exposure for row in rows),
        **panels,
        **counts,
        "blocked_retry_and_terminal_state_validation": "NOT_EVALUATED_PR_A",
        "unexpected_exception_count": unexpected,
        "currency_unit": "CNY",
        "position_unit": "SHARES",
        "post_entry_outcomes_opened": False,
        "embargo_or_prospective_data_accessed": False,
        "security_identifiers_in_report": False,
        "strategy_candidate_available": False,
    }
    captured_definition = definition if definition is not None else _definition_payload()
    try:
        allowed = captured_definition["outcome_free_preflight"]["allowed_fields"]  # type: ignore[index]
    except (KeyError, TypeError) as exc:
        raise UpperLimitDelayContractError(
            "strategy definition preflight allowlist is invalid"
        ) from exc
    if (
        not isinstance(allowed, list)
        or any(not isinstance(field, str) for field in allowed)
        or len(allowed) != len(set(allowed))
    ):
        raise UpperLimitDelayContractError("strategy definition preflight allowlist is invalid")
    if set(report) != set(allowed):
        raise UpperLimitDelayContractError("preflight report differs from its field allowlist")
    return report


def run_read_only_preflight(database_path: str | Path) -> dict[str, object]:
    definition = _definition_payload()
    path = Path(database_path)
    before = _digest(path)
    if before[0] != DATABASE_SHA256:
        raise UpperLimitDelayContractError("database SHA-256 is not frozen")
    receipt = _receipt(path.parent / "receipts" / SNAPSHOT_RECEIPT_FILENAME)
    expected_receipt = {
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
    if any(receipt.get(key) != value for key, value in expected_receipt.items()):
        raise UpperLimitDelayContractError("receipt does not bind the frozen snapshot")
    import duckdb

    connection = duckdb.connect(str(path), read_only=True)
    try:
        connection.execute("SET enable_external_access=false")
        snapshot = connection.execute(
            "SELECT count(*),min(trade_date),max(trade_date),"
            "count(DISTINCT quality_status),min(quality_status),"
            "bool_and(not synthetic_data) FROM a_share.a_share_canonical_daily_bars "
            "WHERE snapshot_id=? AND trade_date<=?",
            [SNAPSHOT_ID, HISTORICAL_CUTOFF.strftime("%Y%m%d")],
        ).fetchone()
        if (
            snapshot is None
            or snapshot[0] <= 0
            or receipt.get("target_rows") != snapshot[0]
            or snapshot[3:] != (1, CLASSIFICATION, True)
        ):
            raise UpperLimitDelayContractError("snapshot identity is invalid")
        coverage = (_parse_day(snapshot[1]), _parse_day(snapshot[2]))
        if coverage != (COVERAGE_START, HISTORICAL_CUTOFF):
            raise UpperLimitDelayContractError("snapshot coverage is not frozen")
        _, calendar_digest = _validated_calendar(connection)
        _validate_master(connection)
        audits = _database_audits(connection)
        report = _preflight_report(
            audits,
            coverage,
            definition=definition,
            calendar_digest=calendar_digest,
        )
    finally:
        connection.close()
    if _digest(path) != before:
        raise UpperLimitDelayContractError("database changed during read-only preflight")
    return report
