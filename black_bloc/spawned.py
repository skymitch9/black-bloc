"""The staff allow that every channel Black Bloc makes carries."""

from __future__ import annotations

from typing import Any

import discord

STAFF_REACH_KEY = "spawned_channels_staff_reach"


def staff_reach(overwrites: dict[Any, Any], staff_roles: Any, *, voice: bool) -> dict[Any, Any]:
    """Give each staff role view + manage, and connect for voice, on top of what is there."""
    for role in staff_roles or ():
        if role is None:
            continue
        overwrite = overwrites.get(role) or discord.PermissionOverwrite()
        overwrite.view_channel = True
        overwrite.manage_channels = True
        if voice:
            overwrite.connect = True
        overwrites[role] = overwrite
    return overwrites


def reach_roles(bot: Any, guild: Any, roles: Any = None) -> list[Any]:
    """The roles that allow is for: none while the key is off, the staff roles otherwise."""
    store = getattr(bot, "store", None)
    if store is None or guild is None:
        return []
    if not store.get(guild.id, STAFF_REACH_KEY):
        return []
    return list(roles if roles is not None else store.staff_roles(guild))
