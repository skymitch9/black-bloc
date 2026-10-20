"""The Posts page's one switch: retired keys go and rehearsing stickies pause, once, at boot."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import discord

from .actionlog import log_action

log = logging.getLogger(__name__)

RETIRED_KEYS: tuple[str, ...] = (
    "sticky_mode",
    "question_mode",
    "sticky_shadow_channel_id",
    "question_shadow_channel_id",
    "frontdoor_shadow_channel_id",
    "frontdoor_shadow_message_id",
    "frontdoor_shadow_hash",
    "poll_shadow_channel_id",
    "poll_shadow_note",
)
MODE_MAPS: dict[str, dict[str, str]] = {
    "posts_mode": {"shadow": "on"},
    "frontdoor_mode": {"shadow": "off"},
    "poll_mode": {"shadow": "off"},
}
PAUSED_KIND = "sticky.paused_by_migration"
MIGRATED_KIND = "settings.migrated"
BUILD = "posts-one-switch"
REHEARSING_ROWS = (
    "SELECT channel_id, post_id, message_id, posted_channel_id FROM sticky_messages "
    "WHERE guild_id = ? AND paused = 0 AND trouble IS NULL AND message_id IS NOT NULL "
    "AND posted_channel_id IS NOT NULL AND posted_channel_id != channel_id ORDER BY channel_id"
)


def _loaded(text: Any) -> Any:
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text


async def guild_ids(db: Any) -> list[int]:
    cur = await db.conn.execute(
        "SELECT guild_id FROM settings UNION SELECT guild_id FROM sticky_messages ORDER BY 1"
    )
    return [int(row[0]) for row in await cur.fetchall()]


async def plan(db: Any, guild_id: int) -> dict[str, Any]:
    """What `apply` would change in one guild, and nothing written."""
    cur = await db.conn.execute(
        f"SELECT key, value FROM settings WHERE guild_id = ? AND key IN "
        f"({', '.join('?' for _ in RETIRED_KEYS)}) ORDER BY key",
        (int(guild_id), *RETIRED_KEYS),
    )
    drop = {row["key"]: _loaded(row["value"]) for row in await cur.fetchall()}
    modes: dict[str, dict[str, Any]] = {}
    for key, mapping in MODE_MAPS.items():
        cur = await db.conn.execute(
            "SELECT value FROM settings WHERE guild_id = ? AND key = ?", (int(guild_id), key)
        )
        row = await cur.fetchone()
        before = _loaded(row["value"]) if row is not None else None
        if before in mapping:
            modes[key] = {"before": before, "after": mapping[before]}
    cur = await db.conn.execute(REHEARSING_ROWS, (int(guild_id),))
    pause = [
        {
            "channel_id": int(row["channel_id"]),
            "post_id": int(row["post_id"]) if row["post_id"] else None,
            "copy": {
                "channel_id": int(row["posted_channel_id"]),
                "message_id": int(row["message_id"]),
            },
            "before": "rehearsing",
            "after": "paused",
        }
        for row in await cur.fetchall()
    ]
    return {"guild_id": int(guild_id), "pause": pause, "drop": drop, "modes": modes}


def is_empty(found: dict[str, Any]) -> bool:
    return not (found["pause"] or found["drop"] or found["modes"])


async def dry_run(db: Any) -> list[dict[str, Any]]:
    """Every guild's plan that would change something."""
    found = [await plan(db, guild_id) for guild_id in await guild_ids(db)]
    return [one for one in found if not is_empty(one)]


async def _write(db: Any, found: dict[str, Any], at: str) -> None:
    guild_id = found["guild_id"]
    for row in found["pause"]:
        await db.conn.execute(
            "UPDATE sticky_messages SET paused = 1, updated_by = NULL, updated_at = ? "
            "WHERE guild_id = ? AND channel_id = ? AND paused = 0",
            (at, guild_id, row["channel_id"]),
        )
    for key, change in found["modes"].items():
        await db.conn.execute(
            "UPDATE settings SET value = ?, updated_by = NULL, updated_at = ? "
            "WHERE guild_id = ? AND key = ?",
            (json.dumps(change["after"]), at, guild_id, key),
        )
    if found["drop"]:
        await db.conn.execute(
            f"DELETE FROM settings WHERE guild_id = ? AND key IN "
            f"({', '.join('?' for _ in found['drop'])})",
            (guild_id, *found["drop"]),
        )
    await db.conn.commit()


async def _logged(bot: Any, found: dict[str, Any]) -> None:
    guild = discord.Object(id=found["guild_id"])
    for row in found["pause"]:
        await log_action(
            bot, guild, "sticky.paused_by_migration", details=row | {"build": BUILD}
        )
    if found["drop"] or found["modes"]:
        await log_action(
            bot,
            guild,
            "settings.migrated",
            details={
                "build": BUILD,
                "removed": sorted(found["drop"]),
                "values": found["drop"],
                "modes": found["modes"],
            },
        )


async def apply(bot: Any) -> list[dict[str, Any]]:
    """Idempotent: a second boot finds nothing to change and writes no row."""
    done = await dry_run(bot.db)
    at = datetime.now(UTC).isoformat()
    for found in done:
        await _write(bot.db, found, at)
        try:
            await _logged(bot, found)
        except Exception as exc:
            log.warning(
                "posts switch: a migration row was not written — %s: %s", type(exc).__name__, exc
            )
    if done:
        log.info("posts switch: migrated %d guild(s)", len(done))
    return done


__all__ = [
    "MIGRATED_KIND",
    "MODE_MAPS",
    "PAUSED_KIND",
    "RETIRED_KEYS",
    "apply",
    "dry_run",
    "guild_ids",
    "is_empty",
    "plan",
]
