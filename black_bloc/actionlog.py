from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import discord

from .logkinds import (
    ALL,
    CORE,
    FEATURE_LABELS,
    FEATURE_PAGES,
    FEATURES,
    LEVELS,
    feature_of,
    hidden_by_default_patterns,
    is_important,
    like_patterns,
    log_level_key,
    should_post,
    via_of,
    via_word,
)
from .settings_store import (
    GUILD_ONLY,
    LOGS_DEFAULT,
    LOGS_MAX,
    LOGS_MIN,
    require_staff,
)

log = logging.getLogger(__name__)

DETAILS_LIMIT = 900
LINE_LIMIT = 100
BODY_LIMIT = 3900
SCAN_LIMIT = 5000
COLUMNS = "id, at, kind, actor_id, target_id, reason, details"
SUMMARY_SKIPS = ("via",)
NOTHING_YET = "Nothing has been logged for this yet."
NOTHING_IMPORTANT = "Nothing important has been logged for this yet."
FOOTER = "The whole log, searchable, is on the dashboard: {origin}/{page}"
LOGS_DB_DOWN = (
    "Black Bloc cannot reach its own database right now, so it cannot read the log. Wait a "
    "moment and run the command again, and tell a Lead if it keeps happening."
)


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


def stamped(kind: str, details: dict[str, Any] | None) -> dict[str, Any]:
    """Every row says where it came from, so no writer can forget the owner's Via column."""
    found = dict(details or {})
    found["via"] = via_of(kind, found)
    return found


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
    carded: bool = False,
) -> int | None:
    """Record one action: a DB row always, a log-channel embed when the level asks for it."""
    at = datetime.now(UTC)
    details = stamped(kind, details)
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
    if notify or should_post(kind, level_for(bot, guild, kind), carded=carded):
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


def default_view_clause() -> tuple[str, tuple[Any, ...]]:
    """The ONE place the unfiltered Logs view leaves the Test rows out; the CSV asks it too."""
    patterns = hidden_by_default_patterns()
    if not patterns:
        return ("", ())
    joined = " AND ".join("kind NOT LIKE ?" for _ in patterns)
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


def summary_of(reason: Any, details: Any) -> str:
    """The reason if there is one, otherwise the details flattened to `key=value`."""
    if reason:
        return str(reason)
    found = details
    if isinstance(found, str):
        try:
            found = json.loads(found)
        except (TypeError, ValueError):
            return found
    if isinstance(found, dict):
        return ", ".join(
            f"{key}={value}" for key, value in found.items() if key not in SUMMARY_SKIPS
        )
    return "" if found is None else str(found)


def summarise(row: Any) -> str:
    return summary_of(row["reason"], row["details"])


def as_details(details: Any) -> Any:
    if isinstance(details, str):
        try:
            return json.loads(details)
        except (TypeError, ValueError):
            return None
    return details


def via_for(row: Any) -> str:
    return via_of(row["kind"], as_details(row["details"]))


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
    # Outside the cap, like the stamp: a truncated line must still say where it came from.
    said_via = f"via {via_word(row['kind'], as_details(row['details']))}"
    return f"{stamp(row['at'])} · {body} · {said_via}"


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


def logs_embed(feature: str, lines: list[str], important_only: bool, origin: str) -> discord.Embed:
    body: list[str] = []
    spent = 0
    for line in lines:
        if spent + len(line) + 1 > BODY_LIMIT:
            break
        body.append(line)
        spent += len(line) + 1
    title = f"{FEATURE_LABELS[feature]} log"
    embed = discord.Embed(
        title=f"{title} — important only" if important_only else title,
        description="\n".join(body),
    )
    embed.set_footer(
        text=FOOTER.format(origin=str(origin).rstrip("/"), page=FEATURE_PAGES[feature])
    )
    return embed


async def send_logs(
    interaction: Any,
    feature: str,
    *,
    count: int = LOGS_DEFAULT,
    important_only: bool = False,
    staff_only: bool = True,
) -> None:
    """The whole body of every `/<feature> logs` command."""
    if staff_only:
        if not await require_staff(interaction):
            return
    elif interaction.guild is None:
        await interaction.response.send_message(GUILD_ONLY, ephemeral=True)
        return
    bot = interaction.client
    if not getattr(bot.db, "is_connected", False):
        await interaction.response.send_message(LOGS_DB_DOWN, ephemeral=True)
        return
    lines = await recent_lines(
        bot.db,
        interaction.guild.id,
        feature,
        max(LOGS_MIN, min(int(count), LOGS_MAX)),
        important_only,
    )
    await interaction.response.send_message(
        embed=logs_embed(feature, lines, important_only, bot.settings.origin),
        ephemeral=True,
        allowed_mentions=discord.AllowedMentions.none(),
    )
