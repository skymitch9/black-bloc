"""Structure snapshots in SQLite: stored once per distinct structure, pruned by count."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .structure import FAILED, SAVED, UNCHANGED, canonical, counts, digest

LIST_COLUMNS = (
    "id, guild_id, taken_at, source, taken_by, digest, roles, categories, channels, "
    "overwrites, checked_at, checks"
)
LIST_LIMIT = 200


@dataclass(frozen=True)
class Stored:
    """What one look left behind: a new row, or the row that already held this structure."""

    outcome: str
    row: Any
    previous: Any = None
    pruned: int = 0


def stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).astimezone(UTC).isoformat()


async def latest(db: Any, guild_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM structure_snapshots WHERE guild_id = ? ORDER BY id DESC LIMIT 1",
        (guild_id,),
    )
    return await cur.fetchone()


async def get(db: Any, guild_id: int, snapshot_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM structure_snapshots WHERE guild_id = ? AND id = ?",
        (guild_id, snapshot_id),
    )
    return await cur.fetchone()


async def listed(db: Any, guild_id: int, limit: int = LIST_LIMIT) -> list[Any]:
    """Newest first, without the bodies."""
    cur = await db.conn.execute(
        f"SELECT {LIST_COLUMNS} FROM structure_snapshots WHERE guild_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (guild_id, max(1, int(limit))),
    )
    return list(await cur.fetchall())


async def count(db: Any, guild_id: int) -> int:
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM structure_snapshots WHERE guild_id = ?", (guild_id,)
    )
    return int((await cur.fetchone())["n"])


async def prune(db: Any, guild_id: int, keep: int) -> int:
    """The oldest beyond `keep` go; the newest is never one of them."""
    cur = await db.conn.execute(
        "DELETE FROM structure_snapshots WHERE guild_id = ? AND id NOT IN ("
        "SELECT id FROM structure_snapshots WHERE guild_id = ? ORDER BY id DESC LIMIT ?)",
        (guild_id, guild_id, max(1, int(keep))),
    )
    await db.conn.commit()
    return int(cur.rowcount or 0)


async def store(
    db: Any,
    guild_id: int,
    body: Any,
    *,
    source: str,
    taken_by: int | None = None,
    keep: int,
    now: datetime | None = None,
) -> Stored:
    """A structure already held is looked at, not copied; a new one is stored and the tail cut."""
    at = stamp(now)
    mark = digest(body)
    previous = await latest(db, guild_id)
    if previous is not None and previous["digest"] == mark:
        await db.conn.execute(
            "UPDATE structure_snapshots SET checked_at = ?, checks = checks + 1 WHERE id = ?",
            (at, previous["id"]),
        )
        await db.conn.commit()
        return Stored(UNCHANGED, await get(db, guild_id, previous["id"]), previous)
    found = counts(body)
    cur = await db.conn.execute(
        "INSERT INTO structure_snapshots(guild_id, taken_at, source, taken_by, digest, roles, "
        "categories, channels, overwrites, checked_at, checks, body) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
        (
            guild_id,
            at,
            source,
            taken_by,
            mark,
            found["roles"],
            found["categories"],
            found["channels"],
            found["overwrites"],
            at,
            canonical(body),
        ),
    )
    await db.conn.commit()
    pruned = await prune(db, guild_id, keep)
    return Stored(SAVED, await get(db, guild_id, cur.lastrowid), previous, pruned)


async def look(db: Any, guild_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM structure_looks WHERE guild_id = ?", (guild_id,))
    return await cur.fetchone()


async def record_look(
    db: Any,
    guild_id: int,
    outcome: str,
    *,
    day: str | None = None,
    reason: str | None = None,
    now: datetime | None = None,
) -> None:
    """`day` is given by the daily run only, so a look by hand never spends the day's turn."""
    before = await look(db, guild_id)
    last_day = before["last_day"] if before is not None else None
    attempts = int(before["attempts"]) if before is not None else 0
    if day is not None:
        if outcome != FAILED:
            attempts = 0
        elif last_day == day:
            attempts += 1
        else:
            attempts = 1
        last_day = day
    await db.conn.execute(
        "INSERT OR REPLACE INTO structure_looks(guild_id, last_at, last_day, outcome, reason, "
        "attempts) VALUES (?, ?, ?, ?, ?, ?)",
        (guild_id, stamp(now), last_day, outcome, reason, attempts),
    )
    await db.conn.commit()


def daily_due(found: Any, day: str, *, retries: int) -> bool:
    """Not yet looked at today, or today's look failed and has tries left."""
    if found is None or found["last_day"] != day:
        return True
    return found["outcome"] == FAILED and int(found["attempts"]) < int(retries)


__all__ = [
    "LIST_LIMIT",
    "Stored",
    "count",
    "daily_due",
    "get",
    "latest",
    "listed",
    "look",
    "prune",
    "record_look",
    "stamp",
    "store",
]
