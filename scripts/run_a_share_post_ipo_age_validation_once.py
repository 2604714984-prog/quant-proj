#!/usr/bin/env python3
# ruff: noqa: E401, E701, E702
"""One-use, validation-only check for the frozen post-IPO-age screen."""

from __future__ import annotations

import argparse, hashlib, json, math, os, subprocess, sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from quant_system.backtest.permanent_portfolio import circular_block_start_indices  # noqa: E402
from quant_system.research import post_ipo_age as age  # noqa: E402
from scripts import run_a_share_post_ipo_age_preflight as preflight  # noqa: E402

VALIDATION, SEED, DRAWS, BLOCK, ALPHA = "validation_2022_2023", 20260728, 10_000, 3, 1 / 60
BASE_COMMIT = "4922362ee5cdef9e244f949c3325ad80d46ed07f"
PREFLIGHT_SHA256 = "449c1cae3b30c808d520da92d8fbf6a558e7b6406dc93946c7e7aece051d4f2a"
ADAPTER_SHA256 = "1e32ff55c7b68555f84d0521d025e72f2562862c5b2bf81deffa6a11f9727a63"
PREFLIGHT_RESULT_SHA256 = "0b1eda369ae8191b28f0a349c28270342632331db6399ee30ee619c308cb0cce"


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Prepared:
    database: Path
    identity: tuple[str, int, int]
    intervals: tuple[tuple[str, str, str], ...]
    pairs: Mapping[tuple[str, str], tuple[age.MatchedPair, ...]]
    identities: Mapping[tuple[str, str], tuple[object, ...]]


def _sha(path: Path) -> tuple[str, int, int]:
    try:
        raw, stat = path.read_bytes(), path.stat()
    except OSError as exc:
        raise ValidationError("required input is unreadable") from exc
    return hashlib.sha256(raw).hexdigest(), stat.st_size, stat.st_mtime_ns


def _commit() -> str:
    try:
        value = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValidationError("cannot bind current commit") from exc
    if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise ValidationError("current commit is invalid")
    return value


def _source_identity(expected: str) -> str:
    if len(expected) != 40 or any(c not in "0123456789abcdef" for c in expected):
        raise ValidationError("source commit is invalid")
    actual = _commit()
    try:
        dirty = subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--porcelain"], text=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValidationError("cannot inspect source worktree") from exc
    if actual != expected or dirty:
        raise ValidationError("source commit differs or worktree is dirty")
    return actual


def _bindings(
    database: Path, database_identity: tuple[str, int, int], expected_source_commit: str
) -> dict[str, str]:
    definition = (
        ROOT / "research/definitions/a_share_post_ipo_age_underperformance_avoidance_v1.json"
    )
    adapter = ROOT / "src/quant_system/research/post_ipo_age.py"
    preflight_code = ROOT / "scripts/run_a_share_post_ipo_age_preflight.py"
    result = ROOT / "reports/validation/a_share_post_ipo_age_preflight_v1_20260718.json"
    values = {
        "definition_sha256": _sha(definition)[0],
        "adapter_sha256": _sha(adapter)[0],
        "preflight_code_sha256": _sha(preflight_code)[0],
        "preflight_result_sha256": _sha(result)[0],
        "database_sha256": database_identity[0],
        "source_commit": _source_identity(expected_source_commit),
        "base_commit": BASE_COMMIT,
    }
    if (
        values["definition_sha256"] != age.DEFINITION_SHA256
        or values["database_sha256"] != age.DATABASE_SHA256
        or values["preflight_code_sha256"] != PREFLIGHT_SHA256
        or values["adapter_sha256"] != ADAPTER_SHA256
        or values["preflight_result_sha256"] != PREFLIGHT_RESULT_SHA256
    ):
        raise ValidationError("frozen identity changed")
    if (
        preflight._strict_json(result.read_bytes(), "accepted preflight").get("status")
        != "PREFLIGHT_PASS"
    ):
        raise ValidationError("accepted preflight no longer passes")
    receipt = database.parent / "receipts" / age.SNAPSHOT_RECEIPT_FILENAME
    values["snapshot_receipt_sha256"] = _sha(receipt)[0]
    if values["snapshot_receipt_sha256"] != age.SNAPSHOT_RECEIPT_SHA256:
        raise ValidationError("snapshot receipt identity changed")
    return values


