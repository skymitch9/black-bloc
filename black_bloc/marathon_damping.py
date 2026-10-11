"""A far-off run's move waits until it reads the same again; public posts say the start last
published until then."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, NamedTuple

from . import marathon as mt
from .golive import parse_ts

PUBLISHED = "published_at"
PUBLISHED_END = "published_ends_at"
PENDING = "pending_at"
READS = "pending_reads"
COLUMNS = (PUBLISHED, PUBLISHED_END, PENDING, READS)
CLEARED: dict[str, Any] = dict.fromkeys(COLUMNS)
MIN_READS = 2

NOTHING = "nothing"
CLEAR = "clear"
PUBLISH = "publish"
HOLD = "hold"


class Step(NamedTuple):
    what: str
    reads: int = 0


def pending(row: Any) -> bool:
    return bool(mt._cell(row, PUBLISHED))


def waits(row: Any) -> bool:
    """Public posts still say an older start than the one stored."""
    return pending(row) and mt._cell(row, "state") == mt.UPCOMING


def shown_start(row: Any) -> Any:
    return mt._cell(row, PUBLISHED) if waits(row) else mt._cell(row, "scheduled_at")


def shown_end(row: Any) -> Any:
    return mt._cell(row, PUBLISHED_END) if waits(row) else mt._cell(row, "ends_at")


def same(one: Any, other: Any) -> bool:
    first, second = parse_ts(one), parse_ts(other)
    if first is None or second is None:
        return (one or None) == (other or None)
    return first == second


def moved_enough(before: Any, after: Any, minutes: int) -> bool:
    shift = mt.moved_by(before, after)
    return shift is not None and shift >= int(minutes)


def far(at: Any, now: datetime, minutes: int) -> bool:
    found = parse_ts(at)
    return found is not None and found - now > timedelta(minutes=int(minutes))


def damped(minutes: Any, now: datetime, *starts: Any) -> bool:
    """Off at 0; on only while every start named is further away than the window."""
    return int(minutes or 0) > 0 and all(far(one, now, int(minutes)) for one in starts)


def held_fields(row: Any, starts_at: Any) -> dict[str, Any]:
    """The columns of a move that waits: what was published is kept, the new start is the
    candidate, and a candidate that changed is counted from nothing."""
    kept = pending(row)
    return {
        PUBLISHED: mt._cell(row, PUBLISHED) if kept else mt._cell(row, "scheduled_at"),
        PUBLISHED_END: mt._cell(row, PUBLISHED_END) if kept else mt._cell(row, "ends_at"),
        PENDING: starts_at,
        READS: int(mt._cell(row, READS) or 0) if same(mt._cell(row, PENDING), starts_at) else 0,
    }


def reads_needed(raw: Any) -> int:
    try:
        return max(MIN_READS, int(raw))
    except (TypeError, ValueError):
        return MIN_READS


def step(row: Any, now: datetime, *, minutes: Any, needed: Any, read: bool) -> Step:
    """What one pass does with a run: a read counts towards the candidate, a tick only lets go."""
    if not pending(row):
        return Step(NOTHING)
    stored = mt._cell(row, "scheduled_at")
    if mt._cell(row, "state") != mt.UPCOMING or same(stored, mt._cell(row, PUBLISHED)):
        return Step(CLEAR)
    if not damped(minutes, now, mt._cell(row, PUBLISHED), stored):
        return Step(PUBLISH)
    if not same(stored, mt._cell(row, PENDING)):
        return Step(PUBLISH)
    if not read:
        return Step(NOTHING)
    reads = int(mt._cell(row, READS) or 0) + 1
    return Step(PUBLISH if reads >= reads_needed(needed) else HOLD, reads)


__all__ = [
    "CLEAR",
    "CLEARED",
    "COLUMNS",
    "HOLD",
    "MIN_READS",
    "NOTHING",
    "PENDING",
    "PUBLISH",
    "PUBLISHED",
    "PUBLISHED_END",
    "READS",
    "Step",
    "damped",
    "far",
    "held_fields",
    "moved_enough",
    "pending",
    "reads_needed",
    "same",
    "shown_end",
    "shown_start",
    "step",
    "waits",
]
