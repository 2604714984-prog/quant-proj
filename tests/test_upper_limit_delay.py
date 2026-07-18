from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from quant_system.data import AcceptedSession, AcceptedSessionCalendar, SourceIdentity
from quant_system.research import upper_limit_delay as delay
from scripts import run_a_share_upper_limit_delay_preflight as preflight


def _source(name: str, available_at: datetime | None = None) -> SourceIdentity:
    available = available_at or datetime(2000, 1, 1, tzinfo=timezone.utc)
    return SourceIdentity(
        f"https://example.test/{name}",
        hashlib.sha256(name.encode()).hexdigest(),
        available,
        available,
        name,
    )


def _calendar(days: tuple[date, ...]) -> AcceptedSessionCalendar:
    zone = ZoneInfo("Asia/Shanghai")
    return AcceptedSessionCalendar(
        tuple(
            AcceptedSession(
                day,
                datetime.combine(day, time(9, 30), zone),
                datetime.combine(day, time(15), zone),
                _source("calendar"),
                "Asia/Shanghai",
            )
            for day in days
        )
    )


def _signal(
    symbol: str,
    *,
    low: float = 9.5,
    limit: float = 10.0,
    is_limit_up: bool = True,
    is_limit_down: bool = False,
    amount: float = 30_000_000.0,
) -> delay.DailySignal:
    return delay.DailySignal(
        symbol,
        low,
        limit,
        is_limit_up,
        is_limit_down,
        (amount,) * 20,
        252,
        True,
        False,
        False,
        False,
    )


def test_definition_is_hash_bound_one_variant_outcome_blind_and_sequential() -> None:
    raw = delay.DEFINITION_PATH.read_bytes()
    definition = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == delay.DEFINITION_SHA256
    assert definition["research_id"] == delay.RESEARCH_ID
    assert definition["lineage_id"] == delay.LINEAGE_ID
    assert definition["feature_contract"]["variant_id"] == delay.VARIANT_ID
    assert definition["feature_contract"]["variant_count"] == 1
    assert definition["inference"]["lifetime_primary_test_count"] == 3
    assert definition["inference"]["bonferroni_one_sided_alpha"] == 1 / 60
    assert definition["inference"]["block_length_intervals"] == 20
    assert definition["inference"]["draws"] == 10_000
    assert definition["historical_sequential_access"].startswith(
        "Compute and adjudicate validation first"
    )
    assert definition["execution_state"]["retrospective_holdout_outcome_authorized"] is False
    assert definition["execution_state"]["strategy_candidate_available"] is False


def test_definition_has_only_nontraded_matched_reference_and_exact_parentheses() -> None:
    benchmark = json.loads(delay.DEFINITION_PATH.read_text(encoding="utf-8"))["benchmark"]
    assert benchmark["type"] == "NON_TRADED_MATCHED_EVENT_REFERENCE"
    assert benchmark["investable_portfolio"] is False
    assert benchmark["interval_return"] == (
        "gross_target_D * (qfq_open_510300[D+2] / qfq_open_510300[D+1] - 1)"
    )
    assert benchmark["cost_capacity_or_fill_model"].startswith("none")
    assert set(benchmark).isdisjoint({"commission", "slippage", "capacity", "blocked_exit"})


@pytest.mark.parametrize(
    "symbol",
    (
        "600000.SH",
        "601999.SH",
        "603001.SH",
        "605001.SH",
        "688001.SH",
        "000001.SZ",
        "001001.SZ",
        "002001.SZ",
        "003001.SZ",
        "300001.SZ",
        "301001.SZ",
    ),
)
def test_common_a_symbol_accepts_only_exchange_aware_prefixes(symbol: str) -> None:
    assert delay.common_a_symbol(symbol)


@pytest.mark.parametrize(
    "symbol",
    (
        "600000.SZ",
        "000001.SH",
        "399001.SZ",
        "510300.SH",
        "900901.SH",
        "200001.SZ",
        "60000.SH",
        "A60000.SH",
    ),
)
def test_common_a_symbol_rejects_cross_suffix_indices_etfs_and_b_shares(symbol: str) -> None:
    assert not delay.common_a_symbol(symbol)


