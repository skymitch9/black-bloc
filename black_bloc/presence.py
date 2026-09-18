from __future__ import annotations

import logging
from typing import Any

import discord

from .actionlog import log_action
from .settings_store import (
    BOOT_STATUS_MODE,
    BOOT_STATUS_TEXT_KEY,
    SHUTDOWN_STATUS_TEXT_KEY,
)

log = logging.getLogger(__name__)

BIO_LIMIT = 400
STATUS_LIMIT = 128

NO_GUILD = "presence: no server in the cache yet, so the status and the About Me were left alone"
NO_COUNT = "presence: server %s has no member count yet, so the status was left alone"
NO_BIO = "presence: bot_bio is empty, so the About Me was left alone rather than wiped"
BIO_REFUSED = (
    "presence: Discord would not take the About Me, so it still says whatever it said before "
    "— %s: %s"
)
BOOT_REFUSED = "presence: the shutdown status was not set — %s: %s"
GREEN_REFUSED = "presence: the boot status could not be cleared — %s: %s"


def status_text(prefix: Any, count: int) -> str:
    """`Cookout attendees: 412`, trimmed to what a custom status will hold."""
    return f"{str(prefix or '').strip()}: {count}"[:STATUS_LIMIT]


def bio_text(raw: Any) -> str:
    return str(raw or "").strip()[:BIO_LIMIT]


def human_count(guild: Any) -> int | None:
    total = getattr(guild, "member_count", None)
    if isinstance(total, bool) or not isinstance(total, int):
        return None
    bots = sum(1 for member in getattr(guild, "members", ()) or () if getattr(member, "bot", False))
    return max(total - bots, 0)


def status_guild(bot: Any) -> Any:
    guild_id = getattr(getattr(bot, "settings", None), "dev_guild_id", None)
    found = bot.get_guild(guild_id) if guild_id else None
    if found is not None:
        return found
    return next(iter(getattr(bot, "guilds", ()) or ()), None)


async def update_status(bot: Any) -> str | None:
    """Set the custom status to the prefix and the human head count; None when it cannot."""
    guild = status_guild(bot)
    if guild is None:
        log.info(NO_GUILD)
        return None
    count = human_count(guild)
    if count is None:
        log.warning(NO_COUNT, getattr(guild, "id", "?"))
        return None
    text = status_text(bot.store.get(guild.id, "status_prefix"), count)
    await bot.change_presence(
        status=discord.Status.online, activity=discord.CustomActivity(name=text)
    )
    return text


def _setting(store: Any, guild_id: int | None, key: str) -> Any:
    return store.default(key) if guild_id is None else store.get(guild_id, key)


def _red(store: Any, guild_id: int | None, key: str) -> dict[str, Any]:
    if _setting(store, guild_id, BOOT_STATUS_MODE) != "on":
        return {}
    said = str(_setting(store, guild_id, key) or "").strip()[:STATUS_LIMIT]
    if not said:
        return {"status": discord.Status.dnd}
    return {"status": discord.Status.dnd, "activity": discord.CustomActivity(name=said)}


def boot_presence(store: Any, guild_id: int | None = None) -> dict[str, Any]:
    """Do Not Disturb and the boot sentence, or nothing at all when the mode is off."""
    return _red(store, guild_id, BOOT_STATUS_TEXT_KEY)


def shutdown_presence(store: Any, guild_id: int | None = None) -> dict[str, Any]:
    """The same, with the sentence a planned shutdown carries."""
    return _red(store, guild_id, SHUTDOWN_STATUS_TEXT_KEY)


async def go_green(bot: Any) -> None:
    """Online with no sentence, so a ready bot with no head count to show is not left red."""
    try:
        await bot.change_presence(status=discord.Status.online)
    except Exception as exc:
        log.warning(GREEN_REFUSED, type(exc).__name__, exc)


async def ensure_bio(bot: Any) -> bool:
    """Make the application's description match `bot_bio`; True when it had to be changed."""
    guild = status_guild(bot)
    if guild is None:
        log.info(NO_GUILD)
        return False
    wanted = bio_text(bot.store.get(guild.id, "bot_bio"))
    if not wanted:
        log.warning(NO_BIO)
        return False
    try:
        app = await bot.application_info()
        if (getattr(app, "description", None) or "") == wanted:
            return False
        await app.edit(description=wanted)
    except Exception as exc:
        log.warning(BIO_REFUSED, type(exc).__name__, exc)
        return False
    log.info("presence: About Me set to %r", wanted)
    await log_action(bot, guild, "presence.bio_set", details={"bio": wanted})
    return True
