from __future__ import annotations

import logging
import re
from typing import Any, NamedTuple

from .channel_notes import NOTE_CHARS

log = logging.getLogger(__name__)

IGNORE_CATEGORIES_KEY = "chat_ignore_categories"
MODMAIL_CATEGORY_KEY = "modmail_category_id"
VISIBILITY_ROLE_KEY = "chat_visibility_role_id"
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

IGNORED_CATEGORY = "ignored_category"
ARCHIVE = "archive"
NOT_VISIBLE = "not_visible"


class Preview(NamedTuple):
    block: str
    used: int
    cap: int
    trimmed: tuple[str, ...]


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


def visibility_role(bot: Any, guild: Any) -> Any:
    """Whose view of the server IS the map — the Member role here, since @everyone sees ~nothing."""
    store = getattr(bot, "store", None)
    guild_id = getattr(guild, "id", None)
    wanted = None
    if store is not None and guild_id is not None:
        try:
            wanted = as_id(store.get(int(guild_id), VISIBILITY_ROLE_KEY))
        except Exception as exc:
            log.warning("directory: the visibility role was unreadable — %s", exc)
    role = None
    if wanted and hasattr(guild, "get_role"):
        try:
            role = guild.get_role(wanted)
        except Exception as exc:
            log.warning("directory: the visibility role could not be resolved — %s", exc)
    return role if role is not None else getattr(guild, "default_role", None)


def everyone_sees(guild: Any, channel: Any, viewer: Any = None) -> bool:
    """False whenever it cannot be worked out — a channel of unknown reach is a private one."""
    default = viewer if viewer is not None else getattr(guild, "default_role", None)
    resolve = getattr(channel, "permissions_for", None)
    if default is None or resolve is None:
        return False
    try:
        perms = resolve(default)
    except Exception as exc:
        log.warning(
            "directory: %s would not say what %s sees — %s",
            getattr(channel, "id", "?"),
            getattr(default, "name", "the viewer role"),
            exc,
        )
        return False
    return bool(getattr(perms, "view_channel", False))


def in_an_ignored_category(channel: Any, hidden: set[int]) -> bool:
    category = getattr(channel, "category", None)
    for number in (as_id(getattr(channel, "category_id", None)), as_id(category)):
        if number is not None and number in hidden:
            return True
    return False


def why_hidden(guild: Any, channel: Any, hidden: set[int], viewer: Any) -> str | None:
    """The one test `open_channels` applies, spelled as the reason the page prints."""
    if in_an_ignored_category(channel, hidden):
        return IGNORED_CATEGORY
    if is_archive(getattr(channel, "category", None)):
        return ARCHIVE
    if not everyone_sees(guild, channel, viewer):
        return NOT_VISIBLE
    return None


def open_channels(bot: Any, guild: Any) -> list[Any]:
    """The text channels a plain verified member can read, and only those."""
    hidden = hidden_category_ids(bot, guild)
    viewer = visibility_role(bot, guild)
    return [
        channel
        for channel in getattr(guild, "text_channels", ()) or ()
        if why_hidden(guild, channel, hidden, viewer) is None
    ]


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


def description_of(channel: Any, notes: Any = None) -> str:
    """Staff's note beats the Discord topic; a channel with neither is just its name."""
    note = shorten((notes or {}).get(as_id(channel)), NOTE_CHARS)
    return note or shorten(getattr(channel, "topic", ""), TOPIC_CHARS)


def rows_for(channels: Any, notes: Any = None) -> list[tuple[str, str]]:
    found = []
    for channel in channels or ():
        name = str(getattr(channel, "name", "") or "").strip()
        if name:
            found.append((name, description_of(channel, notes)))
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


def directory_preview(
    bot: Any, guild: Any, notes: Any = None, budget: int = DIRECTORY_BYTES
) -> Preview:
    """The exact block the model is handed, with what it cost and whose words fell off."""
    wanted = rows_for(open_channels(bot, guild), notes)
    rows = within(wanted, budget)
    kept = set(rows)
    trimmed = tuple(name for name, said in wanted if said and (name, said) not in kept)
    if not rows:
        return Preview(DIRECTORY_NONE, 0, budget, trimmed)
    lines = [line_for(name, topic) for name, topic in rows]
    return Preview("\n".join([DIRECTORY_HEADING, *lines]), spent(rows), budget, trimmed)


def directory_block(
    bot: Any, guild: Any, notes: Any = None, budget: int = DIRECTORY_BYTES
) -> str:
    """The same visibility rules the ingest uses, rendered for the system stack."""
    return directory_preview(bot, guild, notes, budget).block
