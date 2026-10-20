"""One opt-out table: every per-person opt-out store is copied into person_optouts once, at boot."""

from __future__ import annotations

import json
import logging
from typing import Any

import discord

from . import optouts
from .actionlog import log_action

log = logging.getLogger(__name__)

BUILD = "one-optout"
MIGRATED_KIND = "optouts.migrated"
CONSENT_KEY = "chat_memory_consent"
OPTIN = "optin"
NO_GUILD = "golive_optout has no guild column and the guild could not be named: {found} found"

SOURCES: dict[str, str] = {
    optouts.BIRTHDAY: (
        "SELECT guild_id, user_id, NULL AS by, set_at AS at FROM birthdays WHERE opted_in = 0"
    ),
    optouts.PBS: (
        "SELECT guild_id, user_id, set_by AS by, COALESCE(opted_out_at, updated_at) AS at "
        "FROM pb_matches WHERE state = 'opted_out'"
    ),
    optouts.STREAMER_LIST: (
        "SELECT guild_id, user_id, hidden_by AS by, COALESCE(hidden_at, last_live_at) AS at "
        "FROM streamers WHERE listed = 0 AND hidden_by IS NOT NULL"
    ),
}


async def _all(db: Any, sql: str, params: tuple = ()) -> list[Any]:
    try:
        cur = await db.conn.execute(sql, params)
        return list(await cur.fetchall())
    except Exception as exc:
        log.warning("one opt-out: a source was not read — %s: %s", type(exc).__name__, exc)
        return []


async def the_guild(db: Any, preferred: Any = None) -> tuple[int | None, int]:
    """The one guild golive_optout belongs to, and how many were seen."""
    if preferred:
        return int(preferred), 1
    found = {
        int(row[0])
        for row in await _all(
            db,
            "SELECT DISTINCT guild_id FROM settings UNION SELECT DISTINCT guild_id FROM "
            "golive_sessions",
        )
    }
    return (next(iter(found)), 1) if len(found) == 1 else (None, len(found))


async def _consent(db: Any, guild_id: int) -> str:
    rows = await _all(
        db,
        "SELECT value FROM settings WHERE guild_id = ? AND key = ?",
        (int(guild_id), CONSENT_KEY),
    )
    if not rows:
        return "optout"
    try:
        return str(json.loads(rows[0]["value"]))
    except (TypeError, ValueError):
        return str(rows[0]["value"])


async def _have(db: Any) -> set[tuple[int, int, str]]:
    return {
        (int(row["guild_id"]), int(row["user_id"]), str(row["kind"]))
        for row in await _all(db, "SELECT guild_id, user_id, kind FROM person_optouts")
    }


def _one(row: Any) -> dict[str, Any]:
    return {"user_id": int(row["user_id"]), "by": row["by"], "at": row["at"]}


async def sourced(db: Any, preferred: Any = None) -> tuple[dict[int, dict[str, list]], list[str]]:
    """Every per-person opt-out the old stores hold, by guild and kind."""
    found: dict[int, dict[str, list]] = {}
    notes: list[str] = []

    def put(guild_id: Any, kind: str, row: dict[str, Any]) -> None:
        found.setdefault(int(guild_id), {}).setdefault(kind, []).append(row)

    announce = await _all(db, "SELECT user_id, NULL AS by, at FROM golive_optout ORDER BY user_id")
    if announce:
        guild_id, seen = await the_guild(db, preferred)
        if guild_id is None:
            notes.append(NO_GUILD.format(found=seen))
        else:
            for row in announce:
                put(guild_id, optouts.ANNOUNCE, _one(row))
    for kind, sql in SOURCES.items():
        for row in await _all(db, f"{sql} ORDER BY guild_id, user_id"):
            put(row["guild_id"], kind, _one(row))
    memory = await _all(
        db,
        "SELECT guild_id, user_id, NULL AS by, at FROM chat_memory_optout "
        "ORDER BY guild_id, user_id",
    )
    for row in memory:
        consent = await _consent(db, int(row["guild_id"]))
        kind = optouts.CHAT_MEMORY_IN if consent == OPTIN else optouts.CHAT_MEMORY
        put(row["guild_id"], kind, _one(row))
    return found, notes


async def dry_run(db: Any, preferred: Any = None) -> list[dict[str, Any]]:
    """Every guild's rows that `apply` would copy, and nothing written."""
    found, notes = await sourced(db, preferred)
    have = await _have(db)
    plans: list[dict[str, Any]] = []
    for guild_id in sorted(found):
        write = {
            kind: [one for one in people if (guild_id, one["user_id"], kind) not in have]
            for kind, people in sorted(found[guild_id].items())
        }
        write = {kind: people for kind, people in write.items() if people}
        if write:
            plans.append(
                {
                    "guild_id": guild_id,
                    "write": write,
                    "counts": {kind: len(people) for kind, people in write.items()},
                    "notes": [],
                }
            )
    if notes and plans:
        plans[0]["notes"] = notes
    elif notes:
        log.warning("one opt-out: %s", "; ".join(notes))
    return plans


async def _write(db: Any, plan: dict[str, Any]) -> None:
    for kind, people in plan["write"].items():
        for one in people:
            await db.conn.execute(
                "INSERT OR IGNORE INTO person_optouts(guild_id, user_id, kind, by, reason, at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    plan["guild_id"],
                    one["user_id"],
                    kind,
                    int(one["by"]) if one["by"] else None,
                    optouts.MIGRATED,
                    str(one["at"] or ""),
                ),
            )
    await db.conn.commit()


async def apply(bot: Any) -> list[dict[str, Any]]:
    """Idempotent: a second boot finds every row already copied, writes nothing, logs nothing."""
    preferred = getattr(getattr(bot, "settings", None), "dev_guild_id", None)
    done = await dry_run(bot.db, preferred)
    for plan in done:
        await _write(bot.db, plan)
        try:
            await log_action(
                bot,
                discord.Object(id=plan["guild_id"]),
                MIGRATED_KIND,
                details={"build": BUILD, "counts": plan["counts"], "notes": plan["notes"]},
            )
        except Exception as exc:
            log.warning(
                "one opt-out: a migration row was not written — %s: %s",
                type(exc).__name__,
                exc,
            )
    await optouts.load(bot.db)
    if done:
        log.info("one opt-out: %d guild(s) migrated", len(done))
    return done


__all__ = ["BUILD", "MIGRATED_KIND", "apply", "dry_run", "sourced", "the_guild"]
