from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import discord

log = logging.getLogger(__name__)

DETAILS_LIMIT = 900


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


async def log_action(
    bot: Any,
    guild: Any,
    kind: str,
    *,
    actor: Any = None,
    target: Any = None,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
) -> int | None:
    """Record one action: a DB row always, a log-channel embed when it can."""
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
