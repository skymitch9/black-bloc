"""A guild's roles, channels and overwrites read into one snapshot body; nothing about members."""

from __future__ import annotations

from typing import Any

import discord

from .structure import MEMBER, ROLE, clean

NO_ROLES = "Discord sent no roles at all, so there was nothing trustworthy to copy"
NO_CHANNELS = (
    "Discord sent no channels at all, so there was nothing trustworthy to copy. A server "
    "always has at least one, so this is Discord answering badly; try again in a few minutes"
)
MEMBER_TYPES = (discord.Member, discord.User)


class CaptureError(RuntimeError):
    """A capture that could not be trusted, said in words."""


def text_id(value: Any) -> str | None:
    found = getattr(value, "id", value)
    if found is None or isinstance(found, bool):
        return None
    try:
        return str(int(found))
    except (TypeError, ValueError):
        return None


def named(value: Any) -> str | None:
    """An enum's name, a plain value's text, and None for nothing."""
    if value is None:
        return None
    return str(getattr(value, "name", value))


def whole(value: Any) -> int | None:
    found = getattr(value, "value", value)
    if found is None or isinstance(found, bool):
        return None
    try:
        return int(found)
    except (TypeError, ValueError):
        return None


def flag(value: Any) -> bool | None:
    if callable(value):
        value = value()
    return None if value is None else bool(value)


def guild_row(guild: Any) -> dict[str, Any]:
    return {
        "id": text_id(guild),
        "name": named(getattr(guild, "name", None)),
        "verification_level": named(getattr(guild, "verification_level", None)),
        "default_notifications": named(getattr(guild, "default_notifications", None)),
        "system_channel_id": text_id(
            getattr(guild, "system_channel", None) or getattr(guild, "system_channel_id", None)
        ),
        "rules_channel_id": text_id(
            getattr(guild, "rules_channel", None) or getattr(guild, "rules_channel_id", None)
        ),
    }


def role_row(role: Any) -> dict[str, Any]:
    return {
        "id": text_id(role),
        "name": named(getattr(role, "name", None)),
        "color": whole(getattr(role, "color", None)) or 0,
        "permissions": whole(getattr(role, "permissions", None)) or 0,
        "position": whole(getattr(role, "position", None)) or 0,
        "hoist": bool(getattr(role, "hoist", False)),
        "mentionable": bool(getattr(role, "mentionable", False)),
        "managed": bool(getattr(role, "managed", False)),
    }


def tag_row(tag: Any) -> dict[str, Any]:
    emoji = getattr(tag, "emoji", None)
    return {
        "id": text_id(tag),
        "name": named(getattr(tag, "name", None)),
        "moderated": bool(getattr(tag, "moderated", False)),
        "emoji": str(emoji) if emoji else None,
    }


def target_kind(target: Any, target_id: str, role_ids: set[str]) -> str:
    """Discord's own word for what an overwrite is on; the role list only when it has none."""
    kind = getattr(target, "type", None) if isinstance(target, discord.Object) else type(target)
    if isinstance(kind, type) and issubclass(kind, discord.Role):
        return ROLE
    if isinstance(kind, type) and issubclass(kind, MEMBER_TYPES):
        return MEMBER
    return ROLE if target_id in role_ids else MEMBER


def overwrite_rows(channel: Any, role_ids: set[str]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for target, overwrite in (getattr(channel, "overwrites", None) or {}).items():
        target_id = text_id(target)
        if target_id is None:
            continue
        allow, deny = overwrite.pair()
        found.append(
            {
                "target_id": target_id,
                "target_type": target_kind(target, target_id, role_ids),
                "allow": whole(allow) or 0,
                "deny": whole(deny) or 0,
            }
        )
    return found


def channel_row(channel: Any, role_ids: set[str]) -> dict[str, Any]:
    return {
        "id": text_id(channel),
        "name": named(getattr(channel, "name", None)),
        "type": named(getattr(channel, "type", None)),
        "parent_id": text_id(getattr(channel, "category_id", None)),
        "position": whole(getattr(channel, "position", None)) or 0,
        "topic": getattr(channel, "topic", None) or None,
        "slowmode": whole(getattr(channel, "slowmode_delay", None)),
        "nsfw": flag(getattr(channel, "nsfw", None)),
        "bitrate": whole(getattr(channel, "bitrate", None)),
        "user_limit": whole(getattr(channel, "user_limit", None)),
        "tags": [tag_row(tag) for tag in getattr(channel, "available_tags", None) or ()],
        "overwrites": overwrite_rows(channel, role_ids),
    }


def capture(guild: Any, roles: Any, channels: Any) -> dict[str, Any]:
    """One snapshot body. `roles` and `channels` are whatever Discord just answered with."""
    role_rows = [role_row(role) for role in roles or ()]
    if not role_rows:
        raise CaptureError(NO_ROLES)
    role_ids = {row["id"] for row in role_rows}
    guild_id = text_id(guild)
    if guild_id is not None:
        role_ids.add(guild_id)
    channel_rows = [channel_row(channel, role_ids) for channel in channels or ()]
    if not channel_rows:
        raise CaptureError(NO_CHANNELS)
    return clean({"guild": guild_row(guild), "roles": role_rows, "channels": channel_rows})


__all__ = [
    "NO_CHANNELS",
    "NO_ROLES",
    "CaptureError",
    "capture",
    "channel_row",
    "guild_row",
    "overwrite_rows",
    "role_row",
    "tag_row",
]
