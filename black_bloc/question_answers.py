from __future__ import annotations

import logging
import re
from typing import Any

import discord

from . import questions_store
from .settings_store import QUESTION_ANSWER_REACT, QUESTION_ANSWER_REACTION, QUESTION_CHANNEL

log = logging.getLogger(__name__)


def reply_target(message: Any) -> int | None:
    found = getattr(getattr(message, "reference", None), "message_id", None)
    return int(found) if found else None


def in_question_channel(store: Any, guild_id: int, message: Any) -> bool:
    wanted = store.get(guild_id, QUESTION_CHANNEL)
    found = getattr(getattr(message, "channel", None), "id", None)
    return bool(wanted) and found is not None and int(found) == int(wanted)


def names_bot(message: Any, me: Any) -> bool:
    """A typed <@id> of the bot in the text; Discord's reply ping does not count."""
    bot_id = getattr(me, "id", None)
    if bot_id is None:
        return False
    return re.search(rf"<@!?{int(bot_id)}>", str(getattr(message, "content", "") or "")) is not None


async def is_answer(bot: Any, message: Any) -> bool:
    """A Reply, in the question channel, to a posted weekly question."""
    guild_id = getattr(getattr(message, "guild", None), "id", None)
    target = reply_target(message)
    if guild_id is None or target is None:
        return False
    if not in_question_channel(bot.store, guild_id, message):
        return False
    db = getattr(bot, "db", None)
    if db is None or not getattr(db, "is_connected", False):
        return False
    try:
        return await questions_store.posted_message(db, guild_id, target) is not None
    except Exception as exc:
        log.warning("questions: a reply was not matched — %s: %s", type(exc).__name__, exc)
        return False


def reaction_of(store: Any, guild_id: int) -> str:
    if not store.get(guild_id, QUESTION_ANSWER_REACT):
        return ""
    return str(store.get(guild_id, QUESTION_ANSWER_REACTION) or "").strip()


async def react(bot: Any, message: Any) -> bool:
    """One reaction on an answer to the weekly question; a failure is a warning, never a crash."""
    guild_id = message.guild.id
    emoji = reaction_of(bot.store, guild_id)
    if not emoji:
        return False
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(message.channel):
        log.debug("questions: test mode, so the answer in %s was not reacted to", guild_id)
        return False
    try:
        await message.add_reaction(discord.PartialEmoji.from_str(emoji))
    except Exception as exc:
        log.warning("questions: an answer was not reacted to — %s: %s", type(exc).__name__, exc)
        return False
    log.debug("questions: reacted to answer %s", getattr(message, "id", "?"))
    return True
