from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

log = logging.getLogger(__name__)

NOTE_CHARS = 240


def clean_note(value: Any) -> str:
    return " ".join(str(value or "").split())


async def notes_for(db: Any, guild_id: Any) -> dict[int, str]:
    cur = await db.conn.execute(
        "SELECT channel_id, note FROM channel_notes WHERE guild_id = ?", (int(guild_id),)
    )
    return {int(row["channel_id"]): str(row["note"]) for row in await cur.fetchall()}


async def notes_or_nothing(db: Any, guild_id: Any) -> dict[int, str]:
    """A note that cannot be read never costs an answer — the topics are still there."""
    if db is None or guild_id is None or not getattr(db, "is_connected", False):
        return {}
    try:
        return await notes_for(db, guild_id)
    except Exception as exc:
        log.warning("channel notes: unreadable, so the topics stand alone — %s", exc)
        return {}


async def get_note(db: Any, guild_id: Any, channel_id: Any) -> Any:
    cur = await db.conn.execute(
        "SELECT guild_id, channel_id, note, set_by, set_at FROM channel_notes "
        "WHERE guild_id = ? AND channel_id = ?",
        (int(guild_id), int(channel_id)),
    )
    return await cur.fetchone()


async def set_note(
    db: Any, guild_id: Any, channel_id: Any, note: str, *, by: Any = None, at: Any = None
) -> None:
    await db.conn.execute(
        "INSERT INTO channel_notes(guild_id, channel_id, note, set_by, set_at) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(guild_id, channel_id) DO UPDATE SET "
        "note = excluded.note, set_by = excluded.set_by, set_at = excluded.set_at",
        (
            int(guild_id),
            int(channel_id),
            str(note),
            int(by) if by else None,
            str(at or datetime.now(UTC).isoformat()),
        ),
    )
    await db.conn.commit()


async def clear_note(db: Any, guild_id: Any, channel_id: Any) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM channel_notes WHERE guild_id = ? AND channel_id = ?",
        (int(guild_id), int(channel_id)),
    )
    await db.conn.commit()
    return bool(cur.rowcount and cur.rowcount > 0)
