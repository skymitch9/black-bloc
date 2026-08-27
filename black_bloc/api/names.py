from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

MEMBER_SEARCH_LIMIT = 25
MEMBER_SEARCH_MAX = 100
NAMES_MAX = 200

CHANNEL_KINDS: dict[str, str] = {
    "text": "text",
    "news": "text",
    "public_thread": "text",
    "private_thread": "text",
    "news_thread": "text",
    "voice": "voice",
    "stage_voice": "voice",
    "category": "category",
    "forum": "forum",
    "media": "forum",
}

UNKNOWN = {"name": None, "display_name": None, "kind": "unknown"}


def as_id(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def parse_ids(raw: Any, limit: int = NAMES_MAX) -> list[int]:
    found: list[int] = []
    for piece in str(raw or "").split(","):
        number = as_id(piece.strip().lstrip("<#@&!").rstrip(">"))
        if number is not None and number not in found:
            found.append(number)
        if len(found) >= limit:
            break
    return found


def channel_kind(channel: Any) -> str:
    raw = getattr(channel, "type", None)
    name = getattr(raw, "name", None) or str(raw or "")
    return CHANNEL_KINDS.get(name, "text")


def channel_row(channel: Any) -> dict[str, Any]:
    category_id = getattr(channel, "category_id", None)
    if category_id is None:
        category_id = getattr(getattr(channel, "category", None), "id", None)
    return {
        "id": str(channel.id),
        "name": str(getattr(channel, "name", "") or ""),
        "type": channel_kind(channel),
        "category_id": str(category_id) if category_id else None,
        "position": int(getattr(channel, "position", 0) or 0),
    }


def role_row(role: Any) -> dict[str, Any]:
    colour = getattr(role, "color", None) or getattr(role, "colour", None)
    value = getattr(colour, "value", colour)
    return {
        "id": str(role.id),
        "name": str(getattr(role, "name", "") or ""),
        "color": int(value) if isinstance(value, int) and not isinstance(value, bool) else 0,
        "position": int(getattr(role, "position", 0) or 0),
        "managed": bool(getattr(role, "managed", False)),
    }


def avatar_url(member: Any) -> str | None:
    avatar = getattr(member, "display_avatar", None) or getattr(member, "avatar", None)
    url = getattr(avatar, "url", None)
    return str(url) if url else None


def member_row(member: Any) -> dict[str, Any]:
    name = str(getattr(member, "name", "") or getattr(member, "display_name", "") or member.id)
    return {
        "id": str(member.id),
        "name": name,
        "display_name": str(getattr(member, "display_name", None) or name),
        "avatar_url": avatar_url(member),
    }


def channels(guild: Any) -> list[dict[str, Any]]:
    found = list(getattr(guild, "channels", ()) or ())
    return sorted(
        (channel_row(channel) for channel in found),
        key=lambda row: (row["type"] != "category", row["position"], row["name"]),
    )


def roles(guild: Any) -> list[dict[str, Any]]:
    found = list(getattr(guild, "roles", ()) or ())
    return sorted((role_row(role) for role in found), key=lambda row: -row["position"])


def _matches(member: Any, query: str) -> bool:
    if not query:
        return True
    haystack = " ".join(
        str(part or "").lower()
        for part in (
            getattr(member, "name", None),
            getattr(member, "display_name", None),
            getattr(member, "global_name", None),
            member.id,
        )
    )
    return query in haystack


def search_members(guild: Any, query: Any = None, limit: int = MEMBER_SEARCH_LIMIT) -> list[dict]:
    """Cache-only member search: the gateway's member list, never a request to Discord."""
    wanted = max(1, min(int(limit or MEMBER_SEARCH_LIMIT), MEMBER_SEARCH_MAX))
    lowered = str(query or "").strip().lower()
    found: list[dict[str, Any]] = []
    for member in list(getattr(guild, "members", ()) or ()):
        if not _matches(member, lowered):
            continue
        found.append(member_row(member))
        if len(found) >= wanted:
            break
    return sorted(found, key=lambda row: row["display_name"].lower())


def resolve_one(guild: Any, entity_id: Any) -> dict[str, Any]:
    """One id as a name, from the guild cache only — never a network call."""
    number = as_id(entity_id)
    if guild is None or number is None:
        return dict(UNKNOWN)
    member = guild.get_member(number)
    if member is not None:
        row = member_row(member)
        return {"name": row["name"], "display_name": row["display_name"], "kind": "member"}
    role = guild.get_role(number)
    if role is not None:
        name = str(getattr(role, "name", "") or "")
        return {"name": name, "display_name": name, "kind": "role"}
    channel = guild.get_channel(number)
    if channel is not None:
        name = str(getattr(channel, "name", "") or "")
        return {"name": name, "display_name": f"#{name}" if name else "", "kind": "channel"}
    return dict(UNKNOWN)


def resolve(guild: Any, ids: Any) -> dict[str, dict[str, Any]]:
    """Every id at once, so a page makes one call rather than one per row."""
    found: dict[str, dict[str, Any]] = {}
    for entity_id in ids or ():
        number = as_id(entity_id)
        if number is None or str(number) in found:
            continue
        found[str(number)] = resolve_one(guild, number)
    return found


def named(row: dict[str, Any], guild: Any, *fields: str) -> dict[str, Any]:
    """`actor_id` becomes `actor_name` beside it; a missing id stays missing, never a guess."""
    for field in fields:
        value = row.get(f"{field}_id")
        if value is None:
            row[f"{field}_name"] = None
            continue
        row[f"{field}_name"] = resolve_one(guild, value)["display_name"]
    return row


__all__ = [
    "MEMBER_SEARCH_LIMIT",
    "NAMES_MAX",
    "as_id",
    "avatar_url",
    "channel_kind",
    "channel_row",
    "channels",
    "member_row",
    "named",
    "parse_ids",
    "resolve",
    "resolve_one",
    "role_row",
    "roles",
    "search_members",
]
