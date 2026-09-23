from __future__ import annotations

import re
from typing import Any

ANY_MENTION = re.compile(r"<(#|@&|@!?)(\d+)>")
CHANNEL = "#"
ROLE = "@&"


def looked_up(guild: Any, getter: str, found_id: int) -> Any:
    find = getattr(guild, getter, None)
    return find(found_id) if callable(find) else None


def text_of(value: Any) -> str:
    return value if isinstance(value, str) else ""


def resolved(guild: Any, kind: str, found_id: int) -> str:
    if kind == CHANNEL:
        name = text_of(getattr(looked_up(guild, "get_channel", found_id), "name", None))
        return f"#{name}" if name else ""
    if kind == ROLE:
        name = text_of(getattr(looked_up(guild, "get_role", found_id), "name", None))
        return f"@{name}" if name else ""
    member = looked_up(guild, "get_member", found_id)
    return text_of(getattr(member, "display_name", None)) or text_of(getattr(member, "name", None))


def named(guild: Any, text: Any) -> str:
    """Channel, role and member mentions as the names people type; unknown ids and the bot stay."""
    said = str(text or "")
    if guild is None:
        return said
    bot_id = getattr(getattr(guild, "me", None), "id", None)

    def swap(match: re.Match[str]) -> str:
        kind, found_id = match.group(1), int(match.group(2))
        if kind not in (CHANNEL, ROLE) and found_id == bot_id:
            return match.group(0)
        return resolved(guild, kind, found_id) or match.group(0)

    return ANY_MENTION.sub(swap, said)
