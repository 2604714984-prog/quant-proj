from __future__ import annotations

from datetime import date
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ADAPTER = (
    Path(__file__).parents[1]
    / "research"
    / "adapters"
    / "formd_private_capital.py"
)
SPEC = importlib.util.spec_from_file_location("_formd_private_capital_test", ADAPTER)
assert SPEC is not None and SPEC.loader is not None
formd = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = formd
SPEC.loader.exec_module(formd)


def next_month(month: date) -> date:
    return (
        date(month.year + 1, 1, 1)
        if month.month == 12
        else date(month.year, month.month + 1, 1)
    )


def recorded_states(
    counts_rows: list[dict[str, object]],
    segment: str,
) -> list[dict[str, object]]:
    counts: dict[int, int] = {}
    for row in counts_rows:
        year = int(str(row["quarter"])[:4])
        quarter = int(str(row["quarter"])[-1])
        counts[formd.quarter_index(year, quarter)] = int(
            row["nonfund_initial_offerings"]
        )
    rows: list[dict[str, object]] = []
    for month in formd.expected_months(segment):
        execution = formd.quarter_index(month.year, (month.month - 1) // 3 + 1)
        latest, earlier = execution - 2, execution - 6
        row = {
            "execution_quarter": formd.quarter_label(execution),
            "latest_nonfund_initial_offerings": counts[latest],
            "latest_source_quarter": formd.quarter_label(latest),
            "month": month.isoformat(),
            "state": "SPY" if counts[latest] > counts[earlier] else "CASH",
            "year_earlier_nonfund_initial_offerings": counts[earlier],
            "year_earlier_source_quarter": formd.quarter_label(earlier),
        }
        canonical = json.dumps(row, sort_keys=True, separators=(",", ":"))
        row["source_row_sha256"] = formd.sha256_bytes(canonical.encode("ascii"))
        rows.append(row)
    return rows


def test_derive_states_uses_exact_two_and_six_quarter_lags() -> None:
    counts = [
        {
            "quarter": formd.quarter_label(index),
            "nonfund_initial_offerings": index,
        }
        for index in range(
            formd.quarter_index(2019, 3),
            formd.quarter_index(2025, 4) + 1,
        )
    ]
    rows = recorded_states(counts, "validation")
    states = formd.derive_states(counts, rows, "validation")
    assert len(states) == 28
    assert {state.state for state in states} == {"SPY"}
    first = rows[0]
    assert first["latest_source_quarter"] == "2020:Q3"
    assert first["year_earlier_source_quarter"] == "2019:Q3"


def test_derive_states_rejects_tampered_recorded_state() -> None:
    counts = [
        {
            "quarter": formd.quarter_label(index),
            "nonfund_initial_offerings": index,
        }
        for index in range(
            formd.quarter_index(2019, 3),
            formd.quarter_index(2025, 4) + 1,
        )
    ]
    rows = recorded_states(counts, "validation")
    rows[0]["state"] = "CASH"
    with pytest.raises(formd.ContractError, match="mechanically derived"):
        formd.derive_states(counts, rows, "validation")


def test_state_support_requires_both_states_and_both_transition_directions() -> None:
    labels = ("SPY",) * 4 + ("CASH",) * 4 + ("SPY",) * 2
    states = tuple(
        formd.State(date(2021, index + 1, 1), label, "a" * 64)
        for index, label in enumerate(labels)
    )
    assert formd.state_support(states) == {
        "intervals": 10,
        "spy_months": 6,
        "cash_months": 4,
        "spy_to_cash_transitions": 1,
        "cash_to_spy_transitions": 1,
        "passes": True,
    }
    assert formd.state_support(states[:8])["passes"] is False


def synthetic_segment(monkeypatch: pytest.MonkeyPatch):
    months: list[date] = []
    current = date(2021, 2, 1)
    for _ in range(10):
        months.append(current)
        current = next_month(current)
    terminal = current
    monkeypatch.setattr(formd, "VALIDATION_MONTHS", (months[0], months[-1]))
    monkeypatch.setitem(formd.INTERVALS, "validation", 10)
    monkeypatch.setitem(formd.TERMINAL_MONTHS, "validation", terminal)

    labels = ("SPY",) * 4 + ("CASH",) * 4 + ("SPY",) * 2
    states = tuple(
        formd.State(month, label, f"{index + 1:064x}")
        for index, (month, label) in enumerate(zip(months, labels))
    )
    session_dates = [date(2021, 1, 29), *months, terminal]
    sessions = tuple(
        formd.Session(day, 100.0 + index, 100.5 + index)
        for index, day in enumerate(session_dates)
    )
    distributions = (
        formd.Distribution(
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
    result = formd.run_segment("validation", states, sessions, distributions)
    assert result.support["passes"] is True
    assert result.strategy.trade_count == 3
    assert result.spy_buyhold.trade_count == 1
    assert result.strategy.terminal_wealth > 0
    assert len(result.strategy.interval_returns) == 10
    assert tuple(name for name, _ in result.gates) == formd.GATE_NAMES
    assert all(type(value) is bool for _, value in result.gates)


def test_segment_fails_before_execution_when_state_support_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    states, sessions, distributions = synthetic_segment(monkeypatch)
    all_spy = tuple(
        formd.State(state.month, "SPY", state.source_row_sha256) for state in states
    )
    with pytest.raises(formd.ContractError, match="support preflight"):
        formd.run_segment("validation", all_spy, sessions, distributions)


def test_strict_json_rejects_duplicate_and_nonfinite_values() -> None:
    with pytest.raises(formd.ContractError, match="duplicate"):
        formd.strict_json(b'{"a":1,"a":2}')
    with pytest.raises(formd.ContractError, match="nonfinite"):
        formd.strict_json(b'{"a":NaN}')


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
    result = formd.load_distributions(payload)
    assert result[0].amount_per_share == 1.25
    row["unit"] = "USD_per_share"
    with pytest.raises(formd.ContractError, match="identity drift"):
        formd.load_distributions(
            (json.dumps(row, sort_keys=True) + "\n").encode()
        )


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

    assert formd.load_sessions(payload(market), payload(calendar)) == (
        formd.Session(date(2021, 1, 29), 100.0, 101.0),
    )

    wrong_hash = dict(market, calendar_row_sha256=calendar["row_identity_sha256"])
    with pytest.raises(formd.ContractError, match="identity drift"):
        formd.load_sessions(payload(wrong_hash), payload(calendar))

    wrong_basis = dict(market, price_basis="unadjusted_raw_open_close")
    with pytest.raises(formd.ContractError, match="identity drift"):
        formd.load_sessions(payload(wrong_basis), payload(calendar))


def test_exact_file_hash_and_atomic_claim_are_fail_closed(tmp_path: Path) -> None:
    payload = b"accepted bytes\n"
    source = tmp_path / "source"
    source.write_bytes(payload)
    expected = formd.sha256_bytes(payload)
    assert formd.exact_bytes(source, expected) == payload
    with pytest.raises(formd.ContractError, match="SHA256"):
        formd.exact_bytes(source, "0" * 64)

    link = tmp_path / "link"
    link.symlink_to(source)
    with pytest.raises(OSError):
        formd.sha256_file(link)

    claim = tmp_path / "claim.json"
    first = {"status": "claimed"}
    first_hash = formd.atomic_json(claim, first)
    assert first_hash == formd.sha256_bytes(claim.read_bytes())
    with pytest.raises(FileExistsError):
        formd.atomic_json(claim, first)


def test_definition_preserves_outcome_blind_boundaries() -> None:
    definition_path = (
        Path(__file__).parents[1]
        / "research"
        / "definitions"
        / "us_eq_sec_formd_private_capital_formation_yoy_spy_cash_v1.json"
    )
    definition = json.loads(definition_path.read_text(encoding="utf-8"))
    assert definition["post_reset_frozen_mechanism_ordinal"] == 6
    assert definition["multiplicity"] == {
        "historical_inference": "DESCRIPTIVE_ONLY_NO_CONFIRMATORY_P_VALUE",
        "confirmatory_alpha_assigned": False,
        "family_reset": False,
        "alpha_recycling": False,
        "one_shot": True,
        "rerun_or_post_outcome_change": False,
        "maximum_success_label": "EXPLORATORY_SCREENING_PASS_PENDING_USER_REVIEW",
    }
    assert all(value is False for value in definition["sealed"].values())