def test_non_one_price_signal_is_strict_and_makes_no_intraday_order_claim() -> None:
    assert _signal("600000.SH", low=9.99, limit=10.0).is_event
    assert not _signal("600000.SH", low=10.0, limit=10.0).is_event
    assert not _signal("600000.SH", low=9.0, limit=10.0, is_limit_up=False).is_event
    definition = json.loads(delay.DEFINITION_PATH.read_text(encoding="utf-8"))
    assert definition["feature_contract"]["intraday_ordering_claim"].startswith("none")


def test_signal_requires_known_nonconflicting_limit_states_and_low_not_above_limit() -> None:
    with pytest.raises(delay.UpperLimitDelayContractError, match="states conflict"):
        _signal("600000.SH", is_limit_up=True, is_limit_down=True)
    with pytest.raises(delay.UpperLimitDelayContractError, match="cannot exceed"):
        _signal("600000.SH", low=10.1, limit=10.0)


def test_target_ranks_median_amount_desc_symbol_asc_and_keeps_empty_slots_cash() -> None:
    days = (date(2022, 1, 3), date(2022, 1, 4), date(2022, 1, 5))
    calendar = _calendar(days)
    at = calendar.session_on(days[0], as_of=datetime(2030, 1, 1, tzinfo=timezone.utc)).close_at
    at += timedelta(minutes=30)
    signals = (
        _signal("600002.SH", amount=40_000_000.0),
        _signal("600001.SH", amount=40_000_000.0),
        _signal("000001.SZ", amount=30_000_000.0),
        _signal("000002.SZ", amount=30_000_000.0, is_limit_up=False),
    )
    target = delay.build_daily_target(signals, calendar, decision_date=days[0], decision_at=at)
    assert target.selected_symbols == ("600001.SH", "600002.SH", "000001.SZ")
    assert target.event_count == 3
    assert target.target_weights == tuple((symbol, 1 / 15) for symbol in target.selected_symbols)
    assert target.gross_target_exposure == 3 / 15
    assert math.fsum(weight for _, weight in target.target_weights) == 3 / 15


def test_target_caps_at_fifteen_without_tie_expansion() -> None:
    days = (date(2022, 1, 3), date(2022, 1, 4), date(2022, 1, 5))
    calendar = _calendar(days)
    at = calendar.session_on(days[0], as_of=datetime(2030, 1, 1, tzinfo=timezone.utc)).close_at
    signals = tuple(_signal(f"600{index:03d}.SH") for index in range(1, 18))
    target = delay.build_daily_target(
        signals, calendar, decision_date=days[0], decision_at=at + timedelta(minutes=30)
    )
    assert target.event_count == 17
    assert target.selected_symbols == tuple(f"600{index:03d}.SH" for index in range(1, 16))
    assert target.gross_target_exposure == 1.0


def test_matched_reference_formula_has_exact_parentheses_zero_and_missing_fail_closed() -> None:
    assert delay.matched_reference_return(0.5, 10.0, 11.0) == pytest.approx(0.05)
    assert delay.matched_reference_return(0.0, 10.0, 999.0) == 0.0
    with pytest.raises(delay.UpperLimitDelayContractError, match="finite"):
        delay.matched_reference_return(0.5, 10.0, float("nan"))
    with pytest.raises(delay.UpperLimitDelayContractError, match=r"\[0, 1\]"):
        delay.matched_reference_return(1.1, 10.0, 11.0)


def test_split_triplet_purges_last_two_sessions_and_never_crosses_boundary() -> None:
    assert delay.retained_triplet(date(2023, 12, 27), date(2023, 12, 28), date(2023, 12, 29)) == (
        True,
        "validation_2022_2023",
    )
    assert delay.retained_triplet(date(2023, 12, 29), date(2024, 1, 2), date(2024, 1, 3)) == (
        False,
        "validation_2022_2023",
    )
    assert (
        delay.retained_triplet(date(2026, 6, 29), date(2026, 6, 30), date(2026, 7, 1))[0] is False
    )


