from __future__ import annotations

import logging
import re
from typing import Any

log = logging.getLogger(__name__)

IGNORE_CATEGORIES_KEY = "chat_ignore_categories"
MODMAIL_CATEGORY_KEY = "modmail_category_id"
ARCHIVE_WORD = "archive"

DIRECTORY_BYTES = 4 * 1024
TOPIC_CHARS = 160

DIRECTORY_HEADING = (
    "## The channels of this server\n"
    "This is the whole list, and it is the only list. Point somebody at a channel from it or "
    "at nothing at all."
)
DIRECTORY_NONE = (
    "## The channels of this server\n"
    "You have not been given the channel list, so name no channel at all in this answer."
)

SPACES = re.compile(r"\s+")


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


def channel_names(bot: Any, guild: Any) -> set[str]:
    """Every name a reply is allowed to say, case-folded — the guard's whole vocabulary."""
    found = set()
    for channel in open_channels(bot, guild):
        name = str(getattr(channel, "name", "") or "").strip().casefold()
        if name:
            found.add(name)
    return found


def shorten(value: Any, limit: int) -> str:
    said = SPACES.sub(" ", str(value or "")).strip()
    return said if len(said) <= limit else f"{said[: limit - 1]}…"


def rows_for(channels: Any) -> list[tuple[str, str]]:
    found = []
    for channel in channels or ():
        name = str(getattr(channel, "name", "") or "").strip()
        if name:
            found.append((name, shorten(getattr(channel, "topic", ""), TOPIC_CHARS)))
    return found


def line_for(name: str, topic: str) -> str:
    return f"#{name} — {topic}" if topic else f"#{name}"


def spent(rows: Any) -> int:
    return sum(len(line_for(name, topic).encode("utf-8")) + 1 for name, topic in rows)


def within(rows: Any, budget: int = DIRECTORY_BYTES) -> list[tuple[str, str]]:
    """Over the cap the longest TOPIC goes first; a name only falls off once none are left."""
    kept = list(rows or ())
    while spent(kept) > budget and any(topic for _, topic in kept):
        at = max(range(len(kept)), key=lambda i: (len(kept[i][1]), -i))
        kept[at] = (kept[at][0], "")
    while kept and spent(kept) > budget:
        kept.pop()
    return kept


def directory_block(bot: Any, guild: Any, budget: int = DIRECTORY_BYTES) -> str:
    """The same visibility rules the ingest uses, rendered for the system stack."""
    rows = within(rows_for(open_channels(bot, guild)), budget)
    if not rows:
        return DIRECTORY_NONE
    lines = [line_for(name, topic) for name, topic in rows]
    return "\n".join([DIRECTORY_HEADING, *lines])
