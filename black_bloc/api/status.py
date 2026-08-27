from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends

from .. import __version__
from ..events import OPEN_STATUSES
from ..settings_store import DB_UNAVAILABLE, KEY_TYPES
from .auth import Refused, guild_of, staff_dependency

log = logging.getLogger(__name__)

HONEYPOT_WINDOW_DAYS = 7
ACTIONS_DEFAULT_LIMIT = 50
ACTIONS_MAX_LIMIT = 200

NO_GUILD = (
    "Black Bloc is not in a server it can report on yet, so the per-feature figures below are "
    "blank. That is a setup step, not a fault with your access."
)
COUNTS_UNAVAILABLE = (
    "The open counts could not be read because Black Bloc cannot reach its own database right "
    "now. They are left blank rather than shown as zero."
)


def latency_ms(bot: Any) -> int | None:
    """None — never a number — before the gateway has measured a heartbeat."""
    if not bot.is_ready():
        return None
    seconds = getattr(bot, "latency", None)
    if not isinstance(seconds, int | float) or isinstance(seconds, bool):
        return None
    if not math.isfinite(seconds):
        return None
    return round(seconds * 1000)


def mode_keys() -> list[str]:
    return [key for key in KEY_TYPES if key.endswith("_mode")]


def feature_modes(store: Any, guild_id: int) -> list[dict[str, Any]]:
    return [
        {"key": key, "feature": key[: -len("_mode")], "mode": store.get(guild_id, key)}
        for key in mode_keys()
    ]


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return str(value)


def _health(loop: Any, cog: Any, name: str, field: str) -> Any:
    for candidate in (getattr(loop, field, None), getattr(cog, f"{name}_{field}", None)):
        if candidate is not None:
            return candidate
    return getattr(cog, field, None)


def loop_health(bot: Any) -> list[dict[str, Any]]:
    """Every `tasks.loop` on every cog, with whatever health the cog records."""
    found: list[dict[str, Any]] = []
    for cog_name, cog in (getattr(bot, "cogs", None) or {}).items():
        getter = getattr(cog, "get_tasks", None)
        if not callable(getter):
            continue
        for loop in getter() or ():
            name = getattr(getattr(loop, "coro", None), "__name__", "loop")
            running = bool(loop.is_running())
            failed = bool(loop.failed()) if callable(getattr(loop, "failed", None)) else False
            last_error = _health(loop, cog, name, "last_error")
            found.append(
                {
                    "cog": cog_name,
                    "name": name,
                    "running": running,
                    "failed": failed,
                    "state": "danger" if (failed or not running) else "ok",
                    "next_iteration": _iso(getattr(loop, "next_iteration", None)),
                    "last_ok_at": _iso(_health(loop, cog, name, "last_ok_at")),
                    "last_error": str(last_error) if last_error else None,
                }
            )
    return found


async def _count(conn: Any, sql: str, args: tuple[Any, ...]) -> int:
    cur = await conn.execute(sql, args)
    row = await cur.fetchone()
    return int(row[0]) if row else 0


async def open_counts(bot: Any, guild_id: int) -> dict[str, int] | None:
    """None — never zeroes — when the database cannot answer."""
    db = getattr(bot, "db", None)
    if db is None or not db.is_connected:
        return None
    since = (datetime.now(UTC) - timedelta(days=HONEYPOT_WINDOW_DAYS)).isoformat()
    placeholders = ", ".join("?" for _ in OPEN_STATUSES)
    try:
        return {
            "role_menus_posted": await _count(
                db.conn,
                "SELECT COUNT(*) FROM role_menus WHERE guild_id = ? AND message_id IS NOT NULL",
                (guild_id,),
            ),
            "temp_channels": await _count(
                db.conn,
                "SELECT COUNT(*) FROM tempvoice_channels WHERE guild_id = ?",
                (guild_id,),
            ),
            "honeypot_hits_7d": await _count(
                db.conn,
                "SELECT COUNT(*) FROM honeypot_hits WHERE guild_id = ? AND at >= ?",
                (guild_id, since),
            ),
            "open_events": await _count(
                db.conn,
                f"SELECT COUNT(*) FROM events WHERE guild_id = ? AND status IN ({placeholders})",
                (guild_id, *OPEN_STATUSES),
            ),
        }
    except Exception as exc:
        log.warning("status: open counts unavailable — %s: %s", type(exc).__name__, exc)
        return None


def _details(raw: Any) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return str(raw)


async def recent_actions(bot: Any, guild_id: int, limit: int) -> list[dict[str, Any]]:
    cur = await bot.db.conn.execute(
        "SELECT id, at, kind, actor_id, target_id, reason, details FROM action_log "
        "WHERE guild_id = ? ORDER BY id DESC LIMIT ?",
        (guild_id, limit),
    )
    return [
        {
            "id": row["id"],
            "at": row["at"],
            "kind": row["kind"],
            "actor_id": str(row["actor_id"]) if row["actor_id"] is not None else None,
            "target_id": str(row["target_id"]) if row["target_id"] is not None else None,
            "reason": row["reason"],
            "details": _details(row["details"]),
        }
        for row in await cur.fetchall()
    ]


def build_router(bot: Any) -> APIRouter:
    router = APIRouter(
        prefix="/api", tags=["status"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("/status")
    async def status() -> dict[str, Any]:
        guild = guild_of(bot)
        ready = bool(bot.is_ready())
        started_at = getattr(bot, "started_at", None)
        uptime = (
            int((datetime.now(UTC) - started_at).total_seconds())
            if isinstance(started_at, datetime)
            else None
        )
        counts = await open_counts(bot, guild.id) if guild is not None else None
        notes: list[str] = []
        if guild is None:
            notes.append(NO_GUILD)
        elif counts is None:
            notes.append(COUNTS_UNAVAILABLE)
        return {
            "bot": {
                "ready": ready,
                "latency_ms": latency_ms(bot),
                "guilds": len(getattr(bot, "guilds", ()) or ()),
                "uptime_seconds": uptime,
                "started_at": _iso(started_at),
                "version": __version__,
                "test_mode": bool(bot.settings.test_mode),
            },
            "guild": {"id": str(guild.id), "name": guild.name} if guild is not None else None,
            "features": feature_modes(bot.store, guild.id) if guild is not None else [],
            "loops": loop_health(bot),
            "open": counts,
            "notes": notes,
            "checked_at": datetime.now(UTC).isoformat(),
        }

    @router.get("/actions")
    async def actions(limit: int = ACTIONS_DEFAULT_LIMIT) -> dict[str, Any]:
        limit = max(1, min(limit, ACTIONS_MAX_LIMIT))
        guild = guild_of(bot)
        if guild is None:
            return {"actions": [], "limit": limit, "notes": [NO_GUILD]}
        db = getattr(bot, "db", None)
        if db is None or not db.is_connected:
            raise Refused(503, "database_unavailable", DB_UNAVAILABLE)
        return {"actions": await recent_actions(bot, guild.id, limit), "limit": limit, "notes": []}

    return router
