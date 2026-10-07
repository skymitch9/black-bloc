"""Check-in: the window, and who did not show when it closes."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def closes_at(opened_at: datetime, minutes: int) -> datetime:
    return opened_at + timedelta(minutes=int(minutes))


def due(closes: datetime | None, now: datetime) -> bool:
    return closes is not None and closes <= now


def no_shows(entrants: list[Any]) -> list[int]:
    """Everyone still in who has not checked in; they are removed and the bracket rebalances."""
    return [int(row["id"]) for row in entrants if not row["dropped"] and not row["checked_in"]]


def present(entrants: list[Any]) -> list[int]:
    return [int(row["id"]) for row in entrants if not row["dropped"] and row["checked_in"]]