def test_capacity_observation_is_exactly_t_minus_one_and_strictly_preopen() -> None:
    days = (date(2022, 1, 3), date(2022, 1, 4), date(2022, 1, 5), date(2022, 1, 6))
    calendar = _calendar(days)
    zone = ZoneInfo("Asia/Shanghai")
    entry_decision = datetime(2022, 1, 3, 15, 30, tzinfo=zone)
    exit_decision = datetime(2022, 1, 4, 15, 30, tzinfo=zone)
    retry_decision = datetime(2022, 1, 5, 15, 30, tzinfo=zone)
    assert (
        delay.capacity_observation_session(
            calendar, execution_date=days[1], decision_at=entry_decision
        )
        == days[0]
    )
    assert (
        delay.capacity_observation_session(
            calendar, execution_date=days[2], decision_at=exit_decision
        )
        == days[1]
    )
    assert (
        delay.capacity_observation_session(
            calendar, execution_date=days[3], decision_at=retry_decision
        )
        == days[2]
    )
    with pytest.raises(delay.UpperLimitDelayContractError, match="strictly pre-open"):
        delay.capacity_observation_session(
            calendar,
            execution_date=days[1],
            decision_at=datetime(2022, 1, 4, 9, 30, tzinfo=zone),
        )


def _audit(
    day: date,
    split: str,
    *,
    eligible: int = 500,
    events: int = 0,
    reference: bool = True,
    signal_missing: int = 0,
    signal_nonfinite: int = 0,
    signal_identity: int = 0,
) -> delay.IntervalAudit:
    slots = min(events, 15)
    return delay.IntervalAudit(
        day,
        split,
        eligible,
        events,
        slots,
        slots / 15,
        True,
        True,
        True,
        True,
        reference,
        signal_panel_missing_count=signal_missing,
        signal_panel_nonfinite_count=signal_nonfinite,
        signal_panel_identity_failure_count=signal_identity,
    )


def test_preflight_report_exact_allowlist_zero_event_and_three_states() -> None:
    rows = (
        _audit(date(2020, 1, 3), "development_2020_2021", events=0),
        *(
            _audit(
                date(2022, 1, 3) + timedelta(days=index),
                "validation_2022_2023",
                events=20 if index == 0 else 1,
            )
            for index in range(400)
        ),
        *(
            _audit(
                date(2024, 1, 3) + timedelta(days=index),
                "retrospective_holdout_2024_2026h1",
                events=2,
            )
            for index in range(400)
        ),
    )
    report = preflight._preflight_report(rows, (delay.COVERAGE_START, delay.HISTORICAL_CUTOFF))
    definition = json.loads(delay.DEFINITION_PATH.read_text(encoding="utf-8"))
    assert set(report) == set(definition["outcome_free_preflight"]["allowed_fields"])
    assert report["status"] == "PREFLIGHT_PASS"
    assert report["split_zero_event_counts"]["development_2020_2021"] == 1
    assert report["maximum_target_slot_count"] == 15
    assert report["maximum_gross_target_exposure"] == 1.0
    assert report["post_entry_outcomes_opened"] is False
    assert report["security_identifiers_in_report"] is False
    assert report["strategy_candidate_available"] is False
    assert report["blocked_retry_and_terminal_state_validation"] == "NOT_EVALUATED_PR_A"
    assert "terminal_unresolved_holding_count" not in report
    structural = tuple(
        _audit(
            date(2022, 1, 3) + timedelta(days=index),
            "validation_2022_2023",
            eligible=499 if index == 0 else 500,
        )
        for index in range(400)
    ) + tuple(
        _audit(
            date(2024, 1, 3) + timedelta(days=index),
            "retrospective_holdout_2024_2026h1",
        )
        for index in range(400)
    )
    assert (
        preflight._preflight_report(structural, (delay.COVERAGE_START, delay.HISTORICAL_CUTOFF))[
            "status"
        ]
        == "STRUCTURAL_FAIL"
    )
    blocked = tuple(
        _audit(
            date(2022, 1, 3) + timedelta(days=index),
            "validation_2022_2023",
            reference=index != 0,
        )
        for index in range(400)
    ) + tuple(
        _audit(
            date(2024, 1, 3) + timedelta(days=index),
            "retrospective_holdout_2024_2026h1",
        )
        for index in range(400)
    )
    assert (
        preflight._preflight_report(blocked, (delay.COVERAGE_START, delay.HISTORICAL_CUTOFF))[
            "status"
        ]
        == "INPUT_BLOCKED"
    )