def _claim(marker: Path, bindings: Mapping[str, str]) -> None:
    try:
        marker.resolve().relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValidationError("private marker must be outside repository")
    if marker.exists() or marker.is_symlink():
        raise ValidationError("one-use marker already exists")
    marker.parent.mkdir(parents=True, exist_ok=True)
    body = {"status": "CLAIMED_BEFORE_QFQ_OPEN_ACCESS", "research_id": age.RESEARCH_ID, **bindings}
    try:
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValidationError("one-use marker already exists") from exc
    try:
        os.write(
            fd, json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        )
        os.fsync(fd)
    finally:
        os.close(fd)


def _prepare(connection: Any, database: Path, identity: tuple[str, int, int]) -> Prepared:
    """Formation/pair/panel identity only. This statement cannot access qfq_open."""
    connection.execute("SET enable_external_access=false")
    sql = """
WITH cal AS (SELECT trade_date,row_number() over(order by trade_date) n FROM a_share.a_share_trade_calendar WHERE snapshot_id=? AND exchange=? AND source=? AND is_open AND synthetic_data=false AND trade_date BETWEEN '20211201' AND '20231231'), months AS (SELECT min(trade_date) first_d,max(trade_date) d FROM cal GROUP BY strftime(strptime(trade_date,'%Y%m%d'),'%Y%m')), ints AS (SELECT d,lead(first_d) over(order by d) entry_d,lead(first_d,2) over(order by d) exit_d FROM months), valid_i AS (SELECT * FROM ints WHERE entry_d BETWEEN '20220101' AND '20231231' AND exit_d<='20231231'), master AS (SELECT ts_code,market board,strptime(list_date,'%Y%m%d')::DATE list_day FROM a_share.a_share_symbol_master WHERE regexp_full_match(ts_code,?) QUALIFY row_number() over(partition by ts_code order by ingested_at desc,snapshot_id desc)=1), bars AS (SELECT b.*,count(*) over(partition by ts_code,trade_date) key_n FROM a_share.a_share_canonical_daily_bars b WHERE snapshot_id=? AND trade_date BETWEEN '20211201' AND '20231231'), bu AS (SELECT * FROM bars WHERE key_n=1), form AS (SELECT b.*,c.n,count(*) over w cnt,count(amount) over w amount_n,min(c.n) over w first_w,median(amount) over w med,bool_and(amount IS NOT NULL AND isfinite(amount) AND amount>=0) over w amount_ok,bool_and(adj_factor IS NOT NULL AND isfinite(adj_factor) AND adj_factor>0 AND quality_status IS NOT DISTINCT FROM ? AND synthetic_data IS NOT DISTINCT FROM false AND coalesce(regexp_full_match(row_hash,'[0-9a-f]{64}'),false)) over w id_ok FROM bu b JOIN cal c using(trade_date) WINDOW w AS(partition by ts_code order by c.n rows between 19 preceding and current row)), cohort AS (SELECT i.*,m.ts_code,m.board,m.list_day,f.med FROM valid_i i CROSS JOIN master m JOIN form f ON f.ts_code=m.ts_code AND f.trade_date=i.d WHERE m.board IN (?,?,?) AND f.cnt=20 AND f.amount_n=20 AND f.n-f.first_w=19 AND f.amount_ok AND f.id_ok AND ((m.list_day<=strptime(i.d,'%Y%m%d')::DATE AND strptime(i.d,'%Y%m%d')::DATE<m.list_day+interval 3 year) OR strptime(i.d,'%Y%m%d')::DATE>=m.list_day+interval 5 year)), ranked AS (SELECT *,case when strptime(d,'%Y%m%d')::DATE<m.list_day+interval 3 year then 'y' else 's' end side,row_number() over(partition by d,board,case when strptime(d,'%Y%m%d')::DATE<m.list_day+interval 3 year then 'y' else 's' end order by med desc,ts_code) rn FROM cohort), pairs AS (SELECT y.d,y.entry_d,y.exit_d,y.ts_code young_code,s.ts_code seasoned_code,y.board,y.med young_amount,s.med seasoned_amount FROM ranked y JOIN ranked s ON y.d=s.d AND y.board=s.board AND y.rn=s.rn WHERE y.side='y' AND s.side='s'), selected AS (SELECT * FROM pairs QUALIFY row_number() over(partition by d order by least(young_amount,seasoned_amount) desc,young_code,seasoned_code)<=50) SELECT * FROM selected ORDER BY d,young_code
"""
    parameters = [
        age.CALENDAR_SNAPSHOT_ID,
        age.CALENDAR_EXCHANGE,
        age.CALENDAR_SOURCE,
        preflight._ORDINARY,
        age.SNAPSHOT_ID,
        preflight.CLASSIFICATION,
        *age.BOARD_LABELS,
    ]
    rows = connection.execute(sql, parameters).fetchall()
    groups: dict[tuple[str, str], list[age.MatchedPair]] = {}
    exits: dict[str, tuple[str, str]] = {}
    for row in rows:
        if len(row) != 8 or any(v is None for v in row):
            raise ValidationError("missing formation or panel identity")
        decision, entry, exit_day, young, seasoned, board = (str(v) for v in row[:6])
        pair = age.MatchedPair(young, seasoned, board, float(row[6]), float(row[7]))
        groups.setdefault((decision, entry), []).append(pair)
        if decision in exits and exits[decision] != (entry, exit_day):
            raise ValidationError("duplicate interval identity")
        exits[decision] = (entry, exit_day)
    intervals = tuple((d, e, x) for d, (e, x) in sorted(exits.items()))
    if len(intervals) != 23 or any(len(pairs) != age.PAIR_COUNT for pairs in groups.values()):
        raise ValidationError("exact 23x50 validation precheck failed")
    identities: dict[tuple[str, str], tuple[object, ...]] = {}
    for decision, entry, exit_day in intervals:
        symbols = tuple(
            value
            for pair in groups[(decision, entry)]
            for value in (pair.young_symbol, pair.seasoned_symbol)
        )
        sql = (
            "SELECT ts_code,trade_date,adj_factor,quality_status,synthetic_data,row_hash FROM a_share.a_share_canonical_daily_bars WHERE snapshot_id=? AND trade_date IN (?,?) AND ts_code IN ("
            + ",".join("?" for _ in symbols)
            + ") ORDER BY ts_code,trade_date"
        )
        rows = connection.execute(sql, [age.SNAPSHOT_ID, entry, exit_day, *symbols]).fetchall()
        unique = {(str(row[0]), str(row[1])): tuple(row[2:]) for row in rows}
        if len(rows) != 200 or len(unique) != 200 or any(len(row) != 4 for row in unique.values()):
            raise ValidationError("selected panel identity is missing or duplicate")
        for symbol in symbols:
            identities[(decision, symbol)] = (*unique[(symbol, entry)], *unique[(symbol, exit_day)])
    return Prepared(
        database,
        identity,
        intervals,
        {key: tuple(value) for key, value in groups.items()},
        identities,
    )


