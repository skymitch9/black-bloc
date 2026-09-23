from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from .actionlog import log_action
from .directory import (
    Known,
    hidden_category_ids,
    in_an_ignored_category,
    known_of,
    remember,
)
from .logkinds import VIA_DISCORD, kind_via
from .panels import Outcome, refusal
from .rolemenus import STAFF_MODE
from .settings_store import (
    CHANNEL_REACH_CLEARED_KEY,
    CHANNEL_REACH_HIDDEN_KEY,
    CHANNEL_REACH_IGNORED_KEY,
    CHANNEL_REACH_NOTHING_KEY,
    CHANNEL_REACH_SHOWN_KEY,
)

log = logging.getLogger(__name__)

IGNORED_CODE = "ignored_category"


async def overrides_for(db: Any, guild_id: Any) -> dict[int, bool]:
    cur = await db.conn.execute(
        "SELECT channel_id, shown FROM channel_reach WHERE guild_id = ?", (int(guild_id),)
    )
    return {int(row["channel_id"]): bool(row["shown"]) for row in await cur.fetchall()}


async def override_for(db: Any, guild_id: Any, channel_id: Any) -> bool | None:
    cur = await db.conn.execute(
        "SELECT shown FROM channel_reach WHERE guild_id = ? AND channel_id = ?",
        (int(guild_id), int(channel_id)),
    )
    row = await cur.fetchone()
    return None if row is None else bool(row["shown"])


async def set_override(
    db: Any, guild_id: Any, channel_id: Any, shown: bool, *, by: Any = None, at: Any = None
) -> None:
    await db.conn.execute(
        "INSERT INTO channel_reach(guild_id, channel_id, shown, set_by, set_at) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(guild_id, channel_id) DO UPDATE SET "
        "shown = excluded.shown, set_by = excluded.set_by, set_at = excluded.set_at",
        (
            int(guild_id),
            int(channel_id),
            1 if shown else 0,
            int(by) if by else None,
            str(at or datetime.now(UTC).isoformat()),
        ),
    )
    await db.conn.commit()


async def clear_override(db: Any, guild_id: Any, channel_id: Any) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM channel_reach WHERE guild_id = ? AND channel_id = ?",
        (int(guild_id), int(channel_id)),
    )
    await db.conn.commit()
    return bool(cur.rowcount and cur.rowcount > 0)


async def openers_for(db: Any, guild_id: Any) -> frozenset[int]:
    """Every role a member can pick on a role menu; a staff-assigned menu hands out none."""
    cur = await db.conn.execute(
        "SELECT DISTINCT o.role_id FROM role_menu_options o JOIN role_menus m ON m.id = o.menu_id "
        "WHERE m.guild_id = ? AND m.mode != ?",
        (int(guild_id), STAFF_MODE),
    )
    return frozenset(int(row["role_id"]) for row in await cur.fetchall())


async def refresh(bot: Any, guild: Any) -> Known:
    """Read afresh and kept for the sync readers; a failed read keeps the last good one."""
    db = getattr(bot, "db", None)
    guild_id = getattr(guild, "id", None)
    if guild_id is None or db is None or not getattr(db, "is_connected", False):
        return known_of(bot, guild)
    try:
        known = Known(await openers_for(db, guild_id), await overrides_for(db, guild_id))
    except Exception as exc:
        log.warning("channel reach: unreadable, so the last read stands — %s", exc)
        return known_of(bot, guild)
    return remember(bot, guild, known)


def _words(bot: Any, guild: Any, key: str, channel: Any) -> str:
    from .chat_panel import words

    return words(bot.store, guild.id, key, channel=channel.name)


async def _found(bot: Any, guild: Any, channel_id: Any) -> tuple[Any, Outcome | None]:
    from .chat_panel import no_such_channel, text_channel

    channel = text_channel(guild, channel_id)
    if channel is None:
        return None, no_such_channel(bot, guild, channel_id)
    if in_an_ignored_category(channel, hidden_category_ids(bot, guild)):
        return channel, refusal(
            _words(bot, guild, CHANNEL_REACH_IGNORED_KEY, channel), IGNORED_CODE, 409
        )
    return channel, None


def _details(channel: Any, via: str, **extra: Any) -> dict[str, Any]:
    return {"channel_id": str(channel.id), "channel": channel.name, "via": via, **extra}


async def set_shown(
    bot: Any, guild: Any, actor: Any, channel_id: Any, shown: bool, *, via: str = VIA_DISCORD
) -> Outcome:
    """Staff's word on one channel, beating the member view either way."""
    from .chat_panel import actor_id

    channel, refused = await _found(bot, guild, channel_id)
    if refused is not None:
        return refused
    key = CHANNEL_REACH_SHOWN_KEY if shown else CHANNEL_REACH_HIDDEN_KEY
    if await override_for(bot.db, guild.id, channel.id) != bool(shown):
        await set_override(bot.db, guild.id, channel.id, bool(shown), by=actor_id(actor))
        await log_action(
            bot,
            guild,
            kind_via("chat.channel_reach_set", via),
            actor=actor,
            details=_details(channel, via, shown=bool(shown)),
        )
    await refresh(bot, guild)
    return Outcome(True, _words(bot, guild, key, channel), value=bool(shown))


async def back_to_rule(
    bot: Any, guild: Any, actor: Any, channel_id: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    channel, refused = await _found(bot, guild, channel_id)
    if refused is not None:
        return refused
    if not await clear_override(bot.db, guild.id, channel.id):
        return Outcome(True, _words(bot, guild, CHANNEL_REACH_NOTHING_KEY, channel))
    await log_action(
        bot,
        guild,
        kind_via("chat.channel_reach_cleared", via),
        actor=actor,
        details=_details(channel, via),
    )
    await refresh(bot, guild)
    return Outcome(True, _words(bot, guild, CHANNEL_REACH_CLEARED_KEY, channel))

