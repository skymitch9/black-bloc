from __future__ import annotations

from typing import Any

import discord

from .button_block import ButtonLook, Words
from .button_block import look as button_look
from .button_block import said as button_said
from .settings_store import (
    BUTTON_BLOCK_DEFAULTS,
    MARATHON_BLOCK_ADDED_SAID,
    MARATHON_BLOCK_LABEL,
    MARATHON_BLOCK_REMOVED_SAID,
    MARATHON_BLOCK_TEXT,
    MARATHON_BLOCK_TITLE,
    MARATHON_BLOCK_UNSET_SAID,
    MARATHON_ROLE_ID,
)

BLOCK_HEAD = "marathonrole:toggle"
BLOCK_WORDS = Words(MARATHON_BLOCK_TITLE, MARATHON_BLOCK_TEXT, MARATHON_BLOCK_LABEL)
ROLE_REASON = "Black Bloc Marathon role block"
JOINED = "marathon.role_joined"
LEFT = "marathon.role_left"
FAILED = "marathon.role_failed"
UNSET = "unset"
GONE = "gone"
UNSAFE = "unsafe"
STAFF_PERMISSIONS = discord.Permissions.elevated() | discord.Permissions(mention_everyone=True)


def block_drawn(store: Any, guild_id: int) -> bool:
    """Drawn whether or not a role is picked: the press says so in words while none is."""
    return True


def block_look(store: Any, guild_id: int) -> ButtonLook:
    return button_look(store, guild_id, BLOCK_WORDS, BUTTON_BLOCK_DEFAULTS)


def role_id_of(store: Any, guild_id: int) -> int | None:
    found = store.get(guild_id, MARATHON_ROLE_ID)
    try:
        return int(found) if found else None
    except (TypeError, ValueError):
        return None


def unsafe(role: Any) -> bool:
    """A managed role, @everyone, or one carrying a staff permission is never self-served."""
    if getattr(role, "managed", False) or getattr(role, "is_default", lambda: False)():
        return True
    held = getattr(role, "permissions", None)
    return bool(held is not None and (held.value & STAFF_PERMISSIONS.value))


def usable_role(store: Any, guild: Any) -> tuple[Any, str]:
    """(the role, "") or (None, why not): unset, gone from the server, or unsafe to hand out."""
    role_id = role_id_of(store, guild.id)
    if role_id is None:
        return None, UNSET
    role = guild.get_role(role_id)
    if role is None:
        return None, GONE
    if unsafe(role):
        return None, UNSAFE
    return role, ""


def wears(member: Any, role: Any) -> bool:
    return any(int(getattr(one, "id", 0)) == int(role.id) for one in getattr(member, "roles", ()))


def said(store: Any, guild_id: int, key: str, role: Any = None) -> str:
    return button_said(
        store, guild_id, key, BUTTON_BLOCK_DEFAULTS, role=getattr(role, "name", "") or ""
    )


def added_said(store: Any, guild_id: int, role: Any) -> str:
    return said(store, guild_id, MARATHON_BLOCK_ADDED_SAID, role)


def removed_said(store: Any, guild_id: int, role: Any) -> str:
    return said(store, guild_id, MARATHON_BLOCK_REMOVED_SAID, role)


def unset_said(store: Any, guild_id: int) -> str:
    return said(store, guild_id, MARATHON_BLOCK_UNSET_SAID)


__all__ = [
    "BLOCK_HEAD",
    "BLOCK_WORDS",
    "FAILED",
    "GONE",
    "JOINED",
    "LEFT",
    "ROLE_REASON",
    "STAFF_PERMISSIONS",
    "UNSAFE",
    "UNSET",
    "added_said",
    "block_drawn",
    "block_look",
    "removed_said",
    "role_id_of",
    "unsafe",
    "unset_said",
    "usable_role",
    "wears",
]