def _annualized(values: Sequence[float]) -> float:
    frozen = tuple(float(v) for v in values)
    if not frozen or any(not math.isfinite(v) or v <= -1 for v in frozen):
        raise ValidationError("monthly return is invalid")
    return math.exp(math.fsum(math.log1p(v) for v in frozen) * 12 / len(frozen)) - 1


def _bootstrap(values: Sequence[float]) -> tuple[float, float, float]:
    active = tuple(float(v) for v in values)
    if not active or any(not math.isfinite(v) for v in active):
        raise ValidationError("bootstrap requires finite returns")
    observed = math.fsum(active) / len(active)
    centered = tuple(v - observed for v in active)
    starts = circular_block_start_indices(len(centered), draws=DRAWS, seed=SEED)
    means = tuple(
        math.fsum(
            tuple(
                centered[(start + offset) % len(centered)]
                for start in row
                for offset in range(BLOCK)
            )[: len(centered)]
        )
        / len(centered)
        for row in starts
    )
    p_value = (1 + sum(v >= observed for v in means)) / (DRAWS + 1)
    ordered = sorted(means)
    position = (len(ordered) - 1) * (1 - ALPHA)
    lo, hi = ordered[math.floor(position)], ordered[math.ceil(position)]
    quantile = lo + (hi - lo) * (position - math.floor(position))
    return observed, p_value, observed - quantile


