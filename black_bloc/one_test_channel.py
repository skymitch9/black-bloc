"""One test channel: the per-feature rehearsal homes fold into shadow_channel_id, once, at boot."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import discord

from .actionlog import log_action
from .shadow import REHEARSAL_KEY, as_channel_id

log = logging.getLogger(__name__)

RETIRED_KEYS: tuple[str, ...] = (
    "posts_shadow_channel_id",
    "golive_shadow_channel_id",
    "marathon_shadow_channel_id",
    "marathon_public_shadow_channel_id",
    "birthday_shadow_channel_id",
    "pb_feed_shadow_channel_id",
    "brackets_shadow_channel_id",
    "points_shadow_channel_id",
)
MIGRATED_KIND = "settings.migrated"
SKIPPED_KIND = "settings.migration_skipped"
BUILD = "one-test-channel"


def _loaded(text: Any) -> Any:
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text


async def guild_ids(db: Any) -> list[int]:
    cur = await db.conn.execute(
        f"SELECT DISTINCT guild_id FROM settings WHERE key IN "
        f"({', '.join('?' for _ in RETIRED_KEYS)}) ORDER BY 1",
        RETIRED_KEYS,
    )
    return [int(row[0]) for row in await cur.fetchall()]


async def plan(db: Any, guild_id: int) -> dict[str, Any]:
    """What `apply` would change in one guild, and nothing written."""
    cur = await db.conn.execute(
        f"SELECT key, value FROM settings WHERE guild_id = ? AND key IN "
        f"({', '.join('?' for _ in RETIRED_KEYS)}) ORDER BY key",
        (int(guild_id), *RETIRED_KEYS),
    )
    stored = {row["key"]: _loaded(row["value"]) for row in await cur.fetchall()}
    cur = await db.conn.execute(
        "SELECT value FROM settings WHERE guild_id = ? AND key = ?", (int(guild_id), REHEARSAL_KEY)
    )
    row = await cur.fetchone()
    before = as_channel_id(_loaded(row["value"])) if row is not None else None
    set_to = {key: as_channel_id(value) for key, value in stored.items()}
    shared = sorted({value for value in set_to.values() if value is not None})
    found: dict[str, Any] = {"guild_id": int(guild_id), "copy": None, "drop": {}, "skipped": None}
    if len(shared) > 1:
        found["skipped"] = {
            "reason": "the set overrides disagree",
            "test_channel": before,
            "overrides": {key: value for key, value in set_to.items() if value is not None},
        }
        return found
    if shared and shared[0] != before:
        found["copy"] = {"key": REHEARSAL_KEY, "before": before, "after": shared[0]}
    found["drop"] = stored
    return found


def is_empty(found: dict[str, Any]) -> bool:
    return not (found["copy"] or found["drop"] or found["skipped"])


async def dry_run(db: Any) -> list[dict[str, Any]]:
    """Every guild's plan that would change or report something."""
    found = [await plan(db, guild_id) for guild_id in await guild_ids(db)]
    return [one for one in found if not is_empty(one)]


async def _write(db: Any, found: dict[str, Any], at: str) -> None:
    guild_id = found["guild_id"]
    if found["copy"]:
        await db.conn.execute(
            "INSERT OR REPLACE INTO settings(guild_id, key, value, updated_by, updated_at) "
            "VALUES (?, ?, ?, NULL, ?)",
            (guild_id, REHEARSAL_KEY, json.dumps(int(found["copy"]["after"])), at),
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
    if found["skipped"]:
        await log_action(
            bot, guild, "settings.migration_skipped", details={"build": BUILD, **found["skipped"]}
        )
        return
    await log_action(
        bot,
        guild,
        "settings.migrated",
        details={
            "build": BUILD,
            "removed": sorted(found["drop"]),
            "values": found["drop"],
            "copied": found["copy"],
        },
    )


async def apply(bot: Any) -> list[dict[str, Any]]:
    """Idempotent: a second boot changes nothing; a disagreement writes only its row."""
    done = await dry_run(bot.db)
    at = datetime.now(UTC).isoformat()
    for found in done:
        if not found["skipped"]:
            await _write(bot.db, found, at)
        try:
            await _logged(bot, found)
        except Exception as exc:
            log.warning(
                "one test channel: a migration row was not written — %s: %s",
                type(exc).__name__,
                exc,
            )
    if done:
        log.info("one test channel: %d guild(s) looked at", len(done))
    return done


__all__ = [
    "MIGRATED_KIND",
    "RETIRED_KEYS",
    "SKIPPED_KIND",
    "apply",
    "dry_run",
    "guild_ids",
    "is_empty",
    "plan",
]
