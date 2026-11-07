"""Tournaments in SQLite: the tournament row, its entrants, its sets, and the bracket in and out."""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from typing import Any

from .brackets.model import (
    BYE,
    CALLED,
    POOL_FORMATS,
    READY,
    VOID,
    WAITING,
    Bracket,
    Match,
    Options,
    Plan,
)

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

FIGHTERS = "fighters"
SPORTS = "sports"
LIST = "list"
KINDS = (FIGHTERS, SPORTS, LIST)
VOTES = "votes"
ORGANISER = "organiser"
DECIDERS = (VOTES, ORGANISER)
VOTE_SLOTS = ("a", "b")
VOTE_OPEN = (READY, CALLED)
VOTE_GONE = (WAITING, BYE, VOID)

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
    "kind",
    "decide_by",
    "vote_minutes",
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


def column(row: Any, name: str) -> Any:
    try:
        return row[name]
    except (KeyError, IndexError):
        return None


def kind_of(row: Any) -> str:
    """The bracket's kind; a row read before the column existed is a fighters bracket."""
    found = column(row, "kind")
    return found if found in KINDS else FIGHTERS


def votes_decide(row: Any) -> bool:
    return kind_of(row) == LIST and column(row, "decide_by") == VOTES


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
        await db.conn.execute(
            "DELETE FROM tournament_votes WHERE tournament_id = ? AND key = ?", (tournament_id, key)
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
    await db.conn.execute("DELETE FROM tournament_votes WHERE tournament_id = ?", (tournament_id,))
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


async def ballots(db: Any, tournament_id: int) -> dict[str, dict[str, Any]]:
    """Each set's vote: when it opened, when it closes, when it closed, and the counts."""
    cur = await db.conn.execute(
        "SELECT key, vote_opens_at, vote_closes_at, vote_closed_at FROM tournament_sets "
        "WHERE tournament_id = ? AND vote_opens_at IS NOT NULL",
        (tournament_id,),
    )
    found = {
        row["key"]: {
            "opens_at": row["vote_opens_at"],
            "closes_at": row["vote_closes_at"],
            "closed_at": row["vote_closed_at"],
            "a": 0,
            "b": 0,
        }
        for row in await cur.fetchall()
    }
    cur = await db.conn.execute(
        "SELECT key, slot, COUNT(*) AS n FROM tournament_votes WHERE tournament_id = ? "
        "GROUP BY key, slot",
        (tournament_id,),
    )
    for row in await cur.fetchall():
        if row["key"] in found and row["slot"] in VOTE_SLOTS:
            found[row["key"]][row["slot"]] = int(row["n"])
    return found


async def ballot(db: Any, tournament_id: int, key: str) -> dict[str, Any] | None:
    return (await ballots(db, tournament_id)).get(key)


async def my_votes(db: Any, tournament_id: int, user_id: int | None) -> dict[str, str]:
    if user_id is None:
        return {}
    cur = await db.conn.execute(
        "SELECT key, slot FROM tournament_votes WHERE tournament_id = ? AND user_id = ?",
        (tournament_id, int(user_id)),
    )
    return {row["key"]: row["slot"] for row in await cur.fetchall()}


async def cast(db: Any, tournament_id: int, key: str, user_id: int, slot: str) -> None:
    """One row per member and set, changed in place until the vote closes."""
    await db.conn.execute(
        "INSERT INTO tournament_votes(tournament_id, key, user_id, slot, at) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(tournament_id, key, user_id) "
        "DO UPDATE SET slot = excluded.slot, at = excluded.at",
        (tournament_id, key, int(user_id), slot, stamp()),
    )
    await db.conn.commit()


async def vote_closed(db: Any, tournament_id: int, key: str, at: str) -> None:
    await db.conn.execute(
        "UPDATE tournament_sets SET vote_closed_at = ? WHERE tournament_id = ? AND key = ?",
        (at, tournament_id, key),
    )
    await db.conn.commit()


async def forget_votes(db: Any, tournament_id: int, key: str) -> None:
    await db.conn.execute(
        "DELETE FROM tournament_votes WHERE tournament_id = ? AND key = ?", (tournament_id, key)
    )


async def sync_votes(db: Any, row: Any, now: datetime | None = None) -> list[str]:
    """A playable set gets a fresh vote, a decided one is closed, a set gone back to waiting is
    cleared; answers the keys whose vote opened."""
    if not votes_decide(row):
        return []
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    closes = moment + timedelta(minutes=int(row["vote_minutes"] or 1))
    cur = await db.conn.execute(
        "SELECT key, state, vote_opens_at, vote_closed_at FROM tournament_sets "
        "WHERE tournament_id = ?",
        (row["id"],),
    )
    opened: list[str] = []
    fields = "vote_opens_at = ?, vote_closes_at = ?, vote_closed_at = ?"
    where = "WHERE tournament_id = ? AND key = ?"
    for one in await cur.fetchall():
        key, state = one["key"], one["state"]
        if state in VOTE_OPEN and (one["vote_opens_at"] is None or one["vote_closed_at"]):
            await forget_votes(db, row["id"], key)
            await db.conn.execute(
                f"UPDATE tournament_sets SET {fields} {where}",
                (stamp(moment), stamp(closes), None, row["id"], key),
            )
            opened.append(key)
        elif state in VOTE_GONE and one["vote_opens_at"] is not None:
            await forget_votes(db, row["id"], key)
            await db.conn.execute(
                f"UPDATE tournament_sets SET {fields} {where}", (None, None, None, row["id"], key)
            )
        elif state not in VOTE_OPEN and one["vote_opens_at"] and not one["vote_closed_at"]:
            await db.conn.execute(
                f"UPDATE tournament_sets SET vote_closed_at = ? {where}",
                (stamp(moment), row["id"], key),
            )
    await db.conn.commit()
    return opened
