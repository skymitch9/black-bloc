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


def canonical(body: Any) -> str:
    return json.dumps(clean(body), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(body: Any) -> str:
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


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


def export_name(row: Any) -> str:
    day = str(row["taken_at"] or "")[:10] or "undated"
    return f"structure-{row['guild_id']}-{day}-{row['id']}.json"


__all__ = [
    "CATEGORY",
    "CHANNEL_FIELDS",
    "COUNT_FIELDS",
    "DAILY",
    "FAILED",
    "FEATURE",
    "GUILD_FIELDS",
    "MANUAL",
    "MEMBER",
    "MODES",
    "MODE_DEFAULT",
    "OFF",
    "OUTCOMES",
    "OVERWRITE_FIELDS",
    "PAGE",
    "ROLE",
    "ROLE_FIELDS",
    "SAVED",
    "SNAPSHOT_FIELDS",
    "SOURCES",
    "TAG_FIELDS",
    "UNCHANGED",
    "VERSION",
    "body_of",
    "canonical",
    "clean",
    "counts",
    "digest",
    "export",
    "export_name",
    "in_id_order",
    "only",
]
