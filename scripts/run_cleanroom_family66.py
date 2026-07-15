#!/usr/bin/env python3
"""Run the outcome-blind clean-room Family66 retrospective event replay."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from typing import Any, Iterator

import duckdb


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from quant_system.research.event_cohort import (  # noqa: E402
    CohortObservation,
    SplitWindow,
    assign_whole_label_split,
    benjamini_hochberg_adjusted,
    block_bootstrap_summary,
    economic_summary,
    fixed_two_side_cost_return,
)


DEFINITION = ROOT / "research/definitions/a_share_family66_cleanroom_event_replay_v1.json"
OUTPUT = ROOT / "reports/validation/a_share_family66_cleanroom_event_replay_v1.json"
DEFINITION_SHA256 = "f37bca74d6cc2574b05aa375fc189fd072acabbff7bd10337524edc66967ba4d"
HEX = frozenset("0123456789abcdef")


class Family66ReplayError(RuntimeError):
    """Frozen replay identity or mechanics do not match."""


def _reject_constant(value: str) -> None:
    raise Family66ReplayError(f"nonfinite JSON constant is not allowed: {value}")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Family66ReplayError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json_bytes(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(
            raw, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Family66ReplayError(f"{label} is not strict JSON") from exc
    if not isinstance(parsed, dict):
        raise Family66ReplayError(f"{label} root must be an object")
    return parsed


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class CapturedInput:
    source_path: Path
    descriptor: int
    identity: tuple[int, int, int, int, int]
    sha256: str
    byte_count: int
    raw: bytes | None

    @property
    def duckdb_path(self) -> Path:
        return Path(f"/proc/self/fd/{self.descriptor}")


@dataclass(frozen=True)
class VerifiedInputStaging:
    baseline: dict[str, Any]
    packet: Path
    baseline_manifest: Path
    feature_metadata: Path
    feature_files: tuple[Path, ...]
    trade_calendar: Path
    etf_csv: Path


def _file_identity(state: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        state.st_dev,
        state.st_ino,
        state.st_size,
        state.st_mtime_ns,
        state.st_ctime_ns,
    )


def _assert_capture_unchanged(captured: CapturedInput) -> None:
    try:
        descriptor_state = os.fstat(captured.descriptor)
        path_state = captured.source_path.lstat()
    except OSError as exc:
        raise Family66ReplayError(
            f"{captured.source_path} disappeared after descriptor capture"
        ) from exc
    if (
        stat.S_ISLNK(path_state.st_mode)
        or _file_identity(descriptor_state) != captured.identity
        or _file_identity(path_state) != captured.identity
    ):
        raise Family66ReplayError(
            f"{captured.source_path} changed after descriptor capture"
        )


def _capture_open_input(
    source: Path,
    *,
    label: str,
    retain_bytes: bool = False,
) -> CapturedInput:
    """Hash one O_NOFOLLOW descriptor and retain it for zero-copy DuckDB use.

    DuckDB opens ``/proc/self/fd/<fd>`` while this descriptor remains live, so
    hashing and query input are bound to the same inode without a multi-GB copy.
    """

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        source_fd = os.open(source, flags)
    except OSError as exc:
        raise Family66ReplayError(f"cannot safely open {label}: {source}") from exc
    try:
        before = os.fstat(source_fd)
        if not stat.S_ISREG(before.st_mode):
            raise Family66ReplayError(f"{label} must be a regular file")
        digest = hashlib.sha256()
        retained: list[bytes] | None = [] if retain_bytes else None
        byte_count = 0
        while True:
            chunk = os.read(source_fd, 8 * 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            byte_count += len(chunk)
            if retained is not None:
                retained.append(chunk)
        after = os.fstat(source_fd)
        descriptor_identity = _file_identity(after)
        if _file_identity(before) != descriptor_identity or byte_count != after.st_size:
            raise Family66ReplayError(f"{label} changed during descriptor capture")
        try:
            path_state = source.lstat()
        except OSError as exc:
            raise Family66ReplayError(f"{label} disappeared during descriptor capture") from exc
        path_identity = _file_identity(path_state)
        if stat.S_ISLNK(path_state.st_mode) or path_identity != descriptor_identity:
            raise Family66ReplayError(f"{label} path was replaced during descriptor capture")
        captured = CapturedInput(
            source_path=source,
            descriptor=source_fd,
            identity=descriptor_identity,
            sha256=digest.hexdigest(),
            byte_count=byte_count,
            raw=None if retained is None else b"".join(retained),
        )
        os.lseek(source_fd, 0, os.SEEK_SET)
        return captured
    except Exception:
        os.close(source_fd)
        raise


def _is_hash(value: object, lengths: set[int] = {64}) -> bool:
    return isinstance(value, str) and len(value) in lengths and set(value) <= HEX


def _load_definition(path: Path = DEFINITION) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise Family66ReplayError(f"cannot read definition: {path}") from exc
    digest = _sha256_bytes(raw)
    if digest != DEFINITION_SHA256:
        raise Family66ReplayError("definition SHA-256 does not match frozen bytes")
    definition = _strict_json_bytes(raw, label="definition")
    if (
        definition.get("status") != "OUTCOME_BLIND_DEFINITION_NOT_EXECUTED"
        or definition.get("classification")
        != "CLEAN_ROOM_RETROSPECTIVE_REPLAY_OF_REJECTED_LINEAGE"
        or definition.get("family_number") != 66
    ):
        raise Family66ReplayError("definition state or lineage changed")
    boundary = definition.get("lineage_and_execution_boundary")
    if not isinstance(boundary, dict) or any(
        boundary.get(key) is not expected
        for key, expected in (
            ("eligible_for_new_evidence", False),
            ("status_mutation_allowed", False),
            ("strict_pit_eligible", False),
            ("strategy_candidate_available", False),
            ("network_access", False),
            ("database_write", False),
            ("legacy_result_comparison_before_new_output_is_frozen", False),
            ("broker_order_paper_live_auto", False),
        )
    ):
        raise Family66ReplayError("execution boundary changed")
    gate_order = definition.get("gate_contract", {}).get("gate_order")
    if not isinstance(gate_order, list) or len(gate_order) != 48 or len(set(gate_order)) != 48:
        raise Family66ReplayError("exact 48-gate order changed")
    return definition, digest


@contextmanager
def _verified_input_staging(
    definition: Mapping[str, Any],
    *,
    packet: Path,
    baseline_manifest: Path,
    feature_metadata: Path,
    features_dir: Path,
    trade_calendar: Path,
    etf_csv: Path,
) -> Iterator[VerifiedInputStaging]:
    """Verify identities and hold zero-copy descriptors through DuckDB access."""

    contract = definition["source_contract"]
    try:
        directory_before = features_dir.lstat()
    except OSError as exc:
        raise Family66ReplayError("cannot inspect feature directory") from exc
    if stat.S_ISLNK(directory_before.st_mode) or not stat.S_ISDIR(directory_before.st_mode):
        raise Family66ReplayError("feature directory must be a non-symlink directory")
    directory_identity = (
        directory_before.st_dev,
        directory_before.st_ino,
        directory_before.st_mtime_ns,
        directory_before.st_ctime_ns,
    )

    captures: list[CapturedInput] = []
    try:
        fixed_inputs = (
            ("packet", packet, "controlling packet", "controlling_packet_sha256", False),
            (
                "baseline_manifest",
                baseline_manifest,
                "baseline manifest",
                "baseline_manifest_file_sha256",
                True,
            ),
            (
                "feature_metadata",
                feature_metadata,
                "feature metadata",
                "feature_metadata_sha256",
                False,
            ),
            (
                "trade_calendar",
                trade_calendar,
                "trade calendar",
                "trade_calendar_sha256",
                False,
            ),
            ("etf_csv", etf_csv, "ETF CSV", "etf_csv_sha256", False),
        )
        captures_by_key: dict[str, CapturedInput] = {}
        for key, source, label, hash_key, retain in fixed_inputs:
            captured = _capture_open_input(
                source,
                label=label,
                retain_bytes=retain,
            )
            captures.append(captured)
            if captured.sha256 != contract[hash_key]:
                raise Family66ReplayError(f"input hash mismatch: {hash_key}")
            captures_by_key[key] = captured

        baseline_raw = captures_by_key["baseline_manifest"].raw
        assert baseline_raw is not None
        baseline = _strict_json_bytes(baseline_raw, label="baseline manifest")
        dataset = baseline.get("features_daily_dataset")
        if not isinstance(dataset, dict) or any(
            dataset.get(key) != expected
            for key, expected in (
                ("files", contract["feature_part_count"]),
                ("bytes", contract["feature_total_bytes"]),
                ("rows", contract["feature_row_count"]),
                ("columns", contract["feature_column_count"]),
                ("manifest_sha256", contract["feature_dataset_manifest_sha256"]),
            )
        ):
            raise Family66ReplayError("feature dataset baseline identity changed")
        parts = dataset.get("parts")
        if not isinstance(parts, list) or len(parts) != contract["feature_part_count"]:
            raise Family66ReplayError("feature part list changed")
        manifest_digest = hashlib.sha256()
        seen: set[str] = set()
        total_bytes = 0
        feature_captures: list[CapturedInput] = []
        for item in parts:
            if not isinstance(item, dict):
                raise Family66ReplayError("feature part identity is malformed")
            name, size, expected_sha = item.get("path"), item.get("bytes"), item.get("sha256")
            if (
                not isinstance(name, str)
                or Path(name).name != name
                or name in seen
                or type(size) is not int
                or size < 1
                or not _is_hash(expected_sha)
            ):
                raise Family66ReplayError("feature part identity is malformed")
            seen.add(name)
            captured = _capture_open_input(
                features_dir / name,
                label=f"feature part {name}",
            )
            captures.append(captured)
            feature_captures.append(captured)
            if captured.byte_count != size or captured.sha256 != expected_sha:
                raise Family66ReplayError(f"feature part changed: {name}")
            total_bytes += captured.byte_count
            manifest_digest.update(f"{name}\0{size}\0{expected_sha}\n".encode("utf-8"))

        if total_bytes != dataset["bytes"] or manifest_digest.hexdigest() != dataset[
            "manifest_sha256"
        ]:
            raise Family66ReplayError("feature directory or manifest identity changed")

        def assert_directory_unchanged() -> None:
            actual_names: set[str] = set()
            try:
                for path in features_dir.iterdir():
                    if path.suffix != ".parquet":
                        continue
                    state = path.lstat()
                    if stat.S_ISLNK(state.st_mode) or not stat.S_ISREG(state.st_mode):
                        raise Family66ReplayError(
                            "feature parts must be regular non-symlink files"
                        )
                    actual_names.add(path.name)
                directory_after = features_dir.lstat()
            except OSError as exc:
                raise Family66ReplayError("feature directory changed during capture") from exc
            after_identity = (
                directory_after.st_dev,
                directory_after.st_ino,
                directory_after.st_mtime_ns,
                directory_after.st_ctime_ns,
            )
            if (
                stat.S_ISLNK(directory_after.st_mode)
                or after_identity != directory_identity
                or actual_names != seen
            ):
                raise Family66ReplayError("feature directory or manifest identity changed")

        for captured in captures:
            _assert_capture_unchanged(captured)
        assert_directory_unchanged()

        yield VerifiedInputStaging(
            baseline=baseline,
            packet=captures_by_key["packet"].duckdb_path,
            baseline_manifest=captures_by_key["baseline_manifest"].duckdb_path,
            feature_metadata=captures_by_key["feature_metadata"].duckdb_path,
            feature_files=tuple(item.duckdb_path for item in feature_captures),
            trade_calendar=captures_by_key["trade_calendar"].duckdb_path,
            etf_csv=captures_by_key["etf_csv"].duckdb_path,
        )
        for captured in captures:
            _assert_capture_unchanged(captured)
        assert_directory_unchanged()
    finally:
        for captured in captures:
            try:
                os.close(captured.descriptor)
            except OSError:
                pass


def _verify_inputs(
    definition: Mapping[str, Any],
    *,
    packet: Path,
    baseline_manifest: Path,
    feature_metadata: Path,
    features_dir: Path,
    trade_calendar: Path,
    etf_csv: Path,
) -> dict[str, Any]:
    """Backward-compatible validation helper used by focused tests."""

    with _verified_input_staging(
        definition,
        packet=packet,
        baseline_manifest=baseline_manifest,
        feature_metadata=feature_metadata,
        features_dir=features_dir,
        trade_calendar=trade_calendar,
        etf_csv=etf_csv,
    ) as staged:
        return staged.baseline


@dataclass(frozen=True)
class RawCohort:
    signal_date: date
    entry_date: date | None
    exit_date: date | None
    signal_candidate_count: int
    signal_complete_count: int
    breakout_candidate_count: int
    breakout_complete_count: int
    eligible_candidate_count: int
    eligible_complete_count: int
    signal_gross_return: float | None
    breakout_gross_return: float | None
    eligible_gross_return: float | None
    equity_gross_return: float | None
    cash_gross_return: float | None


_COHORT_SQL = r"""
WITH calendar_source AS (
  SELECT strptime(trade_date, '%Y%m%d')::DATE AS session_date
  FROM read_parquet(?)
  WHERE exchange = 'SSE' AND is_open = 1
), calendar AS (
  SELECT session_date, row_number() OVER (ORDER BY session_date) AS rn
  FROM calendar_source
), labels AS (
  SELECT s.session_date AS signal_date,
         e.session_date AS entry_date,
         x.session_date AS exit_date
  FROM calendar s
  JOIN calendar e ON e.rn = s.rn + 1
  JOIN calendar x ON x.rn = s.rn + 16
), features AS (
  SELECT ts_code, strptime(trade_date, '%Y%m%d')::DATE AS trade_date,
         board, list_days, is_st, is_suspended, feature_open, feature_close,
         breakout_60, volatility_20_rank, volume_ratio_20, amount_ma_20, is_limit_up
  FROM read_parquet(?)
), eligible AS (
  SELECT *,
    (breakout_60 IS TRUE AND is_limit_up IS FALSE) AS is_breakout,
    (breakout_60 IS TRUE AND is_limit_up IS FALSE
      AND isfinite(volatility_20_rank) AND volatility_20_rank <= 0.45
      AND isfinite(volume_ratio_20) AND volume_ratio_20 >= 1.1) AS is_signal
  FROM features
  WHERE board IN ('main', 'gem', 'star')
    AND list_days >= 120
    AND is_st IS FALSE
    AND is_suspended IS FALSE
    AND isfinite(amount_ma_20) AND amount_ma_20 >= 80000.0
    AND isfinite(feature_open) AND feature_open > 0.0
    AND isfinite(feature_close) AND feature_close > 0.0
), active_dates AS (
  SELECT DISTINCT trade_date AS signal_date FROM eligible WHERE is_signal
), active_labels AS (
  SELECT a.signal_date, l.entry_date, l.exit_date
  FROM active_dates a LEFT JOIN labels l USING (signal_date)
), etf AS (
  SELECT ts_code, strptime(CAST(trade_date AS VARCHAR), '%Y%m%d')::DATE AS trade_date,
         open
  FROM read_csv_auto(?)
  WHERE ts_code IN ('510300.SH', '511880.SH') AND adjustment = 'qfq'
), benchmarks AS (
  SELECT l.signal_date,
    CASE WHEN isfinite(ce.open) AND ce.open > 0 AND isfinite(cx.open) AND cx.open > 0
         THEN cx.open / ce.open - 1 END AS cash_gross_return,
    CASE WHEN isfinite(ee.open) AND ee.open > 0 AND isfinite(ex.open) AND ex.open > 0
         THEN ex.open / ee.open - 1 END AS equity_gross_return
  FROM active_labels l
  LEFT JOIN etf ce ON ce.ts_code='511880.SH' AND ce.trade_date=l.entry_date
  LEFT JOIN etf cx ON cx.ts_code='511880.SH' AND cx.trade_date=l.exit_date
  LEFT JOIN etf ee ON ee.ts_code='510300.SH' AND ee.trade_date=l.entry_date
  LEFT JOIN etf ex ON ex.ts_code='510300.SH' AND ex.trade_date=l.exit_date
), resolved AS (
  SELECT l.signal_date, l.entry_date, l.exit_date, d.is_signal, d.is_breakout,
    CASE WHEN isfinite(e.feature_open) AND e.feature_open > 0
               AND isfinite(x.feature_open) AND x.feature_open > 0
               AND e.is_limit_up IS NOT NULL AND b.cash_gross_return IS NOT NULL
         THEN CASE WHEN e.is_limit_up THEN b.cash_gross_return
                   ELSE x.feature_open / e.feature_open - 1 END END AS event_gross_return,
    b.equity_gross_return, b.cash_gross_return
  FROM active_labels l
  JOIN eligible d ON d.trade_date=l.signal_date
  LEFT JOIN features e ON e.ts_code=d.ts_code AND e.trade_date=l.entry_date
  LEFT JOIN features x ON x.ts_code=d.ts_code AND x.trade_date=l.exit_date
  JOIN benchmarks b USING (signal_date)
)
SELECT signal_date, min(entry_date), min(exit_date),
  count(*) FILTER (WHERE is_signal),
  count(event_gross_return) FILTER (WHERE is_signal),
  count(*) FILTER (WHERE is_breakout),
  count(event_gross_return) FILTER (WHERE is_breakout),
  count(*), count(event_gross_return),
  avg(event_gross_return) FILTER (WHERE is_signal),
  avg(event_gross_return) FILTER (WHERE is_breakout),
  avg(event_gross_return),
  min(equity_gross_return), min(cash_gross_return)