def _report(
    seasoned: Sequence[float], young: Sequence[float], *, invalid: int
) -> dict[str, object]:
    if len(seasoned) != len(young) or len(seasoned) != 23:
        raise ValidationError("exactly twenty-three validation months are required")
    active = tuple(a - b for a, b in zip(seasoned, young))
    mean, p_value, lower = _bootstrap(active)
    seasoned_annualized, young_annualized = _annualized(seasoned), _annualized(young)
    gates = {
        "interval_count_20_to_23": 20 <= len(active) <= 23,
        "zero_invalid_and_50_pairs_each": invalid == 0,
        "mean_active_positive": mean > 0,
        "centered_bootstrap_p_value_lte_1_60": p_value <= ALPHA,
        "centered_bootstrap_lower_bound_positive": lower > 0,
        "seasoned_annualized_exceeds_young": seasoned_annualized > young_annualized,
    }
    return {
        "status": "VALIDATION_PASS" if all(gates.values()) else "VALIDATION_FAIL",
        "validation_interval_count": len(active),
        "invalid_interval_count": invalid,
        "mean_active_return": mean,
        "centered_bootstrap_p_value": p_value,
        "centered_bootstrap_lower_bound": lower,
        "seasoned_annualized_net_return": seasoned_annualized,
        "young_annualized_net_return": young_annualized,
        "gates": gates,
        "strategy_candidate_available": False,
        "holdout_closed": True,
        "forward_closed": True,
        "security_identifiers_in_report": False,
    }


def _outcomes(connection: Any, prepared: Prepared) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """First qfq_open access: only after the external private marker has been claimed."""
    seasoned: list[float] = []
    young: list[float] = []
    for decision, entry, exit_day in prepared.intervals:
        pairs = prepared.pairs[(decision, entry)]
        symbols = tuple(v for pair in pairs for v in (pair.young_symbol, pair.seasoned_symbol))
        sql = (
            "SELECT ts_code,trade_date,qfq_open FROM a_share.a_share_canonical_daily_bars WHERE snapshot_id=? AND trade_date IN (?,?) AND ts_code IN ("
            + ",".join("?" for _ in symbols)
            + ")"
        )
        rows = connection.execute(sql, [age.SNAPSHOT_ID, entry, exit_day, *symbols]).fetchall()
        values = {(str(symbol), str(day)): open_ for symbol, day, open_ in rows}
        if (
            len(rows) != 200
            or len(values) != 200
            or any(
                value is None or not math.isfinite(float(value)) or float(value) <= 0
                for value in values.values()
            )
        ):
            raise ValidationError("qfq_open panel is missing, duplicate or nonfinite")
        panels = {}
        for symbol in symbols:
            (
                entry_adj,
                entry_quality,
                entry_synth,
                entry_hash,
                exit_adj,
                exit_quality,
                exit_synth,
                exit_hash,
            ) = prepared.identities[(decision, symbol)]
            panels[symbol] = age.SelectedPanel(
                symbol,
                values[(symbol, entry)],
                values[(symbol, exit_day)],
                entry_adj,
                exit_adj,
                entry_hash,
                exit_hash,
                entry_quality,
                exit_quality,
                entry_synth,
                exit_synth,
            )
        result = age.synthetic_interval_return(pairs, panels)
        seasoned.append(result.seasoned_net)
        young.append(result.young_net)
    return tuple(seasoned), tuple(young)


def run_once(
    database_path: str | Path, marker_path: str | Path, expected_source_commit: str
) -> dict[str, object]:
    database, marker = Path(database_path), Path(marker_path)
    before = _sha(database)
    bindings = _bindings(database, before, expected_source_commit)
    if database.with_name(database.name + "-wal").exists():
        raise ValidationError("read-only database must not have a WAL")
    import duckdb

    connection = duckdb.connect(str(database), read_only=True)
    try:
        prepared = _prepare(connection, database, before)
        stat = database.stat()
        if (stat.st_size, stat.st_mtime_ns) != before[1:]:
            raise ValidationError("database changed before outcome access")
        _claim(marker, bindings)
        seasoned, young = _outcomes(connection, prepared)
    finally:
        connection.close()
    if _sha(database) != prepared.identity or database.with_name(database.name + "-wal").exists():
        raise ValidationError("database changed during read-only validation")
    return {
        "research_id": age.RESEARCH_ID,
        "phase": "HISTORICAL_VALIDATION_ONLY",
        **bindings,
        **_report(seasoned, young, invalid=0),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database")
    parser.add_argument("--marker-path")
    parser.add_argument("--source-commit", dest="expected_source_commit")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "DRY_RUN",
                    "strategy_candidate_available": False,
                    "holdout_closed": True,
                    "forward_closed": True,
                },
                sort_keys=True,
            )
        )
        return 0
    if not args.database or not args.marker_path or not args.expected_source_commit:
        raise ValidationError("--database, --marker-path and --expected-source-commit are required")
    print(
        json.dumps(
            run_once(args.database, args.marker_path, args.expected_source_commit),
            sort_keys=True,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
