"""What a structure snapshot is: its fields, its digest, its counts and its download."""

from __future__ import annotations

import hashlib
import json
from typing import Any

VERSION = 1
MODES = ("off", "shadow", "on")
MODE_DEFAULT = "shadow"
FEATURE = "structure_backup"
PAGE = "structure.html"
ROLE_KEY = "structure_backup_role_id"
CHANNEL_KEY = "structure_backup_channel_id"
SHADOW_CHANNEL_KEY = "structure_backup_shadow_channel_id"
LEADS_KEYS = (ROLE_KEY, CHANNEL_KEY, SHADOW_CHANNEL_KEY)
LEADS_ONLY_CODE = "structure_leads_only"
OPERATOR_CODE = "structure_no_operator"
LEADS_ONLY = (
    "Structure backup is the saved copy of every role, channel and permission in the server, "
    "private channels included, so it is for the server's leads: the owner, anyone with "
    "Discord's Administrator permission, and holders of the role in structure_backup_role_id. "
    "You are staff, but none of those, so nothing was shown or changed. Ask the server owner to "
    "give you that role."
)
OPERATOR_REFUSED = (
    "The operator token does not open structure backup, so nothing was read. It is the saved "
    "copy of every role, channel and permission, private channels included, and only the "
    "server's leads may see it. Sign in on the dashboard as the owner, an administrator or a "
    "holder of the role in structure_backup_role_id."
)

DAILY = "daily"
MANUAL = "manual"
SOURCES = (DAILY, MANUAL)

SAVED = "saved"
UNCHANGED = "unchanged"
FAILED = "failed"
OFF = "off"
OUTCOMES = (SAVED, UNCHANGED, FAILED)

CATEGORY = "category"
ROLE = "role"
MEMBER = "member"
VOICE_TYPES = ("voice", "stage_voice")

GUILD_FIELDS = (
    "id",
    "name",
    "verification_level",
    "default_notifications",
    "system_channel_id",
    "rules_channel_id",
)
ROLE_FIELDS = (
    "id",
    "name",
    "color",
    "permissions",
    "position",
    "hoist",
    "mentionable",
    "managed",
)
CHANNEL_FIELDS = (
    "id",
    "name",
    "type",
    "parent_id",
    "position",
    "topic",
    "slowmode",
    "nsfw",
    "bitrate",
    "user_limit",
)
TAG_FIELDS = ("id", "name", "moderated", "emoji")
OVERWRITE_FIELDS = ("target_id", "target_type", "allow", "deny")
SNAPSHOT_FIELDS = (
    "id",
    "taken_at",
    "source",
    "digest",
    "roles",
    "categories",
    "channels",
    "overwrites",
)
COUNT_FIELDS = ("roles", "categories", "channels", "overwrites")