FROM resolved
GROUP BY signal_date
ORDER BY signal_date
"""


def _reject_duplicate_source_keys(
    connection: duckdb.DuckDBPyConnection,
    *,
    feature_input: str | list[str],
    trade_calendar: Path,
    etf_csv: Path,
) -> None:
    """Fail before cohort SQL if any relevant source key is non-unique."""

    checks = (
        (
            "calendar date",
            """
            SELECT count(*) FROM (
              SELECT strptime(trade_date, '%Y%m%d')::DATE AS session_date
              FROM read_parquet(?)
              WHERE exchange = 'SSE'
              GROUP BY session_date
              HAVING count(*) > 1
            )
            """,
            str(trade_calendar),
        ),
        (
            "feature symbol-date",
            """
            SELECT count(*) FROM (
              SELECT ts_code, strptime(trade_date, '%Y%m%d')::DATE AS trade_date
              FROM read_parquet(?)
              GROUP BY ts_code, trade_date
              HAVING count(*) > 1
            )
            """,
            feature_input,
        ),
        (
            "ETF symbol-date",
            """
            SELECT count(*) FROM (
              SELECT ts_code,
                     strptime(CAST(trade_date AS VARCHAR), '%Y%m%d')::DATE AS trade_date
              FROM read_csv_auto(?)
              GROUP BY ts_code, trade_date
              HAVING count(*) > 1
            )
            """,
            str(etf_csv),
        ),
    )
    for label, query, path in checks:
        duplicate_group_count = connection.execute(query, (path,)).fetchone()[0]
        if type(duplicate_group_count) is not int or duplicate_group_count < 0:
            raise Family66ReplayError(f"{label} duplicate preflight shape changed")
        if duplicate_group_count:
            raise Family66ReplayError(f"duplicate {label} key")


def _load_raw_cohorts(
    *,
    trade_calendar: Path,
    etf_csv: Path,
    features_dir: Path | None = None,
    feature_files: Sequence[Path] | None = None,
) -> tuple[RawCohort, ...]:
    if (features_dir is None) == (feature_files is None):
        raise Family66ReplayError("provide exactly one feature input mode")
    if feature_files is not None:
        frozen_files = tuple(feature_files)
        if not frozen_files:
            raise Family66ReplayError("feature file descriptors must be nonempty")
        feature_input: str | list[str] = [str(path) for path in frozen_files]
    else:
        assert features_dir is not None
        feature_input = str(features_dir / "*.parquet")
    connection = duckdb.connect(":memory:")
    try:
        _reject_duplicate_source_keys(
            connection,
            feature_input=feature_input,
            trade_calendar=trade_calendar,
            etf_csv=etf_csv,
        )
        rows = connection.execute(
            _COHORT_SQL,
            (str(trade_calendar), feature_input, str(etf_csv)),
        ).fetchall()
    except duckdb.Error as exc:
        raise Family66ReplayError("source cohorts could not be derived") from exc
    finally:
        connection.close()
    cohorts: list[RawCohort] = []
    for row in rows:
        try:
            cohort = RawCohort(*row)
        except TypeError as exc:
            raise Family66ReplayError("cohort query shape changed") from exc
        if type(cohort.signal_date) is not date or any(
            value is not None and type(value) is not date
            for value in (cohort.entry_date, cohort.exit_date)
        ):
            raise Family66ReplayError("cohort date type changed")
        cohorts.append(cohort)
    return tuple(cohorts)


def _split_windows(definition: Mapping[str, Any]) -> tuple[SplitWindow, ...]:
    return tuple(
        SplitWindow(
            item["split_id"],
            date.fromisoformat(item["start"]),
            date.fromisoformat(item["end"]),
        )
        for item in definition["splits"]
    )


def _observations(
    raw: Sequence[RawCohort], definition: Mapping[str, Any], *, bps_per_side: float
) -> tuple[tuple[CohortObservation, ...], int, int, int, int]:
    splits = _split_windows(definition)
    retained: list[CohortObservation] = []
    purged_dates = incomplete_dates = incomplete_events = incomplete_label_dates = 0
    for row in raw:
        signal_splits = tuple(split for split in splits if split.contains(row.signal_date))
        if not signal_splits:
            # Complete cohorts outside every declared split are not part of the
            # evaluation population and are not cross-boundary purge events.
            continue
        if len(signal_splits) != 1:
            raise Family66ReplayError("signal date matched multiple split windows")
        if row.entry_date is None or row.exit_date is None:
            incomplete_label_dates += 1
            continue
        split_id = assign_whole_label_split(
            row.signal_date, row.entry_date, row.exit_date, splits
        )
        if split_id is None:
            # The signal date is in scope, so this is a genuine whole-label
            # boundary crossing (or label outside its signal split).
            purged_dates += 1
            continue
        if split_id != signal_splits[0].split_id:
            raise Family66ReplayError("whole-label split disagrees with signal split")
        counts = (
            row.signal_candidate_count,
            row.signal_complete_count,
            row.breakout_candidate_count,
            row.breakout_complete_count,
            row.eligible_candidate_count,
            row.eligible_complete_count,
        )
        if any(type(value) is not int or value < 0 for value in counts):
            raise Family66ReplayError("cohort counts are invalid")
        date_incomplete = (
            row.signal_candidate_count - row.signal_complete_count
            + row.breakout_candidate_count - row.breakout_complete_count
            + row.eligible_candidate_count - row.eligible_complete_count
        )
        if date_incomplete < 0:
            raise Family66ReplayError("complete count exceeds candidate count")
        incomplete_events += date_incomplete
        gross = (
            row.signal_gross_return,
            row.breakout_gross_return,
            row.eligible_gross_return,
            row.equity_gross_return,
            row.cash_gross_return,
        )
        if any(value is None or not math.isfinite(float(value)) for value in gross) or any(
            count < 1 for count in (
                row.signal_complete_count,
                row.breakout_complete_count,
                row.eligible_complete_count,
            )
        ):
            incomplete_dates += 1
            continue
        assert all(value is not None for value in gross)
        retained.append(
            CohortObservation(
                split_id=split_id,
                signal_date=row.signal_date,
                entry_date=row.entry_date,
                exit_date=row.exit_date,
                signal_return=fixed_two_side_cost_return(
                    float(row.signal_gross_return), bps_per_side=bps_per_side
                ),
                breakout_return=fixed_two_side_cost_return(
                    float(row.breakout_gross_return), bps_per_side=bps_per_side
                ),
                eligible_return=fixed_two_side_cost_return(
                    float(row.eligible_gross_return), bps_per_side=bps_per_side
                ),
                equity_benchmark_return=float(row.equity_gross_return),
                cash_benchmark_return=float(row.cash_gross_return),
                signal_event_count=row.signal_complete_count,
                incomplete_signal_event_count=(
                    row.signal_candidate_count - row.signal_complete_count
                ),
                incomplete_breakout_event_count=(
                    row.breakout_candidate_count - row.breakout_complete_count
                ),
                incomplete_eligible_event_count=(
                    row.eligible_candidate_count - row.eligible_complete_count
                ),
            )
        )
    return (
        tuple(retained), purged_dates, incomplete_dates, incomplete_events,
        incomplete_label_dates,
    )


def _summary(rows: Sequence[CohortObservation], split_ids: Sequence[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for split_id in split_ids:
        selected = tuple(row for row in rows if row.split_id == split_id)
        payload: dict[str, Any] = {
            "signal_date_count": len(selected),
            "signal_event_count": sum(row.signal_event_count for row in selected),
            "incomplete_signal_event_count": sum(
                row.incomplete_signal_event_count for row in selected
            ),
            "incomplete_breakout_event_count": sum(
                row.incomplete_breakout_event_count for row in selected
            ),
            "incomplete_eligible_event_count": sum(
                row.incomplete_eligible_event_count for row in selected
            ),
        }
        for series_id in (
            "signal_return", "excess_vs_breakout_only", "excess_vs_eligible",
            "excess_vs_510300", "excess_vs_511880",
        ):
            if selected:
                payload[series_id] = asdict(
                    economic_summary(tuple(row.series_value(series_id) for row in selected))
                )
            else:
                payload[series_id] = None
        result[split_id] = payload
    return result


def _gate_checks(
    rows: Sequence[CohortObservation],
    definition: Mapping[str, Any],
    *,
    incomplete_events: int,
    incomplete_label_dates: int,
    incomplete_cohort_dates: int,
) -> tuple[dict[str, Any], ...]:
    splits = tuple(item["split_id"] for item in definition["splits"])
    selected = {split_id: tuple(row for row in rows if row.split_id == split_id) for split_id in splits}
    checks: dict[str, dict[str, Any]] = {}

    def add(gate_id: str, observed: Any, threshold: str, passed: bool) -> None:
        checks[gate_id] = {
            "gate_id": gate_id, "observed": observed, "threshold": threshold,
            "passed": bool(passed),
        }

    add(
        "global.all_four_splits_nonempty",
        {key: len(value) for key, value in selected.items()},
        "each split > 0",
        all(selected.values()),
    )
    finite = all(
        math.isfinite(row.series_value(series_id))
        for row in rows
        for series_id in definition["inference"]["series_order"]
    )
    add("global.all_returns_finite", finite, "true", finite)
    add(
        "global.every_candidate_event_and_label_complete",
        {
            "incomplete_candidate_events": incomplete_events,
            "incomplete_label_dates": incomplete_label_dates,
            "incomplete_cohort_dates": incomplete_cohort_dates,
        },
        "all counts equal 0 on signal dates inside declared splits",
        incomplete_events == 0
        and incomplete_label_dates == 0
        and incomplete_cohort_dates == 0,
    )
    for split_id in ("development", "validation", "holdout"):
        split_rows = selected[split_id]
        event_count = sum(row.signal_event_count for row in split_rows)
        add(
            f"sample.{split_id}.signal_dates_gte_100",
            len(split_rows), ">=100", len(split_rows) >= 100,
        )
        add(
            f"sample.{split_id}.signal_events_gte_300",
            event_count, ">=300", event_count >= 300,
        )
    for split_id in splits:
        split_rows = selected[split_id]
        if split_rows:
            signal = economic_summary(tuple(row.signal_return for row in split_rows))
            observed = {
                "signal_mean_gt_zero": signal.mean,
                "signal_median_gt_zero": signal.median,
                "signal_positive_fraction_gt_half": signal.positive_fraction,
                "excess_vs_breakout_only_mean_gt_zero": economic_summary(tuple(
                    row.series_value("excess_vs_breakout_only") for row in split_rows
                )).mean,
                "excess_vs_eligible_mean_gt_zero": economic_summary(tuple(
                    row.series_value("excess_vs_eligible") for row in split_rows
                )).mean,
                "excess_vs_510300_mean_gt_zero": economic_summary(tuple(
                    row.series_value("excess_vs_510300") for row in split_rows
                )).mean,
                "excess_vs_511880_mean_gt_zero": economic_summary(tuple(
                    row.series_value("excess_vs_511880") for row in split_rows
                )).mean,
            }
        else:
            observed = {name: None for name in (
                "signal_mean_gt_zero", "signal_median_gt_zero",
                "signal_positive_fraction_gt_half",
                "excess_vs_breakout_only_mean_gt_zero", "excess_vs_eligible_mean_gt_zero",
                "excess_vs_510300_mean_gt_zero", "excess_vs_511880_mean_gt_zero",
            )}
        for metric, value in observed.items():
            threshold = ">0.5" if metric == "signal_positive_fraction_gt_half" else ">0"
            limit = 0.5 if metric == "signal_positive_fraction_gt_half" else 0.0
            add(
                f"economic.{split_id}.{metric}", value, threshold,
                value is not None and float(value) > limit,
            )
    inference = definition["inference"]
    holdout = selected["holdout"]
    summaries: list[Any] = []
    if len(holdout) >= inference["circular_moving_block_signal_dates"]:
        for series_id in inference["series_order"]:
            summaries.append(block_bootstrap_summary(
                tuple(row.series_value(series_id) for row in holdout),
                block_length=inference["circular_moving_block_signal_dates"],
                draws=inference["bootstrap_draws"], seed=inference["seed"],
                alpha=inference["alpha"],
            ))
        adjusted = benjamini_hochberg_adjusted(tuple(item.raw_p for item in summaries))
    else:
        summaries, adjusted = [None] * 5, (None,) * 5
    for series_id, summary in zip(inference["series_order"], summaries, strict=True):
        value = None if summary is None else summary.lower_bound
        add(
            f"inference.holdout.{series_id}.lower_bound_gt_zero",
            value, ">0", value is not None and value > 0.0,
        )
    purge_ok = all(
        assign_whole_label_split(row.signal_date, row.entry_date, row.exit_date, _split_windows(definition))
        == row.split_id
        for row in rows
    )
    add("purge.whole_label_within_split", purge_ok, "true", purge_ok)
    for series_id, value in zip(inference["series_order"], adjusted, strict=True):
        add(
            f"inference.holdout.{series_id}.bh_adjusted_p_le_alpha",
            value, f"<={inference['alpha']}",
            value is not None and value <= inference["alpha"],
        )
    gate_order = definition["gate_contract"]["gate_order"]
    if set(checks) != set(gate_order) or len(checks) != 48:
        raise Family66ReplayError("assembled gate family is not the exact frozen 48")
    return tuple(checks[gate_id] for gate_id in gate_order)


def build_report(
    definition: Mapping[str, Any], definition_sha256: str, raw: Sequence[RawCohort],
    *, source_commit: str, source_paths: Mapping[str, str],
) -> dict[str, Any]:
    split_ids = tuple(item["split_id"] for item in definition["splits"])
    cost_runs: dict[str, Any] = {}
    strict_rows: tuple[CohortObservation, ...] | None = None
    strict_incomplete_events = 0
    strict_purged = strict_incomplete_dates = strict_incomplete_label_dates = 0
    for bps in definition["cost_contract"]["reported_bps_per_side"]:
        rows, purged, incomplete_dates, incomplete_events, incomplete_label_dates = _observations(
            raw, definition, bps_per_side=float(bps)
        )
        cost_runs[str(bps)] = {
            "split_summary": _summary(rows, split_ids),
            "retained_signal_date_count": len(rows),
            "whole_label_purged_signal_date_count": purged,
            "incomplete_signal_date_count": incomplete_dates,
            "incomplete_candidate_event_count": incomplete_events,
            "incomplete_label_date_count": incomplete_label_dates,
        }
        if bps == definition["cost_contract"]["strict_gate_bps_per_side"]:
            strict_rows, strict_purged, strict_incomplete_dates = rows, purged, incomplete_dates
            strict_incomplete_events = incomplete_events
            strict_incomplete_label_dates = incomplete_label_dates
    if strict_rows is None:
        raise Family66ReplayError("strict 100-bps cost run is missing")
    gates = _gate_checks(
        strict_rows, definition, incomplete_events=strict_incomplete_events,
        incomplete_label_dates=strict_incomplete_label_dates,
        incomplete_cohort_dates=strict_incomplete_dates,
    )
    return {
        "schema_version": "a-share-family66-cleanroom-event-replay-result-v1",
        "definition_id": definition["definition_id"],
        "definition_sha256": definition_sha256,
        "source_commit": source_commit,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "classification": definition["classification"],
        "source_paths": dict(source_paths),
        "source_feature_manifest_sha256": definition["source_contract"][
            "feature_dataset_manifest_sha256"
        ],
        "active_signal_date_count_before_purge": len(raw),
        "strict_cost_whole_label_purged_signal_date_count": strict_purged,
        "strict_cost_incomplete_signal_date_count": strict_incomplete_dates,
        "strict_cost_incomplete_candidate_event_count": strict_incomplete_events,
        "strict_cost_incomplete_label_date_count": strict_incomplete_label_dates,
        "cost_runs": cost_runs,
        "gate_checks": gates,
        "gate_pass_count": sum(item["passed"] for item in gates),
        "gate_count": len(gates),
        "historical_interval_pass": all(item["passed"] for item in gates),
        "original_status_preserved": "REJECTED_BY_METHODOLOGY_RECOMPUTE_GATE",
        "strict_pit_eligible": False,
        "eligible_for_new_evidence": False,
        "strategy_candidate_available": False,
        "broker_order_paper_live_auto": False,
    }


def _git_identity() -> str:
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain=v1"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise Family66ReplayError("cannot verify committed source identity") from exc
    if status.stdout:
        raise Family66ReplayError("--execute requires a clean committed worktree")
    commit = head.stdout.strip()
    if not _is_hash(commit, {40, 64}):
        raise Family66ReplayError("source commit identity is invalid")
    return commit


def _publish(report: Mapping[str, Any], output: Path) -> tuple[str, Path]:
    sidecar = output.with_suffix(output.suffix + ".sha256")
    if output.exists() or sidecar.exists():
        raise Family66ReplayError("result or sidecar already exists")
    try:
        raw = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    except (TypeError, ValueError) as exc:
        raise Family66ReplayError("result is not strict finite JSON") from exc
    digest = _sha256_bytes(raw)
    output.parent.mkdir(parents=True, exist_ok=True)
    payloads = ((output, raw), (sidecar, f"{digest}  {output.name}\n".encode("ascii")))
    temporaries: list[Path] = []
    try:
        for target, payload in payloads:
            with tempfile.NamedTemporaryFile(
                dir=output.parent, prefix=f".{target.name}.", delete=False
            ) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
                temporaries.append(Path(handle.name))
        for temporary, (target, _) in zip(temporaries, payloads, strict=True):
            os.replace(temporary, target)
    finally:
        for path in temporaries:
            path.unlink(missing_ok=True)
    return digest, sidecar


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--definition", type=Path, default=DEFINITION)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--baseline-manifest", type=Path)
    parser.add_argument("--feature-metadata", type=Path)
    parser.add_argument("--features-dir", type=Path)
    parser.add_argument("--trade-calendar", type=Path)
    parser.add_argument("--etf-csv", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    definition, digest = _load_definition(args.definition.resolve())
    if not args.execute:
        print(json.dumps({
            "status": "VALIDATE_DEFINITION_ONLY", "definition_sha256": digest,
            "database_opened": False, "network_used": False, "output_written": False,
        }, sort_keys=True))
        return 0
    if args.definition.resolve() != DEFINITION.resolve() or args.output.resolve() != OUTPUT.resolve():
        raise Family66ReplayError("--execute requires exact repository definition/output paths")
    required = {
        "packet": args.packet, "baseline_manifest": args.baseline_manifest,
        "feature_metadata": args.feature_metadata, "features_dir": args.features_dir,
        "trade_calendar": args.trade_calendar, "etf_csv": args.etf_csv,
    }
    if any(value is None for value in required.values()):
        raise Family66ReplayError("--execute requires every explicit external input path")
    # Preserve the final path component so O_NOFOLLOW can reject symlink inputs.
    paths = {key: value.absolute() for key, value in required.items() if value is not None}
    source_commit = _git_identity()
    with _verified_input_staging(definition, **paths) as verified:
        raw = _load_raw_cohorts(
            feature_files=verified.feature_files,
            trade_calendar=verified.trade_calendar,
            etf_csv=verified.etf_csv,
        )
    report = build_report(
        definition, digest, raw, source_commit=source_commit,
        source_paths={key: str(value) for key, value in paths.items()},
    )
    result_sha, sidecar = _publish(report, args.output.resolve())
    print(json.dumps({
        "status": "COMPLETED_CLEANROOM_RETROSPECTIVE_REPLAY",
        "result": str(args.output.resolve()), "result_sha256": result_sha,
        "sidecar": str(sidecar),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
