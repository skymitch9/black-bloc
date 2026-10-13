"""An unreadable marathon is archived, and tried again when its feed lists it."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from . import marathon_inbox as mi
from .golive import parse_ts
from .marathon import _cell
from .marathon_archive import STALE

CLOCK = "stale_clock_at"


def clock_of(marathon: Any) -> datetime | None:
    return parse_ts(_cell(marathon, CLOCK))


def failed_fields(marathon: Any, now: datetime, *, unpublished: bool) -> dict[str, Any]:
    """The clock starts at an answer, or at the first failure seen with no answer stored."""
    if unpublished or clock_of(marathon) is None:
        return {CLOCK: now.isoformat()}
    return {}


def counted(before: Any, after: Any) -> bool:
    return int(_cell(after, "fetch_failures") or 0) > int(_cell(before, "fetch_failures") or 0)


def is_stale(marathon: Any, now: datetime, *, reads: Any, hours: Any) -> bool:
    if marathon is None or int(reads or 0) <= 0:
        return False
    if not _cell(marathon, "active", 1) or mi.is_ignored(marathon):
        return False
    if int(_cell(marathon, "fetch_failures") or 0) < int(reads):
        return False
    since = clock_of(marathon)
    return since is not None and now - since >= timedelta(hours=max(0, int(hours or 0)))


def archived_details(marathon: Any, hours: Any) -> dict[str, Any]:
    return {
        "marathon_id": marathon["id"],
        "name": marathon["name"],
        "reason": str(_cell(marathon, "last_error") or "")[:300],
        "failures": int(_cell(marathon, "fetch_failures") or 0),
        "unreadable_since": _cell(marathon, CLOCK),
        "hours": int(hours or 0),
    }


def is_marked(archived: Any) -> bool:
    return _cell(archived, "archived_why") == STALE


def tries(known: Any, refs: Any) -> list[Any]:
    """The archived rows marked stale that a feed's list names; a live row hides its ref."""
    found = []
    for ref in dict.fromkeys(str(one) for one in refs):
        row = known.get(ref)
        if row is not None and _cell(row, "archived") and is_marked(row):
            found.append(row)
    return found


def restored_fields(archived: Any, now: datetime) -> dict[str, Any]:
    """A restore restarts the clock; one archived for staleness also starts its count again."""
    fields: dict[str, Any] = {CLOCK: now.isoformat()}
    if is_marked(archived):
        fields["fetch_failures"] = 0
    return fields


__all__ = [
    "CLOCK",
    "archived_details",
    "clock_of",
    "counted",
    "failed_fields",
    "is_marked",
    "is_stale",
    "restored_fields",
    "tries",
]
