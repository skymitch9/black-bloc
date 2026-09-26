from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .golive import parse_ts
from .marathon import MarathonMove

ENDED = "ended"
STAFF = "staff"
REMOVED = "removed"
WHYS = (ENDED, STAFF, REMOVED)
WHY_WORDS = {ENDED: "ended", STAFF: "archived by staff", REMOVED: "removed by staff"}
BECAUSE_ARCHIVED = "marathon_archived"
UNPIN_BECAUSE = "archived"
PAGE_LIMIT = 50
PAGE_MAX = 200

ARCHIVE_ACTION = "archive"
ARCHIVE_LIST_ACTION = "archive_list"
ARCHIVE_MOVE = MarathonMove(ARCHIVE_ACTION, "Archive it", row=4)
ARCHIVE_LIST_MOVE = MarathonMove(ARCHIVE_LIST_ACTION, "Archive…", row=3)
ARCHIVE_TITLE = "Archive · {count}"
ARCHIVE_EMPTY = "Nothing is archived yet. A marathon moves here {days} day(s) after its last run."
ARCHIVE_LINE = "**{name}** · {source} · {dates} · {runs} run(s), {ours} BaF · {why} {when}"
PICK_ARCHIVED = "Pick an archived marathon to restore…"
RESTORE_LABEL = "Restore it"


def _cell(row: Any, key: str, fallback: Any = None) -> Any:
    if row is None:
        return fallback
    if isinstance(row, dict):
        return row.get(key, fallback)
    try:
        return row[key]
    except (IndexError, KeyError):
        return fallback


def end_of(marathon: Any) -> datetime | None:
    """The span end; a marathon with no ends_at never ends by itself."""
    ends = parse_ts(_cell(marathon, "ends_at"))
    if ends is None:
        return None
    starts = parse_ts(_cell(marathon, "starts_at"))
    return max(ends, starts) if starts is not None else ends


def is_ended(marathon: Any, now: datetime, after_days: int) -> bool:
    ends = end_of(marathon)
    return ends is not None and now > ends + timedelta(days=max(0, int(after_days)))


def first_ended(rows: Any, now: datetime, after_days: int) -> Any:
    """The one marathon a tick moves: the one that ended longest ago."""
    ended = [row for row in rows or () if is_ended(row, now, after_days)]
    return min(ended, key=lambda row: (end_of(row), int(row["id"]))) if ended else None


def clean_why(given: Any) -> str:
    return given if given in WHYS else ENDED


def page_of(limit: Any, offset: Any) -> tuple[int, int]:
    try:
        wanted = int(limit)
    except (TypeError, ValueError):
        wanted = PAGE_LIMIT
    try:
        skip = int(offset)
    except (TypeError, ValueError):
        skip = 0
    return (min(max(wanted, 1), PAGE_MAX), max(skip, 0))


__all__ = [
    "ARCHIVE_LIST_MOVE",
    "ARCHIVE_MOVE",
    "ENDED",
    "REMOVED",
    "STAFF",
    "WHYS",
    "WHY_WORDS",
    "clean_why",
    "end_of",
    "first_ended",
    "is_ended",
    "page_of",
]
