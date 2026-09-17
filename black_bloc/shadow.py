"""Where a rehearsal goes, for every feature that has a shadow mode."""

from __future__ import annotations

from typing import Any

LOG_CHANNEL_KEY = "log_channel_id"


def as_channel_id(value: Any) -> int | None:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def guild_id_of(guild: Any) -> int:
    if isinstance(guild, int):
        return guild
    return int(getattr(guild, "id", 0) or 0)


def channel_id(bot: Any, guild: Any, *, log_key: str = LOG_CHANNEL_KEY) -> int | None:
    """Where a rehearsal GOES: the guard's own channel while it is installed, else the log."""
    guard = getattr(bot, "guard", None)
    wanted = getattr(guard, "test_channel_id", None) if guard is not None else None
    if not wanted:
        wanted = bot.store.get(guild_id_of(guild), log_key)
    return as_channel_id(wanted)


def channel_ids(bot: Any, guild: Any, *, log_key: str = LOG_CHANNEL_KEY) -> list[int]:
    """Where a rehearsal already IS: the cutover lifts the guard under a copy already up."""
    found: list[int] = []
    guard = getattr(bot, "guard", None)
    for wanted in (
        getattr(guard, "test_channel_id", None) if guard is not None else None,
        getattr(getattr(bot, "settings", None), "test_channel_id", None),
        bot.store.get(guild_id_of(guild), log_key),
    ):
        value = as_channel_id(wanted)
        if value is not None and value not in found:
            found.append(value)
    return found


__all__ = ["LOG_CHANNEL_KEY", "as_channel_id", "channel_id", "channel_ids", "guild_id_of"]
