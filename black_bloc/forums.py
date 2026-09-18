"""Forum-channel helpers shared by every feature that keeps one post per thing."""

from __future__ import annotations

from typing import Any

import discord

AUTO_ARCHIVE_MINUTES = 1440


def forum_tags(names: Any, emoji: dict[str, str]) -> list[discord.ForumTag]:
    """The tags a forum is made with; their ids live in the forum, never in a key."""
    return [
        discord.ForumTag(name=name, emoji=discord.PartialEmoji(name=emoji[name]))
        for name in names
    ]


def tag_named(forum: Any, name: Any) -> Any:
    for tag in getattr(forum, "available_tags", None) or ():
        if str(getattr(tag, "name", "")).lower() == str(name or "").lower():
            return tag
    return None


def forum_overwrites(guild: Any, category: Any) -> dict[Any, Any]:
    """The category's own overwrites, plus everything the bot needs to run a post."""
    overwrites = dict(getattr(category, "overwrites", None) or {})
    me = getattr(guild, "me", None)
    if me is not None:
        overwrites[me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_threads=True,
            send_messages_in_threads=True,
        )
    return overwrites


def thread_id_of(thread: Any) -> int | None:
    found = getattr(thread, "id", None)
    try:
        return int(found) if found is not None else None
    except (TypeError, ValueError):
        return None


def parent_id_of(thread: Any) -> int | None:
    found = getattr(thread, "parent_id", None) or getattr(
        getattr(thread, "parent", None), "id", None
    )
    try:
        return int(found) if found is not None else None
    except (TypeError, ValueError):
        return None


__all__ = [
    "AUTO_ARCHIVE_MINUTES",
    "forum_overwrites",
    "forum_tags",
    "parent_id_of",
    "tag_named",
    "thread_id_of",
]
