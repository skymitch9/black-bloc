from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ..settings_store import (
    KEY_CHOICES,
    KEY_HELP,
    KEY_MAX,
    KEY_MIN,
    KEY_TYPES,
    SettingError,
)
from .auth import Refused, staff_dependency
from .names import resolve_one
from .writes import note, require_db, require_guild, writer_dependency

log = logging.getLogger(__name__)

CORE_KEYS = ("log_channel_id", "staff_channel_id", "role_menu_channel_id")
CORE = "core"
NAMESPACE_OVERRIDE = {
    "modlog_channel_id": "automod",
    "mod_dm_on_action": "automod",
}
AUDIT_DEFAULT_LIMIT = 100
AUDIT_MAX_LIMIT = 500

NO_VALUE = (
    "That change arrived without a value, so nothing was changed. It is a fault in the page "
    "rather than in what you typed — reload the settings page and try again."
)
UNKNOWN_KEY = (
    "**{key}** is not a Black Bloc setting, so nothing was changed. The settings page lists every "
    "one it has."
)


def namespace_of(key: str) -> str:
    if key in NAMESPACE_OVERRIDE:
        return NAMESPACE_OVERRIDE[key]
    if key in CORE_KEYS:
        return CORE
    head, _, rest = key.partition("_")
    return head if rest else CORE


def from_json(key: str, value: Any) -> Any:
    """JSON carries snowflakes as strings; the registry's validator wants the numbers."""
    kind = KEY_TYPES.get(key)
    if kind in ("channel", "role", "int"):
        if isinstance(value, str) and value.strip().lstrip("<#@&!").rstrip(">").isdigit():
            return int(value.strip().lstrip("<#@&!").rstrip(">"))
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value
    if kind in ("channels", "roles") and isinstance(value, list):
        return [from_json_id(item) for item in value]
    return value


def from_json_id(item: Any) -> Any:
    if isinstance(item, str) and item.strip().lstrip("<#@&!").rstrip(">").isdigit():
        return int(item.strip().lstrip("<#@&!").rstrip(">"))
    if isinstance(item, float) and item.is_integer():
        return int(item)
    return item


def as_json(key: str, value: Any) -> Any:
    """Ids leave as strings, because a snowflake does not survive a JavaScript number."""
    kind = KEY_TYPES.get(key)
    if value is None:
        return None
    if kind in ("channel", "role"):
        return str(value)
    if kind in ("channels", "roles"):
        return [str(item) for item in value or ()]
    return value


def key_row(store: Any, guild_id: int, key: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "key": key,
        "type": KEY_TYPES[key],
        "value": as_json(key, store.get(guild_id, key)),
        "default": as_json(key, store.default(key)),
        "help": KEY_HELP.get(key, ""),
    }
    if key in KEY_CHOICES:
        row["choices"] = list(KEY_CHOICES[key])
    if key in KEY_MAX:
        row["max"] = KEY_MAX[key]
    if key in KEY_MIN:
        row["min"] = KEY_MIN[key]
    return row


def grouped(store: Any, guild_id: int) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {CORE: []}
    for key in KEY_TYPES:
        found.setdefault(namespace_of(key), []).append(key_row(store, guild_id, key))
    return found


def audit_row(guild: Any, row: Any) -> dict[str, Any]:
    key = str(row["key"])
    try:
        value = json.loads(row["value"])
    except (TypeError, ValueError):
        value = row["value"]
    by = row["updated_by"]
    return {
        "key": key,
        "namespace": namespace_of(key),
        "value": as_json(key, value),
        "updated_by_id": str(by) if by is not None else None,
        "updated_by_name": resolve_one(guild, by)["display_name"] if by is not None else None,
        "updated_at": row["updated_at"],
    }


async def audit_rows(bot: Any, guild: Any, limit: int) -> list[dict[str, Any]]:
    cur = await bot.db.conn.execute(
        "SELECT key, value, updated_by, updated_at FROM settings WHERE guild_id = ? "
        "ORDER BY updated_at DESC, key LIMIT ?",
        (guild.id, limit),
    )
    return [audit_row(guild, row) for row in await cur.fetchall()]


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/settings", tags=["settings"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("")
    async def settings_index() -> dict[str, Any]:
        guild = require_guild(bot)
        return grouped(bot.store, guild.id)

    @router.get("/audit")
    async def settings_audit(limit: int = AUDIT_DEFAULT_LIMIT) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        wanted = max(1, min(int(limit), AUDIT_MAX_LIMIT))
        return {"audit": await audit_rows(bot, guild, wanted), "limit": wanted}

    @router.put("/{key}")
    async def settings_set(request: Request, key: str, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        if key not in KEY_TYPES:
            raise Refused(400, "unknown_setting", UNKNOWN_KEY.format(key=key))
        if "value" not in payload:
            raise Refused(400, "no_value", NO_VALUE)
        try:
            stored = await bot.store.set(
                guild.id, key, from_json(key, payload["value"]), by=int(who["id"])
            )
        except SettingError as exc:
            raise Refused(400, "bad_value", str(exc)) from None
        await note(
            bot, guild, "web.settings.set", who, details={"key": key, "value": as_json(key, stored)}
        )
        return key_row(bot.store, guild.id, key)

    @router.delete("/{key}")
    async def settings_clear(request: Request, key: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        if key not in KEY_TYPES:
            raise Refused(400, "unknown_setting", UNKNOWN_KEY.format(key=key))
        cleared = await bot.store.clear(guild.id, key, by=int(who["id"]))
        await note(bot, guild, "web.settings.clear", who, details={"key": key})
        return key_row(bot.store, guild.id, key) | {"cleared": cleared}

    return router
