"""Runs and bounties in SQLite, and the members' approved totals the board is ranked from."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from .points.board import Row
from .points.model import APPROVED, PENDING

RUN_FIELDS = ("game", "category", "seconds", "proof_url", "note")
BOUNTY_FIELDS = ("name", "games", "kind", "amount", "event_id", "starts_at", "ends_at", "active")
LIST_LIMIT = 200


def stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).astimezone(UTC).isoformat()


async def add_run(
    db: Any, guild_id: int, user_id: int, values: dict[str, Any], at: str | None = None
) -> int:
    wanted = {key: values.get(key) for key in RUN_FIELDS}
    columns = ["guild_id", "user_id", *wanted, "submitted_at"]
    cur = await db.conn.execute(
        f"INSERT INTO points_runs({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
        (guild_id, user_id, *wanted.values(), at or stamp()),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def run(db: Any, guild_id: int, run_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM points_runs WHERE id = ? AND guild_id = ?", (run_id, guild_id)
    )
    return await cur.fetchone()


async def runs(
    db: Any,
    guild_id: int,
    *,
    state: str | None = None,
    user_id: int | None = None,
    limit: int = LIST_LIMIT,
) -> list[Any]:
    where, args = ["guild_id = ?"], [guild_id]
    if state is not None:
        where.append("state = ?")
        args.append(state)
    if user_id is not None:
        where.append("user_id = ?")
        args.append(user_id)
    newest = "ASC" if state == PENDING else "DESC"
    cur = await db.conn.execute(
        f"SELECT * FROM points_runs WHERE {' AND '.join(where)} ORDER BY id {newest} LIMIT ?",
        (*args, limit),
    )
    return list(await cur.fetchall())


async def update_run(
    db: Any, run_id: int, values: dict[str, Any], *, when_state: str | None = None
) -> bool:
    """One write; with `when_state` it only lands while the run is still in that state."""
    if not values:
        return True
    sets = ", ".join(f"{column} = ?" for column in values)
    guard, args = ("", ()) if when_state is None else (" AND state = ?", (when_state,))
    cur = await db.conn.execute(
        f"UPDATE points_runs SET {sets} WHERE id = ?{guard}", (*values.values(), run_id, *args)
    )
    await db.conn.commit()
    return cur.rowcount == 1


async def totals(db: Any, guild_id: int) -> list[Row]:
    cur = await db.conn.execute(
        "SELECT user_id, COUNT(*) AS runs, SUM(xp) AS xp, SUM(speedpoints) AS speedpoints, "
        "MAX(decided_at) AS last_at FROM points_runs WHERE guild_id = ? AND state = ? "
        "GROUP BY user_id",
        (guild_id, APPROVED),
    )
    return [
        Row(
            int(row["user_id"]),
            int(row["runs"]),
            int(row["xp"] or 0),
            int(row["speedpoints"] or 0),
            str(row["last_at"] or ""),
        )
        for row in await cur.fetchall()
    ]


def bounty_values(values: dict[str, Any]) -> dict[str, Any]:
    found = {key: values[key] for key in BOUNTY_FIELDS if key in values}
    if "games" in found:
        found["games"] = json.dumps(list(found["games"]))
    if "active" in found:
        found["active"] = int(bool(found["active"]))
    return found


async def add_bounty(db: Any, guild_id: int, values: dict[str, Any], created_by: int) -> int:
    wanted = bounty_values(values)
    columns = ["guild_id", *wanted, "created_by", "created_at"]
    cur = await db.conn.execute(
        f"INSERT INTO points_bounties({', '.join(columns)}) "
        f"VALUES ({', '.join('?' for _ in columns)})",
        (guild_id, *wanted.values(), created_by, stamp()),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def bounty(db: Any, guild_id: int, bounty_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM points_bounties WHERE id = ? AND guild_id = ?", (bounty_id, guild_id)
    )
    return await cur.fetchone()


async def bounties(db: Any, guild_id: int, *, active_only: bool = False) -> list[Any]:
    only = " AND active = 1" if active_only else ""
    cur = await db.conn.execute(
        f"SELECT * FROM points_bounties WHERE guild_id = ?{only} ORDER BY id DESC LIMIT ?",
        (guild_id, LIST_LIMIT),
    )
    return list(await cur.fetchall())


async def update_bounty(db: Any, bounty_id: int, values: dict[str, Any]) -> None:
    wanted = bounty_values(values)
    if not wanted:
        return
    sets = ", ".join(f"{column} = ?" for column in wanted)
    await db.conn.execute(
        f"UPDATE points_bounties SET {sets} WHERE id = ?", (*wanted.values(), bounty_id)
    )
    await db.conn.commit()


def games_of(row: Any) -> list[str]:
    try:
        found = json.loads(row["games"] or "[]")
    except (TypeError, ValueError):
        return []
    return [str(one) for one in found] if isinstance(found, list) else []


async def events(db: Any, guild_id: int, event_ids: list[int]) -> dict[int, Any]:
    if not event_ids:
        return {}
    marks = ", ".join("?" for _ in event_ids)
    cur = await db.conn.execute(
        f"SELECT id, title, status, starts_at, ends_at FROM events "
        f"WHERE guild_id = ? AND id IN ({marks})",
        (guild_id, *event_ids),
    )
    return {int(row["id"]): row for row in await cur.fetchall()}


async def count(db: Any, guild_id: int, state: str) -> int:
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM points_runs WHERE guild_id = ? AND state = ?", (guild_id, state)
    )
    return int((await cur.fetchone())["n"])
