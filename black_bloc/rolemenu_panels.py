from __future__ import annotations

import logging
from typing import Any

import discord

from .actionlog import log_action
from .cogs.community.role_menus import (
    MODE_KEY,
    STAFF_MODE,
    clear_message,
    get_options,
    post_panel,
    posted_menus,
    unposted_menus,
)
from .command_visibility import controller as visibility_controller
from .logkinds import VIA_DISCORD, kind_via

log = logging.getLogger(__name__)

ON = "on"
UNPOSTED = "role_menu.unposted"
UNPOST_FAILED = "role_menu.unpost_failed"
WOULD_UNPOST = "role_menu.would_unpost"
REPOSTED = "role_menu.reposted"
REPOST_FAILED = "role_menu.repost_failed"
WOULD_REPOST = "role_menu.would_repost"
NO_CHANNEL = "the channel is not one Black Bloc can see any more"


def picking_is_on(bot: Any, guild_id: int) -> bool:
    return bot.store.get(guild_id, MODE_KEY) == ON


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


async def repost(bot: Any, menu: Any, actor: Any) -> bool:
    if menu["mode"] == STAFF_MODE:
        return False
    options = await get_options(bot.db, menu["id"])
    if not options:
        log.info("role menu %s: nothing to post, it has no roles on it", menu["name"])
        return False
    channel_id = menu["channel_id"]
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel_id):
        await note(bot, menu, WOULD_REPOST, actor)
        return False
    channel = bot.get_channel(channel_id)
    if channel is None:
        await note(bot, menu, REPOST_FAILED, actor, reason=NO_CHANNEL)
        return False
    try:
        message = await post_panel(bot, menu, options, channel)
    except discord.HTTPException as exc:
        await note(bot, menu, REPOST_FAILED, actor, reason=str(exc))
        return False
    await note(bot, menu, REPOSTED, actor, message_id=message.id)
    return True


async def each(bot: Any, menus: Any, actor: Any, action: Any) -> int:
    done = 0
    for menu in menus:
        try:
            if await action(bot, menu, actor):
                done += 1
        except Exception as exc:
            log.error(
                "role menu %s: %s failed — %s: %s",
                menu["name"],
                action.__name__,
                type(exc).__name__,
                exc,
            )
    return done


async def reconcile(bot: Any, *, actor: Any = None, reposting: bool = True) -> dict[str, int]:
    """Match the posted panels to the stored mode; menu rows and options are never touched."""
    db = getattr(bot, "db", None)
    done = {"unposted": 0, "reposted": 0}
    if db is None or not db.is_connected:
        return done
    down = [row for row in await posted_menus(db) if not picking_is_on(bot, row["guild_id"])]
    done["unposted"] = await each(bot, down, actor, unpost)
    if reposting:
        up = [row for row in await unposted_menus(db) if picking_is_on(bot, row["guild_id"])]
        done["reposted"] = await each(bot, up, actor, repost)
    if done["unposted"] or done["reposted"]:
        log.info(
            "role menu panels: %d taken down, %d posted again", done["unposted"], done["reposted"]
        )
    return done


class PanelSync:
    def __init__(self, bot: Any) -> None:
        self.bot = bot
        self.installed = False
        self.ready = False

    async def run(self, actor: Any = None) -> dict[str, int]:
        if not self.ready:
            return {"unposted": 0, "reposted": 0}
        return await reconcile(self.bot, actor=actor)


def controller(bot: Any) -> PanelSync:
    found = getattr(bot, "rolemenu_panels", None)
    if found is None:
        found = PanelSync(bot)
        bot.rolemenu_panels = found
    return found


def install(bot: Any) -> PanelSync:
    """Register the one trigger path — every `rolemenu_mode` write — on the shared debounce."""
    found = controller(bot)
    if found.installed:
        return found
    flips = visibility_controller(bot)
    flips.also(found.run)
    bot.store.on_change(MODE_KEY, lambda guild_id, key, value, by: flips.schedule(actor=by))
    found.installed = True
    return found


async def panels_on_boot(bot: Any) -> dict[str, int]:
    """A restart mid-flip converges: panels left up while off come down, none are posted."""
    found = controller(bot)
    found.ready = True
    return await reconcile(bot, reposting=False)
