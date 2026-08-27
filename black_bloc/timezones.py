from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

log = logging.getLogger(__name__)

DEFAULT_TZ = "America/Phoenix"
START_FORMAT = "%Y-%m-%d %H:%M"
START_EXAMPLE = "2026-09-14 19:30"
CHOICE_LIMIT = 25
GAP = "gap"
AMBIGUOUS = "ambiguous"


def zone(name: Any) -> ZoneInfo | None:
    """The tzdata zone for a name, or None when nothing on this machine knows it."""
    try:
        return ZoneInfo(str(name))
    except (ZoneInfoNotFoundError, KeyError, ValueError, OSError):
        return None


def is_known(name: Any) -> bool:
    return zone(name) is not None


def known_timezones() -> list[str]:
    return sorted(available_timezones())


def suggest(text: Any, limit: int = CHOICE_LIMIT) -> list[str]:
    """The zone names an autocomplete offers for what has been typed so far."""
    typed = str(text or "").strip().lower().replace(" ", "_")
    names = known_timezones()
    if not typed:
        return names[:limit]
    starts = [n for n in names if n.lower().startswith(typed)]
    contains = [n for n in names if typed in n.lower() and n not in starts]
    return (starts + contains)[:limit]


def parse_start(text: Any, tz_name: Any) -> datetime | None:
    """`YYYY-MM-DD HH:MM` read in someone's own zone, returned as UTC."""
    zi = zone(tz_name)
    if zi is None:
        return None
    try:
        naive = datetime.strptime(str(text or "").strip(), START_FORMAT)
    except ValueError:
        return None
    return naive.replace(tzinfo=zi).astimezone(UTC)


def clock_trouble(text: Any, tz_name: Any) -> str | None:
    """Whether the clocks skipped that local time, or ran through it twice."""
    zi = zone(tz_name)
    if zi is None:
        return None
    try:
        naive = datetime.strptime(str(text or "").strip(), START_FORMAT)
    except ValueError:
        return None
    early = naive.replace(tzinfo=zi)
    if early.astimezone(UTC).astimezone(zi).replace(tzinfo=None) != naive:
        return GAP
    if early.utcoffset() != naive.replace(tzinfo=zi, fold=1).utcoffset():
        return AMBIGUOUS
    return None


def local_time(tz_name: Any, now: datetime | None = None) -> str:
    zi = zone(tz_name)
    when = now or datetime.now(UTC)
    if zi is None:
        return when.strftime(START_FORMAT)
    return when.astimezone(zi).strftime(START_FORMAT)


def unix(when: datetime) -> int:
    return int(when.timestamp())


def stamp(when: datetime) -> str:
    """HammerTime: every viewer reads the time in their own zone."""
    seconds = unix(when)
    return f"<t:{seconds}:F> (<t:{seconds}:R>)"


async def stored_timezone(db: Any, user_id: int) -> str | None:
    """What this member chose, or None when they never chose or the zone has since gone."""
    cur = await db.conn.execute("SELECT tz FROM user_timezones WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    if row is None:
        return None
    name = str(row["tz"])
    if not is_known(name):
        log.warning("timezones: %s has %r stored, which this machine cannot resolve", user_id, name)
        return None
    return name


async def get_timezone(db: Any, user_id: int) -> str:
    return await stored_timezone(db, user_id) or DEFAULT_TZ


async def set_timezone(db: Any, user_id: int, tz_name: str) -> None:
    await db.conn.execute(
        "INSERT OR REPLACE INTO user_timezones(user_id, tz, set_at) VALUES (?, ?, ?)",
        (user_id, tz_name, datetime.now(UTC).isoformat()),
    )
    await db.conn.commit()
