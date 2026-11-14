from __future__ import annotations

from datetime import UTC
from typing import Any, NamedTuple

from .golive import now_iso, parse_ts

LABEL_MAX = 100
LIST_MAX = 25


class Plan(NamedTuple):
    take: list[tuple[Any, list[int]]]
    keep: int

    @property
    def members(self) -> int:
        return len(self.take)

    @property
    def roles(self) -> int:
        return len({role_id for _, worn in self.take for role_id in worn})


async def listed(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM timed_roles WHERE guild_id = ? ORDER BY position, role_id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def role_ids(db: Any, guild_id: int) -> list[int]:
    return [int(row["role_id"]) for row in await listed(db, guild_id)]


async def is_timed(db: Any, guild_id: int, role_id: Any) -> bool:
    if db is None or not getattr(db, "is_connected", False):
        return False
    cur = await db.conn.execute(
        "SELECT 1 FROM timed_roles WHERE guild_id = ? AND role_id = ?",
        (int(guild_id), int(role_id)),
    )
    return await cur.fetchone() is not None


async def labels(db: Any, guild_id: int) -> dict[int, str]:
    return {int(row["role_id"]): str(row["label"]) for row in await listed(db, guild_id)}


async def add(
    db: Any, guild_id: int, role_id: int, label: str, *, emoji: Any = None, by: Any = None
) -> bool:
    """False when the role is already on the list; its first label stands."""
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM timed_roles WHERE guild_id = ?", (int(guild_id),)
    )
    position = (await cur.fetchone())["n"]
    cur = await db.conn.execute(
        "INSERT OR IGNORE INTO timed_roles(guild_id, role_id, label, emoji, position, added_by, "
        "added_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (int(guild_id), int(role_id), str(label)[:LABEL_MAX], emoji, position, by, now_iso()),
    )
    await db.conn.commit()
    return bool(cur.rowcount and cur.rowcount > 0)


async def remove(db: Any, guild_id: int, role_id: int) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM timed_roles WHERE guild_id = ? AND role_id = ?", (int(guild_id), int(role_id))
    )
    await db.conn.commit()
    return bool(cur.rowcount and cur.rowcount > 0)


async def assigned_count(db: Any, guild_id: int, role_id: int) -> int:
    """Open assignments of this role on events that have not ended."""
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM role_grants g JOIN role_menus m ON m.id = g.menu_id "
        "WHERE g.guild_id = ? AND g.role_id = ? AND g.removed_at IS NULL AND m.ended_at IS NULL",
        (int(guild_id), int(role_id)),
    )
    return int((await cur.fetchone())["n"])


async def event_grants(db: Any, guild_id: int, menu_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM role_grants WHERE guild_id = ? AND menu_id = ? AND removed_at IS NULL "
        "ORDER BY id",
        (int(guild_id), int(menu_id)),
    )
    return list(await cur.fetchall())


async def event_grant(db: Any, guild_id: int, user_id: int, role_id: int, menu_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM role_grants WHERE guild_id = ? AND user_id = ? AND role_id = ? "
        "AND menu_id = ? AND removed_at IS NULL",
        (int(guild_id), int(user_id), int(role_id), int(menu_id)),
    )
    return await cur.fetchone()


async def assigned_by_role(db: Any, guild_id: int, menu_id: int) -> dict[int, int]:
    found: dict[int, int] = {}
    for row in await event_grants(db, guild_id, menu_id):
        found[int(row["role_id"])] = found.get(int(row["role_id"]), 0) + 1
    return found


async def assigned_people(db: Any, guild_id: int, menu_id: int) -> int:
    return len({int(row["user_id"]) for row in await event_grants(db, guild_id, menu_id)})


async def keepers(db: Any, guild_id: int, menu_id: int) -> set[tuple[int, int]]:
    """(member, role) pairs held through ANOTHER event that has not ended."""
    cur = await db.conn.execute(
        "SELECT g.user_id, g.role_id FROM role_grants g JOIN role_menus m ON m.id = g.menu_id "
        "WHERE g.guild_id = ? AND g.menu_id != ? AND g.removed_at IS NULL "
        "AND m.ended_at IS NULL",
        (int(guild_id), int(menu_id)),
    )
    return {(int(row["user_id"]), int(row["role_id"])) for row in await cur.fetchall()}


