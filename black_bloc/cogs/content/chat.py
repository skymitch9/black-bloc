from __future__ import annotations

import logging
import time
from typing import Any

import discord
from discord.ext import commands

from ...actionlog import log_action
from ...chat import INSULT, classify, reply_for
from ...settings_store import CHAT_COOLDOWN_SECONDS

log = logging.getLogger(__name__)

MESSAGE_TYPES = (discord.MessageType.default, discord.MessageType.reply)
ON = "on"
LOG_KIND = "chat.insult"


def mentions_bot(message: Any, me: Any) -> bool:
    """A direct @-mention of Black Bloc; @everyone and role pings are not one."""
    if me is None or getattr(message, "mention_everyone", False):
        return False
    return any(
        getattr(user, "id", None) == getattr(me, "id", None)
        for user in getattr(message, "mentions", ()) or ()
    )


class Chat(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._answered: dict[int, float] = {}

    def cooldown_seconds(self, guild_id: int | None) -> int:
        """A DM has no guild to read the setting from, so it gets the registry's default."""
        if guild_id is None:
            return CHAT_COOLDOWN_SECONDS
        return int(self.bot.store.get(guild_id, "chat_cooldown_seconds") or 0)

    def cooling(self, user_id: int, seconds: int, now: float) -> bool:
        last = self._answered.get(user_id)
        return last is not None and now - last < seconds

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        me = getattr(self.bot, "user", None)
        author = getattr(message, "author", None)
        if author is None or getattr(author, "bot", False):
            return
        if getattr(message, "webhook_id", None) is not None:
            return
        if getattr(message, "type", None) not in MESSAGE_TYPES:
            return
        if not mentions_bot(message, me):
            return
        guild = getattr(message, "guild", None)
        guild_id = getattr(guild, "id", None)
        if guild_id is not None and self.bot.store.get(guild_id, "chat_mode") != ON:
            return
        channel = getattr(message, "channel", None)
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel):
            log.debug(
                "chat: test mode, so %s was not answered in channel %s",
                getattr(author, "id", "?"),
                getattr(channel, "id", "?"),
            )
            return
        now = time.monotonic()
        user_id = getattr(author, "id", 0)
        if self.cooling(user_id, self.cooldown_seconds(guild_id), now):
            return
        text = str(getattr(message, "content", "") or "")
        answer = reply_for(text, author, self.bot)
        if answer is None:
            return
        try:
            await message.reply(
                answer,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as exc:
            log.warning(
                "chat: %s could not be answered — %s: %s", user_id, type(exc).__name__, exc
            )
            return
        self._answered[user_id] = now
        intent = classify(text)
        log.info("chat: answered %s (%s)", user_id, intent)
        if intent == INSULT and guild is not None:
            await log_action(
                self.bot, guild, LOG_KIND, actor=author, details={"intent": intent}
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Chat(bot))
