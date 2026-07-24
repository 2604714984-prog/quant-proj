from __future__ import annotations

from datetime import date, datetime, time, timedelta
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ADAPTER = Path(__file__).parents[1] / "research" / "adapters" / "tic_foreign_equity_demand.py"
SPEC = importlib.util.spec_from_file_location("_tic_foreign_equity_demand_test", ADAPTER)
assert SPEC is not None and SPEC.loader is not None
tic = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tic
SPEC.loader.exec_module(tic)


def next_month(month: date) -> date:
    return date(month.year + 1, 1, 1) if month.month == 12 else date(month.year, month.month + 1, 1)


def prior_month(month: date) -> date:
    return (
        date(month.year - 1, 12, 1)
        if month.month == 1
        else date(
            month.year,
            month.month - 1,
            1,
        )
    )


def tic_month_label(month: date) -> str:
    return month.strftime("%Y-%b")


def recorded_row(
    month: date,
    segment: str,
    total: int,
    *,
    release_date: date | None = None,
    newest_as_of: date | None = None,
) -> dict[str, object]:
    decision_date = month - timedelta(days=1)
    selected_date = release_date or decision_date - timedelta(days=10)
    newest = newest_as_of or prior_month(prior_month(month))
    perspective = (
        "NET_US_SALES" if selected_date >= tic.NET_US_SALES_FROM else "NET_FOREIGN_PURCHASES"
    )
    member = "npr_history.html" if selected_date >= tic.HTML_MEMBER_FROM else "npr_history.csv"
    private = total - 5
    row: dict[str, object] = {
        "archive_sha256": "a" * 64,
        "archive_url": (f"{tic.ARCHIVE_URL_PREFIX}{selected_date.strftime('%Y%m%d')}.zip"),
        "decision_at": datetime.combine(
            decision_date,
            time(20, 5),
            tzinfo=tic.NEW_YORK,
        ).isoformat(),
        "execution_month": month.isoformat(),
        "foreign_equity_demand": total,
        "line_13_official_equity_net": 5,
        "line_8_private_equity_net": private,
        "member_name": member,
        "member_sha256": "b" * 64,
        "newest_as_of_month": tic_month_label(newest),
        "perspective": perspective,
        "segment": segment,
        "selected_release_at": datetime.combine(
            selected_date,
            time(16, 0),
            tzinfo=tic.NEW_YORK,
        ).isoformat(),
        "state": "SPY" if total > 0 else "CASH",
    }
    identity = tic.sha256_bytes(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode("ascii")
    )
    return dict(row, row_identity_sha256=identity)


def recorded_states(segment: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    labels = ("SPY", "SPY", "CASH", "CASH") * 9
    for month, label in zip(tic.expected_months(segment), labels):
        rows.append(recorded_row(month, segment, 10 if label == "SPY" else -10))
    return rows


def rehash(row: dict[str, object]) -> None:
    canonical = {key: value for key, value in row.items() if key != "row_identity_sha256"}
    row["row_identity_sha256"] = tic.sha256_bytes(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("ascii")
    )


def test_derive_states_reproduces_exact_tic_rows_and_support() -> None:
    rows = recorded_states("validation")
    states = tic.derive_states(rows, "validation")
    assert len(states) == 28
    assert states[0].month == date(2021, 2, 1)
    assert states[0].state == "SPY"
    assert states[0].decision_at.hour == 20
    assert tic.state_support(states)["passes"] is True


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("unexpected", 1, "fields"),
        ("foreign_equity_demand", True, "integers"),
        ("foreign_equity_demand", 999, "sum"),
        ("state", "CASH", "sign"),
        ("row_identity_sha256", "0" * 64, "identity"),
    ),
)
def test_derive_states_rejects_tampering(
    field: str,
    value: object,
    message: str,
) -> None:
    rows = recorded_states("validation")
    rows[0][field] = value
    if field not in {"unexpected", "row_identity_sha256"}:
        rehash(rows[0])
    with pytest.raises(tic.ContractError, match=message):
        tic.derive_states(rows, "validation")


def test_derive_states_enforces_release_member_and_perspective_cutovers() -> None:
    rows = recorded_states("validation")
    row = recorded_row(
        date(2023, 5, 1),
        "validation",
        10,
        release_date=date(2023, 4, 17),
        newest_as_of=date(2023, 2, 1),
    )
    assert row["perspective"] == "NET_US_SALES"
    row["perspective"] = "NET_FOREIGN_PURCHASES"
    rehash(row)
    rows[-1] = row
    with pytest.raises(tic.ContractError, match="perspective"):
        tic.derive_states(rows, "validation")

    rows = recorded_states("secondary")
    rows[2]["member_name"] = "npr_history.csv"
    rehash(rows[2])
    with pytest.raises(tic.ContractError, match="member"):
        tic.derive_states(rows, "secondary")


