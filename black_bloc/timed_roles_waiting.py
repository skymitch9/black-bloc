from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

WAITING = "waiting"
ATTACHED = "attached"
TAKEN_OFF = "taken_off"
CAME_OFF = "came_off"
LEFT = "left"
REMOVED = "removed"
STATES = (WAITING, ATTACHED, TAKEN_OFF, CAME_OFF, LEFT, REMOVED)
OFFSETS_MAX = 10
OFFSET_DAYS_MAX = 365

LATER_TEMPLATE = r"tbhlater:(?P<prompt_id>[0-9]+)"
MOVE_TEMPLATE = r"tbw:(?P<user_id>[0-9]+):(?P<move>date|off|new)"
PICK_TEMPLATE = r"tbwpick:(?P<user_id>[0-9]+)"
REMINDER_TEMPLATE = r"tbwrem:(?P<assigner_id>[0-9]+)"
EVENT_TEMPLATE = r"tbwev:(?P<menu_id>[0-9]+)"
REVERT_TEMPLATE = r"tbwrev:(?P<wait_id>[0-9]+)"
DATE = "date"
OFF = "off"
NEW = "new"


def later_id(prompt_id: int) -> str:
    return f"tbhlater:{int(prompt_id)}"


def move_id(user_id: int, move: str) -> str:
    return f"tbw:{int(user_id)}:{move}"


def pick_id(user_id: int) -> str:
    return f"tbwpick:{int(user_id)}"


def reminder_id(assigner_id: Any) -> str:
    return f"tbwrem:{int(assigner_id or 0)}"


def event_id(menu_id: int) -> str:
    return f"tbwev:{int(menu_id)}"


def revert_id(wait_id: int) -> str:
    return f"tbwrev:{int(wait_id)}"


def now() -> datetime:
    return datetime.now(UTC)


def moment(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def iso(when: datetime) -> str:
    return when.astimezone(UTC).isoformat()


def day_offsets(text: Any) -> list[int] | None:
    """`0, 7, 13` → [0, 7, 13]; None when any part is not a whole number of days."""
    parts = [part.strip() for part in str(text or "").replace(";", ",").split(",")]
    parts = [part for part in parts if part]
    if len(parts) > OFFSETS_MAX:
        return None
    found: list[int] = []
    for part in parts:
        if not part.isdigit() or int(part) > OFFSET_DAYS_MAX:
            return None
        if int(part) not in found:
            found.append(int(part))
    return sorted(found)


def offsets_text(offsets: Any) -> str:
    return ", ".join(str(int(one)) for one in offsets)


def live_offsets(text: Any, removal_days: int) -> list[int]:
    """The reminder offsets that land before the removal day; an unreadable key reminds never."""
    return [one for one in day_offsets(text) or [] if one < int(removal_days)]


def removal_at(until: Any, removal_days: int) -> datetime | None:
    start = moment(until)
    return None if start is None else start + timedelta(days=int(removal_days))


def due_stage(until: Any, offsets: Any, at: datetime | None = None) -> int:
    """How many reminder offsets have come by `at`: the stage a row should have reached."""
    start = moment(until)
    if start is None:
        return 0
    when = at or now()
    return sum(1 for one in offsets if start + timedelta(days=int(one)) <= when)


def removal_due(row: Any, removal_days: int, at: datetime | None = None) -> bool:
    end = removal_at(row["until"], removal_days)
    return end is not None and end <= (at or now())


def reminder_due(row: Any, offsets: Any, at: datetime | None = None) -> int | None:
    """The latest stage due and not yet sent, or None: after downtime one reminder, not a burst."""
    stage = due_stage(row["until"], offsets, at)
    return stage if stage > int(row["stage"] or 0) else None


async def put(
    db: Any,
    guild_id: int,
    user_id: int,
    role_ids: Any,
    *,
    prompt_id: Any,
    assigner_id: Any,
    until: datetime,
    by: Any,
    offsets: Any = (),
) -> list[int]:
    """One waiting row per role; a pair already waiting keeps its row."""
    made: list[int] = []
    stage = due_stage(iso(until), offsets)
    for role_id in dict.fromkeys(int(one) for one in role_ids or ()):
        try:
            cur = await db.conn.execute(
                "INSERT INTO timed_role_waits(guild_id, user_id, role_id, prompt_id, assigner_id, "
                "until, set_by, set_at, stage, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    int(guild_id),
                    int(user_id),
                    role_id,
                    prompt_id,
                    assigner_id,
                    iso(until),
                    by,
                    iso(now()),
                    stage,
                    WAITING,
                ),
            )
        except sqlite3.IntegrityError:
            continue
        made.append(int(cur.lastrowid))
    await db.conn.commit()
    return made


async def get(db: Any, wait_id: Any) -> Any:
    cur = await db.conn.execute("SELECT * FROM timed_role_waits WHERE id = ?", (int(wait_id),))
    return await cur.fetchone()


