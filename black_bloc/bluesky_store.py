from __future__ import annotations

from datetime import datetime
from typing import Any

from .bluesky import CLAIMED, FAILED, POSTED, RETRY, Item

RECLAIMABLE_BY_LOOP = (RETRY,)
NOT_RECLAIMABLE = (CLAIMED, POSTED)


async def get(db: Any, guild_id: int, uri: str) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM bluesky_posts WHERE guild_id = ? AND uri = ?", (int(guild_id), uri)
    )
    return await cur.fetchone()


async def known(db: Any, guild_id: int, uris: list[str]) -> dict[str, Any]:
    if not uris:
        return {}
    marks = ", ".join("?" for _ in uris)
    cur = await db.conn.execute(
        f"SELECT * FROM bluesky_posts WHERE guild_id = ? AND uri IN ({marks})",
        (int(guild_id), *uris),
    )
    return {str(row["uri"]): row for row in await cur.fetchall()}


async def record(db: Any, guild_id: int, item: Item, status: str, now: datetime) -> bool:
    """A first sighting that is not posted; True when this call wrote it."""
    cur = await db.conn.execute(
        "INSERT OR IGNORE INTO bluesky_posts(guild_id, uri, cid, kind, author_handle, "
        "indexed_at, text, status, seen_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        _row(guild_id, item, status, now),
    )
    await db.conn.commit()
    return cur.rowcount == 1


async def claim(
    db: Any, guild_id: int, item: Item, now: datetime, *, over: tuple[str, ...] = ()
) -> bool:
    """The once-guard: one conditional INSERT, taking a row only from a status in `over`."""
    allowed = ", ".join("?" for _ in over) or "NULL"
    cur = await db.conn.execute(
        "INSERT INTO bluesky_posts(guild_id, uri, cid, kind, author_handle, indexed_at, text, "
        "status, seen_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(guild_id, uri) DO UPDATE SET status = excluded.status "
        f"WHERE bluesky_posts.status IN ({allowed})",
        (*_row(guild_id, item, CLAIMED, now), *over),
    )
    await db.conn.commit()
    return cur.rowcount == 1


def _row(guild_id: int, item: Item, status: str, now: datetime) -> tuple[Any, ...]:
    return (
        int(guild_id),
        item.uri,
        item.cid,
        item.kind,
        item.handle,
        item.indexed_at,
        item.text,
        status,
        now.isoformat(),
    )


async def settle(
    db: Any,
    guild_id: int,
    uri: str,
    status: str,
    now: datetime,
    *,
    channel_id: int | None = None,
    message_id: int | None = None,
) -> None:
    await db.conn.execute(
        "UPDATE bluesky_posts SET status = ?, channel_id = ?, message_id = ?, posted_at = ? "
        "WHERE guild_id = ? AND uri = ?",
        (
            status,
            channel_id,
            message_id,
            now.isoformat() if message_id else None,
            int(guild_id),
            uri,
        ),
    )
    await db.conn.commit()


async def let_go(db: Any, guild_id: int, uri: str, retried: bool) -> str:
    """A failed send: back to unclaimed once, then failed for good."""
    status = FAILED if retried else RETRY
    await db.conn.execute(
        "UPDATE bluesky_posts SET status = ? WHERE guild_id = ? AND uri = ?",
        (status, int(guild_id), uri),
    )
    await db.conn.commit()
    return status


async def recent(db: Any, guild_id: int, limit: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM bluesky_posts WHERE guild_id = ? "
        "ORDER BY COALESCE(posted_at, seen_at) DESC, rowid DESC LIMIT ?",
        (int(guild_id), int(limit)),
    )
    return list(await cur.fetchall())


async def prune(db: Any, guild_id: int, keep: int) -> int:
    cur = await db.conn.execute(
        "DELETE FROM bluesky_posts WHERE guild_id = ? AND rowid NOT IN ("
        "SELECT rowid FROM bluesky_posts WHERE guild_id = ? "
        "ORDER BY seen_at DESC, rowid DESC LIMIT ?)",
        (int(guild_id), int(guild_id), int(keep)),
    )
    await db.conn.commit()
    return int(cur.rowcount or 0)


async def get_read(db: Any, guild_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM bluesky_reads WHERE guild_id = ?", (int(guild_id),))
    return await cur.fetchone()


async def read_ok(db: Any, guild_id: int, now: datetime) -> None:
    stamp = now.isoformat()
    await db.conn.execute(
        "INSERT INTO bluesky_reads(guild_id, last_read_at, last_ok_at, failures, last_error) "
        "VALUES (?, ?, ?, 0, NULL) ON CONFLICT(guild_id) DO UPDATE SET "
        "last_read_at = excluded.last_read_at, last_ok_at = excluded.last_ok_at, "
        "failures = 0, last_error = NULL",
        (int(guild_id), stamp, stamp),
    )
    await db.conn.commit()


async def read_failed(db: Any, guild_id: int, now: datetime, why: str) -> int:
    """The failure count after this one."""
    await db.conn.execute(
        "INSERT INTO bluesky_reads(guild_id, last_read_at, failures, last_error) "
        "VALUES (?, ?, 1, ?) ON CONFLICT(guild_id) DO UPDATE SET "
        "last_read_at = excluded.last_read_at, failures = bluesky_reads.failures + 1, "
        "last_error = excluded.last_error",
        (int(guild_id), now.isoformat(), why),
    )
    await db.conn.commit()
    row = await get_read(db, guild_id)
    return int(row["failures"])


async def set_error(db: Any, guild_id: int, why: str | None) -> bool:
    """True when the stored error changed, so a standing reason is logged once."""
    row = await get_read(db, guild_id)
    if row is not None and (row["last_error"] or None) == (why or None):
        return False
    await db.conn.execute(
        "INSERT INTO bluesky_reads(guild_id, failures, last_error) VALUES (?, 0, ?) "
        "ON CONFLICT(guild_id) DO UPDATE SET last_error = excluded.last_error",
        (int(guild_id), why),
    )
    await db.conn.commit()
    return True
