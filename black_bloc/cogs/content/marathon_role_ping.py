"""The Marathon role on a marathon's ping-mark heads-up: the verdict, and the line staff read."""

from __future__ import annotations

from typing import Any

from ... import marathon as mt
from ... import marathon_ping as mp
from ... import marathon_role
from ... import marathon_role_ping as mrp
from ... import shadow as shadow_home
from ...settings_store import (
    MARATHON_PING_MINUTES_KEY,
    MARATHON_PUBLIC_REMINDERS_KEY,
    MARATHON_REMINDER_PINGS_KEY,
    MARATHON_ROLE_PING_LINE_ANNOUNCEMENTS_OFF_KEY,
    MARATHON_ROLE_PING_LINE_GONE_KEY,
    MARATHON_ROLE_PING_LINE_KEY_OFF_KEY,
    MARATHON_ROLE_PING_LINE_NOT_MENTIONABLE_KEY,
    MARATHON_ROLE_PING_LINE_ON_KEY,
    MARATHON_ROLE_PING_LINE_UNSET_KEY,
    MARATHON_ROLE_PINGS_KEY,
)
from .marathon import said_default
from .marathon_announce import announces

REASON_KEYS = (
    (mrp.ROLE_PINGS_OFF, MARATHON_ROLE_PINGS_KEY),
    (mrp.REMINDER_PINGS_OFF, MARATHON_REMINDER_PINGS_KEY),
    (mrp.PUBLIC_REMINDERS_OFF, MARATHON_PUBLIC_REMINDERS_KEY),
)
KEY_OF = dict(REASON_KEYS)
LINE_KEYS = {
    mrp.ANNOUNCEMENTS_OFF: MARATHON_ROLE_PING_LINE_ANNOUNCEMENTS_OFF_KEY,
    mrp.UNSET: MARATHON_ROLE_PING_LINE_UNSET_KEY,
    mrp.GONE: MARATHON_ROLE_PING_LINE_GONE_KEY,
    mrp.NOT_MENTIONABLE: MARATHON_ROLE_PING_LINE_NOT_MENTIONABLE_KEY,
}


def words(bot: Any, guild_id: int, key: str, /, **fields: Any) -> str:
    return mt.render(bot.store.get(guild_id, key), said_default(key), **fields).text


def may_mention_every_role(bot: Any, guild: Any, channel_id: Any = None) -> bool:
    """Mention Everyone where the heads-up posts, or server-wide when that channel is unknown."""
    me = getattr(guild, "me", None)
    if me is None:
        return False
    channel = shadow_home.channel_of(bot, guild, channel_id) if channel_id else None
    reader = getattr(channel, "permissions_for", None)
    held = reader(me) if callable(reader) else getattr(me, "guild_permissions", None)
    return bool(getattr(held, "mention_everyone", False))


def verdict_for(bot: Any, guild: Any, marathon: Any) -> mrp.Verdict:
    from .marathon_public_reminders import reminder_channel

    configured = marathon_role.role_id_of(bot.store, guild.id)
    getter = getattr(guild, "get_role", None)
    role = getter(configured) if configured is not None and callable(getter) else None
    return mrp.decide(
        switch_on=mp.pings_role(marathon),
        off=tuple((reason, bool(bot.store.get(guild.id, key))) for reason, key in REASON_KEYS),
        announces=announces(bot, guild.id, marathon),
        configured=configured,
        role=role,
        may_mention_every_role=may_mention_every_role(
            bot, guild, reminder_channel(bot, guild.id)
        ),
    )


def role_word(verdict: mrp.Verdict, *, mention: bool) -> str:
    if mention and verdict.configured:
        return f"<@&{int(verdict.configured)}>"
    return f"@{verdict.name}" if verdict.name else "the Marathon role"


def status_line(bot: Any, guild: Any, marathon: Any, *, mention: bool = True) -> str:
    """Empty while the marathon's ping switch is off: the switch itself says so."""
    verdict = verdict_for(bot, guild, marathon)
    if verdict.reason == mrp.SWITCH_OFF:
        return ""
    role = role_word(verdict, mention=mention)
    if verdict.mentions:
        return words(
            bot,
            guild.id,
            MARATHON_ROLE_PING_LINE_ON_KEY,
            role=role,
            minutes=int(bot.store.get(guild.id, MARATHON_PING_MINUTES_KEY)),
        )
    if verdict.reason in KEY_OF:
        return words(
            bot, guild.id, MARATHON_ROLE_PING_LINE_KEY_OFF_KEY, key=KEY_OF[verdict.reason]
        )
    return words(bot, guild.id, LINE_KEYS[verdict.reason], role=role)


def state_of(bot: Any, guild: Any, marathon: Any) -> dict[str, Any]:
    """What the dashboard draws under the ping switch."""
    verdict = verdict_for(bot, guild, marathon)
    return {
        "mentions": verdict.mentions,
        "reason": verdict.reason,
        "line": status_line(bot, guild, marathon, mention=False),
    }


__all__ = [
    "may_mention_every_role",
    "role_word",
    "state_of",
    "status_line",
    "verdict_for",
    "words",
]
