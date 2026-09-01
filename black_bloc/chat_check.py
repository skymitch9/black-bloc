from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

HOME_CHANNEL_KEY = "chat_home_channel_id"
FIXED_KIND = "chat.reply_reference_fixed"

GONE = "\x00"
EVERYONE = "everyone"
HERE = "here"
ALWAYS_A_ROLE: frozenset[str] = frozenset({EVERYONE, HERE})

CHANNEL_TOKEN = re.compile(r"(?<![\w<:/#])#([A-Za-z0-9_-]{2,100})")
ROLE_TOKEN = re.compile(r"(?<![\w<:/@])@([A-Za-z][A-Za-z0-9_'-]{0,63})")
HAS_A_LETTER = re.compile(r"[A-Za-z]")

FILLER = (
    "in",
    "at",
    "to",
    "into",
    "onto",
    "on",
    "over",
    "from",
    "via",
    "under",
    "inside",
    "through",
    "toward",
    "towards",
)
FILLER_BEFORE = re.compile(rf"\s+\b(?:{'|'.join(FILLER)})\b(?=\s*{GONE})", re.IGNORECASE)
JOINER_LEFT = re.compile(r"\s+\b(?:or|and)\b(?=\s*(?:[.,;:!?]|$))", re.IGNORECASE)
SPACE_BEFORE = re.compile(r"\s+([.,;:!?])")
SPACES = re.compile(r"[ \t]{2,}")
EMPTY_BRACKETS = re.compile(r"\(\s*\)")


@dataclass
class Checked:
    text: str
    channels: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)

    @property
    def fixed(self) -> int:
        return len(self.channels) + len(self.roles)


def role_words(guild: Any) -> set[str]:
    """Whole role names and their first words — `@Aunties` stands for `Aunties / Uncles`."""
    found = set(ALWAYS_A_ROLE)
    for role in getattr(guild, "roles", ()) or ():
        name = str(getattr(role, "name", "") or "").strip().casefold()
        if not name or name == "@everyone":
            continue
        found.add(name)
        first = name.split()[0] if name.split() else ""
        if first:
            found.add(first)
    return found


def home_mention(bot: Any, guild: Any) -> str:
    store = getattr(bot, "store", None)
    guild_id = getattr(guild, "id", None)
    if store is None or guild_id is None:
        return ""
    try:
        channel_id = store.get(int(guild_id), HOME_CHANNEL_KEY)
    except Exception as exc:
        log.warning("chat: the home channel was unreadable — %s", exc)
        return ""
    return f"<#{int(channel_id)}>" if channel_id else ""


def tidy(said: str) -> str:
    said = FILLER_BEFORE.sub("", said)
    said = said.replace(GONE, "")
    said = JOINER_LEFT.sub("", said)
    said = EMPTY_BRACKETS.sub("", said)
    said = SPACES.sub(" ", said)
    said = SPACE_BEFORE.sub(r"\1", said)
    return "\n".join(line.strip() for line in said.splitlines()).strip()


def checked(
    text: Any, *, channels: Any = (), roles: Any = (), people: Any = (), home: str = ""
) -> Checked:
    """Anything the reply names that the server does not have is swapped out or taken out."""
    said = str(text or "")
    known_channels = {str(one).casefold() for one in channels or ()}
    known_roles = {str(one).casefold() for one in roles or ()}
    known_people = {str(one).casefold() for one in people or ()}
    found = Checked(text=said)

    def channel(match: re.Match[str]) -> str:
        name = match.group(1)
        if name.casefold() in known_channels or not HAS_A_LETTER.search(name):
            return match.group(0)
        found.channels.append(name)
        return home or GONE

    def role(match: re.Match[str]) -> str:
        name = match.group(1)
        folded = name.casefold()
        if folded in known_roles or folded in known_people:
            return match.group(0)
        found.roles.append(name)
        return GONE

    said = CHANNEL_TOKEN.sub(channel, said)
    said = ROLE_TOKEN.sub(role, said)
    found.text = tidy(said) if GONE in said else said
    return found


def check_reply(bot: Any, guild: Any, text: Any, people: Any = ()) -> Checked:
    """The live names, then the swap. A guild that cannot be read knows no names at all."""
    from .directory import channel_names

    try:
        channels = channel_names(bot, guild)
    except Exception as exc:
        log.warning("chat: the channel names were not read — %s: %s", type(exc).__name__, exc)
        channels = set()
    return checked(
        text,
        channels=channels,
        roles=role_words(guild),
        people=people,
        home=home_mention(bot, guild),
    )
