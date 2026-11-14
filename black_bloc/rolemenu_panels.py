from __future__ import annotations

import logging
from typing import Any

import discord

from .actionlog import log_action
from .cogs.community.role_menus import clear_message
from .logkinds import VIA_DISCORD, kind_via

log = logging.getLogger(__name__)

UNPOSTED = "role_menu.unposted"
UNPOST_FAILED = "role_menu.unpost_failed"
WOULD_UNPOST = "role_menu.would_unpost"
NO_CHANNEL = "the channel is not one Black Bloc can see any more"


def guild_of(bot: Any, guild_id: int) -> Any:
    return bot.get_guild(guild_id) or discord.Object(id=guild_id)


async def note(
    bot: Any, menu: Any, kind: str, actor: Any, *, via: str = VIA_DISCORD, **extra: Any
) -> None:
    try:
        await log_action(
            bot,
            guild_of(bot, menu["guild_id"]),
            kind_via(kind, via),
            actor=actor,
            details={
                "menu": menu["name"],
                "channel_id": menu["channel_id"],
                "via": via,
                **extra,
            },
        )
    except Exception as exc:
        log.warning("role menu panels: %s not logged — %s: %s", kind, type(exc).__name__, exc)


async def delete_panel(channel: Any, message_id: int) -> None:
    partial = getattr(channel, "get_partial_message", None)
    if partial is None:
        await (await channel.fetch_message(message_id)).delete()
        return
    await partial(message_id).delete()


async def unpost(bot: Any, menu: Any, actor: Any, *, via: str = VIA_DISCORD) -> bool:
    channel_id = menu["channel_id"]
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel_id):
        await note(bot, menu, WOULD_UNPOST, actor, via=via, message_id=menu["message_id"])
        return False
    channel = bot.get_channel(channel_id) if channel_id else None
    if channel is None:
        await note(bot, menu, UNPOST_FAILED, actor, via=via, reason=NO_CHANNEL)
        return False
    try:
        await delete_panel(channel, menu["message_id"])
    except discord.NotFound:
        log.info("role menu %s: its panel was already gone", menu["name"])
    except discord.HTTPException as exc:
        await note(bot, menu, UNPOST_FAILED, actor, via=via, reason=str(exc))
        return False
    await clear_message(bot.db, menu["id"])
    await note(bot, menu, UNPOSTED, actor, via=via, message_id=menu["message_id"])
    return True
