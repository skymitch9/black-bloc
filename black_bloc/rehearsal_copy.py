"""Post to test: the one sender of a copy into a rehearsal home, whatever the feature."""

from __future__ import annotations

from typing import Any

from .shadow import channel_of

TEST_MODE = "test_mode"
CHANNEL_GONE = "channel_gone"
MESSAGE_URL = "https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"


def reach(bot: Any, guild: Any, target: Any) -> tuple[Any, str | None]:
    """The rehearsal home's channel, or why a copy cannot go there."""
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(target):
        return None, TEST_MODE
    channel = channel_of(bot, guild, target)
    if channel is None:
        return None, CHANNEL_GONE
    return channel, None


async def deliver(channel: Any, payload: dict[str, Any], existing: Any = None) -> tuple[Any, bool]:
    """`(message, edited)`; Discord's own error is raised to the caller, who words it."""
    if existing is not None:
        await existing.edit(**payload)
        return existing, True
    return await channel.send(**payload), False


def message_url(guild: Any, channel: Any, message: Any) -> str:
    return MESSAGE_URL.format(
        guild_id=int(getattr(guild, "id", guild)),
        channel_id=int(getattr(channel, "id", channel)),
        message_id=int(getattr(message, "id", message)),
    )


__all__ = ["CHANNEL_GONE", "MESSAGE_URL", "TEST_MODE", "deliver", "message_url", "reach"]
