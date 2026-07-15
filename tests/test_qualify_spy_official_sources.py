from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO
import json
from pathlib import Path
import socket

from openpyxl import Workbook
import pytest

from scripts import qualify_spy_official_sources as p3


def _xlsx(rows: list[list[object]]) -> bytes:
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("data")
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _product() -> bytes:
    return _xlsx(
        [
            ["notice"],
            [
                "As of** ",
                "Ticker",
                "Name",
                "ISIN",
                "CUSIP",
                "Inception Date",
                "Distribution Frequency",
                "Primary Exchange",
            ],
            [
                "Jul 13 2026",
                "SPY",
                "State Street SPDR S&P 500 ETF Trust",
                "US78462F1030",
                "78462F103",
                "Jan 22 1993",
                "Quarterly",
                "NYSE ARCA",
            ],
        ]
    )


def _distributions(*, omit_last: bool = False) -> bytes:
    rows: list[list[object]] = [
        [
            "FUND NAME",
            "TICKER",
            "CUSIP",
            "EX-DATE",
            "RECORD DATE",
            "PAYABLE DATE",
            "DIVIDEND ($)",
            "SHORT TERM CAPITAL GAIN ($)",
            "LONG TERM CAPITAL GAIN ($)",
            "FREQUENCY",
        ]
    ]
    for year in range(2016, 2026):
        for month in (3, 6, 9, 12):
            ex_date = date(year, month, 15)
            rows.append(
                [
                    "State Street SPDR S&P 500 ETF Trust",
                    "SPY",
                    "78462F103",
                    ex_date.strftime("%m/%d/%Y"),
                    (ex_date + timedelta(days=1)).strftime("%m/%d/%Y"),
                    (ex_date + timedelta(days=10)).strftime("%m/%d/%Y"),
                    "1.25",
                    "",
                    "0.000000",
                    "Quarterly",
                ]
            )
    if omit_last:
        rows.pop()
    return _xlsx(rows)


def _nav(*, wrong_count: bool = False) -> bytes:
    expected = {int(year): count for year, count in p3.strict_load(p3.DEFINITION)[
        "acceptance"
    ]["target_nav_session_counts"].items()}
    if wrong_count:
        expected[2025] -= 1
    rows: list[list[object]] = [
        ["Fund Name:", "State Street SPDR S&P 500 ETF Trust"],
        ["Ticker Symbol:", "SPY"],
        [],
        ["Date", "NAV", "Shares Outstanding", "Total Net Assets"],
        ["30-May-2006", "126.28", "-", "-"],
    ]
    for year, count in expected.items():
        first = date(year, 1, 4) if year == 2016 else date(year, 1, 1)
        for offset in range(count):
            rows.append(
                [
                    (first + timedelta(days=offset)).strftime("%d-%b-%Y"),
                    "100.25",
                    "1000000",
                    "100250000",
                ]
            )
    rows.append(["State Street disclaimer"])
    return _xlsx(rows)


def _premium_discount() -> bytes:
    return _xlsx(
        [
            ["Fund Name:", "State Street SPDR S&P 500 ETF Trust"],
            ["Ticker Symbol:", "SPY"],
            [],
            ["Date", "Premium/Discount"],
            ["02-Jan-2025", "0.01"],
            ["31-Dec-2025", "-0.01"],
            ["State Street disclaimer"],
        ]
    )