def plan(wearing: Any, keeping: set[tuple[int, int]], skip: Any = ()) -> Plan:
    """What an event's end takes: every worn timed role not held through another open event."""
    left_alone = {int(one) for one in skip or ()}
    take: list[tuple[Any, list[int]]] = []
    keep = 0
    for member, worn in wearing or ():
        user_id = int(member.id)
        kept = [one for one in worn if (user_id, int(one)) in keeping]
        gone = [int(one) for one in worn if int(one) not in left_alone and int(one) not in kept]
        keep += int(bool(kept))
        if gone:
            take.append((member, gone))
    return Plan(take, keep)


async def stamp_event(db: Any, guild_id: int, menu_id: int, ends_at: Any) -> int:
    """Every open assignment on the event carries the event's end, one date on every surface."""
    cur = await db.conn.execute(
        "UPDATE role_grants SET expires_at = ? WHERE guild_id = ? AND menu_id = ? "
        "AND removed_at IS NULL AND expires_at IS NOT ?",
        (ends_at, int(guild_id), int(menu_id), ends_at),
    )
    await db.conn.commit()
    return max(cur.rowcount, 0)


async def close_event(db: Any, guild_id: int, menu_id: int, reason: str, *, keep: Any = ()) -> int:
    """Every open assignment on the event closes, except (member, role) pairs in `keep`."""
    kept = {(int(user), int(role)) for user, role in keep or ()}
    closed = 0
    for row in await event_grants(db, guild_id, menu_id):
        if (int(row["user_id"]), int(row["role_id"])) in kept:
            continue
        cur = await db.conn.execute(
            "UPDATE role_grants SET removed_at = ?, removed_reason = ? "
            "WHERE id = ? AND removed_at IS NULL",
            (now_iso(), reason, row["id"]),
        )
        closed += max(cur.rowcount, 0)
    await db.conn.commit()
    return closed


async def close_member_roles(
    db: Any, guild_id: int, user_id: int, role_ids: Any, reason: str
) -> int:
    """Every open row for these roles closes once the member no longer wears them."""
    closed = 0
    for role_id in dict.fromkeys(int(one) for one in role_ids or ()):
        cur = await db.conn.execute(
            "UPDATE role_grants SET removed_at = ?, removed_reason = ? WHERE guild_id = ? "
            "AND user_id = ? AND role_id = ? AND removed_at IS NULL",
            (now_iso(), reason, int(guild_id), int(user_id), role_id),
        )
        closed += max(cur.rowcount, 0)
    await db.conn.commit()
    return closed


async def open_events(db: Any, guild_id: int) -> list[Any]:
    """Events still to end: soonest end first, then the ones with no end, by name."""
    cur = await db.conn.execute(
        "SELECT * FROM role_menus WHERE guild_id = ? AND ended_at IS NULL", (int(guild_id),)
    )
    rows = list(await cur.fetchall())

    def order(row: Any) -> tuple[int, str, str]:
        end = parse_ts(row["ends_at"])
        return (1, "", str(row["title"]).lower()) if end is None else (0, end.isoformat(), "")

    return sorted(rows, key=order)


async def ended_events(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM role_menus WHERE guild_id = ? AND ended_at IS NOT NULL "
        "ORDER BY ended_at DESC, id DESC",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def event_for_marathon(db: Any, guild_id: int, marathon_id: Any) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM role_menus WHERE guild_id = ? AND ends_source = 'marathon' "
        "AND ends_marathon_id = ? AND ended_at IS NULL ORDER BY id LIMIT 1",
        (int(guild_id), int(marathon_id)),
    )
    return await cur.fetchone()


async def soonest_ends(db: Any, guild_id: Any) -> dict[int, dict[str, str]]:
    """Each timed role's next end — the soonest open event's — with that event's name."""
    if db is None or not getattr(db, "is_connected", False):
        return {}
    ids = await role_ids(db, int(guild_id))
    if not ids:
        return {}
    soonest = None
    for row in await open_events(db, int(guild_id)):
        if parse_ts(row["ends_at"]) is not None:
            soonest = row
            break
    if soonest is None:
        return {}
    end = parse_ts(soonest["ends_at"]).astimezone(UTC).isoformat()
    found = {"ends_at": end, "menu": str(soonest["title"])}
    return {role_id: dict(found) for role_id in ids}


__all__ = [
    "LABEL_MAX",
    "LIST_MAX",
    "Plan",
    "add",
    "assigned_by_role",
    "assigned_count",
    "assigned_people",
    "close_event",
    "close_member_roles",
    "ended_events",
    "event_for_marathon",
    "event_grant",
    "event_grants",
    "is_timed",
    "keepers",
    "labels",
    "listed",
    "open_events",
    "plan",
    "remove",
    "role_ids",
    "soonest_ends",
    "stamp_event",
]
