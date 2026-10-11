"""Staff re-timing a schedule Black Bloc keeps the clock for: Set start and Shift the day."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from . import marathon as mt
from . import marathon_signals as sig
from .golive import parse_ts
from .timezones import zone

START = "start"
SHIFT = "shift"
MOVES = (START, SHIFT)
START_SET = "marathon.start_set"
DAY_SHIFTED = "marathon.day_shifted"
PICK_LIMIT = 25
DATED = ("%Y-%m-%d %H:%M", "%Y-%m-%d %I:%M %p", "%Y-%m-%d %I %p", "%Y-%m-%dT%H:%M")
CLOCKS = ("%H:%M", "%I:%M %p", "%I %p")
OFFSET = re.compile(r"(?:[+-]\d{2}:?\d{2}|Z)$")
MERIDIEM = re.compile(r"\s*([AP])\.?\s*M\.?$")
MINUS = ("−", "–", "—")


def current(row: Any) -> datetime | None:
    return parse_ts(mt._cell(row, "scheduled_at")) or sig.sheet_start(row)


def _plain(text: Any) -> str:
    found = " ".join(str(text or "").split()).upper()
    return MERIDIEM.sub(r" \1M", found)


def target_of(text: Any, tz_name: Any, near: datetime | None) -> datetime | None:
    """A typed time as a moment: a full date and time, an ISO moment with its offset, or a
    clock time on whichever day around `near` puts it closest."""
    raw = _plain(text)
    if not raw:
        return None
    where = zone(tz_name) or UTC
    if OFFSET.search(raw) and "T" in raw:
        return parse_ts(raw.replace("Z", "+00:00"))
    for shape in DATED:
        try:
            return datetime.strptime(raw, shape).replace(tzinfo=where).astimezone(UTC)
        except ValueError:
            continue
    if near is None:
        return None
    for shape in CLOCKS:
        try:
            clock = datetime.strptime(raw, shape).time()
        except ValueError:
            continue
        day = near.astimezone(where).date()
        options = [
            datetime.combine(day + timedelta(days=step), clock, where).astimezone(UTC)
            for step in (-1, 0, 1)
        ]
        return min(options, key=lambda one: abs(one - near))
    return None


def minutes_of(text: Any) -> int | None:
    raw = "".join(str(text or "").split())
    for sign in MINUS:
        raw = raw.replace(sign, "-")
    try:
        return int(raw)
    except ValueError:
        return None


def minutes_trouble(minutes: int | None, most: int) -> bool:
    return minutes is None or minutes == 0 or abs(minutes) > int(most)


def signed(minutes: int) -> str:
    return f"{minutes:+d}"


def chain_of(days: Any, row: Any) -> list[Any]:
    return sig.day_of(row, days) or [row]


def _after(chain: list[Any], row: Any) -> list[Any]:
    for index, one in enumerate(chain):
        if sig.same(one, row):
            return chain[index + 1 :]
    return []


def _before(chain: list[Any], row: Any) -> list[Any]:
    for index, one in enumerate(chain):
        if sig.same(one, row):
            return chain[:index]
    return []


def ahead_started(chain: list[Any], row: Any) -> Any:
    """The last run ahead of this one in its day that really began, or None."""
    begun = [one for one in _before(chain, row) if mt._cell(one, "actual_started_at")]
    return begun[-1] if begun else None


def anchors(chain: list[Any], row: Any, target: datetime) -> list[tuple[Any, datetime]]:
    """The run's new start, and each later start staff set that day carried by the same
    amount, so the gaps staff chose between them stay."""
    was = current(row)
    delta = target - was if was is not None else timedelta(0)
    found: list[tuple[Any, datetime]] = [(row, target)]
    for one in _after(chain, row):
        held = sig.staff_start(one)
        if held is not None and mt._cell(one, "state") == mt.UPCOMING:
            found.append((one, held + delta))
    return found


def pickable(rows: Any, limit: int = PICK_LIMIT) -> list[Any]:
    """Runs not yet started, soonest first, as many as one Discord picker holds."""
    waiting = [
        one
        for one in rows or ()
        if mt._cell(one, "state") == mt.UPCOMING and current(one) is not None
    ]
    waiting.sort(key=lambda one: (current(one), int(mt._cell(one, "order_no") or 0)))
    return waiting[:limit]


__all__ = [
    "DAY_SHIFTED",
    "MOVES",
    "PICK_LIMIT",
    "SHIFT",
    "START",
    "START_SET",
    "ahead_started",
    "anchors",
    "chain_of",
    "current",
    "minutes_of",
    "minutes_trouble",
    "pickable",
    "signed",
    "target_of",
]