def only(found: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    """The named fields and nothing else, a missing one read as None."""
    source = found if isinstance(found, dict) else {}
    return {name: source.get(name) for name in fields}


def in_id_order(rows: list[dict[str, Any]], field: str = "id") -> list[dict[str, Any]]:
    """Snowflakes are strings here, so shorter sorts first and equal lengths sort as text."""
    return sorted(rows, key=lambda row: (len(str(row[field] or "")), str(row[field] or "")))


def clean_channel(found: Any) -> dict[str, Any]:
    source = found if isinstance(found, dict) else {}
    channel = only(source, CHANNEL_FIELDS)
    channel["tags"] = in_id_order([only(tag, TAG_FIELDS) for tag in source.get("tags") or ()])
    channel["overwrites"] = in_id_order(
        [only(one, OVERWRITE_FIELDS) for one in source.get("overwrites") or ()], "target_id"
    )
    return channel


def clean(body: Any) -> dict[str, Any]:
    """A snapshot body rebuilt through the field lists, so nothing unnamed survives."""
    source = body if isinstance(body, dict) else {}
    return {
        "version": VERSION,
        "guild": only(source.get("guild"), GUILD_FIELDS),
        "roles": in_id_order([only(role, ROLE_FIELDS) for role in source.get("roles") or ()]),
        "channels": in_id_order(
            [clean_channel(channel) for channel in source.get("channels") or ()]
        ),
    }


def by_id(rows: list[dict[str, Any]], field: str = "id") -> dict[str, dict[str, Any]]:
    return {str(row[field]): row for row in rows if row.get(field) is not None}


def top_down(roles: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(roles, key=lambda one: (-int(roles[one]["position"] or 0), one))


def bucket(channel: dict[str, Any]) -> str:
    if channel["type"] == CATEGORY:
        return CATEGORY
    return "voice" if channel["type"] in VOICE_TYPES else "text"


def in_order(channels: dict[str, dict[str, Any]]) -> dict[tuple[Any, str], list[str]]:
    groups: dict[tuple[Any, str], list[str]] = {}
    ranked = sorted(channels, key=lambda one: (int(channels[one]["position"] or 0), one))
    for ident in ranked:
        channel = channels[ident]
        groups.setdefault((channel["parent_id"], bucket(channel)), []).append(ident)
    return groups


def placed(body: Any) -> dict[str, Any]:
    """A clean body with each position read as a place in its list, so renumbering is no change."""
    found = clean(body)
    roles = by_id(found["roles"])
    for place, ident in enumerate(top_down(roles)):
        roles[ident]["position"] = place
    channels = by_id(found["channels"])
    for group in in_order(channels).values():
        for place, ident in enumerate(group):
            channels[ident]["position"] = place
    return found


def canonical(body: Any) -> str:
    return json.dumps(clean(body), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(body: Any) -> str:
    """One digest per structure a person could tell apart: order counts, raw positions do not."""
    marked = json.dumps(placed(body), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(marked.encode("utf-8")).hexdigest()


def counts(body: Any) -> dict[str, int]:
    found = clean(body)
    channels = found["channels"]
    categories = sum(1 for channel in channels if channel["type"] == CATEGORY)
    return {
        "roles": len(found["roles"]),
        "categories": categories,
        "channels": len(channels) - categories,
        "overwrites": sum(len(channel["overwrites"]) for channel in channels),
    }


def body_of(row: Any) -> dict[str, Any]:
    """A stored row's body; an unreadable one is an empty structure, never a crash."""
    try:
        found = json.loads(row["body"])
    except (KeyError, TypeError, ValueError):
        found = {}
    return clean(found)


def export(row: Any) -> dict[str, Any]:
    """What a download carries: named fields of the row and the body, never the row itself."""
    snapshot = {name: row[name] for name in SNAPSHOT_FIELDS}
    snapshot["guild_id"] = str(row["guild_id"])
    snapshot["filename"] = export_name(row)
    return {"snapshot": snapshot, **body_of(row)}


def may_see(store: Any, guild: Any, person: Any) -> bool:
    """The one rule for every structure door: the owner, an administrator, or the leads role."""
    if guild is None or person is None:
        return False
    try:
        user_id = int(getattr(person, "id", person))
    except (TypeError, ValueError):
        return False
    if getattr(guild, "owner_id", None) == user_id:
        return True
    if getattr(getattr(person, "guild_permissions", None), "administrator", False) is True:
        return True
    try:
        wanted = int(store.get(guild.id, ROLE_KEY) or 0)
    except (TypeError, ValueError):
        return False
    held = {getattr(role, "id", None) for role in getattr(person, "roles", None) or ()}
    return bool(wanted) and wanted in held


def export_name(row: Any) -> str:
    day = str(row["taken_at"] or "")[:10] or "undated"
    return f"structure-{row['guild_id']}-{day}-{row['id']}.json"


__all__ = [
    "CATEGORY",
    "CHANNEL_FIELDS",
    "CHANNEL_KEY",
    "COUNT_FIELDS",
    "DAILY",
    "FAILED",
    "FEATURE",
    "GUILD_FIELDS",
    "LEADS_KEYS",
    "LEADS_ONLY",
    "LEADS_ONLY_CODE",
    "MANUAL",
    "MEMBER",
    "MODES",
    "MODE_DEFAULT",
    "OFF",
    "OPERATOR_CODE",
    "OPERATOR_REFUSED",
    "OUTCOMES",
    "OVERWRITE_FIELDS",
    "PAGE",
    "ROLE",
    "ROLE_FIELDS",
    "ROLE_KEY",
    "SAVED",
    "SHADOW_CHANNEL_KEY",
    "SNAPSHOT_FIELDS",
    "SOURCES",
    "TAG_FIELDS",
    "UNCHANGED",
    "VERSION",
    "VOICE_TYPES",
    "body_of",
    "bucket",
    "by_id",
    "canonical",
    "clean",
    "counts",
    "digest",
    "export",
    "export_name",
    "in_id_order",
    "in_order",
    "may_see",
    "only",
    "placed",
    "top_down",
]
