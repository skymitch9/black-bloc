from __future__ import annotations

import hashlib
import json
from typing import Any, NamedTuple

import discord

from .settings_store import BLOCKS_LIVE_DEFAULTS

TITLE_MAX = 256
TEXT_MAX = 4000
LABEL_MAX = 80
ROW_WIDTH = 5
LINK_PREFIXES = ("https://", "http://")


class Look(NamedTuple):
    """What one block draws: a card (none when both are blank) and its link buttons."""

    title: str
    text: str
    buttons: tuple[tuple[str, str], ...] = ()

    def stamp(self) -> str:
        return hashlib.sha256(json.dumps(list(self), ensure_ascii=False).encode()).hexdigest()


def word(store: Any, guild_id: int, key: str, limit: int = TEXT_MAX) -> str:
    """A block word as saved, or the shipped one while it is blank."""
    text = str(store.get(guild_id, key) or "").strip()
    return (text or str(BLOCKS_LIVE_DEFAULTS.get(key) or ""))[:limit]


def number(store: Any, guild_id: int, key: str) -> int:
    found = store.get(guild_id, key)
    try:
        return int(found)
    except (TypeError, ValueError):
        return int(BLOCKS_LIVE_DEFAULTS[key])


def plain(text: Any) -> str:
    """Member-written words drawn as they are: no markdown, no link syntax, no mention."""
    said = discord.utils.escape_markdown(str(text or ""))
    said = discord.utils.escape_mentions(said)
    return said.replace("[", "\\[").replace("]", "\\]")


def clipped(text: Any, limit: int) -> str:
    said = " ".join(str(text or "").split())
    return said if len(said) <= limit else said[: max(limit - 1, 0)] + "…"


def linked(text: str, url: Any) -> str:
    found = str(url or "").strip()
    if not found.startswith(LINK_PREFIXES) or any(ch in found for ch in " ()<>"):
        return text
    return f"[{text}]({found})"


def lines_within(lines: list[str], limit: int = TEXT_MAX) -> str:
    """Whole lines only, as many as fit in one card."""
    kept: list[str] = []
    used = 0
    for line in lines:
        cost = len(line) + (1 if kept else 0)
        if used + cost > limit:
            break
        kept.append(line)
        used += cost
    return "\n".join(kept)


def embed_of(look: Look) -> discord.Embed | None:
    if not look.title and not look.text:
        return None
    return discord.Embed(title=look.title or None, description=look.text or None)


def view_of(look: Look) -> discord.ui.View | None:
    if not look.buttons:
        return None
    view = discord.ui.View(timeout=None)
    for at, (label, url) in enumerate(look.buttons):
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link, label=label, url=url, row=at // ROW_WIDTH
            )
        )
    return view


def parts_of(look: Look) -> tuple[Any, Any, str]:
    return embed_of(look), view_of(look), look.stamp()


__all__ = [
    "LABEL_MAX",
    "TEXT_MAX",
    "TITLE_MAX",
    "Look",
    "clipped",
    "embed_of",
    "lines_within",
    "linked",
    "number",
    "parts_of",
    "plain",
    "view_of",
    "word",
]
