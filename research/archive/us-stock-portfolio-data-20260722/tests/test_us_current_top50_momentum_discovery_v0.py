from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_us_current_top50_momentum_discovery_v0 as discovery  # noqa: E402


def test_contract_and_three_prior_terminal_results_are_immutable() -> None:
    contract = ROOT / "research/definitions/us_current_top50_momentum_discovery_v0.json"
    assert hashlib.sha256(contract.read_bytes()).hexdigest() == discovery.CONTRACT_SHA
    for name, expected in discovery.OLD.items():
        path = ROOT / "research/results" / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


def test_official_holdings_json_parser_finds_nested_security_rows() -> None:
    rows = [
        {"ticker": f"T{i:02}", "securityName": f"Issuer {i}", "weight": "2.0%"}
        for i in range(50)
    ]
    raw = json.dumps({"data": {"fundHoldings": {"holdings": rows}}}).encode()

    parsed = discovery.parse_holdings_json(raw)

    assert len(parsed) == 50
    assert parsed[0] == {"symbol": "T00", "name": "Issuer 0", "weight": 0.02}


def test_fallback_table_parser_requires_machine_readable_symbol_name_weight() -> None:
    body = ["<table><tr><th>Symbol</th><th>Company</th><th>Weight</th></tr>"]
    body.extend(
        f"<tr><td>T{i:02}</td><td>Issuer {i}</td><td>2.0%</td></tr>" for i in range(50)
    )
    body.append("</table>")

    parsed = discovery.parse_holdings_html("".join(body).encode())

    assert len(parsed) == 50
    assert parsed[-1]["weight"] == 0.02


def test_company_grouping_only_removes_terminal_share_class() -> None:
    assert discovery.company("Alphabet Inc Class A") == discovery.company(
        "Alphabet Inc Class C"
    )
    assert discovery.company("Class A Rail Holdings") != discovery.company(
        "Rail Holdings Class A"
    )


def _history(multiplier: float) -> list[dict[str, object]]:
    start = date(2026, 1, 1)
    return [
        {
            "date": start + timedelta(days=i),
            "close": 100.0,
            "volume": multiplier * (1_000_000 + i),
        }
        for i in range(60)
    ]


def test_multiclass_selection_uses_frozen_60_session_median_dollar_volume() -> None:
    rows = [
        {"symbol": "AAA", "name": "Example Inc Class A", "weight": 0.01},
        {"symbol": "AAB", "name": "Example Inc Class B", "weight": 0.01},
    ]
    rows.extend(
        {"symbol": f"S{i:02}", "name": f"Single Issuer {i}", "weight": 0.01}
        for i in range(49)
    )
    histories = {row["symbol"]: _history(2.0 if row["symbol"] == "AAB" else 1.0) for row in rows}

    selected = discovery.choose_lines(rows, histories)

    assert len(selected) == 50
    assert {row["symbol"] for row in selected} >= {"AAB", "S00", "S48"}
    assert "AAA" not in {row["symbol"] for row in selected}


def test_crosscheck_gate_is_exactly_98_percent_with_half_percent_tolerance() -> None:
    start = date(2020, 1, 1)
    primary = [{"date": start + timedelta(days=i), "close": 100.0} for i in range(100)]
    other = {start + timedelta(days=i): (101.0 if i < 2 else 100.5) for i in range(100)}

    result = discovery.crosscheck(primary, other)

    assert result["pass_ratio"] == 0.98
    assert result["passed"] is True
    assert len(result["worst"]) == 3


def test_simulation_applies_new_close_weights_only_to_subsequent_returns() -> None:
    days = [date(2020, 1, 1) + timedelta(days=i) for i in range(4)]
    prices = {"AAA": {days[0]: 100.0, days[1]: 100.0, days[2]: 110.0, days[3]: 121.0}}
    schedule = {days[1]: {"AAA": 1.0}}

    output_days, equity, returns, turnover = discovery.simulate(
        days, prices, schedule, 0.0
    )

    assert output_days == days[1:]
    assert equity == pytest.approx([1.0, 1.1, 1.21])
    assert returns == pytest.approx([0.0, 0.1, 0.1])
    assert turnover == 0.0


def test_research_script_stays_small_and_has_no_forbidden_sec_route() -> None:
    source = (ROOT / "scripts/run_us_current_top50_momentum_discovery_v0.py").read_text()
    logical_lines = [
        line for line in source.splitlines() if line.strip() and not line.lstrip().startswith("#")
    ]

    assert len(logical_lines) <= 500
    assert "sec.gov" not in source.lower()
    assert "n-port" not in source.lower()
    assert "strategy_candidate_available\": True" not in source


def test_terminal_result_is_input_blocked_before_prices_or_formal_run() -> None:
    path = (
        ROOT
        / "research/results/us_current_top50_momentum_discovery_v0_input_blocked_20260722.json"
    )
    result = json.loads(path.read_text())

    assert result["result"] == "INPUT_BLOCKED"
    assert result["smoke"]["status"] == "SMOKE_FAIL"
    assert result["source_attempts"]["yahoo_price_requests"] == 0
    assert result["source_attempts"]["stooq_price_requests"] == 0
    assert result["central_data"]["writer_invoked"] is False
    assert result["central_data"]["unchanged"] is True
    assert result["formal_discovery"]["run_count"] == 0
    assert result["strategy_candidate_available"] is False