def _snapshot(
    tmp_path: Path,
    *,
    omit_distribution: bool = False,
    wrong_nav_count: bool = False,
    taq_fields: int = 14,
) -> Path:
    definition = p3.strict_load(p3.DEFINITION)
    taq = [
        "SPY",
        "78462F103",
        "653.74",
        "658.52",
        "653.00",
        "655.24",
        "4.90",
        "24799876000000",
        "04/01/2026",
        "0.00",
        "0",
        "0.00",
        "0",
        "P",
    ][:taq_fields]
    payloads = {
        "ssga_product_snapshot": _product(),
        "ssga_historical_distributions": _distributions(omit_last=omit_distribution),
        "ssga_nav_history": _nav(wrong_count=wrong_nav_count),
        "ssga_premium_discount_history": _premium_discount(),
        "nyse_arca_closing_prices_sample": ("|".join(taq) + "\n").encode(),
        **{f"nyse_calendar_{year}": f"%PDF-1.4\n{year}\n".encode() for year in range(2022, 2026)},
    }
    resources = []
    for spec in definition["sources"]:
        raw = payloads[spec["source_id"]]
        (tmp_path / spec["filename"]).write_bytes(raw)
        resources.append(
            {
                "bytes": len(raw),
                "content_sha256": p3.sha256_bytes(raw),
                "filename": spec["filename"],
                "observed_available_at": "2026-07-15T00:00:00Z",
                "redirects_followed": 0,
                "retrieved_at": "2026-07-15T00:00:00Z",
                "server_last_modified": None,
                "source_id": spec["source_id"],
                "url": spec["url"],
            }
        )
    (tmp_path / "retrieval_manifest.json").write_bytes(
        p3.canonical_json(
            {
                "authentication_used": False,
                "cookies_used": False,
                "redirects_followed": 0,
                "resources": resources,
                "retries": 0,
                "snapshot_id": "synthetic-snapshot",
            }
        )
    )
    return tmp_path


def test_complete_source_set_is_partially_qualified_and_p4_r_blocked(tmp_path: Path) -> None:
    result = p3.qualify_source_dir(_snapshot(tmp_path))

    assert result["conclusion"] == (
        "PARTIALLY_QUALIFIED_BLOCKED_ANONYMOUS_OFFICIAL_RAW_OHLC"
    )
    assert result["p4_r_strict_eligible"] is False
    assert result["strategy_candidate_available"] is False
    assert result["gate_counts"] is None
    assert result["component_results"]["distributions"]["target_event_count"] == 40
    assert result["component_results"]["nav"]["target_row_count"] == 2514
    assert result["component_results"]["raw_ohlc"]["historical_access"] == (
        "BLOCKED_ENTITLEMENT"
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"omit_distribution": True}, "four per year"),
        ({"wrong_nav_count": True}, "NAV session counts"),
        ({"taq_fields": 13}, "exactly 14 fields"),
    ],
)
def test_incomplete_official_inputs_fail_closed(
    tmp_path: Path, kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(p3.QualificationError, match=message):
        p3.qualify_source_dir(_snapshot(tmp_path, **kwargs))


def test_manifest_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    source = _snapshot(tmp_path)
    path = source / "spdr-etf-historical-distributions.xlsx"
    path.write_bytes(path.read_bytes() + b"drift")
    with pytest.raises(p3.QualificationError, match="retrieved bytes changed"):
        p3.qualify_source_dir(source)


def test_default_plan_opens_no_socket_and_writes_no_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("dry run must not open a socket")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    before = set(tmp_path.iterdir())
    assert p3.main([]) == 0
    assert set(tmp_path.iterdir()) == before
    assert json.loads(capsys.readouterr().out)["status"] == "DRY_RUN_PLAN"


def test_strict_json_rejects_duplicate_and_nonfinite_values() -> None:
    with pytest.raises(p3.QualificationError, match="duplicate JSON key"):
        p3.strict_load_bytes(b'{"value": 1, "value": 2}')
    with pytest.raises(p3.QualificationError, match="nonfinite"):
        p3.strict_load_bytes(b'{"value": NaN}')


def test_result_and_sidecar_are_non_overwriting(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    digest, sidecar = p3.write_result({"ok": True}, output)
    assert p3.sha256_bytes(output.read_bytes()) == digest
    assert sidecar.read_text(encoding="ascii") == f"{digest}  result.json\n"
    with pytest.raises(p3.QualificationError, match="already exists"):
        p3.write_result({"ok": True}, output)
