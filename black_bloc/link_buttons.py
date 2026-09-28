from __future__ import annotations

import json
import logging
from typing import Any

from . import block_look as look
from .settings_store import (
    LINKS_MAX,
    POSTS_BLOCK_LINKS_CARD,
    POSTS_BLOCK_LINKS_ROWS,
    POSTS_BLOCK_LINKS_TEXT,
    POSTS_BLOCK_LINKS_TITLE,
    SettingError,
    checked_links,
)

log = logging.getLogger(__name__)

SAMPLE_ROWS = (("Our website", "https://example.org"), ("Schedule", "https://example.org/when"))


def rows_of(given: Any) -> list[tuple[str, str]]:
    """The stored list read back; a stored value that no longer checks draws no buttons."""
    try:
        text = checked_links(given if given is not None else "")
    except SettingError as exc:
        log.warning("link buttons: the stored list does not check (%s); drawing none", exc)
        return []
    if not text:
        return []
    return [(str(one["label"]), str(one["url"])) for one in json.loads(text)][:LINKS_MAX]


def shows_card(store: Any, guild_id: int, wanted: Any = "") -> bool:
    """`wanted` is an editor's unsaved tick ("on" / "off"); blank reads the key."""
    said = str(wanted or "").strip().lower()
    if said in ("on", "true", "1"):
        return True
    if said in ("off", "false", "0"):
        return False
    found = store.get(guild_id, POSTS_BLOCK_LINKS_CARD)
    return True if found is None else bool(found)


def links_look(
    store: Any, guild_id: int, rows: Any = None, *, card: Any = ""
) -> look.Look:
    """The staff-set buttons, in their order, under a card unless the card is switched off."""
    found = rows_of(store.get(guild_id, POSTS_BLOCK_LINKS_ROWS)) if rows is None else rows
    buttons = tuple(
        (str(label)[: look.LABEL_MAX], str(url)) for label, url in list(found)[:LINKS_MAX]
    )
    if not shows_card(store, guild_id, card):
        return look.Look("", "", buttons)
    return look.Look(
        look.word(store, guild_id, POSTS_BLOCK_LINKS_TITLE, look.TITLE_MAX),
        look.word(store, guild_id, POSTS_BLOCK_LINKS_TEXT),
        buttons,
    )


def links_parts(bot: Any, guild: Any, row: Any) -> Any:
    """Nothing is drawn while there is neither a card nor a button."""
    found = links_look(bot.store, guild.id)
    if not found.buttons and not found.title and not found.text:
        return None
    return look.parts_of(found)


__all__ = ["SAMPLE_ROWS", "links_look", "links_parts", "rows_of", "shows_card"]
