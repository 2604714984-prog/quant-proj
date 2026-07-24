import datetime as dt

from research.us_top50_gross_profitability import (
    factor_at,
    is_next_quarter,
    normalize,
    one_way_turnover,
    rank_ic,
    second_session_after,
    choose,
)


def test_quarter_sequence_crosses_year():
    assert is_next_quarter((2024, 4), (2025, 1))
    assert not is_next_quarter((2025, 2), (2025, 4))


def test_second_session_is_strictly_after_notice():
    sessions = [dt.date(2026, 1, day) for day in (2, 5, 6, 7)]
    assert second_session_after(dt.date(2026, 1, 2), sessions) == dt.date(2026, 1, 6)


def test_normalize_single_quarter_same_currency():
    sessions = [dt.date(2026, 6, 26), dt.date(2026, 6, 29)]
    gross = [{
        "DATE_TYPE": "单季报", "REPORT_TYPE": "2026/Q2",
        "REPORT_DATE": "2026-03-28 00:00:00", "NOTICE_DATE": "2026-05-01 00:00:00",
        "GROSS_PROFIT": 10.0, "CURRENCY_ABBR": "USD",
    }]
    assets = [{
        "REPORT_DATE": "2026-03-28 00:00:00", "STD_ITEM_CODE": "004005999",
        "AMOUNT": 100.0, "CURRENCY_ABBR": "USD",
    }]
    rows = normalize("AAPL", "AAPL.O", gross, assets, sessions, "a" * 64, "b" * 64, "now")
    assert len(rows) == 1
    assert rows[0]["available_at"] == "2026-06-26"


def test_factor_needs_four_consecutive_quarters():
    rows = [{
        "fiscal": (2025, q), "available_at": dt.date(2025, q * 2, 1),
        "notice_date": dt.date(2025, q * 2 - 1, 20),
        "gross_profit": 10.0, "total_assets": 100.0, "currency": "USD",
    } for q in (1, 2, 3, 4)]
    assert factor_at(rows, dt.date(2025, 12, 31)) == 0.4
    rows[2]["fiscal"] = (2025, 4)
    assert factor_at(rows, dt.date(2025, 12, 31)) is None


def test_factor_uses_latest_revision_available_at_formation():
    rows = [{
        "fiscal": (2025, q), "notice_date": dt.date(2025, q * 2 - 1, 20),
        "available_at": dt.date(2025, q * 2, 1), "gross_profit": 10.0,
        "total_assets": 100.0, "currency": "USD",
    } for q in (1, 2, 3, 4)]
    rows.append({
        **rows[-1], "notice_date": dt.date(2026, 2, 1),
        "available_at": dt.date(2026, 2, 3), "gross_profit": 30.0,
    })
    assert factor_at(rows, dt.date(2025, 12, 31)) == 0.4
    assert factor_at(rows, dt.date(2026, 3, 1)) == 0.6


def test_retention_through_rank_20():
    scores = {f"S{i:02d}": float(30 - i) for i in range(30)}
    portfolio = choose(scores, {"S18"})
    assert len(portfolio) == 15
    assert "S18" in portfolio and "S14" not in portfolio


def test_turnover_includes_initial_cash():
    assert one_way_turnover({}, {"A": 0.5, "B": 0.5}) == 1.0
    assert one_way_turnover({"A": 0.5, "B": 0.5}, {"A": 0.5, "C": 0.5}) == 0.5


def test_rank_ic_direction():
    assert rank_ic([(float(i), float(i)) for i in range(10)]) == 1.0