async def waiting(db: Any, guild_id: int, user_id: Any = None) -> list[Any]:
    """Open rows, soonest end first; one member's when `user_id` is given."""
    if user_id is None:
        cur = await db.conn.execute(
            "SELECT * FROM timed_role_waits WHERE guild_id = ? AND state = ? "
            "ORDER BY until, user_id, role_id",
            (int(guild_id), WAITING),
        )
    else:
        cur = await db.conn.execute(
            "SELECT * FROM timed_role_waits WHERE guild_id = ? AND user_id = ? AND state = ? "
            "ORDER BY until, role_id",
            (int(guild_id), int(user_id), WAITING),
        )
    return list(await cur.fetchall())


async def guilds_waiting(db: Any) -> list[int]:
    cur = await db.conn.execute(
        "SELECT DISTINCT guild_id FROM timed_role_waits WHERE state = ?", (WAITING,)
    )
    return [int(row["guild_id"]) for row in await cur.fetchall()]


async def of_prompt(db: Any, prompt_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM timed_role_waits WHERE prompt_id = ? ORDER BY id", (int(prompt_id),)
    )
    return list(await cur.fetchall())


async def pairs(db: Any, guild_id: int) -> set[tuple[int, int]]:
    """(member, role) pairs waiting for an event: no event's end takes these."""
    return {(int(row["user_id"]), int(row["role_id"])) for row in await waiting(db, guild_id)}


async def roles_waiting(db: Any, guild_id: int, user_id: int) -> set[int]:
    return {int(row["role_id"]) for row in await waiting(db, guild_id, user_id)}


async def count_on_role(db: Any, guild_id: int, role_id: int) -> int:
    cur = await db.conn.execute(
        "SELECT COUNT(*) AS n FROM timed_role_waits WHERE guild_id = ? AND role_id = ? "
        "AND state = ?",
        (int(guild_id), int(role_id), WAITING),
    )
    return int((await cur.fetchone())["n"])


async def people_waiting(db: Any, guild_id: int) -> int:
    return len({int(row["user_id"]) for row in await waiting(db, guild_id)})


async def end(
    db: Any, wait_ids: Any, state: str, *, by: Any = None, menu_id: Any = None
) -> list[int]:
    """Only an open row moves; the ids that did, so one writer wins."""
    if state not in STATES or state == WAITING:
        raise ValueError(f"state must be one of {STATES[1:]}")
    moved: list[int] = []
    for wait_id in dict.fromkeys(int(one) for one in wait_ids or ()):
        cur = await db.conn.execute(
            "UPDATE timed_role_waits SET state = ?, ended_at = ?, ended_by = ?, menu_id = ? "
            "WHERE id = ? AND state = ?",
            (state, iso(now()), by, menu_id, wait_id, WAITING),
        )
        if cur.rowcount and cur.rowcount > 0:
            moved.append(wait_id)
    await db.conn.commit()
    return moved


async def end_pairs(
    db: Any,
    guild_id: int,
    user_id: int,
    role_ids: Any,
    state: str,
    *,
    by: Any = None,
    menu_id: Any = None,
) -> list[int]:
    wanted = {int(one) for one in role_ids or ()}
    rows = [row for row in await waiting(db, guild_id, user_id) if int(row["role_id"]) in wanted]
    return await end(db, [row["id"] for row in rows], state, by=by, menu_id=menu_id)


async def end_member(db: Any, guild_id: int, user_id: int, state: str) -> list[int]:
    return await end(db, [row["id"] for row in await waiting(db, guild_id, user_id)], state)


async def set_until(db: Any, wait_ids: Any, until: datetime, offsets: Any, by: Any) -> int:
    """A new rough end: the reminder stage becomes what the new date implies."""
    stage = due_stage(iso(until), offsets)
    moved = 0
    for wait_id in dict.fromkeys(int(one) for one in wait_ids or ()):
        cur = await db.conn.execute(
            "UPDATE timed_role_waits SET until = ?, stage = ?, set_by = ?, set_at = ?, "
            "remove_failures = 0 WHERE id = ? AND state = ?",
            (iso(until), stage, by, iso(now()), wait_id, WAITING),
        )
        moved += max(cur.rowcount, 0)
    await db.conn.commit()
    return moved


async def mark_reminded(db: Any, wait_ids: Any, stage_of: dict[int, int]) -> None:
    for wait_id in wait_ids:
        await db.conn.execute(
            "UPDATE timed_role_waits SET stage = ?, reminded_at = ? WHERE id = ? AND state = ?",
            (int(stage_of[int(wait_id)]), iso(now()), int(wait_id), WAITING),
        )
    await db.conn.commit()


async def mark_removed(db: Any, wait_ids: Any) -> list[int]:
    return await end(db, wait_ids, REMOVED)


async def failed_removal(db: Any, wait_ids: Any) -> dict[int, int]:
    """Each row's count of removals Discord refused, after this one."""
    found: dict[int, int] = {}
    for wait_id in wait_ids:
        await db.conn.execute(
            "UPDATE timed_role_waits SET remove_failures = remove_failures + 1 WHERE id = ?",
            (int(wait_id),),
        )
        row = await get(db, wait_id)
        found[int(wait_id)] = int(row["remove_failures"]) if row is not None else 0
    await db.conn.commit()
    return found


