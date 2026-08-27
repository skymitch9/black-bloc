from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends

from .. import __version__
from ..events import OPEN_STATUSES
from ..modmail import OPEN as MODMAIL_OPEN
from ..settings_store import KEY_TYPES
from .auth import Refused, guild_of, staff_dependency
from .names import as_id, named

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
DB_UNREACHABLE = (
    "Black Bloc's database is not reachable right now, so this page cannot load its data; try "
    "again in a minute."
)
NOT_AN_ID = (
    "**{given}** is not an id Black Bloc can read, so the log was not filtered. Ids are the long "
    "numbers Discord shows under Copy ID."
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


def _health(cog: Any, name: str) -> tuple[Any, Any]:
    """A cog is the only home of its own health attribute names; ask it, never guess."""
    reader = getattr(cog, "loop_health", None)
    if not callable(reader):
        return (None, None)
    try:
        last_ok_at, last_error = reader(name)
    except Exception as exc:
        log.warning("status: %s could not report loop health — %s", type(cog).__name__, exc)
        return (None, None)
    return (last_ok_at, last_error)


def loop_health(bot: Any) -> list[dict[str, Any]]:
    """Every `tasks.loop` on every cog, with the health the cog itself reports."""
    found: list[dict[str, Any]] = []
    for cog_name, cog in (getattr(bot, "cogs", None) or {}).items():
        getter = getattr(cog, "get_tasks", None)
        if not callable(getter):
            continue
        for loop in getter() or ():
            name = getattr(getattr(loop, "coro", None), "__name__", "loop")
            running = bool(loop.is_running())
            failed = bool(loop.failed()) if callable(getattr(loop, "failed", None)) else False
            last_ok_at, last_error = _health(cog, name)
            found.append(
                {
                    "cog": cog_name,
                    "name": name,
                    "running": running,
                    "failed": failed,
                    "state": "danger" if (failed or not running) else "ok",
                    "next_iteration": _iso(getattr(loop, "next_iteration", None)),
                    "last_ok_at": _iso(last_ok_at),
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
            "open_modmail": await _count(
                db.conn,
                "SELECT COUNT(*) FROM modmail_tickets WHERE guild_id = ? AND status = ?",
                (guild_id, MODMAIL_OPEN),
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


def _action(row: Any, with_details: bool) -> dict[str, Any]:
    found = {
        "id": row["id"],
        "at": row["at"],
        "kind": row["kind"],
        "actor_id": str(row["actor_id"]) if row["actor_id"] is not None else None,
        "target_id": str(row["target_id"]) if row["target_id"] is not None else None,
        "reason": row["reason"],
    }
    if with_details:
        found["details"] = _details(row["details"])
    return found


async def recent_actions(
    bot: Any,
    guild_id: int,
    limit: int,
    *,
    with_details: bool = False,
    kind: str | None = None,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    """`kind` matches a whole kind or a prefix like `web.` or `mod.`; `user_id` either end."""
    sql = (
        "SELECT id, at, kind, actor_id, target_id, reason, details FROM action_log "
        "WHERE guild_id = ?"
    )
    params: tuple[Any, ...] = (guild_id,)
    if kind:
        sql += " AND (kind = ? OR kind LIKE ?)"
        params += (kind, f"{kind.rstrip('.')}.%")
    if user_id is not None:
        sql += " AND (actor_id = ? OR target_id = ?)"
        params += (user_id, user_id)
    cur = await bot.db.conn.execute(sql + " ORDER BY id DESC LIMIT ?", (*params, limit))
    return [_action(row, with_details) for row in await cur.fetchall()]


def build_router(bot: Any) -> APIRouter:
    from .writes import reader_dependency

    reader = reader_dependency(bot)
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

    @router.get("/actions", dependencies=[Depends(reader)])
    async def actions(
        limit: int = ACTIONS_DEFAULT_LIMIT,
        details: int = 0,
        kind: str = "",
        user_id: str = "",
    ) -> dict[str, Any]:
        limit = max(1, min(limit, ACTIONS_MAX_LIMIT))
        guild = guild_of(bot)
        if guild is None:
            return {"actions": [], "limit": limit, "notes": [NO_GUILD]}
        db = getattr(bot, "db", None)
        if db is None or not db.is_connected:
            raise Refused(503, "database_unavailable", DB_UNREACHABLE)
        wanted = as_id(user_id) if user_id else None
        if user_id and wanted is None:
            raise Refused(400, "bad_request", NOT_AN_ID.format(given=str(user_id)[:40]))
        rows = await recent_actions(
            bot,
            guild.id,
            limit,
            with_details=bool(details),
            kind=str(kind or "").strip() or None,
            user_id=wanted,
        )
        return {
            "actions": [named(row, guild, "actor", "target") for row in rows],
            "limit": limit,
            "notes": [],
        }

    return router
