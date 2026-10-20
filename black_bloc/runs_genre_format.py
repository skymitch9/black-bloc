"""One genre spelling: every stored baf_series.genre goes through genre_format once, at boot."""

from __future__ import annotations

import logging
from typing import Any

import discord

from .actionlog import log_action
from .runs_genres import genre_format, parse_families, parse_qualifiers, parse_upper
from .settings_store import RUNS_GENRE_FAMILIES, RUNS_GENRE_QUALIFIERS, RUNS_GENRE_UPPER

log = logging.getLogger(__name__)

BUILD = "runs-genre-format"
GENRE_LIMIT = 100


def _format_of(store: Any, guild_id: int) -> Any:
    qualifiers = parse_qualifiers(store.get(guild_id, RUNS_GENRE_QUALIFIERS))
    families = parse_families(store.get(guild_id, RUNS_GENRE_FAMILIES))
    upper = parse_upper(store.get(guild_id, RUNS_GENRE_UPPER))

    def shaped(text: Any) -> str:
        return genre_format(text, qualifiers, families, upper)[:GENRE_LIMIT]

    return shaped


async def dry_run(db: Any, store: Any) -> list[dict[str, Any]]:
    """Every stored genre whose house spelling differs, and nothing written."""
    cur = await db.conn.execute(
        "SELECT guild_id, game_key, genre FROM baf_series WHERE genre != '' "
        "ORDER BY guild_id, game_key"
    )
    found: list[dict[str, Any]] = []
    shapers: dict[int, Any] = {}
    for row in await cur.fetchall():
        guild_id = int(row["guild_id"])
        shaped = shapers.setdefault(guild_id, _format_of(store, guild_id))
        after = shaped(row["genre"])
        if after != row["genre"]:
            found.append(
                {
                    "guild_id": guild_id,
                    "game_key": row["game_key"],
                    "before": row["genre"],
                    "after": after,
                }
            )
    return found


async def _logged(bot: Any, guild_id: int, changes: list[dict[str, Any]]) -> None:
    await log_action(
        bot,
        discord.Object(id=guild_id),
        "runs.migrated",
        details={
            "build": BUILD,
            "rewritten": len(changes),
            "genres": {one["game_key"]: [one["before"], one["after"]] for one in changes},
        },
    )


async def apply(bot: Any) -> list[dict[str, Any]]:
    """Idempotent: genre_format of a formatted genre is itself, so a second boot writes nothing."""
    done = await dry_run(bot.db, bot.store)
    for one in done:
        await bot.db.conn.execute(
            "UPDATE baf_series SET genre = ? WHERE guild_id = ? AND game_key = ?",
            (one["after"], one["guild_id"], one["game_key"]),
        )
    if done:
        await bot.db.conn.commit()
    for guild_id in sorted({one["guild_id"] for one in done}):
        try:
            await _logged(bot, guild_id, [one for one in done if one["guild_id"] == guild_id])
        except Exception as exc:
            log.warning(
                "runs genre format: a migration row was not written — %s: %s",
                type(exc).__name__,
                exc,
            )
    if done:
        log.info("runs genre format: %d game(s) rewritten", len(done))
    return done


__all__ = ["BUILD", "apply", "dry_run"]
