"""Database access plus small offline point-in-time data primitives."""

from .calendar import AcceptedSession, AcceptedSessionCalendar, CalendarIdentityError
from .reader import DatabaseInfo, QueryResult, database_info, query
from .sec_edgar import (
    CompanyFactsSnapshot,
    FilingIdentity,
    PointInTimeRatio,
    SecEdgarDataError,
    SecFact,
    adjust_share_fact_for_splits,
    build_pit_ratios,
    normalize_companyfacts_payload,
    select_facts_as_of,
)
from .source_identity import (
    CorporateActionIdentity,
    SourceIdentity,
    SourceIdentityError,
    select_corporate_action_revision,
)
from .writer import AppendResult, DataWriteError, append_rows

__all__ = [
    "AcceptedSession",
    "AcceptedSessionCalendar",
    "AppendResult",
    "CalendarIdentityError",
    "CompanyFactsSnapshot",
    "CorporateActionIdentity",
    "DatabaseInfo",
    "DataWriteError",
    "FilingIdentity",
    "PointInTimeRatio",
    "QueryResult",
    "SecEdgarDataError",
    "SecFact",
    "SourceIdentity",
    "SourceIdentityError",
    "adjust_share_fact_for_splits",
    "append_rows",
    "build_pit_ratios",
    "database_info",
    "normalize_companyfacts_payload",
    "query",
    "select_corporate_action_revision",
    "select_facts_as_of",
]
