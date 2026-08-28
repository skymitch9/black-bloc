from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import discord

from .logkinds import (
    ALL,
    CORE,
    FEATURES,
    LEVELS,
    feature_of,
    is_important,
    like_patterns,
    log_level_key,
    should_post,
)

log = logging.getLogger(__name__)

DETAILS_LIMIT = 900
LINE_LIMIT = 100
LOGS_MIN = 1
LOGS_MAX = 50
LOGS_DEFAULT = 10
SCAN_LIMIT = 5000
COLUMNS = "id, at, kind, actor_id, target_id, reason, details"
NOTHING_YET = "Nothing has been logged for this yet."
NOTHING_IMPORTANT = "Nothing important has been logged for this yet."


def entity_id(entity: Any) -> int | None:
    if entity is None:
        return None
    if isinstance(entity, int):
        return entity
    return getattr(entity, "id", None)


def describe(entity: Any) -> str | None:
    if entity is None:
        return None
    if isinstance(entity, int):
        return f"<@{entity}>"
    return getattr(entity, "mention", None) or str(entity)


def build_embed(
    kind: str,
    *,
    actor: Any = None,
    target: Any = None,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
    at: datetime | None = None,
) -> discord.Embed:
    """The compact one-action embed posted to the log channel."""
    embed = discord.Embed(title=kind, timestamp=at or datetime.now(UTC))
    if actor is not None:
        embed.add_field(name="Actor", value=describe(actor), inline=True)
    if target is not None:
        embed.add_field(name="Target", value=describe(target), inline=True)
    if reason:
        embed.add_field(name="Reason", value=reason[:1024], inline=False)
    if details:
        body = json.dumps(details, default=str)[:DETAILS_LIMIT]
        embed.add_field(name="Details", value=f"```json\n{body}\n```", inline=False)
    return embed


def level_for(bot: Any, guild: Any, kind: str) -> str:
    """No store and no guild both mean `all` — today's behaviour, never accidental silence."""
    store = getattr(bot, "store", None)
    guild_id = getattr(guild, "id", None)
    if store is None or guild_id is None:
        return ALL
    try:
        found = store.get(guild_id, log_level_key(feature_of(kind)))
    except Exception as exc:
        log.warning("action log: %s level unreadable — %s: %s", kind, type(exc).__name__, exc)
        return ALL
    return found if found in LEVELS else ALL


async def log_action(
    bot: Any,
    guild: Any,
    kind: str,
    *,
    actor: Any = None,
    target: Any = None,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
    notify: bool = False,
) -> int | None:
    """Record one action: a DB row always, a log-channel embed when the level asks for it."""
    at = datetime.now(UTC)
    cur = await bot.db.conn.execute(
        "INSERT INTO action_log(guild_id, at, kind, actor_id, target_id, reason, details) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            guild.id,
            at.isoformat(),
            kind,
            entity_id(actor),
            entity_id(target),
            reason,
            json.dumps(details, default=str) if details else None,
        ),
    )
    await bot.db.conn.commit()
    if notify or should_post(kind, level_for(bot, guild, kind)):
        embed = build_embed(
            kind, actor=actor, target=target, reason=reason, details=details, at=at
        )
        await _post(bot, guild, kind, embed)
    return cur.lastrowid


async def _post(bot: Any, guild: Any, kind: str, embed: discord.Embed) -> None:
    try:
        channel_id = bot.store.get(guild.id, "log_channel_id")
        if not channel_id:
            log.warning("action log: %s not posted — log_channel_id is not set", kind)
            return
        channel = bot.get_channel(channel_id) or guild.get_channel(channel_id)
        if channel is None:
            log.warning("action log: %s not posted — channel %s is not visible", kind, channel_id)
            return
        await channel.send(embed=embed)
    except Exception as exc:
        log.warning("action log: %s not posted — %s: %s", kind, type(exc).__name__, exc)


def feature_clause(feature: str) -> tuple[str, tuple[Any, ...]]:
    """`core` is everything no other feature claims, so it asks the question backwards."""
    if feature == CORE:
        patterns = tuple(
            pattern for other in FEATURES if other != CORE for pattern in like_patterns(other)
        )
        joined = " OR ".join("kind LIKE ?" for _ in patterns)
        return (f"NOT ({joined})", patterns)
    patterns = like_patterns(feature)
    joined = " OR ".join("kind LIKE ?" for _ in patterns)
    return (f"({joined})", patterns)


async def recent_rows(
    db: Any,
    guild_id: int,
    feature: str,
    limit: int,
    important_only: bool = False,
) -> list[Any]:
    clause, params = feature_clause(feature)
    cur = await db.conn.execute(
        f"SELECT {COLUMNS} FROM action_log WHERE guild_id = ? AND {clause} ORDER BY id DESC "
        "LIMIT ?",
        (guild_id, *params, SCAN_LIMIT if important_only else limit),
    )
    rows = list(await cur.fetchall())
    if important_only:
        rows = [row for row in rows if is_important(row["kind"])]
    return rows[:limit]


def stamp(at: Any) -> str:
    try:
        when = datetime.fromisoformat(str(at))
    except (TypeError, ValueError):
        return str(at)
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return f"<t:{int(when.timestamp())}:R>"


def summarise(row: Any) -> str:
    """The reason if there is one, otherwise the details flattened to `key=value`."""
    reason = row["reason"]
    if reason:
        return str(reason)
    try:
        found = json.loads(row["details"]) if row["details"] else None
    except (TypeError, ValueError):
        return str(row["details"])
    if isinstance(found, dict):
        return ", ".join(f"{key}={value}" for key, value in found.items())
    return "" if found is None else str(found)


def action_line(row: Any) -> str:
    parts = [f"`{row['kind']}`"]
    actor = describe(row["actor_id"])
    target = describe(row["target_id"])
    if actor and target:
        parts.append(f"{actor} → {target}")
    elif actor or target:
        parts.append(f"→ {target}" if target else str(actor))
    said = summarise(row)
    if said:
        parts.append(said)
    body = " · ".join(parts)
    if len(body) > LINE_LIMIT:
        body = f"{body[: LINE_LIMIT - 1]}…"
    return f"{stamp(row['at'])} · {body}"


async def recent_lines(
    db: Any,
    guild_id: int,
    feature: str,
    limit: int = LOGS_DEFAULT,
    important_only: bool = False,
) -> list[str]:
    """The one rendering of an action log line; every `/… logs` command is a caller."""
    rows = await recent_rows(db, guild_id, feature, limit, important_only)
    if not rows:
        return [NOTHING_IMPORTANT if important_only else NOTHING_YET]
    return [action_line(row) for row in rows]
