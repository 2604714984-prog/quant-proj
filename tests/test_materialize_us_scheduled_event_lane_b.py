from datetime import date
from pathlib import Path

from scripts import materialize_us_scheduled_event_lane_b as lane_b


def test_third_friday_and_quarter_assignment():
    assert lane_b.third_friday(2008, 3) == date(2008, 3, 21)
    events = lane_b.expiration_identities({date(2008, 3, 20)})
    march = [item for item in events if item["ordinary_third_friday"] == "2008-03-21"]
    assert march[0]["event_date"] == "2008-03-20"
    assert march[0]["mechanism"] == "M7"
    assert march[0]["identity_status"] == "RULE_DERIVED_OFFICIAL_RULE_NOT_HISTORICAL_IDENTITY"


def test_bls_schedule_parser_marks_not_actual():
    raw = b"<table><tr><td>Friday, January 09, 2009</td><td>08:30 AM</td><td>Employment Situation for December 2008</td></tr></table>"
    records = lane_b.bls_schedule_identities(2009, raw, "a" * 64)
    assert records[0]["event_date"] == "2009-01-09"
    assert records[0]["identity_status"] == "OFFICIAL_SCHEDULE_ONLY_NOT_ACTUAL_RECONCILED"


def test_source_routes_and_fomc_fail_closed():
    assert len(lane_b.URLS) == 34
    assert lane_b.URLS["fed_fomc_1994"].startswith("https://www.federalreserve.gov/")
    source = Path(lane_b.__file__).read_text()
    assert '"status": "UNAVAILABLE"' in source
    assert "OFFICIAL_ARCHIVE_BYTES_MATERIALIZED_PARSING_AMBIGUOUS" in source


def test_no_price_or_return_sql_or_fields():
    source = Path(lane_b.__file__).read_text()
    assert "SELECT trade_date" in source
    assert "adj_close" not in source
    assert "event_return" not in source
