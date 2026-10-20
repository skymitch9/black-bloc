"""Shadow has one meaning: folded and retired switches leave the settings table once, at boot."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import discord

from .actionlog import log_action

log = logging.getLogger(__name__)

YOUTUBE_LIVE = "youtube_live_mode"
SPOTLIGHT = "spotlight_mode"
GREETING = "chat_greeting_via_model"
GOLIVE_MODE = "golive_mode"
GOLIVE_YOUTUBE = "golive_youtube"
RETIRED_KEYS: tuple[str, ...] = (
    YOUTUBE_LIVE,
    SPOTLIGHT,
    "boot_status_mode",
    "handoff_mode",
    "golive_costream_mode",
    "modmail_enabled",
    "pb_feed_posting_shadow",
    "pb_feed_no_channel_words",
    "points_modmail_off_said",
    "youtube_mode",
    "rehearsal_note",
)
READ_KEYS: tuple[str, ...] = (*RETIRED_KEYS, GREETING, GOLIVE_MODE, GOLIVE_YOUTUBE)
YOUTUBE_WATCHES = {"on": True, "shadow": False, "off": False}
GREETING_FLAGS = {"on": True, "off": False}
OFF = "off"
MIGRATED_KIND = "settings.migrated"
BUILD = "shadow-one-meaning"
SPOTLIGHT_FOLLOWS = "spotlights now follow golive_mode"
YOUTUBE_SHADOW_WAS = "youtube_live_mode shadow only logged, so it maps to false"


def _loaded(text: Any) -> Any:
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text


async def guild_ids(db: Any) -> list[int]:
    keys = (*RETIRED_KEYS, GREETING)
    cur = await db.conn.execute(
        f"SELECT DISTINCT guild_id FROM settings WHERE key IN ({', '.join('?' for _ in keys)}) "
        "ORDER BY 1",
        keys,
    )
    return [int(row[0]) for row in await cur.fetchall()]


async def _stored(db: Any, guild_id: int) -> dict[str, Any]:
    cur = await db.conn.execute(
        f"SELECT key, value FROM settings WHERE guild_id = ? AND key IN "
        f"({', '.join('?' for _ in READ_KEYS)}) ORDER BY key",
        (int(guild_id), *READ_KEYS),
    )
    return {row["key"]: _loaded(row["value"]) for row in await cur.fetchall()}


def _youtube(stored: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    if YOUTUBE_LIVE not in stored or GOLIVE_YOUTUBE in stored:
        return {}, []
    was = str(stored[YOUTUBE_LIVE])
    write = {GOLIVE_YOUTUBE: {"before": None, "after": YOUTUBE_WATCHES.get(was, False)}}
    return write, [YOUTUBE_SHADOW_WAS] if was == "shadow" else []


def _greeting(stored: dict[str, Any]) -> dict[str, Any]:
    was = stored.get(GREETING)
    if not isinstance(was, str):
        return {}
    return {GREETING: {"before": was, "after": GREETING_FLAGS.get(was, True)}}


def _spotlight(stored: dict[str, Any], golive_default: Any) -> list[str]:
    golive = stored.get(GOLIVE_MODE, golive_default)
    if stored.get(SPOTLIGHT) == OFF and golive != OFF:
        return [f"{SPOTLIGHT_FOLLOWS}: spotlight_mode was off, golive_mode is {golive}"]
    return []


async def plan(db: Any, guild_id: int, golive_default: Any = "shadow") -> dict[str, Any]:
    """What `apply` would change in one guild, and nothing written."""
    stored = await _stored(db, guild_id)
    youtube, youtube_notes = _youtube(stored)
    return {
        "guild_id": int(guild_id),
        "drop": {key: stored[key] for key in RETIRED_KEYS if key in stored},
        "write": youtube | _greeting(stored),
        "notes": youtube_notes + _spotlight(stored, golive_default),
    }


def is_empty(found: dict[str, Any]) -> bool:
    return not (found["drop"] or found["write"])


async def dry_run(db: Any, golive_default: Any = "shadow") -> list[dict[str, Any]]:
    """Every guild's plan that would change something."""
    found = [await plan(db, guild_id, golive_default) for guild_id in await guild_ids(db)]
    return [one for one in found if not is_empty(one)]


async def _write(db: Any, found: dict[str, Any], at: str) -> None:
    guild_id = found["guild_id"]
    for key, change in found["write"].items():
        await db.conn.execute(
            "INSERT OR REPLACE INTO settings(guild_id, key, value, updated_by, updated_at) "
            "VALUES (?, ?, ?, NULL, ?)",
            (guild_id, key, json.dumps(change["after"]), at),
        )
    if found["drop"]:
        await db.conn.execute(
            f"DELETE FROM settings WHERE guild_id = ? AND key IN "
            f"({', '.join('?' for _ in found['drop'])})",
            (guild_id, *found["drop"]),
        )
    await db.conn.commit()


async def _logged(bot: Any, found: dict[str, Any]) -> None:
    await log_action(
        bot,
        discord.Object(id=found["guild_id"]),
        "settings.migrated",
        details={
            "build": BUILD,
            "removed": sorted(found["drop"]),
            "values": found["drop"],
            "written": found["write"],
            "notes": found["notes"],
        },
    )


async def apply(bot: Any) -> list[dict[str, Any]]:
    """Idempotent: a second boot finds no retired row and no string greeting, and writes nothing."""
    done = await dry_run(bot.db, bot.store.default(GOLIVE_MODE))
    at = datetime.now(UTC).isoformat()
    for found in done:
        await _write(bot.db, found, at)
        try:
            await _logged(bot, found)
        except Exception as exc:
            log.warning(
                "shadow one meaning: a migration row was not written — %s: %s",
                type(exc).__name__,
                exc,
            )
    if done:
        log.info("shadow one meaning: %d guild(s) migrated", len(done))
    return done


__all__ = [
    "BUILD",
    "MIGRATED_KIND",
    "RETIRED_KEYS",
    "apply",
    "dry_run",
    "guild_ids",
    "is_empty",
    "plan",
]