def test_preflight_default_path_has_no_network_write_outcomes_or_identifiers() -> None:
    source = Path(preflight.__file__).read_text(encoding="utf-8")
    lowered = source.lower()
    assert "read_only=true" in lowered
    assert "enable_external_access=false" in lowered
    assert "import socket" not in lowered
    assert "import requests" not in lowered
    assert all(token not in lowered for token in ("insert into", "update a_share", "delete from"))
    allowed = json.loads(delay.DEFINITION_PATH.read_text(encoding="utf-8"))[
        "outcome_free_preflight"
    ]["allowed_fields"]
    forbidden = ("return", "nav", "sharpe", "selected_symbols", "rankings")
    assert not any(any(token in key.lower() for token in forbidden) for key in allowed)


def test_master_accepts_exact_legacy_identity_and_rejects_forged_composition() -> None:
    class Result:
        def __init__(self, forged: bool) -> None:
            self.forged = forged

        def fetchall(self) -> list[tuple[object, ...]]:
            return [
                (
                    (symbol := f"600{index:03d}.SH"),
                    "20100101",
                    "wsl2_chain_repair_20260706",
                    "wsl2_chain_repair_20260706_195210",
                    (
                        "wsl2_chain_repair_20260706|forged|symbol_master|" + symbol + "|"
                        if self.forged and index == 0
                        else "wsl2_chain_repair_20260706|"
                        "wsl2_chain_repair_20260706_195210|symbol_master|" + symbol + "|"
                    ),
                    False,
                )
                for index in range(500)
            ]

    class Connection:
        def __init__(self, forged: bool) -> None:
            self.forged = forged

        def execute(self, _: str) -> Result:
            return Result(self.forged)

    preflight._validate_master(Connection(False))
    with pytest.raises(delay.UpperLimitDelayContractError, match="row identity differs"):
        preflight._validate_master(Connection(True))


def test_definition_capture_is_repo_relative_and_independent_of_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    assert preflight._definition_payload()["research_id"] == delay.RESEARCH_ID


def test_definition_capture_rejects_forged_bytes_and_symlink(tmp_path: Path) -> None:
    forged = tmp_path / "forged.json"
    forged.write_text('{"research_id":"forged"}', encoding="utf-8")
    with pytest.raises(delay.UpperLimitDelayContractError, match="SHA-256"):
        preflight._definition_payload(forged)
    linked = tmp_path / "definition-link.json"
    linked.symlink_to(preflight._DEFINITION_PATH)
    with pytest.raises(delay.UpperLimitDelayContractError, match="regular file"):
        preflight._definition_payload(linked)


@pytest.mark.parametrize(
    ("raw", "message"),
    (
        (b'{"x":1,"x":2}', "duplicate JSON key"),
        (b'{"x":NaN}', "nonfinite JSON"),
    ),
)
def test_definition_capture_uses_strict_json_from_same_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, raw: bytes, message: str
) -> None:
    path = tmp_path / "strict.json"
    path.write_bytes(raw)
    monkeypatch.setattr(preflight, "DEFINITION_SHA256", hashlib.sha256(raw).hexdigest())
    with pytest.raises(delay.UpperLimitDelayContractError, match=message):
        preflight._definition_payload(path)


class _Rows:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.rows = rows

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows


class _CalendarConnection:
    def __init__(
        self,
        rows: list[tuple[object, ...]],
        snapshot_dates: list[str],
        reference_dates: list[str],
    ) -> None:
        self.rows = rows
        self.snapshot_dates = snapshot_dates
        self.reference_dates = reference_dates

    def execute(self, sql: str, parameters: list[object]) -> _Rows:
        if "a_share_trade_calendar" in sql:
            return _Rows(self.rows)
        dates = self.reference_dates if "ts_code=?" in sql else self.snapshot_dates
        return _Rows([(day, 1) for day in dates])


def _calendar_rows() -> list[tuple[object, ...]]:
    return [
        (
            "calendar-test",
            "SSE",
            "20220103",
            1,
            None,
            "OFFICIAL_TEST_CALENDAR",
            "2026-07-18T00:00:00Z",
            hashlib.sha256(b"calendar-1").hexdigest(),
            False,
        ),
        (
            "calendar-test",
            "SSE",
            "20220104",
            1,
            "20220103",
            "OFFICIAL_TEST_CALENDAR",
            "2026-07-18T00:00:00Z",
            hashlib.sha256(b"calendar-2").hexdigest(),
            False,
        ),
    ]


