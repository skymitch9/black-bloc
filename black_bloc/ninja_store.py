from __future__ import annotations

import sqlite3
from typing import Any

RECENT_LIMIT = 50
POSTS = "posts"
TIME = "time"
STAFF = "staff"


async def add(
    db: Any,
    guild_id: int,
    user_id: int,
    channel_id: int,
    emoji: str,
    posts_left: int | None,
    until: str | None,
    made_by: int | None,
    made_at: str,
) -> int | None:
    """The new mark's id, or None when the member already has an active one in that channel."""
    try:
        cur = await db.conn.execute(
            "INSERT INTO ninja_marks(guild_id, user_id, channel_id, emoji, posts_left, until, "
            "made_by, made_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                int(guild_id),
                int(user_id),
                int(channel_id),
                emoji,
                posts_left,
                until,
                made_by,
                made_at,
            ),
        )
    except sqlite3.IntegrityError:
        return None
    await db.conn.commit()
    return int(cur.lastrowid)


async def get(db: Any, guild_id: int, mark_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM ninja_marks WHERE guild_id = ? AND id = ?", (int(guild_id), int(mark_id))
    )
    return await cur.fetchone()


async def active(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM ninja_marks WHERE guild_id = ? AND ended_at IS NULL ORDER BY made_at, id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def active_everywhere(db: Any) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT guild_id, user_id, channel_id FROM ninja_marks WHERE ended_at IS NULL"
    )
    return list(await cur.fetchall())


async def active_for(db: Any, guild_id: int, user_id: int, channel_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM ninja_marks WHERE guild_id = ? AND user_id = ? AND channel_id = ? "
        "AND ended_at IS NULL LIMIT 1",
        (int(guild_id), int(user_id), int(channel_id)),
    )
    return await cur.fetchone()


async def recent_ended(db: Any, guild_id: int, limit: int = RECENT_LIMIT) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM ninja_marks WHERE guild_id = ? AND ended_at IS NOT NULL "
        "ORDER BY ended_at DESC, id DESC LIMIT ?",
        (int(guild_id), int(limit)),
    )
    return list(await cur.fetchall())


async def due(db: Any, now: str) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM ninja_marks WHERE ended_at IS NULL "
        "AND ((until IS NOT NULL AND until <= ?) OR posts_left <= 0) ORDER BY id",
        (now,),
    )
    return list(await cur.fetchall())


async def claim_post(db: Any, mark_id: int, now: str) -> bool:
    """One post taken from a live mark, in one statement, so two posts cannot share the last."""
    cur = await db.conn.execute(
        "UPDATE ninja_marks SET posts_left = CASE WHEN posts_left IS NULL THEN NULL "
        "ELSE posts_left - 1 END WHERE id = ? AND ended_at IS NULL "
        "AND (posts_left IS NULL OR posts_left > 0) AND (until IS NULL OR until > ?)",
        (int(mark_id), now),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def give_back(db: Any, mark_id: int) -> None:
    await db.conn.execute(
        "UPDATE ninja_marks SET posts_left = posts_left + 1 "
        "WHERE id = ? AND posts_left IS NOT NULL",
        (int(mark_id),),
    )
    await db.conn.commit()


async def end(db: Any, mark_id: int, because: str, now: str) -> bool:
    """True for the one caller that ended it; a second end of the same mark changes nothing."""
    cur = await db.conn.execute(
        "UPDATE ninja_marks SET ended_at = ?, ended_because = ? WHERE id = ? AND ended_at IS NULL",
        (now, because, int(mark_id)),
    )
    await db.conn.commit()
    return bool(cur.rowcount)