def test_derive_states_allows_one_archive_for_two_decision_months() -> None:
    rows = recorded_states("secondary")
    for field in (
        "archive_sha256",
        "archive_url",
        "member_name",
        "member_sha256",
        "newest_as_of_month",
        "perspective",
        "selected_release_at",
    ):
        rows[1][field] = rows[0][field]
    rehash(rows[1])
    assert len(tic.derive_states(rows, "secondary")) == 34


def test_derive_states_rejects_late_release_and_nonmonotonic_source_month() -> None:
    rows = recorded_states("validation")
    rows[0]["selected_release_at"] = rows[0]["decision_at"]
    rows[0]["archive_url"] = (
        f"{tic.ARCHIVE_URL_PREFIX}{str(rows[0]['decision_at'])[:10].replace('-', '')}.zip"
    )
    rehash(rows[0])
    with pytest.raises(tic.ContractError, match="chronology"):
        tic.derive_states(rows, "validation")

    rows = recorded_states("validation")
    rows[1]["newest_as_of_month"] = "2019-Jan"
    rehash(rows[1])
    with pytest.raises(tic.ContractError, match="newest month"):
        tic.derive_states(rows, "validation")


def test_state_support_requires_both_states_and_both_transition_directions() -> None:
    labels = ("SPY",) * 4 + ("CASH",) * 4 + ("SPY",) * 2
    states = tuple(
        tic.State(
            date(2021, index + 1, 1),
            label,
            "a" * 64,
            datetime(2020, 12, 31, 20, 5, tzinfo=tic.NEW_YORK),
        )
        for index, label in enumerate(labels)
    )
    assert tic.state_support(states) == {
        "intervals": 10,
        "spy_months": 6,
        "cash_months": 4,
        "spy_to_cash_transitions": 1,
        "cash_to_spy_transitions": 1,
        "passes": True,
    }
    assert tic.state_support(states[:8])["passes"] is False


def synthetic_segment(monkeypatch: pytest.MonkeyPatch):
    months: list[date] = []
    current = date(2021, 2, 1)
    for _ in range(10):
        months.append(current)
        current = next_month(current)
    terminal = current
    monkeypatch.setattr(tic, "VALIDATION_MONTHS", (months[0], months[-1]))
    monkeypatch.setitem(tic.INTERVALS, "validation", 10)
    monkeypatch.setitem(tic.TERMINAL_MONTHS, "validation", terminal)

    labels = ("SPY",) * 4 + ("CASH",) * 4 + ("SPY",) * 2
    session_dates = [date(2021, 1, 29), *months, terminal]
    states = tuple(
        tic.State(
            month,
            label,
            f"{index + 1:064x}",
            datetime.combine(
                session_dates[index],
                time(20, 5),
                tzinfo=tic.NEW_YORK,
            ),
        )
        for index, (month, label) in enumerate(zip(months, labels))
    )
    sessions = tuple(
        tic.Session(day, 100.0 + index, 100.5 + index) for index, day in enumerate(session_dates)
    )
    distributions = (
        tic.Distribution(
            "synthetic-dividend-1",
            months[1],
            months[2],
            1.0,
        ),
    )
    return states, sessions, distributions


def test_segment_keeps_same_state_exposure_and_uses_shared_portfolio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    states, sessions, distributions = synthetic_segment(monkeypatch)
    result = tic.run_segment("validation", states, sessions, distributions)
    assert result.support["passes"] is True
    assert result.strategy.trade_count == 3
    assert result.spy_buyhold.trade_count == 1
    assert result.strategy.terminal_wealth > 0
    assert len(result.strategy.interval_returns) == 10
    assert tuple(name for name, _ in result.gates) == tic.GATE_NAMES
    assert all(type(value) is bool for _, value in result.gates)