def _freeze_test_calendar(monkeypatch: pytest.MonkeyPatch, rows: list[tuple[object, ...]]) -> None:
    monkeypatch.setattr(preflight, "CALENDAR_SNAPSHOT_ID", "calendar-test")
    monkeypatch.setattr(preflight, "CALENDAR_EXCHANGE", "SSE")
    monkeypatch.setattr(preflight, "CALENDAR_SOURCE", "OFFICIAL_TEST_CALENDAR")
    monkeypatch.setattr(preflight, "CALENDAR_ROW_COUNT", len(rows))
    monkeypatch.setattr(preflight, "CALENDAR_DIGEST", preflight._calendar_digest(rows))
    monkeypatch.setattr(preflight, "COVERAGE_START", date(2022, 1, 3))
    monkeypatch.setattr(preflight, "HISTORICAL_CUTOFF", date(2022, 1, 4))


def test_calendar_validation_binds_rows_digest_coverage_and_bar_parity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = _calendar_rows()
    _freeze_test_calendar(monkeypatch, rows)
    days, digest = preflight._validated_calendar(
        _CalendarConnection(rows, ["20220103", "20220104"], ["20220103", "20220104"])
    )
    assert days == ("20220103", "20220104")
    assert digest == preflight.CALENDAR_DIGEST


