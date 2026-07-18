from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from quant_system.research import post_ipo_age as age

CLASSIFICATION = "RETROSPECTIVE_PERSONAL_RESEARCH_GRADE_SECONDARY_NOT_STRICT_PIT"
AVAILABLE_AT_STATUS = "UNKNOWN_NOT_PIT_QUALIFIED"
HISTORICAL_IS_ST_STATUS = "UNKNOWN_NOT_USED_AS_FILTER"
_DEFINITION_PATH = (
    Path(__file__).resolve().parents[1]
    / "research/definitions/a_share_post_ipo_age_underperformance_avoidance_v1.json"
)
_ORDINARY = r"((600|601|603|605|688)[0-9]{3}\.SH|(000|001|002|003|300|301)[0-9]{3}\.SZ)"


def _capture(path: Path, label: str) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            raise OSError
        return path.read_bytes()
    except OSError as exc:
        raise age.PostIpoAgeContractError(f"{label} must be a readable regular file") from exc


def _strict_json(raw: bytes, label: str) -> dict[str, object]:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            if key in result:
                raise age.PostIpoAgeContractError(f"{label} has duplicate JSON keys")
            result[key] = value
        return result

    def constant(value: str) -> object:
        raise age.PostIpoAgeContractError(f"{label} has nonfinite JSON {value}")

    try:
        value = json.loads(raw.decode(), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise age.PostIpoAgeContractError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise age.PostIpoAgeContractError(f"{label} must be a JSON object")
    return value


def _definition(path: Path | None = None) -> dict[str, object]:
    raw = _capture(path or _DEFINITION_PATH, "strategy definition")
    if hashlib.sha256(raw).hexdigest() != age.DEFINITION_SHA256:
        raise age.PostIpoAgeContractError("strategy definition SHA-256 is not frozen")
    return _strict_json(raw, "strategy definition")


def _parse_day(value: object) -> date:
    return datetime.strptime(str(value), "%Y%m%d").date()


def _digest(path: Path) -> tuple[str, int, int]:
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return digest, (metadata := path.stat()).st_size, metadata.st_mtime_ns


def _validated_calendar(connection: Any) -> None:
    rows = connection.execute(
        "SELECT snapshot_id,exchange,trade_date,is_open,pretrade_date,source,ingested_at,"
        "row_hash,synthetic_data FROM a_share.a_share_trade_calendar WHERE trade_date<=? "
        "ORDER BY exchange,trade_date,row_hash",
        [age.HISTORICAL_CUTOFF.strftime("%Y%m%d")],
    ).fetchall()
    if len(rows) != age.CALENDAR_ROW_COUNT or any(len(row) != 9 for row in rows):
        raise age.PostIpoAgeContractError("calendar row count is not frozen")
    days = [str(row[2]) for row in rows]
    for day in days:
        _parse_day(day)
    digest = hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
    if (
        days[0] != age.COVERAGE_START.strftime("%Y%m%d")
        or days[-1] != age.HISTORICAL_CUTOFF.strftime("%Y%m%d")
        or len(days) != len(set(days))
        or days != sorted(days)
        or digest != age.CALENDAR_DIGEST
    ):
        raise age.PostIpoAgeContractError("calendar coverage or digest is not frozen")


def _cohort_counts(connection: Any) -> tuple[int, int, int, int]:
    row = connection.execute(
        "WITH m AS (SELECT * FROM a_share.a_share_symbol_master QUALIFY row_number() OVER "
        "(PARTITION BY ts_code ORDER BY ingested_at DESC,snapshot_id DESC)=1), ordinary AS "
        "(SELECT * FROM m WHERE regexp_full_match(ts_code,?)), observed AS (SELECT DISTINCT "
        "b.ts_code FROM a_share.a_share_canonical_daily_bars b JOIN ordinary o USING(ts_code) "
        "WHERE b.snapshot_id=?) SELECT (SELECT count(*) FROM ordinary),(SELECT count(*) FROM "
        "observed),(SELECT count(*) FROM ordinary o WHERE NOT EXISTS (SELECT 1 FROM observed s "
        "WHERE s.ts_code=o.ts_code)),(SELECT count(*) FROM ordinary WHERE market NOT IN "
        "(?,?,?) OR list_date IS NULL OR NOT regexp_full_match(list_date,'[0-9]{8}') OR "
        "synthetic_data IS DISTINCT FROM false OR row_hash IS DISTINCT FROM "
        "source||'|'||snapshot_id||'|symbol_master|'||ts_code||'|')",
        [_ORDINARY, age.SNAPSHOT_ID, *age.BOARD_LABELS],
    ).fetchone()
    if row is None or len(row) != 4 or any(type(value) is not int or value < 0 for value in row):
        raise age.PostIpoAgeContractError("cohort count audit is invalid")
    master, observed, unobserved, failures = row
    if (master, observed, unobserved) != (
        age.EXPECTED_MASTER_ORDINARY,
        age.EXPECTED_OBSERVED_ORDINARY,
        age.EXPECTED_UNOBSERVED_ORDINARY,
    ):
        failures += 1
    return master, observed, unobserved, failures


_SCAN_SQL = r"""
WITH cb AS (
 SELECT trade_date,row_number() OVER(ORDER BY trade_date) si FROM a_share.a_share_trade_calendar
 WHERE snapshot_id=? AND exchange=? AND source=? AND is_open=1 AND synthetic_data=false
   AND trade_date<=?
), mo AS (
 SELECT min(trade_date) first_d,max(trade_date) d FROM cb
 GROUP BY strftime(strptime(trade_date,'%Y%m%d'),'%Y%m')
), mi AS (
 SELECT d,lead(first_d,1) OVER(ORDER BY d) entry_d,lead(first_d,2) OVER(ORDER BY d) exit_d
 FROM mo
), intervals AS (
 SELECT d,entry_d,exit_d,CASE
  WHEN entry_d BETWEEN '20200101' AND '20211231' AND exit_d<='20211231' THEN 'development_2020_2021'
  WHEN entry_d BETWEEN '20220101' AND '20231231' AND exit_d<='20231231' THEN 'validation_2022_2023'
  WHEN entry_d BETWEEN '20240101' AND '20260630' AND exit_d<='20260630' THEN 'retrospective_holdout_2024_2026h1'
 END split_id FROM mi WHERE entry_d>='20200101' AND d<'20260501'
), master AS (
 SELECT ts_code,market board,strptime(list_date,'%Y%m%d')::DATE list_day
 FROM a_share.a_share_symbol_master WHERE regexp_full_match(ts_code,?)
 QUALIFY row_number() OVER(PARTITION BY ts_code ORDER BY ingested_at DESC,snapshot_id DESC)=1
), observed AS (
 SELECT m.* FROM master m JOIN (SELECT DISTINCT ts_code FROM a_share.a_share_canonical_daily_bars
 WHERE snapshot_id=?) b USING(ts_code) WHERE board IN (?,?,?)
), bc AS (
 SELECT b.*,count(*) OVER(PARTITION BY ts_code,trade_date) key_n
 FROM a_share.a_share_canonical_daily_bars b WHERE snapshot_id=? AND trade_date<=?
), bu AS (SELECT * FROM bc WHERE key_n=1), bw AS (
 SELECT b.*,c.si,count(*) OVER w n,count(amount) OVER w amount_n,min(c.si) OVER w first_w,
  median(amount) OVER w med_amount,
  bool_and(amount IS NOT NULL AND isfinite(amount) AND amount>=0) OVER w amount_ok,
  bool_and(adj_factor IS NOT NULL AND isfinite(adj_factor) AND adj_factor>0
   AND quality_status IS NOT DISTINCT FROM ? AND synthetic_data IS NOT DISTINCT FROM false
   AND coalesce(regexp_full_match(row_hash,'[0-9a-f]{64}'),false)) OVER w identity_ok
 FROM bu b JOIN cb c USING(trade_date)
 WINDOW w AS(PARTITION BY ts_code ORDER BY c.si ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
), scope AS (
 SELECT i.*,m.ts_code,m.board,m.list_day,CASE
  WHEN m.list_day<=strptime(i.d,'%Y%m%d')::DATE
   AND strptime(i.d,'%Y%m%d')::DATE<m.list_day+INTERVAL 3 YEAR THEN 'young'
  WHEN strptime(i.d,'%Y%m%d')::DATE>=m.list_day+INTERVAL 5 YEAR THEN 'seasoned' END side
 FROM intervals i CROSS JOIN observed m WHERE i.split_id IS NOT NULL
), classified AS (
 SELECT s.*,b.med_amount,CASE WHEN b.ts_code IS NULL OR b.n<>20 OR b.amount_n<>20
   OR b.si-b.first_w<>19 OR b.amount_ok IS DISTINCT FROM true
   OR b.identity_ok IS DISTINCT FROM true THEN 1 ELSE 0 END excluded
 FROM scope s LEFT JOIN bw b ON b.ts_code=s.ts_code AND b.trade_date=s.d WHERE s.side IS NOT NULL
), valid AS (SELECT * FROM classified WHERE excluded=0), ranked AS (
 SELECT *,row_number() OVER(PARTITION BY d,board,side ORDER BY med_amount DESC,ts_code) rn
 FROM valid
), pairs AS (
 SELECT y.d,y.entry_d,y.exit_d,y.split_id,y.ts_code young_code,s.ts_code seasoned_code,
  least(y.med_amount,s.med_amount) pair_liq FROM ranked y JOIN ranked s
 ON y.d=s.d AND y.board=s.board AND y.rn=s.rn WHERE y.side='young' AND s.side='seasoned'
), selected AS (
 SELECT * FROM pairs QUALIFY row_number() OVER(PARTITION BY d ORDER BY pair_liq DESC,
  young_code,seasoned_code)<=50
), symbols AS (
 SELECT d,entry_d,exit_d,young_code ts_code FROM selected UNION ALL
 SELECT d,entry_d,exit_d,seasoned_code FROM selected
), panels AS (
 SELECT s.*,e.qfq_open entry_qfq,e.adj_factor entry_adj,e.quality_status entry_quality,
  e.synthetic_data entry_synth,e.row_hash entry_hash,x.qfq_open exit_qfq,x.adj_factor exit_adj,
  x.quality_status exit_quality,x.synthetic_data exit_synth,x.row_hash exit_hash
 FROM symbols s LEFT JOIN bu e ON e.ts_code=s.ts_code AND e.trade_date=s.entry_d
 LEFT JOIN bu x ON x.ts_code=s.ts_code AND x.trade_date=s.exit_d
), pa AS (
 SELECT d,count(*) panel_n,
  sum(CASE WHEN entry_qfq IS NULL OR exit_qfq IS NULL OR entry_adj IS NULL OR exit_adj IS NULL
   THEN 1 ELSE 0 END)::BIGINT panel_missing,
  sum(CASE WHEN (entry_qfq IS NOT NULL AND (NOT isfinite(entry_qfq) OR entry_qfq<=0))
   OR (exit_qfq IS NOT NULL AND (NOT isfinite(exit_qfq) OR exit_qfq<=0))
   OR (entry_adj IS NOT NULL AND (NOT isfinite(entry_adj) OR entry_adj<=0))
   OR (exit_adj IS NOT NULL AND (NOT isfinite(exit_adj) OR exit_adj<=0)) THEN 1 ELSE 0 END)::BIGINT panel_nonfinite,
  sum(CASE WHEN entry_quality IS DISTINCT FROM ? OR exit_quality IS DISTINCT FROM ?
   OR entry_synth IS DISTINCT FROM false OR exit_synth IS DISTINCT FROM false
   OR NOT coalesce(regexp_full_match(entry_hash,'[0-9a-f]{64}'),false)
   OR NOT coalesce(regexp_full_match(exit_hash,'[0-9a-f]{64}'),false) THEN 1 ELSE 0 END)::BIGINT panel_identity
 FROM panels GROUP BY d
), pc AS (SELECT d,count(*)::BIGINT pair_n FROM pairs GROUP BY d), exclusions AS (
 SELECT d,sum(CASE WHEN side='young' THEN excluded ELSE 0 END)::BIGINT young_excluded,
  sum(CASE WHEN side='seasoned' THEN excluded ELSE 0 END)::BIGINT seasoned_excluded
 FROM classified GROUP BY d
)
SELECT i.d,i.split_id,(i.split_id IS NULL) purged,coalesce(pc.pair_n,0)::BIGINT pair_n,
 coalesce(e.young_excluded,0)::BIGINT young_excluded,
 coalesce(e.seasoned_excluded,0)::BIGINT seasoned_excluded,coalesce(pa.panel_n,0)::BIGINT panel_n,
 coalesce(pa.panel_missing,0)::BIGINT panel_missing,coalesce(pa.panel_nonfinite,0)::BIGINT panel_nonfinite,
 coalesce(pa.panel_identity,0)::BIGINT panel_identity
FROM intervals i LEFT JOIN pc USING(d) LEFT JOIN exclusions e USING(d) LEFT JOIN pa USING(d)
ORDER BY i.d
"""


@dataclass(frozen=True)
class IntervalAudit:
    decision_date: date
    split_id: str | None
    purged: bool
    pair_count: int
    young_excluded: int = 0
    seasoned_excluded: int = 0
    panel_count: int = 0
    panel_missing: int = 0
    panel_nonfinite: int = 0
    panel_identity: int = 0


def _database_audits(connection: Any) -> tuple[IntervalAudit, ...]:
    parameters = [
        age.CALENDAR_SNAPSHOT_ID,
        age.CALENDAR_EXCHANGE,
        age.CALENDAR_SOURCE,
        age.HISTORICAL_CUTOFF.strftime("%Y%m%d"),
        _ORDINARY,
        age.SNAPSHOT_ID,
        *age.BOARD_LABELS,
        age.SNAPSHOT_ID,
        age.HISTORICAL_CUTOFF.strftime("%Y%m%d"),
        CLASSIFICATION,
        CLASSIFICATION,
        CLASSIFICATION,
    ]
    audits = []
    for row in connection.execute(_SCAN_SQL, parameters).fetchall():
        if len(row) != 10:
            raise age.PostIpoAgeContractError("preflight interval shape is invalid")
        day, split, purged, *counts = row
        if type(purged) is not bool or any(type(value) is not int or value < 0 for value in counts):
            raise age.PostIpoAgeContractError("preflight interval counts are invalid")
        audits.append(IntervalAudit(_parse_day(day), split, purged, *counts))
    return tuple(audits)


def _duplicate_keys(connection: Any) -> int:
    row = connection.execute(
        "SELECT coalesce(sum(n-1),0) FROM (SELECT count(*) n FROM "
        "a_share.a_share_canonical_daily_bars WHERE snapshot_id=? AND trade_date<=? "
        "GROUP BY ts_code,trade_date HAVING count(*)>1)",
        [age.SNAPSHOT_ID, age.HISTORICAL_CUTOFF.strftime("%Y%m%d")],
    ).fetchone()
    if row is None or type(row[0]) is not int or row[0] < 0:
        raise age.PostIpoAgeContractError("duplicate-key count is invalid")
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
    valid = tuple(row for row in rows if not row.purged)
    if not valid or any(row.split_id not in split_ids for row in valid):
        raise age.PostIpoAgeContractError("preflight requires historical interval audits")
    if len({row.decision_date for row in rows}) != len(rows):
        raise age.PostIpoAgeContractError("duplicate interval audit")
    master, observed, unobserved, master_failures = cohort
    values = (*cohort, duplicate_keys, unexpected)
    if any(type(value) is not int or value < 0 for value in values):
        raise age.PostIpoAgeContractError("preflight aggregate count is invalid")
    split_counts = {name: sum(row.split_id == name for row in valid) for name in split_ids}
    minimum_pairs = {
        name: min(row.pair_count for row in valid if row.split_id == name) for name in split_ids
    }
    maximum_pairs = {
        name: max(row.pair_count for row in valid if row.split_id == name) for name in split_ids
    }
    incomplete = {
        name: sum(row.split_id == name and row.pair_count < age.PAIR_COUNT for row in valid)
        for name in split_ids
    }
    invalid = {
        name: sum(
            row.split_id == name
            and (
                row.pair_count < age.PAIR_COUNT
                or row.panel_count != age.PAIR_COUNT * 2
                or row.panel_missing + row.panel_nonfinite + row.panel_identity > 0
            )
            for row in valid
        )
        for name in split_ids
    }
    selected = {
        "selected_panel_missing_count": sum(row.panel_missing for row in valid),
        "selected_panel_nonfinite_count": sum(row.panel_nonfinite for row in valid),
        "selected_panel_identity_failure_count": sum(row.panel_identity for row in valid),
    }
    panel_count_wrong = any(
        row.panel_count != min(row.pair_count, age.PAIR_COUNT) * 2 for row in valid
    )
    blocked = (
        master_failures > 0
        or any(selected.values())
        or panel_count_wrong
        or duplicate_keys > 0
        or unexpected > 0
    )
    structural = (
        any(incomplete.values())
        or split_counts["validation_2022_2023"] < 20
        or split_counts["validation_2022_2023"] > 23
        or split_counts["retrospective_holdout_2024_2026h1"] < 24
    )
    report: dict[str, object] = {
        "schema_version": "a-share-post-ipo-age-preflight-v1",
        "research_id": age.RESEARCH_ID,
        "phase": "OUTCOME_FREE_PREFLIGHT",
        "status": "INPUT_BLOCKED"
        if blocked
        else "STRUCTURAL_FAIL"
        if structural
        else "PREFLIGHT_PASS",
        "snapshot_id": age.SNAPSHOT_ID,
        "database_sha256": age.DATABASE_SHA256,
        "snapshot_digest": age.SNAPSHOT_DIGEST,
        "snapshot_receipt_sha256": age.SNAPSHOT_RECEIPT_SHA256,
        "calendar_snapshot_id": age.CALENDAR_SNAPSHOT_ID,
        "calendar_digest": age.CALENDAR_DIGEST,
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
        "split_invalid_interval_counts": invalid,
        "cross_boundary_purge_count": sum(row.purged for row in rows),
        "young_candidate_excluded_counts": {
            name: sum(row.young_excluded for row in valid if row.split_id == name)
            for name in split_ids
        },
        "seasoned_candidate_excluded_counts": {
            name: sum(row.seasoned_excluded for row in valid if row.split_id == name)
            for name in split_ids
        },
        "qfq_panels_complete": not any(selected.values()) and not panel_count_wrong,
        "adj_factor_panels_complete": not any(selected.values()) and not panel_count_wrong,
        "master_identity_failure_count": master_failures,
        **selected,
        "duplicate_key_count": duplicate_keys,
        "unexpected_exception_count": unexpected,
        "post_entry_outcomes_opened": False,
        "holdout_outcomes_opened": False,
        "prospective_data_accessed": False,
        "security_identifiers_in_report": False,
        "strategy_candidate_available": False,
    }
    frozen = definition if definition is not None else _definition()
    allowed = frozen.get("outcome_free_preflight", {}).get("allowed_fields")  # type: ignore[union-attr]
    if (
        not isinstance(allowed, list)
        or set(report) != set(allowed)
        or len(allowed) != len(set(allowed))
    ):
        raise age.PostIpoAgeContractError("preflight report differs from frozen allowlist")
    return report


def run_read_only_preflight(database_path: str | Path) -> dict[str, object]:
    definition = _definition()
    path = Path(database_path)
    before = _digest(path)
    if before[0] != age.DATABASE_SHA256:
        raise age.PostIpoAgeContractError("database SHA-256 is not frozen")
    receipt_raw = _capture(path.parent / "receipts" / age.SNAPSHOT_RECEIPT_FILENAME, "receipt")
    if hashlib.sha256(receipt_raw).hexdigest() != age.SNAPSHOT_RECEIPT_SHA256:
        raise age.PostIpoAgeContractError("snapshot receipt SHA-256 is not frozen")
    receipt = _strict_json(receipt_raw, "snapshot receipt")
    expected = {
        "post_db_sha256": age.DATABASE_SHA256,
        "target_snapshot": age.SNAPSHOT_ID,
        "v5_digest": age.SNAPSHOT_DIGEST,
        "date_start": age.COVERAGE_START.strftime("%Y%m%d"),
        "date_end": age.HISTORICAL_CUTOFF.strftime("%Y%m%d"),
        "volume_unit": "SHARES",
        "amount_unit": "CNY",
        "status": "PUBLISHED_V5_VOLUME_UNIT_SHARES_VERIFIED",
        "strategy_candidate_available": False,
        "strategy_outcomes_opened": False,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise age.PostIpoAgeContractError("receipt does not bind the frozen snapshot")
    import duckdb

    connection = duckdb.connect(str(path), read_only=True)
    try:
        connection.execute("SET enable_external_access=false")
        snapshot = connection.execute(
            "SELECT count(*),min(trade_date),max(trade_date),count(DISTINCT quality_status),"
            "min(quality_status),bool_and(not synthetic_data) FROM "
            "a_share.a_share_canonical_daily_bars WHERE snapshot_id=? AND trade_date<=?",
            [age.SNAPSHOT_ID, age.HISTORICAL_CUTOFF.strftime("%Y%m%d")],
        ).fetchone()
        if (
            snapshot is None
            or snapshot[0] <= 0
            or receipt.get("target_rows") != snapshot[0]
            or snapshot[3:] != (1, CLASSIFICATION, True)
        ):
            raise age.PostIpoAgeContractError("snapshot identity is invalid")
        coverage = (_parse_day(snapshot[1]), _parse_day(snapshot[2]))
        if coverage != (age.COVERAGE_START, age.HISTORICAL_CUTOFF):
            raise age.PostIpoAgeContractError("snapshot coverage is not frozen")
        _validated_calendar(connection)
        report = _report(
            _database_audits(connection),
            _cohort_counts(connection),
            coverage,
            duplicate_keys=_duplicate_keys(connection),
            definition=definition,
        )
    finally:
        connection.close()
    if _digest(path) != before:
        raise age.PostIpoAgeContractError("database changed during read-only preflight")
    return report