async def set_notice(db: Any, wait_ids: Any, channel_id: int, message_id: int) -> None:
    for wait_id in wait_ids:
        await db.conn.execute(
            "UPDATE timed_role_waits SET notice_channel_id = ?, notice_message_id = ? WHERE id = ?",
            (int(channel_id), int(message_id), int(wait_id)),
        )
    await db.conn.commit()


async def notice_rows(db: Any, lead: Any) -> list[Any]:
    """The rows one removal notice covers: the lead's member, removed in the same notice."""
    if lead["notice_message_id"] is None:
        cur = await db.conn.execute(
            "SELECT * FROM timed_role_waits WHERE id = ? AND state = ?", (lead["id"], REMOVED)
        )
    else:
        cur = await db.conn.execute(
            "SELECT * FROM timed_role_waits WHERE guild_id = ? AND user_id = ? AND state = ? "
            "AND notice_message_id = ? ORDER BY id",
            (lead["guild_id"], lead["user_id"], REMOVED, lead["notice_message_id"]),
        )
    return list(await cur.fetchall())


async def wait_again(db: Any, wait_ids: Any, until: datetime, by: Any) -> list[int]:
    """Revert: a removed row waits again from `until`, reminders from the start; one writer wins."""
    moved: list[int] = []
    for wait_id in dict.fromkeys(int(one) for one in wait_ids or ()):
        try:
            cur = await db.conn.execute(
                "UPDATE timed_role_waits SET state = ?, until = ?, stage = 0, reminded_at = NULL, "
                "ended_at = NULL, ended_by = NULL, set_by = ?, set_at = ?, remove_failures = 0 "
                "WHERE id = ? AND state = ?",
                (WAITING, iso(until), by, iso(now()), wait_id, REMOVED),
            )
        except sqlite3.IntegrityError:
            continue
        if cur.rowcount and cur.rowcount > 0:
            moved.append(wait_id)
    await db.conn.commit()
    return moved


async def removal_ends(
    db: Any, guild_id: Any, user_ids: Any, removal_days: int
) -> dict[tuple[int, int], dict[str, Any]]:
    """(member, role) → the day a waiting role comes off unless an event is picked."""
    wanted = {int(one) for one in user_ids or ()}
    if not wanted or db is None or not getattr(db, "is_connected", False):
        return {}
    found: dict[tuple[int, int], dict[str, Any]] = {}
    for row in await waiting(db, int(guild_id)):
        end = removal_at(row["until"], removal_days)
        if int(row["user_id"]) in wanted and end is not None:
            found[(int(row["user_id"]), int(row["role_id"]))] = {"ends_at": iso(end), "menu": None}
    return found


def entries(rows: Any) -> list[dict[str, Any]]:
    """One entry per member: their waiting roles, the soonest end, who set it and who assigned."""
    found: dict[int, dict[str, Any]] = {}
    for row in rows:
        user_id = int(row["user_id"])
        one = found.setdefault(
            user_id,
            {
                "user_id": user_id,
                "role_ids": [],
                "wait_ids": [],
                "until": row["until"],
                "set_by": row["set_by"],
                "assigner_id": row["assigner_id"],
                "prompt_ids": [],
            },
        )
        one["role_ids"].append(int(row["role_id"]))
        one["wait_ids"].append(int(row["id"]))
        if row["prompt_id"] is not None and int(row["prompt_id"]) not in one["prompt_ids"]:
            one["prompt_ids"].append(int(row["prompt_id"]))
        start, held = moment(row["until"]), moment(one["until"])
        if start is not None and (held is None or start < held):
            one["until"] = row["until"]
    return sorted(found.values(), key=lambda one: (str(one["until"]), one["user_id"]))


__all__ = [
    "ATTACHED",
    "CAME_OFF",
    "DATE",
    "EVENT_TEMPLATE",
    "LATER_TEMPLATE",
    "LEFT",
    "MOVE_TEMPLATE",
    "NEW",
    "OFF",
    "OFFSETS_MAX",
    "OFFSET_DAYS_MAX",
    "PICK_TEMPLATE",
    "REMINDER_TEMPLATE",
    "REMOVED",
    "REVERT_TEMPLATE",
    "STATES",
    "TAKEN_OFF",
    "WAITING",
    "count_on_role",
    "day_offsets",
    "due_stage",
    "end",
    "end_member",
    "end_pairs",
    "entries",
    "event_id",
    "failed_removal",
    "get",
    "guilds_waiting",
    "iso",
    "later_id",
    "live_offsets",
    "mark_reminded",
    "mark_removed",
    "moment",
    "move_id",
    "notice_rows",
    "of_prompt",
    "offsets_text",
    "pairs",
    "people_waiting",
    "pick_id",
    "put",
    "reminder_due",
    "reminder_id",
    "removal_at",
    "removal_due",
    "removal_ends",
    "revert_id",
    "roles_waiting",
    "set_notice",
    "set_until",
    "wait_again",
    "waiting",
]