def test_segment_fails_before_execution_when_support_or_decision_date_is_wrong(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    states, sessions, distributions = synthetic_segment(monkeypatch)
    all_spy = tuple(
        tic.State(
            state.month,
            "SPY",
            state.source_row_sha256,
            state.decision_at,
        )
        for state in states
    )
    with pytest.raises(tic.ContractError, match="support preflight"):
        tic.run_segment("validation", all_spy, sessions, distributions)

    wrong_date = list(states)
    state = wrong_date[0]
    wrong_date[0] = tic.State(
        state.month,
        state.state,
        state.source_row_sha256,
        state.decision_at - timedelta(days=1),
    )
    with pytest.raises(tic.ContractError, match="prior accepted session"):
        tic.run_segment("validation", tuple(wrong_date), sessions, distributions)


def test_strict_json_rejects_duplicate_and_nonfinite_values() -> None:
    with pytest.raises(tic.ContractError, match="duplicate"):
        tic.strict_json(b'{"a":1,"a":2}')
    with pytest.raises(tic.ContractError, match="nonfinite"):
        tic.strict_json(b'{"a":NaN}')


def test_distribution_loader_uses_exact_accepted_unit() -> None:
    row = {
        "symbol": "SPY",
        "action_type": "cash_distribution",
        "currency": "USD",
        "unit": "per_share",
        "event_id": "synthetic-distribution",
        "ex_date": "2021-03-01",
        "pay_date": "2021-03-15",
        "amount_per_share": "1.25",
    }
    payload = (json.dumps(row, sort_keys=True) + "\n").encode()
    result = tic.load_distributions(payload)
    assert result[0].amount_per_share == 1.25
    row["unit"] = "USD_per_share"
    with pytest.raises(tic.ContractError, match="identity drift"):
        tic.load_distributions((json.dumps(row, sort_keys=True) + "\n").encode())


def test_session_loader_uses_exact_frozen_market_calendar_contract() -> None:
    calendar = {
        "session_date": "2021-01-29",
        "exchange": "XNYS",
        "open_at": "2021-01-29T09:30:00-05:00",
        "close_at": "2021-01-29T16:00:00-05:00",
        "source_row_sha256": "a" * 64,
        "row_identity_sha256": "b" * 64,
    }
    market = {
        "session_date": "2021-01-29",
        "symbol": "SPY",
        "currency": "USD",
        "price_basis": "UNADJUSTED_RAW_OPEN_CLOSE_ONLY",
        "calendar_row_sha256": calendar["source_row_sha256"],
        "raw_open": 100.0,
        "raw_close": 101.0,
    }

    def payload(row: dict[str, object]) -> bytes:
        return (json.dumps(row, sort_keys=True) + "\n").encode()

    assert tic.load_sessions(payload(market), payload(calendar)) == (
        tic.Session(date(2021, 1, 29), 100.0, 101.0),
    )

    wrong_hash = dict(market, calendar_row_sha256=calendar["row_identity_sha256"])
    with pytest.raises(tic.ContractError, match="identity drift"):
        tic.load_sessions(payload(wrong_hash), payload(calendar))

    wrong_basis = dict(market, price_basis="unadjusted_raw_open_close")
    with pytest.raises(tic.ContractError, match="identity drift"):
        tic.load_sessions(payload(wrong_basis), payload(calendar))


def test_exact_file_hash_and_atomic_claim_are_fail_closed(tmp_path: Path) -> None:
    payload = b"accepted bytes\n"
    source = tmp_path / "source"
    source.write_bytes(payload)
    expected = tic.sha256_bytes(payload)
    assert tic.exact_bytes(source, expected) == payload
    with pytest.raises(tic.ContractError, match="SHA256"):
        tic.exact_bytes(source, "0" * 64)

    link = tmp_path / "link"
    link.symlink_to(source)
    with pytest.raises(OSError):
        tic.sha256_file(link)

    claim = tmp_path / "claim.json"
    first = {"status": "claimed"}
    first_hash = tic.atomic_json(claim, first)
    assert first_hash == tic.sha256_bytes(claim.read_bytes())
    with pytest.raises(FileExistsError):
        tic.atomic_json(claim, first)


def test_definition_preserves_outcome_blind_boundaries() -> None:
    definition_path = (
        Path(__file__).parents[1]
        / "research"
        / "definitions"
        / "us_eq_tic_foreign_equity_demand_sign_spy_cash_v1.json"
    )
    definition = json.loads(definition_path.read_text(encoding="utf-8"))
    assert definition["post_reset_frozen_mechanism_ordinal"] == 7
    assert definition["accepted_input"] == {
        "input_receipt_sha256": tic.ACCEPTED_INPUT_RECEIPT_SHA256,
        "archive_manifest_sha256": tic.ACCEPTED_ARCHIVE_MANIFEST_SHA256,
        "validation_states_sha256": tic.ACCEPTED_STATE_SHA256["validation"],
        "secondary_states_sha256": tic.ACCEPTED_STATE_SHA256["secondary"],
        "unique_official_archives": 61,
        "decision_release_selections": 62,
        "revision_policy": "AS_PUBLISHED_ARCHIVE_PER_DECISION_NO_OVERWRITE",
        "february_2022_exact_object": "ticrel_20220222.zip",
        "delayed_2025_rule": (
            "the 2025-09-18 archive is reused for the October and November 2025 "
            "execution decisions because no later archive was public by the latter cutoff"
        ),
    }
    assert definition["multiplicity"] == {
        "historical_inference": "DESCRIPTIVE_ONLY_NO_CONFIRMATORY_P_VALUE",
        "confirmatory_alpha_assigned": False,
        "family_reset": False,
        "alpha_recycling": False,
        "one_shot": True,
        "rerun_or_post_outcome_change": False,
        "maximum_success_label": "RETROSPECTIVE_SECONDARY_PASS_PENDING_USER_REVIEW",
    }
    assert all(value is False for value in definition["sealed"].values())
