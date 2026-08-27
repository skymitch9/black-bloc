from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from .birthdays import member_zone_name, stamp, upcoming
from .cogs.community.birthdays import rows_for_guild
from .cogs.community.events import events_by_status
from .cogs.community.role_menus import get_options, list_menus, picking_is_on
from .cogs.content.golive import open_sessions
from .events import APPROVED
from .presence import human_count
from .settings_store import resolved_staff_roles
from .timezones import DEFAULT_TZ, stored_timezone, zone

log = logging.getLogger(__name__)

BIRTHDAY_LIMIT = 3
NOBODY = "nobody"
NOTHING_HELD = "nothing from them yet"
SOME_MODS = "the mods"

STAMP = re.compile(r"<t:(-?\d{1,12})(?::[a-zA-Z])?>")
CLOCK_12 = re.compile(r"(?<![\d:])(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*([ap])\.?m\.?", re.IGNORECASE)
CLOCK_24 = re.compile(r"(?<![\d:])([01]?\d|2[0-3]):([0-5]\d)(?![\d:])")


def usable_db(bot: Any) -> Any:
    db = getattr(bot, "db", None)
    return db if db is not None and getattr(db, "is_connected", False) else None


def display_of(guild: Any, user_id: Any) -> str:
    member = guild.get_member(int(user_id)) if guild is not None else None
    found = getattr(member, "display_name", None) or getattr(member, "name", None)
    return str(found) if found else f"<@{int(user_id)}>"


def read_time(value: Any) -> datetime | None:
    try:
        when = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return when if when.tzinfo is not None else when.replace(tzinfo=UTC)


def relative(when: datetime) -> str:
    return f"<t:{int(when.timestamp())}:R>"


def clock(when: datetime) -> str:
    """`7:30 pm`, written the same way on every machine rather than by strftime."""
    hour = when.hour % 12 or 12
    return f"{hour}:{when.minute:02d} {'am' if when.hour < 12 else 'pm'}"


def wanted_time(text: Any) -> datetime | None:
    """A HammerTime stamp, a 12-hour clock or a 24-hour clock, read as an instant."""
    said = str(text or "")
    found = STAMP.search(said)
    if found is not None:
        try:
            return datetime.fromtimestamp(int(found.group(1)), UTC)
        except (OverflowError, OSError, ValueError):
            return None
    twelve = CLOCK_12.search(said)
    if twelve is not None:
        hour = int(twelve.group(1)) % 12
        if twelve.group(3).lower() == "p":
            hour += 12
        return at_local(hour, int(twelve.group(2) or 0))
    day = CLOCK_24.search(said)
    if day is not None:
        return at_local(int(day.group(1)), int(day.group(2)))
    return None


def at_local(hour: int, minute: int) -> datetime | None:
    """A bare clock time is today's, read in the server's own zone."""
    here = zone(DEFAULT_TZ)
    if here is None:
        return None
    today = datetime.now(here)
    return today.replace(hour=hour, minute=minute, second=0, microsecond=0).astimezone(UTC)


async def who_is_live(bot: Any, guild: Any, member: Any, text: Any) -> tuple[dict[str, Any], bool]:
    db = usable_db(bot)
    if db is None or guild is None:
        return {"who": NOBODY, "count": 0}, False
    named = []
    for row in await open_sessions(db, guild.id):
        who = display_of(guild, row["user_id"])
        named.append(f"{who} — <{row['url']}>" if row["url"] else who)
    if not named:
        return {"who": NOBODY, "count": 0}, False
    return {"who": ", ".join(named), "count": len(named)}, True


async def whats_next(bot: Any, guild: Any, member: Any, text: Any) -> tuple[dict[str, Any], bool]:
    db = usable_db(bot)
    if db is None or guild is None:
        return {}, False
    now = datetime.now(UTC)
    for row in await events_by_status(db, guild.id, (APPROVED,)):
        when = read_time(row["starts_at"])
        if when is None or when < now:
            continue
        return {
            "title": str(row["title"]),
            "when": relative(when),
            "where": event_place(row),
        }, True
    return {}, False


