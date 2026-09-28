from __future__ import annotations

import logging
from typing import Any

import discord
from discord.ext import commands

from ...actionlog import log_action
from ...settings_store import QUIET_BOT_PINS

log = logging.getLogger(__name__)


def pinned_by_this_bot(bot: Any, message: Any) -> bool:
    me = getattr(bot, "user", None)
    author = getattr(message, "author", None)
    return me is not None and getattr(author, "id", None) == me.id


def should_quiet(bot: Any, message: Any) -> bool:
    guild = getattr(message, "guild", None)
    if guild is None or getattr(message, "type", None) is not discord.MessageType.pins_add:
        return False
    if not pinned_by_this_bot(bot, message):
        return False
    return bool(bot.store.get(guild.id, QUIET_BOT_PINS))


def pin_details(message: Any, reason: str | None = None) -> dict[str, Any]:
    channel = message.channel
    found: dict[str, Any] = {
        "channel_id": channel.id,
        "channel": getattr(channel, "name", None),
        "notice_id": message.id,
    }
    pinned = getattr(getattr(message, "reference", None), "message_id", None)
    if pinned is not None:
        found["pinned_message_id"] = pinned
    parent = getattr(channel, "parent_id", None)
    if parent is not None:
        found["parent_id"] = parent
    if reason:
        found["reason"] = reason
    return found


def failure_reason(exc: discord.HTTPException) -> str:
    if isinstance(exc, discord.Forbidden):
        return f"Missing Manage Messages here (Discord said: {exc.text or exc.status})"
    if isinstance(exc, discord.NotFound):
        return "The notice was already gone"
    return f"Discord refused ({exc.status}): {exc.text or type(exc).__name__}"


class QuietPins(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.failed_channels: set[int] = set()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not should_quiet(self.bot, message):
            return
        try:
            await message.delete()
        except discord.HTTPException as exc:
            await self._failed(message, exc)
            return
        if self._may_log():
            await self._safely(
                log_action(
                    self.bot, message.guild, "quiet_pins.deleted", details=pin_details(message)
                )
            )

    async def _failed(self, message: Any, exc: discord.HTTPException) -> None:
        channel_id = message.channel.id
        if channel_id in self.failed_channels:
            return
        self.failed_channels.add(channel_id)
        reason = failure_reason(exc)
        log.warning("quiet pins: notice in channel %s not deleted — %s", channel_id, reason)
        if self._may_log():
            await self._safely(
                log_action(
                    self.bot,
                    message.guild,
                    "quiet_pins.delete_failed",
                    details=pin_details(message, reason),
                )
            )

    def _may_log(self) -> bool:
        db = getattr(self.bot, "db", None)
        return db is not None and db.is_connected

    async def _safely(self, writing: Any) -> None:
        try:
            await writing
        except Exception as exc:
            log.warning("quiet pins: log row not written — %s: %s", type(exc).__name__, exc)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(QuietPins(bot))
