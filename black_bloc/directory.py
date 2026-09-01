from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

IGNORE_CATEGORIES_KEY = "chat_ignore_categories"
MODMAIL_CATEGORY_KEY = "modmail_category_id"
ARCHIVE_WORD = "archive"


def as_id(value: Any) -> int | None:
    try:
        return int(getattr(value, "id", value))
    except (TypeError, ValueError):
        return None


def is_archive(category: Any) -> bool:
    return ARCHIVE_WORD in str(getattr(category, "name", "") or "").casefold()


def hidden_category_ids(bot: Any, guild: Any) -> set[int]:
    """The modmail category, the ones staff listed, and nothing else by id."""
    found: set[int] = set()
    store = getattr(bot, "store", None)
    guild_id = getattr(guild, "id", None)
    if store is None or guild_id is None:
        return found
    try:
        listed = store.get(int(guild_id), IGNORE_CATEGORIES_KEY) or ()
        modmail = store.get(int(guild_id), MODMAIL_CATEGORY_KEY)
    except Exception as exc:
        log.warning("directory: the ignored categories were unreadable — %s", exc)
        return found
    for item in listed:
        number = as_id(item)
        if number is not None:
            found.add(number)
    number = as_id(modmail)
    if number is not None:
        found.add(number)
    return found


def everyone_sees(guild: Any, channel: Any) -> bool:
    """False whenever it cannot be worked out — a channel of unknown reach is a private one."""
    default = getattr(guild, "default_role", None)
    resolve = getattr(channel, "permissions_for", None)
    if default is None or resolve is None:
        return False
    try:
        perms = resolve(default)
    except Exception as exc:
        log.warning(
            "directory: %s would not say what @everyone sees — %s",
            getattr(channel, "id", "?"),
            exc,
        )
        return False
    return bool(getattr(perms, "view_channel", False))


def in_a_hidden_category(channel: Any, hidden: set[int]) -> bool:
    category = getattr(channel, "category", None)
    for number in (as_id(getattr(channel, "category_id", None)), as_id(category)):
        if number is not None and number in hidden:
            return True
    return is_archive(category)


def open_channels(bot: Any, guild: Any) -> list[Any]:
    """The text channels a member with no roles can read, and only those."""
    hidden = hidden_category_ids(bot, guild)
    found = []
    for channel in getattr(guild, "text_channels", ()) or ():
        if in_a_hidden_category(channel, hidden):
            continue
        if not everyone_sees(guild, channel):
            continue
        found.append(channel)
    return found