def event_place(row: Any) -> str:
    channel_id = row["card_channel_id"] if "card_channel_id" in row.keys() else None
    if channel_id:
        return f"<#{int(channel_id)}>"
    return str(row["location"] or "the usual place")


async def birthdays(bot: Any, guild: Any, member: Any, text: Any) -> tuple[dict[str, Any], bool]:
    db = usable_db(bot)
    if db is None or guild is None:
        return {}, False
    rows = [row for row in await rows_for_guild(db, guild.id) if row["opted_in"]]
    if not rows:
        return {}, False
    entries = [
        {
            "user_id": row["user_id"],
            "month": row["month"],
            "day": row["day"],
            "year": row["year"],
            "tz": await member_zone_name(db, row["user_id"]),
        }
        for row in rows
    ]
    found = upcoming(entries, limit=BIRTHDAY_LIMIT)
    if not found:
        return {}, False
    said = ", ".join(f"{display_of(guild, item.user_id)} {stamp(item.when)}" for item in found)
    return {"who": said, "count": len(found)}, True


async def head_count(bot: Any, guild: Any, member: Any, text: Any) -> tuple[dict[str, Any], bool]:
    count = human_count(guild)
    if count is None:
        return {}, False
    return {"count": count}, True


async def my_roles(bot: Any, guild: Any, member: Any, text: Any) -> tuple[dict[str, Any], bool]:
    db = usable_db(bot)
    if db is None or guild is None or not picking_is_on(bot, guild.id):
        return {}, False
    mine = {getattr(role, "id", None) for role in getattr(member, "roles", ()) or ()}
    offered, held = [], []
    for menu in await list_menus(db, guild.id):
        options = await get_options(db, menu["id"])
        if not options:
            continue
        offered.append(str(menu["title"] or menu["name"]))
        for option in options:
            role = guild.get_role(int(option["role_id"]))
            if role is not None and role.id in mine:
                held.append(str(role.name))
    if not offered:
        return {}, False
    return {
        "can_pick": ", ".join(offered),
        "have": ", ".join(held) or NOTHING_HELD,
        "count": len(offered),
    }, True


async def time_for_me(bot: Any, guild: Any, member: Any, text: Any) -> tuple[dict[str, Any], bool]:
    db = usable_db(bot)
    when = wanted_time(text)
    if db is None or when is None:
        return {}, False
    name = await stored_timezone(db, int(getattr(member, "id", 0) or 0))
    here = zone(name) if name else None
    if here is None:
        return {}, False
    return {
        "time": clock(when.astimezone(here)),
        "zone": str(name),
        "when": relative(when),
    }, True


async def need_a_mod(bot: Any, guild: Any, member: Any, text: Any) -> tuple[dict[str, Any], bool]:
    """Filled means modmail is answering; empty means the staff roles are the way in."""
    if guild is None:
        return {"roles": SOME_MODS}, False
    if bool(bot.store.get(guild.id, "modmail_enabled")):
        return {"roles": SOME_MODS}, True
    channel_id = bot.store.get(guild.id, "staff_channel_id")
    channel = guild.get_channel(channel_id) if channel_id else None
    names = [f"**{role.name}**" for role in resolved_staff_roles(guild, channel)]
    return {"roles": ", ".join(names) or SOME_MODS}, False


RESOLVERS = {
    "who_is_live": who_is_live,
    "whats_next": whats_next,
    "birthdays": birthdays,
    "head_count": head_count,
    "my_roles": my_roles,
    "time_for_me": time_for_me,
    "need_a_mod": need_a_mod,
}


async def tokens_for(
    bot: Any, guild: Any, member: Any, intent: str, text: Any
) -> tuple[dict[str, Any], bool]:
    """The live values one intent's line needs, and whether there was anything to say."""
    resolver = RESOLVERS.get(intent)
    if resolver is None:
        return {}, True
    try:
        return await resolver(bot, guild, member, text)
    except Exception as exc:
        log.warning("chat: %s could not be looked up — %s: %s", intent, type(exc).__name__, exc)
        return {}, False
