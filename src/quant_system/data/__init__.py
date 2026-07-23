"""Database access plus small offline point-in-time data primitives."""

from .calendar import (
    AcceptedSession,
    AcceptedSessionCalendar,
    CalendarIdentity,
    CalendarIdentityError,
    calendar_identity_sha256,
    session_dates_sha256,
    session_rows_sha256,
)
from .reader import DatabaseInfo, QueryResult, database_info, query
from .source_identity import (
    CorporateActionIdentity,
    SourceCaptureReceipt,
    SourceIdentity,
    SourceIdentityError,
    capture_file_bytes,
    capture_file_digest,
    capture_github_release_asset,
    capture_source_bytes,
    capture_source_file,
    require_trusted_source,
    require_provider_qualified_source,
    select_corporate_action_revision,
    select_source_revision,
)
from .writer import AppendResult, DataWriteError, append_rows

__all__ = [
    "AcceptedSession",
    "AcceptedSessionCalendar",
    "AppendResult",
    "CalendarIdentity",
    "CalendarIdentityError",
    "CorporateActionIdentity",
    "DatabaseInfo",
    "DataWriteError",
    "QueryResult",
    "SourceCaptureReceipt",
    "SourceIdentity",
    "SourceIdentityError",
    "append_rows",
    "capture_file_bytes",
    "capture_file_digest",
    "capture_github_release_asset",
    "capture_source_bytes",
    "capture_source_file",
    "calendar_identity_sha256",
    "database_info",
    "query",
    "require_trusted_source",
    "require_provider_qualified_source",
    "select_corporate_action_revision",
    "select_source_revision",
    "session_dates_sha256",
    "session_rows_sha256",
]
