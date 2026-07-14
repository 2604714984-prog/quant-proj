"""Accepted-session scheduling helpers."""

from __future__ import annotations

from datetime import date
from typing import Sequence


def next_session(sessions: Sequence[date], signal_date: date) -> date:
    """Return the next accepted session, refusing an ambiguous calendar."""

    frozen = tuple(sessions)
    if frozen != tuple(sorted(frozen)) or len(frozen) != len(set(frozen)):
        raise ValueError("sessions must be strictly increasing and unique")
    try:
        index = frozen.index(signal_date)
    except ValueError as exc:
        raise ValueError("signal_date is not an accepted session") from exc
    if index + 1 >= len(frozen):
        raise ValueError("no accepted session exists after signal_date")
    return frozen[index + 1]
