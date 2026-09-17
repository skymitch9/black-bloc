from __future__ import annotations

import logging
from typing import Any

import discord

from .actionlog import log_action
from .posts import get_post, row_value, shadow_channel_id, shadow_id

log = logging.getLogger(__name__)


async def message_is_there(channel: Any, message_id: int) -> bool:
    """A message somebody deleted by hand reads as gone; anything else leaves it alone."""
    try:
        await channel.fetch_message(message_id)
    except discord.NotFound:
        return False
    except Exception as exc:
        log.info("posted: could not look up message %s: %s", message_id, exc)
        return True
    return True


async def drop_message(
    bot: Any, guild: Any, channel: Any, message_id: int, *, would_kind: str
) -> bool:
    """Deleting a MESSAGE is a side effect `guard.py` never sees, so this one asks by hand."""
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        await log_action(
            bot,
            guild,
            would_kind,
            details={"channel_id": channel.id, "message_id": message_id},
        )
        return False
    partial = getattr(channel, "get_partial_message", None)
    try:
        if partial is None:
            await (await channel.fetch_message(message_id)).delete()
        else:
            await partial(message_id).delete()
    except discord.NotFound:
        return True
    except Exception as exc:
        log.info("posted: message %s stayed where it was: %s", message_id, exc)
        return False
    return True


async def overtaken_by(
    bot: Any, guild: Any, channel: Any, message_id: Any, slug: str
) -> int | None:
    """The followed post's message when it has landed UNDER the posted one.

    A snowflake counts up with the clock, so the newer id is the message further down. In
    `posts_mode = shadow` the rehearsal is the copy that counts, because that is the one in
    the guard's channel beside it."""
    if not slug or channel is None or not message_id:
        return None
    if not getattr(bot.db, "is_connected", False):
        return None
    row = await get_post(bot.db, guild.id, slug)
    if row is None:
        return None
    for where, found in (
        (row_value(row, "channel_id"), row_value(row, "message_id")),
        (shadow_channel_id(bot, guild), shadow_id(row)),
    ):
        if not where or not found:
            continue
        if int(where) == int(channel.id) and int(found) > int(message_id):
            return int(found)
    return None


__all__ = ["drop_message", "message_is_there", "overtaken_by"]
