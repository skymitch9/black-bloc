from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, NamedTuple

import discord

log = logging.getLogger(__name__)

TITLE_MAX = 256
TEXT_MAX = 4000
LABEL_MAX = 80
SAID_MAX = 2000


class Words(NamedTuple):
    title: str
    text: str
    label: str


class ButtonLook(NamedTuple):
    title: str
    text: str
    label: str

    def stamp(self) -> str:
        return hashlib.sha256(json.dumps(list(self), ensure_ascii=False).encode()).hexdigest()


def word(store: Any, guild_id: int, key: str, defaults: dict[str, Any], limit: int) -> str:
    """A block word as saved, or the shipped one while it is blank."""
    text = str(store.get(guild_id, key) or "").strip()
    return (text or str(defaults.get(key) or ""))[:limit]


def look(store: Any, guild_id: int, words: Words, defaults: dict[str, Any]) -> ButtonLook:
    return ButtonLook(
        word(store, guild_id, words.title, defaults, TITLE_MAX),
        word(store, guild_id, words.text, defaults, TEXT_MAX),
        word(store, guild_id, words.label, defaults, LABEL_MAX),
    )


def custom_id(head: str, guild_id: Any) -> str:
    return f"{head}:{int(guild_id)}"


def template(head: str) -> str:
    return rf"{re.escape(head)}:(?P<guild_id>[0-9]+)"


def embed_of(found: ButtonLook) -> discord.Embed:
    return discord.Embed(title=found.title, description=found.text)


def parts(found: ButtonLook, item: Any) -> tuple[discord.Embed, discord.ui.View, str]:
    """The (embed, view, stamp) a post carries: one card, one persistent button."""
    view = discord.ui.View(timeout=None)
    view.add_item(item)
    return embed_of(found), view, found.stamp()


def said(store: Any, guild_id: int, key: str, defaults: dict[str, Any], **values: Any) -> str:
    """A member's private answer from its key; a broken template falls back to the shipped one."""
    shipped = str(defaults.get(key) or "")
    typed = str(store.get(guild_id, key) or "").strip() or shipped
    try:
        return typed.format(**values)[:SAID_MAX]
    except Exception as exc:
        log.warning("button block: %s would not fill (%s); the shipped words were used", key, exc)
        return shipped.format(**values)[:SAID_MAX]


__all__ = [
    "LABEL_MAX",
    "SAID_MAX",
    "TEXT_MAX",
    "TITLE_MAX",
    "ButtonLook",
    "Words",
    "custom_id",
    "embed_of",
    "look",
    "parts",
    "said",
    "template",
    "word",
]
