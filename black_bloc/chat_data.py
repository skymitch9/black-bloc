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
NO_LINKS = "no links"
NOTHING_HELD = "nothing from them yet"
SOME_MODS = "the mods"

WHO_HAS = "who_has"
HOLDERS_SHOWN = 25
CLOSEST_SHOWN = 3
EVERYONE = "@everyone"
LEADING_FILLER = ("a", "an", "the", "our", "my", "your", "all", "of", "us", "role", "roles")
TRAILING_FILLER = ("role", "roles", "here", "now", "right", "please", "rn", "then", "again")

NO_ROLE_ASKED = (
    "I did not catch which role you meant. Name it — `who has the Leads role` — and I will count "
    "them."
)
NOT_IN_A_SERVER = "I can only count roles inside the server itself, and this is not in one."
NO_SUCH_ROLE = "there is no role here called **{asked}**, and nothing else comes close."
NO_SUCH_ROLE_BUT = "there is no role here called **{asked}**. The closest I have are {close}."
TOO_MANY_ROLES = "**{asked}** could be {close} — say which one and I will count it."
NOBODY_HOLDS_IT = "**{role}** has nobody in it right now."
AND_MORE = " …and {count} more"
ESCALATE_MODMAIL = " Any of them can help — or ask for a mod and I will point you at modmail."
ESCALATE_STAFF = " Any of them can help — or ask for a mod and I will name the staff to ask."

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
        return {"names": NOBODY, "links": NO_LINKS, "count": 0}, False
    named, linked = [], []
    for row in await open_sessions(db, guild.id):
        named.append(display_of(guild, row["user_id"]))
        if row["url"]:
            linked.append(f"<{row['url']}>")
    if not named:
        return {"names": NOBODY, "links": NO_LINKS, "count": 0}, False
    return {
        "names": ", ".join(named),
        "links": ", ".join(linked) or NO_LINKS,
        "count": len(named),
    }, True


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
            "channel": event_place(row),
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
    return {"list": said, "count": len(found)}, True


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
        "menus": ", ".join(offered),
        "roles": ", ".join(held) or NOTHING_HELD,
        "count": len(offered),
    }, True


def stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def role_key(value: Any) -> str:
    """A role name reduced to the words a member would type, singular and punctuation-free."""
    from .chat import normalise

    return " ".join(stem(word) for word in normalise(value).split())


def wanted_role(text: Any) -> str:
    """Whatever the member put after the trigger phrase, with the polite words taken off."""
    from .chat import DATA_INTENTS, normalise

    words = normalise(text)
    if not words:
        return ""
    padded = f" {words} "
    rest = ""
    for phrase in sorted((normalise(one) for one in DATA_INTENTS[WHO_HAS]), key=len, reverse=True):
        at = padded.find(f" {phrase} ")
        if at == -1:
            continue
        rest = padded[at + len(phrase) + 2 :].strip()
        break
    parts = rest.split()
    while parts and parts[0] in LEADING_FILLER:
        parts.pop(0)
    while parts and parts[-1] in TRAILING_FILLER:
        parts.pop()
    return " ".join(parts)


def named_roles(guild: Any) -> list[Any]:
    return [
        role
        for role in getattr(guild, "roles", ()) or ()
        if str(getattr(role, "name", "") or "").strip() not in ("", EVERYONE)
    ]


def matching_roles(roles: Any, asked: str) -> list[Any]:
    """Whole name, then the name as a word inside it, then any part of it."""
    from .chat import has_phrase

    key = role_key(asked)
    if not key:
        return []
    keyed = [(role, role_key(getattr(role, "name", ""))) for role in roles or ()]
    for found in (
        [role for role, name in keyed if name == key],
        [role for role, name in keyed if has_phrase(name, key)],
        [role for role, name in keyed if name and (key in name or name in key)],
    ):
        if found:
            return found
    return []


def closest_roles(roles: Any, asked: str) -> list[Any]:
    words = [word for word in role_key(asked).split() if word]
    scored = []
    for role in roles or ():
        name = role_key(getattr(role, "name", ""))
        near = sum(1 for word in words if word in name.split()) + sum(
            1 for word in words if word in name
        )
        if near:
            scored.append((-near, str(getattr(role, "name", "")), role))
    scored.sort()
    return [role for _, _, role in scored[:CLOSEST_SHOWN]]


def role_words(roles: Any, joiner: str) -> str:
    names = [f"**{getattr(role, 'name', '')}**" for role in roles or ()]
    if len(names) < 2:
        return "".join(names)
    return f"{', '.join(names[:-1])}{joiner}{names[-1]}"


def holders_of(role: Any) -> list[str]:
    """Bots are left out of the listing unless they are all there is."""
    members = list(getattr(role, "members", ()) or ())
    people = [one for one in members if not getattr(one, "bot", False)] or members
    names = [
        str(getattr(one, "display_name", "") or getattr(one, "name", "") or "").strip()
        for one in people
    ]
    return sorted((name for name in names if name), key=str.casefold)


def escalation(bot: Any, guild: Any, role: Any) -> str:
    channel_id = bot.store.get(guild.id, "staff_channel_id")
    channel = guild.get_channel(channel_id) if channel_id else None
    staff = {getattr(one, "id", None) for one in resolved_staff_roles(guild, channel)}
    if getattr(role, "id", None) not in staff:
        return ""
    return ESCALATE_MODMAIL if bot.store.get(guild.id, "modmail_enabled") else ESCALATE_STAFF


async def who_has(bot: Any, guild: Any, member: Any, text: Any) -> tuple[dict[str, Any], bool]:
    """The live gateway cache answers this one; nothing is stored and nobody is pinged."""
    if guild is None:
        return {"trouble": NOT_IN_A_SERVER}, False
    asked = wanted_role(text)
    if not asked:
        return {"trouble": NO_ROLE_ASKED}, False
    roles = named_roles(guild)
    found = matching_roles(roles, asked)
    if len(found) > 1:
        close = role_words(found[:CLOSEST_SHOWN], " or ")
        return {"trouble": TOO_MANY_ROLES.format(asked=asked, close=close)}, False
    if not found:
        close = closest_roles(roles, asked)
        if close:
            return {
                "trouble": NO_SUCH_ROLE_BUT.format(asked=asked, close=role_words(close, " and "))
            }, False
        return {"trouble": NO_SUCH_ROLE.format(asked=asked)}, False
    role = found[0]
    names = holders_of(role)
    if not names:
        return {"trouble": NOBODY_HOLDS_IT.format(role=str(role.name))}, False
    shown = names[:HOLDERS_SHOWN]
    left = len(names) - len(shown)
    return {
        "role": str(role.name),
        "count": len(names),
        "holders": ", ".join(shown),
        "more": AND_MORE.format(count=left) if left else "",
        "escalate": escalation(bot, guild, role),
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
    WHO_HAS: who_has,
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
