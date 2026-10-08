"""Tournaments in SQLite: the tournament row, its entrants, its sets, and the bracket in and out."""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime
from typing import Any

from .brackets.model import POOL_FORMATS, Bracket, Match, Options, Plan

DRAFT = "draft"
SIGNUPS = "signups"
CHECK_IN = "check_in"
SEEDING = "seeding"
POOLS = "pools"
RUNNING = "running"
COMPLETE = "complete"
CANCELLED = "cancelled"
STATES = (DRAFT, SIGNUPS, CHECK_IN, SEEDING, POOLS, RUNNING, COMPLETE, CANCELLED)
BEFORE_START = (DRAFT, SIGNUPS, CHECK_IN, SEEDING)
PLAYING = (POOLS, RUNNING)
NO_POOLS = "none"

OWN = "own"
STARTGG = "startgg"
SOURCES = (OWN, STARTGG)

REMOVED = "removed"
LEFT = "left"
NO_SHOW = "no_show"
DROPPED = "dropped"
DROP_WHYS = (REMOVED, LEFT, NO_SHOW, DROPPED)

OPTION_COLUMNS = (
    "format",
    "third_place",
    "grand_final_reset",
    "swiss_rounds",
    "best_of",
    "best_of_from_round",
    "best_of_late",
    "best_of_finals",
)
POOL_COLUMNS = (
    "pools_format",
    "pool_count",
    "advance_per_pool",
    "advance_losers_from",
    "pools_swiss_rounds",
    "pools_best_of",
)
EDITABLE = (
    "name",
    "game",
    *OPTION_COLUMNS,
    *POOL_COLUMNS,
    "entrant_cap",
    "check_in_minutes",
    "confirm_minutes",
    "rules_text",
    "starts_at",
    "to_user_id",
)
SET_COLUMNS = tuple(one.name for one in fields(Match))
LIST_LIMIT = 200


def stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).astimezone(UTC).isoformat()


async def create(db: Any, guild_id: int, values: dict[str, Any], created_by: int) -> int:
    now = stamp()
    wanted = {key: values[key] for key in EDITABLE if key in values}
    columns = ["guild_id", *wanted, "created_by", "created_at", "updated_at"]
    cur = await db.conn.execute(
        f"INSERT INTO tournaments({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
        (guild_id, *wanted.values(), created_by, now, now),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def tournament(db: Any, guild_id: int, tournament_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM tournaments WHERE id = ? AND guild_id = ?", (tournament_id, guild_id)
    )
    return await cur.fetchone()


async def tournaments(db: Any, guild_id: int, limit: int = LIST_LIMIT) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT t.*, (SELECT COUNT(*) FROM tournament_entrants e WHERE e.tournament_id = t.id "
        "AND e.dropped = 0) AS entrant_count FROM tournaments t WHERE t.guild_id = ? "
        "ORDER BY t.id DESC LIMIT ?",
        (guild_id, limit),
    )
    return list(await cur.fetchall())


async def update(db: Any, tournament_id: int, values: dict[str, Any]) -> None:
    if not values:
        return
    sets = ", ".join(f"{column} = ?" for column in values)
    await db.conn.execute(
        f"UPDATE tournaments SET {sets}, updated_at = ? WHERE id = ?",
        (*values.values(), stamp(), tournament_id),
    )
    await db.conn.commit()


async def entrants(db: Any, tournament_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM tournament_entrants WHERE tournament_id = ? ORDER BY seed IS NULL, seed, id",
        (tournament_id,),
    )
    return list(await cur.fetchall())


async def entrant(db: Any, tournament_id: int, entrant_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM tournament_entrants WHERE tournament_id = ? AND id = ?",
        (tournament_id, entrant_id),
    )
    return await cur.fetchone()


async def entrant_of(db: Any, tournament_id: int, user_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM tournament_entrants WHERE tournament_id = ? AND user_id = ?",
        (tournament_id, user_id),
    )
    return await cur.fetchone()


async def add_entrant(
    db: Any,
    tournament_id: int,
    name: str,
    *,
    user_id: int | None,
    added_by: int | None,
    checked_in: bool = False,
) -> int:
    seed = await next_seed(db, tournament_id)
    cur = await db.conn.execute(
        "INSERT INTO tournament_entrants(tournament_id, user_id, name, seed, checked_in, "
        "checked_in_at, added_by, added_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            tournament_id,
            user_id,
            name,
            seed,
            int(checked_in),
            stamp() if checked_in else None,
            added_by,
            stamp(),
        ),
    )
    await db.conn.commit()
    return int(cur.lastrowid)


async def next_seed(db: Any, tournament_id: int) -> int:
    cur = await db.conn.execute(
        "SELECT COALESCE(MAX(seed), 0) + 1 AS n FROM tournament_entrants WHERE tournament_id = ?",
        (tournament_id,),
    )
    return int((await cur.fetchone())["n"])


async def update_entrant(db: Any, entrant_id: int, values: dict[str, Any]) -> None:
    sets = ", ".join(f"{column} = ?" for column in values)
    await db.conn.execute(
        f"UPDATE tournament_entrants SET {sets} WHERE id = ?", (*values.values(), entrant_id)
    )
    await db.conn.commit()


async def write_seeds(db: Any, tournament_id: int, order: list[int]) -> None:
    for seed, entrant_id in enumerate(order, start=1):
        await db.conn.execute(
            "UPDATE tournament_entrants SET seed = ? WHERE id = ? AND tournament_id = ?",
            (seed, entrant_id, tournament_id),
        )
    await db.conn.commit()


