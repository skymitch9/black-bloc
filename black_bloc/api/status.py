from __future__ import annotations

import csv
import io
import json
import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from discord.ext import tasks
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from .. import __version__
from ..actionlog import SCAN_LIMIT, default_view_clause, feature_clause, summary_of
from ..events import OPEN_STATUSES
from ..logkinds import FEATURES, feature_of, is_important, via_of
from ..modmail import OPEN as MODMAIL_OPEN
from ..settings_store import KEY_TYPES
from .auth import Refused, guild_of, staff_dependency
from .names import as_id, named

log = logging.getLogger(__name__)

HONEYPOT_WINDOW_DAYS = 7
NOT_A_FEATURE = (
    "poll_review_mode",
    "chat_llm_mode",
    "chat_memory_mode",
)
ACTIONS_DEFAULT_LIMIT = 50
ACTIONS_MAX_LIMIT = 200
CSV_MEDIA_TYPE = "text/csv"
CSV_COLUMNS = (
    "id",
    "at",
    "kind",
    "feature",
    "important",
    "actor_id",
    "actor_name",
    "target_id",
    "target_name",
    "reason",
    "via",
    "details",
)

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
NOT_A_DATE = (
    "**{given}** is not a date Black Bloc can read, so the log was not filtered. Dates look like "
    "2026-08-27 or 2026-08-27T14:30:00Z."
)
UNKNOWN_FEATURE = (
    "**{given}** is not one of Black Bloc's features, so the log was not filtered. The features "
    "are: {known}."
)
SCAN_TRUNCATED = (
    "Only the most recent {limit} log lines were searched, so the count below is what matched "
    "inside that window rather than the whole history. Narrow the dates or the feature to see "
    "further back."
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
    """The feature switches only; a `_mode` key that names no feature is not one."""
    return [key for key in KEY_TYPES if key.endswith("_mode") and key not in NOT_A_FEATURE]


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


def _loops(cog: Any) -> list[tuple[str, Any]]:
    """Every `tasks.Loop` a cog holds, found by type — never by `dir()`, which fires properties."""
    names: dict[str, None] = {}
    for owner in (*type(cog).__mro__, cog):
        for name, value in (getattr(owner, "__dict__", None) or {}).items():
            if isinstance(value, tasks.Loop):
                names[name] = None
    found: list[tuple[str, Any]] = []
    seen: set[int] = set()
    for name in names:
        loop = getattr(cog, name, None)
        if isinstance(loop, tasks.Loop) and id(loop) not in seen:
            seen.add(id(loop))
            found.append((name, loop))
    return found


def loop_health(bot: Any) -> list[dict[str, Any]]:
    """Every `tasks.loop` on every cog, with the health the cog itself reports."""
    found: list[dict[str, Any]] = []
    for cog_name, cog in (getattr(bot, "cogs", None) or {}).items():
        for name, loop in _loops(cog):
            running = bool(loop.is_running())
            failed = bool(loop.failed())
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
    """Actor and target stay FLAT — Overview, Health and the Logs page all read them that way."""
    kind = row["kind"]
    details = _details(row["details"])
    found = {
        "id": row["id"],
        "at": row["at"],
        "kind": kind,
        "feature": feature_of(kind),
        "important": is_important(kind),
        "actor_id": str(row["actor_id"]) if row["actor_id"] is not None else None,
        "target_id": str(row["target_id"]) if row["target_id"] is not None else None,
        "reason": row["reason"],
        "summary": summary_of(row["reason"], details),
        "via": via_of(kind, details),
    }
    if with_details:
        found["details"] = details
    return found


async def kinds_present(bot: Any, guild_id: int, feature: str | None) -> list[str]:
    """The chips the Logs page offers: what this guild has actually logged, not the whole table."""
    sql = "SELECT DISTINCT kind FROM action_log WHERE guild_id = ?"
    params: tuple[Any, ...] = (guild_id,)
    if feature:
        clause, wanted = feature_clause(feature)
        sql += f" AND {clause}"
        params += wanted
    else:
        hidden, patterns = default_view_clause()
        if hidden:
            sql += f" AND {hidden}"
            params += patterns
    cur = await bot.db.conn.execute(f"{sql} ORDER BY kind", params)
    return [row["kind"] for row in await cur.fetchall()]


async def recent_actions(
    bot: Any,
    guild_id: int,
    limit: int,
    *,
    with_details: bool = False,
    kind: str | None = None,
    user_id: int | None = None,
    feature: str | None = None,
    since: str | None = None,
    until: str | None = None,
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
    if feature:
        clause, wanted = feature_clause(feature)
        sql += f" AND {clause}"
        params += wanted
    elif not kind:
        hidden, patterns = default_view_clause()
        if hidden:
            sql += f" AND {hidden}"
            params += patterns
    if since:
        sql += " AND at >= ?"
        params += (since,)
    if until:
        sql += " AND at <= ?"
        params += (until,)
    cur = await bot.db.conn.execute(sql + " ORDER BY id DESC LIMIT ?", (*params, limit))
    return [_action(row, with_details) for row in await cur.fetchall()]


def csv_cell(row: dict[str, Any], name: str) -> Any:
    value = row.get(name)
    if name == "details":
        return json.dumps(value, default=str) if value else ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else value


def searchable(row: dict[str, Any]) -> str:
    parts = [str(row.get(name) or "") for name in ("kind", "actor_name", "target_name", "reason")]
    parts.append(json.dumps(row.get("details"), default=str) if row.get("details") else "")
    return " ".join(parts).lower()


def wanted_when(given: str, name: str) -> str | None:
    """A bare date is the whole day: `until=2026-08-27` must not exclude that afternoon."""
    text = str(given or "").strip()
    if not text:
        return None
    try:
        when = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise Refused(400, "bad_request", NOT_A_DATE.format(given=text[:40])) from None
    if len(text) == 10 and name == "until":
        when = when.replace(hour=23, minute=59, second=59, microsecond=999999)
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return when.astimezone(UTC).isoformat()


def wanted_feature(given: str) -> str | None:
    text = str(given or "").strip().lower()
    if not text:
        return None
    if text not in FEATURES:
        raise Refused(
            400,
            "bad_request",
            UNKNOWN_FEATURE.format(given=text[:40], known=", ".join(FEATURES)),
        )
    return text


async def searched_actions(
    bot: Any,
    guild: Any,
    *,
    kind: str,
    user_id: str,
    feature: str,
    since: str,
    until: str,
    q: str,
    important: bool,
) -> tuple[list[dict[str, Any]], bool]:
    """Everything SQL can filter, then importance and the free-text search in Python."""
    wanted_id = as_id(user_id) if user_id else None
    if user_id and wanted_id is None:
        raise Refused(400, "bad_request", NOT_AN_ID.format(given=str(user_id)[:40]))
    rows = await recent_actions(
        bot,
        guild.id,
        SCAN_LIMIT,
        with_details=True,
        kind=str(kind or "").strip() or None,
        user_id=wanted_id,
        feature=wanted_feature(feature),
        since=wanted_when(since, "since"),
        until=wanted_when(until, "until"),
    )
    truncated = len(rows) >= SCAN_LIMIT
    found = [named(row, guild, "actor", "target") for row in rows]
    if important:
        found = [row for row in found if row["important"]]
    needle = str(q or "").strip().lower()
    if needle:
        found = [row for row in found if needle in searchable(row)]
    return (found, truncated)


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
        per_page: int = 0,
        page: int = 1,
        details: int = 0,
        kind: str = "",
        user_id: str = "",
        feature: str = "",
        q: str = "",
        since: str = "",
        until: str = "",
        important: int = 0,
    ) -> dict[str, Any]:
        size = max(1, min(per_page or limit, ACTIONS_MAX_LIMIT))
        page = max(1, page)
        guild = guild_of(bot)
        if guild is None:
            return {
                "actions": [],
                "kinds": [],
                "limit": size,
                "per_page": size,
                "page": page,
                "total": 0,
                "shown": 0,
                "notes": [NO_GUILD],
            }
        db = getattr(bot, "db", None)
        if db is None or not db.is_connected:
            raise Refused(503, "database_unavailable", DB_UNREACHABLE)
        found, truncated = await searched_actions(
            bot,
            guild,
            kind=kind,
            user_id=user_id,
            feature=feature,
            since=since,
            until=until,
            q=q,
            important=bool(important),
        )
        start = (page - 1) * size
        shown = found[start : start + size]
        if not details:
            shown = [
                {key: value for key, value in row.items() if key != "details"} for row in shown
            ]
        return {
            "actions": shown,
            "kinds": await kinds_present(bot, guild.id, wanted_feature(feature)),
            "limit": size,
            "per_page": size,
            "page": page,
            "total": len(found),
            "shown": len(shown),
            "notes": [SCAN_TRUNCATED.format(limit=SCAN_LIMIT)] if truncated else [],
        }

    @router.get("/actions/export.csv", dependencies=[Depends(reader)])
    async def actions_export(
        kind: str = "",
        user_id: str = "",
        feature: str = "",
        q: str = "",
        since: str = "",
        until: str = "",
        important: int = 0,
    ) -> PlainTextResponse:
        guild = guild_of(bot)
        if guild is None:
            raise Refused(503, "no_guild", NO_GUILD)
        db = getattr(bot, "db", None)
        if db is None or not db.is_connected:
            raise Refused(503, "database_unavailable", DB_UNREACHABLE)
        found, _ = await searched_actions(
            bot,
            guild,
            kind=kind,
            user_id=user_id,
            feature=feature,
            since=since,
            until=until,
            q=q,
            important=bool(important),
        )
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        for row in found:
            writer.writerow([csv_cell(row, name) for name in CSV_COLUMNS])
        return PlainTextResponse(
            out.getvalue(),
            media_type=CSV_MEDIA_TYPE,
            headers={"Content-Disposition": 'attachment; filename="black-bloc-log.csv"'},
        )

    return router
