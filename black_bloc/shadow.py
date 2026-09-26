"""Where a rehearsal goes, for every feature that has a shadow mode."""

from __future__ import annotations

import logging
from typing import Any

import discord

log = logging.getLogger(__name__)

LOG_CHANNEL_KEY = "log_channel_id"
REHEARSAL_KEY = "shadow_channel_id"
NOTE_KEY = "rehearsal_note"
NOTE_DEFAULT = "Rehearsal — this is where it would go: {channel}"
FEATURE_KEY = "{feature}_shadow_channel_id"


def feature_key(feature: str) -> str:
    return FEATURE_KEY.format(feature=feature)


def as_channel_id(value: Any) -> int | None:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def guild_id_of(guild: Any) -> int:
    if isinstance(guild, int):
        return guild
    return int(getattr(guild, "id", 0) or 0)


def _guard_channel(bot: Any) -> Any:
    guard = getattr(bot, "guard", None)
    return getattr(guard, "test_channel_id", None) if guard is not None else None


def _override(bot: Any, guild_id: int, feature: str | None) -> Any:
    return bot.store.get(guild_id, feature_key(feature)) if feature else None


def home_id(bot: Any, guild: Any, *, feature: str | None = None) -> int | None:
    """The rehearsal home the keys name, the feature's own first, and nothing else."""
    guild_id = guild_id_of(guild)
    for wanted in (_override(bot, guild_id, feature), bot.store.get(guild_id, REHEARSAL_KEY)):
        found = as_channel_id(wanted)
        if found is not None:
            return found
    return None


def channel_id(
    bot: Any, guild: Any, *, log_key: str = LOG_CHANNEL_KEY, feature: str | None = None
) -> int | None:
    """Where a rehearsal GOES: the feature's home, the rehearsal home, the guard's, the log."""
    guild_id = guild_id_of(guild)
    for wanted in (
        _override(bot, guild_id, feature),
        bot.store.get(guild_id, REHEARSAL_KEY),
        _guard_channel(bot),
        bot.store.get(guild_id, log_key),
    ):
        found = as_channel_id(wanted)
        if found is not None:
            return found
    return None


def channel_ids(
    bot: Any, guild: Any, *, log_key: str = LOG_CHANNEL_KEY, feature: str | None = None
) -> list[int]:
    """Where a rehearsal already IS: the key may have moved under a copy that is already up."""
    guild_id = guild_id_of(guild)
    found: list[int] = []
    for wanted in (
        _override(bot, guild_id, feature),
        bot.store.get(guild_id, REHEARSAL_KEY),
        _guard_channel(bot),
        getattr(getattr(bot, "settings", None), "test_channel_id", None),
        bot.store.get(guild_id, log_key),
    ):
        value = as_channel_id(wanted)
        if value is not None and value not in found:
            found.append(value)
    return found


def channel_of(bot: Any, guild: Any, wanted: Any) -> Any:
    if not wanted:
        return None
    found = bot.get_channel(int(wanted))
    if found is None and guild is not None:
        found = guild.get_channel(int(wanted))
    return found


async def find_copy(
    bot: Any,
    guild: Any,
    message_id: Any,
    *,
    log_key: str = LOG_CHANNEL_KEY,
    feature: str | None = None,
) -> tuple[Any, Any]:
    """A rehearsal copy and the channel it is in, hunted through every home it could be in."""
    if not message_id:
        return (None, None)
    for wanted in channel_ids(bot, guild, log_key=log_key, feature=feature):
        channel = channel_of(bot, guild, wanted)
        if channel is None:
            continue
        try:
            return (channel, await channel.fetch_message(int(message_id)))
        except discord.NotFound:
            continue
        except discord.HTTPException as exc:
            log.warning("shadow: a rehearsal copy could not be re-read — %s", exc)
    return (None, None)


def note_line(bot: Any, guild: Any, channel_words: str) -> str:
    """The one line a rehearsal copy carries above the real thing; blank means no line."""
    wording = str(bot.store.get(guild_id_of(guild), NOTE_KEY) or "").strip()
    if not wording:
        return ""
    try:
        return wording.format(channel=channel_words)
    except (IndexError, KeyError, ValueError):
        return wording


def teach_guard(bot: Any, guild_id: Any, value: Any) -> None:
    """The key is the one deliberate act that widens test mode, by exactly one channel."""
    guard = getattr(bot, "guard", None)
    if guard is None:
        return
    guard.rehearse_in(guild_id, as_channel_id(value))


def install(bot: Any) -> None:
    """Seed the guard from what is already stored, then follow the key for the rest of the run."""
    guard = getattr(bot, "guard", None)
    if guard is None:
        return
    for guild_id, value in bot.store.stored_values(REHEARSAL_KEY).items():
        teach_guard(bot, guild_id, value)

    async def _changed(guild_id: Any, key: str, value: Any, by: Any) -> None:
        teach_guard(bot, guild_id, value)

    bot.store.on_change(REHEARSAL_KEY, _changed)


__all__ = [
    "FEATURE_KEY",
    "LOG_CHANNEL_KEY",
    "NOTE_DEFAULT",
    "NOTE_KEY",
    "REHEARSAL_KEY",
    "as_channel_id",
    "channel_id",
    "channel_ids",
    "channel_of",
    "feature_key",
    "find_copy",
    "guild_id_of",
    "home_id",
    "install",
    "note_line",
    "teach_guard",
]