async def write_placements(db: Any, tournament_id: int, placed: dict[int, int]) -> None:
    await db.conn.execute(
        "UPDATE tournament_entrants SET placement = NULL WHERE tournament_id = ?",
        (tournament_id,),
    )
    for entrant_id, place in placed.items():
        await db.conn.execute(
            "UPDATE tournament_entrants SET placement = ? WHERE id = ? AND tournament_id = ?",
            (place, entrant_id, tournament_id),
        )
    await db.conn.commit()


async def write_final_order(db: Any, tournament_id: int, order: list[int]) -> None:
    await db.conn.execute(
        "UPDATE tournament_entrants SET final_rank = NULL WHERE tournament_id = ?",
        (tournament_id,),
    )
    for rank, entrant_id in enumerate(order, start=1):
        await db.conn.execute(
            "UPDATE tournament_entrants SET final_rank = ? WHERE id = ? AND tournament_id = ?",
            (rank, entrant_id, tournament_id),
        )
    await db.conn.commit()


async def sets(db: Any, tournament_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM tournament_sets WHERE tournament_id = ? ORDER BY id", (tournament_id,)
    )
    return list(await cur.fetchall())


def options_of(row: Any) -> Options:
    return Options(
        format=row["format"],
        third_place=bool(row["third_place"]),
        grand_final_reset=bool(row["grand_final_reset"]),
        swiss_rounds=row["swiss_rounds"],
        best_of=row["best_of"],
        best_of_from_round=row["best_of_from_round"],
        best_of_late=row["best_of_late"],
        best_of_finals=row["best_of_finals"],
    )


def plan_of(row: Any) -> Plan | None:
    """The tournament's pools, or None when it plays one bracket."""
    if row["pools_format"] not in POOL_FORMATS:
        return None
    return Plan(
        format=row["pools_format"],
        count=int(row["pool_count"]),
        advance=int(row["advance_per_pool"]),
        losers_from=row["advance_losers_from"],
        best_of=int(row["pools_best_of"]),
        swiss_rounds=row["pools_swiss_rounds"],
    )


def match_of(row: Any) -> Match:
    return Match(**{name: row[name] for name in SET_COLUMNS} | {"rematch": bool(row["rematch"])})


async def bracket(db: Any, row: Any) -> Bracket | None:
    """The stored bracket, or None before it is started."""
    stored = await sets(db, row["id"])
    if not stored:
        return None
    people = await entrants(db, row["id"])
    seated = {value for one in stored for value in (one["slot_a"], one["slot_b"]) if value}
    order = [one["id"] for one in people if one["id"] in seated]
    withdrawn = {
        one["id"]: ("dq" if one["dq"] else "drop")
        for one in people
        if one["id"] in seated and (one["dq"] or one["dropped"])
    }
    told = sorted(
        (one for one in people if one["final_rank"] is not None), key=lambda one: one["final_rank"]
    )
    return Bracket(
        options=options_of(row),
        entrants=order,
        matches={one["key"]: match_of(one) for one in stored},
        withdrawn=withdrawn,
        final_order=[one["id"] for one in told],
        plan=plan_of(row),
    )


async def save(
    db: Any, tournament_id: int, found: Bracket, changed: list[str], removed: list[str]
) -> dict[str, int]:
    """Upserts the changed sets and deletes the removed ones, answering the removed sets' cards."""
    held = await cards(db, tournament_id) if removed else {}
    gone = {key: held[key][0] for key in removed if key in held}
    for key in removed:
        await db.conn.execute(
            "DELETE FROM tournament_sets WHERE tournament_id = ? AND key = ?", (tournament_id, key)
        )
    columns = ", ".join(SET_COLUMNS)
    marks = ", ".join("?" for _ in SET_COLUMNS)
    updates = ", ".join(f"{name} = excluded.{name}" for name in SET_COLUMNS if name != "key")
    for key in changed:
        match = found.matches[key]
        await db.conn.execute(
            f"INSERT INTO tournament_sets(tournament_id, {columns}) VALUES (?, {marks}) "
            f"ON CONFLICT(tournament_id, key) DO UPDATE SET {updates}",
            (tournament_id, *(getattr(match, name) for name in SET_COLUMNS)),
        )
    await db.conn.commit()
    return gone


async def clear_sets(db: Any, tournament_id: int) -> dict[str, int]:
    gone = {key: found[0] for key, found in (await cards(db, tournament_id)).items()}
    await db.conn.execute("DELETE FROM tournament_sets WHERE tournament_id = ?", (tournament_id,))
    await db.conn.commit()
    return gone


async def cards(db: Any, tournament_id: int) -> dict[str, tuple[int, str | None]]:
    """Each set's card in the tournament thread: its message id and when it was posted."""
    cur = await db.conn.execute(
        "SELECT key, message_id, card_at FROM tournament_sets WHERE tournament_id = ? "
        "AND message_id IS NOT NULL",
        (tournament_id,),
    )
    return {row["key"]: (int(row["message_id"]), row["card_at"]) for row in await cur.fetchall()}


async def card_rows(db: Any, tournament_id: int) -> dict[str, tuple[int | None, str | None]]:
    """Every set's card id and stamp, the half-posted ones (a stamp and no id) included."""
    cur = await db.conn.execute(
        "SELECT key, message_id, card_at FROM tournament_sets WHERE tournament_id = ?",
        (tournament_id,),
    )
    return {
        row["key"]: (int(row["message_id"]) if row["message_id"] else None, row["card_at"])
        for row in await cur.fetchall()
    }


async def set_card(
    db: Any, tournament_id: int, key: str, message_id: int | None, card_at: str | None
) -> None:
    await db.conn.execute(
        "UPDATE tournament_sets SET message_id = ?, card_at = ? "
        "WHERE tournament_id = ? AND key = ?",
        (message_id, card_at, tournament_id, key),
    )
    await db.conn.commit()
