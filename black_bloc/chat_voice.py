"""Which tone each member hears on top of the cookout voice, and the staff pin that fixes it."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .personas import COOKOUT, POOL, Trope, enabled_tropes, from_the_pool, pick_trope

log = logging.getLogger(__name__)

WINDOW_MINUTES = 30
PINNED = "pinned"
NAMED = "named"
ROLLED = "rolled"


@dataclass(frozen=True)
class Heard:
    trope: Trope | None
    source: str = COOKOUT
    turns: int = 0
    since: str | None = None

    @property
    def name(self) -> str:
        return self.trope.name if self.trope is not None else COOKOUT


def voice_key(guild_id: Any, user_id: Any, since: Any) -> str:
    return f"{int(guild_id or 0)}:{int(user_id or 0)}:{since}"


def window_start(now: datetime, minutes: int = WINDOW_MINUTES) -> str:
    return (now - timedelta(minutes=minutes)).isoformat()


async def voice_row(db: Any, guild_id: Any, user_id: Any) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM chat_voice WHERE guild_id = ? AND user_id = ?",
        (int(guild_id), int(user_id)),
    )
    return await cur.fetchone()


async def window_turns(db: Any, guild_id: Any, user_id: Any, *, now: datetime) -> int:
    """Model turns this member had anywhere in the server in the last half hour."""
    cur = await db.conn.execute(
        "SELECT COUNT(*) FROM chat_window WHERE guild_id = ? AND user_id = ? AND at >= ? "
        "AND tier IS NOT NULL",
        (int(guild_id), int(user_id), window_start(now)),
    )
    row = await cur.fetchone()
    return int((row[0] if row is not None else 0) or 0)


async def talking_now(db: Any, guild_id: Any, *, now: datetime) -> dict[int, int]:
    cur = await db.conn.execute(
        "SELECT user_id, COUNT(*) AS n FROM chat_window WHERE guild_id = ? AND at >= ? "
        "AND tier IS NOT NULL GROUP BY user_id",
        (int(guild_id), window_start(now)),
    )
    return {int(row["user_id"]): int(row["n"]) for row in await cur.fetchall()}


def heard_from(
    setting: Any,
    rows: Any,
    row: Any,
    *,
    guild_id: Any,
    user_id: Any,
    turns: int,
    now: datetime,
) -> Heard:
    """cookout for everyone > a member's pin > a named server mood > the member's own roll."""
    said = str(setting or COOKOUT).strip().lower()
    if said == COOKOUT:
        return Heard(None)
    fresh = turns <= 0 or row is None or not row["since"]
    since = now.isoformat() if fresh else str(row["since"])
    counted = 0 if turns <= 0 else int(turns)
    pool = enabled_tropes(rows)
    pinned = str(row["pinned"] or "") if row is not None else ""
    if pinned:
        found = next((one for one in pool if one.name == pinned), None)
        if found is not None:
            return Heard(found, PINNED, counted, since)
        log.info("chat_voice: %s is pinned to %s, which is off", user_id, pinned)
    if said != POOL:
        found = pick_trope(said, rows)
        return Heard(found, NAMED if found else COOKOUT, counted, since)
    rolled = from_the_pool(pool, voice_key(guild_id, user_id, since), counted)
    return Heard(rolled, ROLLED if rolled else COOKOUT, counted, since)


async def remember_heard(db: Any, guild_id: Any, user_id: Any, heard: Heard) -> None:
    await db.conn.execute(
        "INSERT INTO chat_voice(guild_id, user_id, trope, turns, since) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(guild_id, user_id) DO UPDATE SET trope = excluded.trope, "
        "turns = excluded.turns, since = excluded.since",
        (int(guild_id), int(user_id), heard.name, heard.turns, heard.since),
    )
    await db.conn.commit()


async def heard_for(
    db: Any, setting: Any, rows: Any, *, guild_id: Any, user_id: Any, now: datetime | None = None
) -> Heard:
    """The tone for one reply, written down so the same member hears it in every channel."""
    at = now or datetime.now(UTC)
    if str(setting or COOKOUT).strip().lower() == COOKOUT:
        return Heard(None)
    try:
        row = await voice_row(db, guild_id, user_id)
        turns = await window_turns(db, guild_id, user_id, now=at)
    except Exception as exc:
        log.warning("chat_voice: the member's tone was not read — %s: %s", type(exc).__name__, exc)
        row, turns = None, 0
    heard = heard_from(
        setting, rows, row, guild_id=guild_id, user_id=user_id, turns=turns, now=at
    )
    if heard.trope is None:
        return heard
    try:
        await remember_heard(db, guild_id, user_id, heard)
    except Exception as exc:
        log.warning("chat_voice: the member's tone was not kept — %s: %s", type(exc).__name__, exc)
    return heard


async def pin(db: Any, guild_id: Any, user_id: Any, trope: str, *, by: Any = None) -> None:
    at = datetime.now(UTC).isoformat()
    await db.conn.execute(
        "INSERT INTO chat_voice(guild_id, user_id, pinned, pinned_by, pinned_at) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(guild_id, user_id) DO UPDATE SET "
        "pinned = excluded.pinned, pinned_by = excluded.pinned_by, pinned_at = excluded.pinned_at",
        (int(guild_id), int(user_id), str(trope), by, at),
    )
    await db.conn.commit()


async def unpin(db: Any, guild_id: Any, user_id: Any) -> bool:
    cur = await db.conn.execute(
        "UPDATE chat_voice SET pinned = NULL, pinned_by = NULL, pinned_at = NULL "
        "WHERE guild_id = ? AND user_id = ? AND pinned IS NOT NULL",
        (int(guild_id), int(user_id)),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def voice_rows(db: Any, guild_id: Any) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM chat_voice WHERE guild_id = ? "
        "ORDER BY pinned IS NULL, COALESCE(since, pinned_at) DESC, user_id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


def hears_now(setting: Any, row: Any, enabled: set[str]) -> str:
    """What the member's next answer is written in, as far as it can be known before it."""
    said = str(setting or COOKOUT).strip().lower()
    if said == COOKOUT:
        return COOKOUT
    pinned = str(row["pinned"] or "")
    if pinned and pinned in enabled:
        return pinned
    if said != POOL:
        return said if said in enabled else COOKOUT
    return str(row["trope"] or COOKOUT)


def roster(rows: Any, setting: Any, enabled: Any, talking: dict[int, int]) -> list[dict[str, Any]]:
    """One entry per member with a row, in the shape both doors read."""
    live = set(enabled or ())
    found = []
    for row in rows or ():
        pinned = str(row["pinned"] or "") or None
        user_id = int(row["user_id"])
        found.append(
            {
                "user_id": user_id,
                "trope": hears_now(setting, row, live),
                "last_trope": row["trope"],
                "pinned": pinned,
                "pinned_by": row["pinned_by"],
                "pinned_at": row["pinned_at"],
                "waiting": bool(pinned) and pinned not in live,
                "since": row["since"],
                "turns": int(row["turns"] or 0),
                "active": user_id in talking,
            }
        )
    return found
