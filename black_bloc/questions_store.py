from __future__ import annotations

from datetime import datetime
from typing import Any

from .questions import PENDING, QUEUED, REMOVED

HISTORY_LIMIT = 100


async def add_many(db: Any, guild_id: int, bodies: list[str], by: Any, now: datetime) -> list[int]:
    cur = await db.conn.execute(
        "SELECT COALESCE(MAX(position), 0) AS top FROM weekly_questions WHERE guild_id = ?",
        (int(guild_id),),
    )
    top = int((await cur.fetchone())["top"])
    ids: list[int] = []
    for place, body in enumerate(bodies, start=1):
        cur = await db.conn.execute(
            "INSERT INTO weekly_questions(guild_id, position, body, status, added_by, added_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (int(guild_id), top + place, body, QUEUED, by, now.isoformat()),
        )
        ids.append(int(cur.lastrowid))
    await db.conn.commit()
    return ids


async def get(db: Any, guild_id: int, question_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM weekly_questions WHERE guild_id = ? AND id = ?",
        (int(guild_id), int(question_id)),
    )
    return await cur.fetchone()


async def queued(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM weekly_questions WHERE guild_id = ? AND status = ? ORDER BY position, id",
        (int(guild_id), QUEUED),
    )
    return list(await cur.fetchall())


async def first_queued(db: Any, guild_id: int) -> Any:
    rows = await queued(db, guild_id)
    return rows[0] if rows else None


async def history(db: Any, guild_id: int, limit: int = HISTORY_LIMIT) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM weekly_questions WHERE guild_id = ? AND status != ? "
        "ORDER BY COALESCE(resolved_at, added_at) DESC, id DESC LIMIT ?",
        (int(guild_id), QUEUED, int(limit)),
    )
    return list(await cur.fetchall())


async def edit_body(db: Any, question_id: int, body: str) -> None:
    await db.conn.execute(
        "UPDATE weekly_questions SET body = ? WHERE id = ?", (body, int(question_id))
    )
    await db.conn.commit()


async def set_removed(db: Any, question_id: int, now: datetime) -> None:
    await db.conn.execute(
        "UPDATE weekly_questions SET status = ?, resolved_at = ? WHERE id = ?",
        (REMOVED, now.isoformat(), int(question_id)),
    )
    await db.conn.commit()


async def swap(db: Any, one: Any, other: Any) -> None:
    await db.conn.execute(
        "UPDATE weekly_questions SET position = ? WHERE id = ?", (other["position"], one["id"])
    )
    await db.conn.execute(
        "UPDATE weekly_questions SET position = ? WHERE id = ?", (one["position"], other["id"])
    )
    await db.conn.commit()


async def back_in_queue(db: Any, guild_id: int, question_id: int, *, top: bool) -> None:
    """Queued again with no trace of a post, first or last."""
    edge = "MIN(position) - 1" if top else "MAX(position) + 1"
    cur = await db.conn.execute(
        f"SELECT COALESCE({edge}, 1) AS place FROM weekly_questions "
        "WHERE guild_id = ? AND status = ?",
        (int(guild_id), QUEUED),
    )
    place = int((await cur.fetchone())["place"])
    await db.conn.execute(
        "UPDATE weekly_questions SET status = ?, position = ?, slot_at = NULL, posted_by = NULL, "
        "channel_id = NULL, message_id = NULL, resolved_at = NULL WHERE id = ?",
        (QUEUED, place, int(question_id)),
    )
    await db.conn.commit()


async def mark_posted(
    db: Any,
    question_id: int,
    slot_at: str | None,
    by: str,
    channel_id: int,
    message_id: int,
    now: datetime,
) -> None:
    await db.conn.execute(
        "UPDATE weekly_questions SET status = 'posted', slot_at = ?, posted_by = ?, "
        "channel_id = ?, message_id = ?, resolved_at = ? WHERE id = ?",
        (slot_at, by, int(channel_id), int(message_id), now.isoformat(), int(question_id)),
    )
    await db.conn.commit()


async def get_slot(db: Any, guild_id: int, slot_at: str) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM weekly_question_slots WHERE guild_id = ? AND slot_at = ?",
        (int(guild_id), slot_at),
    )
    return await cur.fetchone()


async def settled_from(db: Any, guild_id: int, slot_at: str) -> set[str]:
    cur = await db.conn.execute(
        "SELECT slot_at FROM weekly_question_slots WHERE guild_id = ? AND slot_at >= ? "
        "AND status != ?",
        (int(guild_id), slot_at, PENDING),
    )
    return {str(row["slot_at"]) for row in await cur.fetchall()}


async def ensure_slot(db: Any, guild_id: int, slot_at: str, now: datetime) -> Any:
    await db.conn.execute(
        "INSERT OR IGNORE INTO weekly_question_slots(guild_id, slot_at, status, seen_at) "
        "VALUES (?, ?, ?, ?)",
        (int(guild_id), slot_at, PENDING, now.isoformat()),
    )
    await db.conn.commit()
    return await get_slot(db, guild_id, slot_at)


async def set_slot(
    db: Any,
    guild_id: int,
    slot_at: str,
    status: str,
    now: datetime,
    *,
    question_id: int | None = None,
) -> None:
    resolved = None if status == PENDING else now.isoformat()
    await db.conn.execute(
        "UPDATE weekly_question_slots SET status = ?, question_id = ?, resolved_at = ?, "
        "note = NULL WHERE guild_id = ? AND slot_at = ?",
        (status, question_id, resolved, int(guild_id), slot_at),
    )
    await db.conn.commit()


async def set_note(db: Any, guild_id: int, slot_at: str, note: str | None) -> None:
    await db.conn.execute(
        "UPDATE weekly_question_slots SET note = ? WHERE guild_id = ? AND slot_at = ?",
        (note, int(guild_id), slot_at),
    )
    await db.conn.commit()


async def set_warned(db: Any, guild_id: int, slot_at: str, now: datetime) -> None:
    await db.conn.execute(
        "UPDATE weekly_question_slots SET warned_at = ? WHERE guild_id = ? AND slot_at = ?",
        (now.isoformat(), int(guild_id), slot_at),
    )
    await db.conn.commit()


async def slot_of_question(db: Any, guild_id: int, question_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM weekly_question_slots WHERE guild_id = ? AND question_id = ? "
        "ORDER BY slot_at DESC LIMIT 1",
        (int(guild_id), int(question_id)),
    )
    return await cur.fetchone()


async def latest_posted(db: Any, guild_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM weekly_questions WHERE guild_id = ? AND status = 'posted' "
        "ORDER BY resolved_at DESC, id DESC LIMIT 1",
        (int(guild_id),),
    )
    return await cur.fetchone()