@pytest.mark.parametrize("defect", ("hash", "synthetic", "duplicate", "conflict", "parity"))
def test_calendar_validation_fails_closed_on_adversarial_identity(
    monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    rows = _calendar_rows()
    snapshot_dates = ["20220103", "20220104"]
    reference_dates = list(snapshot_dates)
    if defect == "hash":
        rows[1] = (*rows[1][:-2], "not-a-hash", rows[1][-1])
    elif defect == "synthetic":
        rows[1] = (*rows[1][:-1], True)
    elif defect in {"duplicate", "conflict"}:
        rows[1] = (
            rows[1][0],
            rows[1][1],
            rows[0][2],
            0 if defect == "conflict" else 1,
            rows[1][4],
            rows[1][5],
            rows[1][6],
            rows[1][7],
            rows[1][8],
        )
    else:
        reference_dates[-1] = "20220105"
    _freeze_test_calendar(monkeypatch, rows)
    with pytest.raises(delay.UpperLimitDelayContractError):
        preflight._validated_calendar(_CalendarConnection(rows, snapshot_dates, reference_dates))


@pytest.mark.parametrize(
    ("missing", "nonfinite", "identity"),
    ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
)
def test_signal_panel_failures_take_precedence_over_structural_failure(
    missing: int, nonfinite: int, identity: int
) -> None:
    rows = tuple(
        _audit(
            date(2022, 1, 3) + timedelta(days=index),
            "validation_2022_2023",
            eligible=499 if index == 0 else 500,
            signal_missing=missing if index == 0 else 0,
            signal_nonfinite=nonfinite if index == 0 else 0,
            signal_identity=identity if index == 0 else 0,
        )
        for index in range(400)
    ) + tuple(
        _audit(
            date(2024, 1, 3) + timedelta(days=index),
            "retrospective_holdout_2024_2026h1",
        )
        for index in range(400)
    )
    report = preflight._preflight_report(rows, (delay.COVERAGE_START, delay.HISTORICAL_CUTOFF))
    assert report["status"] == "INPUT_BLOCKED"
    assert report["signal_panels_complete"] is False
    assert report["signal_panel_missing_count"] == missing
    assert report["signal_panel_nonfinite_count"] == nonfinite
    assert report["signal_panel_identity_failure_count"] == identity


def _signal_sql_connection(defect: str):
    import duckdb

    connection = duckdb.connect(":memory:")
    connection.execute("CREATE SCHEMA a_share")
    connection.execute(
        "CREATE TABLE a_share.a_share_trade_calendar(snapshot_id VARCHAR,exchange VARCHAR,"
        "trade_date VARCHAR,is_open INTEGER,source VARCHAR,synthetic_data BOOLEAN)"
    )
    connection.execute(
        "CREATE TABLE a_share.a_share_symbol_master(ts_code VARCHAR,list_date VARCHAR,"
        "delist_date VARCHAR,ingested_at VARCHAR,snapshot_id VARCHAR)"
    )
    connection.execute(
        "CREATE TABLE a_share.a_share_canonical_daily_bars("
        "snapshot_id VARCHAR,ts_code VARCHAR,trade_date VARCHAR,amount DOUBLE,low DOUBLE,"
        "up_limit DOUBLE,qfq_close DOUBLE,vol DOUBLE,is_limit_up BOOLEAN,is_limit_down BOOLEAN,"
        "list_status VARCHAR,is_st BOOLEAN,is_suspended BOOLEAN,quality_status VARCHAR,"
        "synthetic_data BOOLEAN,row_hash VARCHAR,qfq_open DOUBLE,open DOUBLE,down_limit DOUBLE)"
    )
    days: list[str] = []
    day = date(2021, 1, 4)
    while len(days) < 260:
        if day.weekday() < 5:
            days.append(day.strftime("%Y%m%d"))
        day += timedelta(days=1)
    connection.executemany(
        "INSERT INTO a_share.a_share_trade_calendar VALUES (?,?,?,?,?,?)",
        [
            (
                delay.CALENDAR_SNAPSHOT_ID,
                delay.CALENDAR_EXCHANGE,
                trade_day,
                1,
                delay.CALENDAR_SOURCE,
                False,
            )
            for trade_day in days
        ],
    )
    connection.executemany(
        "INSERT INTO a_share.a_share_symbol_master VALUES (?,?,?,?,?)",
        [
            (symbol, days[0], None, "2026-07-18T00:00:00Z", "master-test")
            for symbol in ("600001.SH", "600002.SH")
        ],
    )
    signal_day = days[-3]
    entry_day = days[-2]
    exit_day = days[-1]
    prior_day = days[-10]
    rows: list[tuple[object, ...]] = []
    for symbol in ("600001.SH", "600002.SH", "510300.SH"):
        for trade_day in days:
            if defect == "missing_d" and symbol == "600001.SH" and trade_day == signal_day:
                continue
            low: object = 9.0
            quality = preflight.CLASSIFICATION
            synthetic = False
            row_hash = hashlib.sha256(f"{symbol}|{trade_day}".encode()).hexdigest()
            is_limit_up: object = symbol != "510300.SH" and trade_day == signal_day
            is_limit_down: object = False
            is_st: object = False
            is_suspended: object = False
            qfq_open: object = 9.8
            raw_open: object = 9.8
            if symbol == "600001.SH" and trade_day == prior_day:
                if defect == "prior_invalid_hash":
                    row_hash = "invalid"
                elif defect == "prior_quality_null":
                    quality = None
                elif defect == "prior_synthetic":
                    synthetic = True
            if symbol == "600001.SH" and trade_day == signal_day:
                if defect == "null_required":
                    low = None
                elif defect == "nonfinite":
                    low = float("nan")
                elif defect == "low_gt_limit":
                    low = 10.1
                elif defect == "invalid_hash":
                    row_hash = "invalid"
                elif defect == "wrong_quality":
                    quality = "WRONG"
                elif defect == "synthetic":
                    synthetic = True
                elif defect == "limit_down_null":
                    is_limit_down = None
                elif defect == "limit_conflict":
                    is_limit_down = True
            if symbol == "600002.SH" and trade_day == entry_day:
                if defect == "entry_st_true":
                    is_st = True
                elif defect == "entry_suspended_true":
                    is_suspended = True
                elif defect == "entry_limit_up_true":
                    is_limit_up = True
                elif defect == "mixed_entry_null_suspended":
                    is_suspended = None
                elif defect == "mixed_entry_null_open":
                    qfq_open = None
                elif defect == "mixed_entry_limit_conflict":
                    is_limit_up = True
                    is_limit_down = True
                elif defect == "entry_above_up":
                    raw_open = 10.01
                elif defect == "entry_below_down":
                    raw_open = 7.99
                elif defect == "entry_at_up":
                    raw_open = 10.0
                elif defect == "entry_at_down":
                    raw_open = 8.0
                elif defect == "entry_within_tolerance":
                    raw_open = 10.0005
            if symbol == "600002.SH" and trade_day == exit_day:
                if defect == "mixed_exit_null_limit_down":
                    is_limit_down = None
                elif defect == "exit_st_true":
                    is_st = True
                elif defect == "exit_suspended_true":
                    is_suspended = True
                elif defect == "exit_limit_down_true":
                    is_limit_down = True
                elif defect == "exit_above_up":
                    raw_open = 10.01
                elif defect == "exit_below_down":
                    raw_open = 7.99
                elif defect == "exit_at_up":
                    raw_open = 10.0
                elif defect == "exit_at_down":
                    raw_open = 8.0
                elif defect == "exit_within_tolerance":
                    raw_open = 7.9995
            rows.append(
                (
                    delay.SNAPSHOT_ID,
                    symbol,
                    trade_day,
                    30_000_000.0,
                    low,
                    10.0,
                    9.8,
                    1000.0,
                    is_limit_up,
                    is_limit_down,
                    "L",
                    is_st,
                    is_suspended,
                    quality,
                    synthetic,
                    row_hash,
                    qfq_open,
                    raw_open,
                    8.0,
                )
            )
    connection.executemany(
        "INSERT INTO a_share.a_share_canonical_daily_bars VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return connection


@pytest.mark.parametrize(
    ("defect", "expected"),
    (
        ("missing_d", "missing"),
        ("null_required", "missing"),
        ("limit_down_null", "missing"),
        ("nonfinite", "nonfinite"),
        ("low_gt_limit", "nonfinite"),
        ("invalid_hash", "identity"),
        ("wrong_quality", "identity"),
        ("synthetic", "identity"),
        ("limit_conflict", "identity"),
        ("prior_invalid_hash", "identity"),
        ("prior_quality_null", "identity"),
        ("prior_synthetic", "identity"),
    ),
)
def test_signal_sql_classifies_missing_nonfinite_and_identity_failures(
    defect: str, expected: str
) -> None:
    connection = _signal_sql_connection(defect)
    try:
        audits = preflight._database_audits(connection)
    finally:
        connection.close()
    assert audits
    totals = {
        "missing": sum(row.signal_panel_missing_count for row in audits),
        "nonfinite": sum(row.signal_panel_nonfinite_count for row in audits),
        "identity": sum(row.signal_panel_identity_failure_count for row in audits),
    }
    assert totals[expected] > 0
    assert any(not row.signal_panel_complete for row in audits)


@pytest.mark.parametrize(
    "known_state",
    (
        "entry_st_true",
        "entry_suspended_true",
        "entry_limit_up_true",
        "exit_st_true",
        "exit_suspended_true",
        "exit_limit_down_true",
        "entry_at_up",
        "entry_at_down",
        "exit_at_up",
        "exit_at_down",
        "entry_within_tolerance",
        "exit_within_tolerance",
    ),
)
def test_selected_known_economic_states_and_boundary_tolerance_are_complete(
    known_state: str,
) -> None:
    connection = _signal_sql_connection(known_state)
    try:
        audit = preflight._database_audits(connection)[-1]
    finally:
        connection.close()
    assert audit.target_slot_count == 2
    assert audit.entry_panel_complete is True
    assert audit.exit_panel_complete is True


@pytest.mark.parametrize(
    ("defect", "panel"),
    (
        ("mixed_entry_null_suspended", "entry"),
        ("mixed_entry_null_open", "entry"),
        ("mixed_entry_limit_conflict", "entry"),
        ("mixed_exit_null_limit_down", "exit"),
        ("entry_above_up", "entry"),
        ("entry_below_down", "entry"),
        ("exit_above_up", "exit"),
        ("exit_below_down", "exit"),
    ),
)
def test_selected_panel_mixed_valid_and_invalid_rows_fail_closed(defect: str, panel: str) -> None:
    connection = _signal_sql_connection(defect)
    try:
        audit = preflight._database_audits(connection)[-1]
    finally:
        connection.close()
    assert audit.target_slot_count == 2
    if panel == "entry":
        assert audit.entry_panel_complete is False
    else:
        assert audit.exit_panel_complete is False


def test_zero_event_panel_is_complete_only_against_zero_expected_slots() -> None:
    connection = _signal_sql_connection("valid")
    connection.execute(
        "UPDATE a_share.a_share_canonical_daily_bars SET is_limit_up=false "
        "WHERE ts_code IN ('600001.SH','600002.SH')"
    )
    try:
        audit = preflight._database_audits(connection)[-1]
    finally:
        connection.close()
    assert audit.target_slot_count == 0
    assert audit.entry_panel_complete is True
    assert audit.exit_panel_complete is True
    assert (
        "bool_and"
        not in preflight._SCAN_SQL.split("), panel_aggregates AS (", 1)[1].split(
            "), reference_panels AS (", 1
        )[0]
    )
