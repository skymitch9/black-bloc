from __future__ import annotations

import logging
import time
from typing import Any

import discord
from discord.ext import commands

from ...actionlog import log_action
from ...chat import (
    GREETING,
    INSULT,
    ROUTE,
    answer_for,
    bare_greeting,
    guild_intents,
    invalidate,
    seed_defaults,
)
from ...emoji import tone_for, toned
from ...settings_store import CHAT_COOLDOWN_SECONDS

log = logging.getLogger(__name__)

MESSAGE_TYPES = (discord.MessageType.default, discord.MessageType.reply)
THREAD_TYPES = ("public_thread", "private_thread", "news_thread")
ON = "on"
LOG_KIND = "chat.insult"
ROUTE_KIND = "chat.route"
WAVE = "\U0001f44b"
WATCHED = (
    "chat_ignore_channels",
    "chat_greeting_reaction",
    "chat_reply_in_threads",
    "chat_route_ping_staff",
)
STAFF_NOTE = "{who} asked for a mod in {where}. {link}"


def mentions_bot(message: Any, me: Any) -> bool:
    """A direct @-mention of Black Bloc; @everyone and role pings are not one."""
    if me is None or getattr(message, "mention_everyone", False):
        return False
    return any(
        getattr(user, "id", None) == getattr(me, "id", None)
        for user in getattr(message, "mentions", ()) or ()
    )


def in_a_thread(channel: Any) -> bool:
    return str(getattr(getattr(channel, "type", None), "name", "")) in THREAD_TYPES


class Chat(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._answered: dict[int, float] = {}
        self._seeded: set[int] = set()

    async def cog_load(self) -> None:
        for key in WATCHED:
            self.bot.store.on_change(key, self._settings_changed)
        await self.seed_guilds()

    def _settings_changed(self, guild_id: int, key: str, value: Any, by: Any) -> None:
        invalidate(self.bot, guild_id)

    async def seed_guilds(self) -> None:
        """The code tables become editable rows the first time Black Bloc sees a server."""
        db = getattr(self.bot, "db", None)
        if db is None or not getattr(db, "is_connected", False):
            return
        for guild in getattr(self.bot, "guilds", ()) or ():
            if guild.id in self._seeded:
                continue
            try:
                made = await seed_defaults(db, guild.id)
            except Exception as exc:
                log.warning(
                    "chat: %s was not seeded — %s: %s", guild.id, type(exc).__name__, exc
                )
                continue
            self._seeded.add(guild.id)
            if made:
                invalidate(self.bot, guild.id)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self.seed_guilds()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self.seed_guilds()

    def cooldown_seconds(self, guild_id: int | None) -> int:
        """A DM has no guild to read the setting from, so it gets the registry's default."""
        if guild_id is None:
            return CHAT_COOLDOWN_SECONDS
        return int(self.bot.store.get(guild_id, "chat_cooldown_seconds") or 0)

    def cooling(self, user_id: int, seconds: int, now: float) -> bool:
        last = self._answered.get(user_id)
        return last is not None and now - last < seconds

    def welcome_here(self, guild_id: int | None, channel: Any) -> bool:
        if guild_id is None:
            return True
        ignored = self.bot.store.get(guild_id, "chat_ignore_channels") or []
        if getattr(channel, "id", None) in ignored:
            return False
        if in_a_thread(channel) and not self.bot.store.get(guild_id, "chat_reply_in_threads"):
            return False
        return True

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
        if not self.welcome_here(guild_id, channel):
            log.debug("chat: %s is a channel Black Bloc keeps out of", getattr(channel, "id", "?"))
            return
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
        answer = await answer_for(text, author, self.bot)
        if not answer.text:
            return
        if await self.waved_instead(message, text, guild_id, answer.intent):
            self._answered[user_id] = now
            return
        try:
            await message.reply(
                answer.text,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as exc:
            log.warning(
                "chat: %s could not be answered — %s: %s", user_id, type(exc).__name__, exc
            )
            return
        self._answered[user_id] = now
        log.info("chat: answered %s (%s)", user_id, answer.intent)
        if guild is None:
            return
        if answer.intent == INSULT:
            await log_action(
                self.bot, guild, LOG_KIND, actor=author, details={"intent": answer.intent}
            )
        if answer.kind == ROUTE:
            await self.tell_staff(guild, message, author)
            await log_action(
                self.bot, guild, ROUTE_KIND, actor=author, details={"intent": answer.intent}
            )

    async def waved_instead(
        self, message: Any, text: str, guild_id: int | None, intent: str
    ) -> bool:
        """A bare hello gets a wave rather than a sentence, when a server asks for that."""
        if intent != GREETING or guild_id is None:
            return False
        if not self.bot.store.get(guild_id, "chat_greeting_reaction"):
            return False
        if not bare_greeting(text, await guild_intents(self.bot, guild_id)):
            return False
        try:
            await message.add_reaction(toned(WAVE, tone_for(self.bot, guild_id)))
        except Exception as exc:
            log.warning("chat: the wave did not land — %s: %s", type(exc).__name__, exc)
            return False
        return True

    async def tell_staff(self, guild: Any, message: Any, author: Any) -> None:
        """One line in the staff channel, only when modmail is the way in and staff asked for it."""
        if not self.bot.store.get(guild.id, "chat_route_ping_staff"):
            return
        if not self.bot.store.get(guild.id, "modmail_enabled"):
            return
        channel_id = self.bot.store.get(guild.id, "staff_channel_id")
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel is None:
            log.warning("chat: no staff channel is set, so the route note was not posted")
            return
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(channel):
            log.debug("chat: test mode, so the route note was not posted in %s", channel_id)
            return
        try:
            await channel.send(
                STAFF_NOTE.format(
                    who=getattr(author, "mention", getattr(author, "id", "somebody")),
                    where=getattr(message.channel, "mention", "a channel"),
                    link=getattr(message, "jump_url", ""),
                ),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as exc:
            log.warning(
                "chat: the staff note was not posted — %s: %s", type(exc).__name__, exc
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Chat(bot))
