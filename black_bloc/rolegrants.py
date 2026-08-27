from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from .golive import now_iso, parse_ts

log = logging.getLogger(__name__)

PENDING = "pending"
APPROVED = "approved"
DENIED = "denied"
WITHDRAWN = "withdrawn"
GRANTED_BY_HAND = "granted_by_hand"
REQUEST_STATUSES = (PENDING, APPROVED, DENIED, WITHDRAWN, GRANTED_BY_HAND)
SETTLED_STATUSES = (APPROVED, DENIED, WITHDRAWN, GRANTED_BY_HAND)

MENU = "menu"
APPROVAL = "approval"
STAFF = "staff"
MANUAL = "manual"
SOURCES = (MENU, APPROVAL, STAFF, MANUAL)

EXPIRED = "expired"
BY_HAND = "by_hand"
GIVEN_UP = "given_up"
ENDED_BY_STAFF = "ended_by_staff"

ADDED = "added"
REMOVED = "removed"

RETRY_DAYS_DEFAULT = 7
DAYS_MAX = 3650
REASON_LIMIT = 400

LEDGER_ATTR = "_role_change_ledger"
LEDGER_SECONDS = 30.0

REQUEST_SENT = (
    "Sent to staff for approval — you'll get a DM when it's decided. Pick **{label}** again on the "
    "panel if you change your mind and want to take the request back."
)
ALREADY_ASKED = (
    "You have already asked for **{label}** and staff have not decided yet, so nothing was sent "
    "twice. Pick it again on the panel to take the request back."
)
TOO_SOON = (
    "Staff said no to **{label}** on {when}; you can ask again {stamp}. Nothing was sent. A member "
    "of staff can still hand it to you before then if they want to."
)
WITHDRAWN_SAID = (
    "Your request for **{label}** has been taken back, so staff will not be deciding it. Pick it "
    "again whenever you want to ask."
)
NOTHING_TO_APPROVE = (
    "Black Bloc has no record of that request any more, so nothing was changed. The role menus "
    "page lists the ones it still has."
)
ALREADY_DECIDED = (
    "Somebody got there first — that request is already **{status}**, so nothing was changed. The "
    "card above says who decided and when."
)
CARD_HEADING = "Role request #{request_id}"
APPROVED_SAID = "Approved — {name} has **{label}** now.{extra}"
DENIED_SAID = "Denied, and they have been told why."
DM_APPROVED = (
    "Staff approved **{label}** on **{guild}**, and you have it now.{extra}"
)
DM_DENIED = (
    "Staff did not approve **{label}** on **{guild}**. The reason given was: {reason}. You can ask "
    "again {stamp}."
)
DM_EXPIRED = (
    "Your **{label}** on **{guild}** ran out today, so it has been taken off. Ask staff, or pick "
    "it on the role menu again, if you still need it."
)
EXPIRES_EXTRA = " It runs out {stamp}."
NEVER_EXPIRES = ""
GRANTED_SAID = "**{name}** has **{label}**{until}."
NO_SUCH_GRANT = (
    "Black Bloc is not keeping time on **{label}** for **{name}**, so there was nothing to change. "
    "`/role grant` starts one."
)
GRANT_NEVER_ENDS = (
    "**{name}**'s **{label}** has no end date, so there is nothing to push back. Take it off with "
    "`/rolemenu unassign` when they should lose it."
)
EXTENDED_SAID = "**{name}**'s **{label}** now runs out {stamp}."
CANNOT_EDIT_THEIRS = (
    "Discord refused the change, so **{name}** still has exactly the roles they had. Black Bloc "
    "needs the Manage Roles permission and its own role has to sit above **{label}** in Server "
    "Settings → Roles. Ask an admin to fix that, then run the command again."
)
NO_APPROVAL_CHANNEL = (
    "Black Bloc has nowhere to send the request, so nothing was submitted. A Lead points it at a "
    "channel with `/settings set-value rolemenu_approval_channel_id`, or sets `staff_channel_id`."
)
CARD_NOT_POSTED = (
    "Your request for **{label}** is saved, but Black Bloc could not post the card for staff — "
    "the log says why. Tell a Lead so they can decide it by hand."
)


def stamp(at: Any, style: str = "F") -> str:
    """A Discord timestamp, so everybody reads it in their own zone."""
    when = at if isinstance(at, datetime) else parse_ts(at)
    if when is None:
        return "at an unreadable time"
    return f"<t:{int(when.timestamp())}:{style}>"


def expires_at(days: Any, *, at: datetime | None = None) -> str | None:
    """The moment a grant of `days` runs out; None when it never does."""
    try:
        number = int(days)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return ((at or datetime.now(UTC)) + timedelta(days=min(number, DAYS_MAX))).isoformat()


def pushed_back(current: Any, days: int, *, at: datetime | None = None) -> str:
    """Extending starts from the later of now and the end it already had."""
    now = at or datetime.now(UTC)
    end = parse_ts(current)
    start = end if end is not None and end > now else now
    return (start + timedelta(days=min(max(int(days), 1), DAYS_MAX))).isoformat()


def retry_at(decided_at: Any, retry_days: Any) -> datetime | None:
    when = parse_ts(decided_at)
    try:
        days = int(retry_days)
    except (TypeError, ValueError):
        days = RETRY_DAYS_DEFAULT
    if when is None or days <= 0:
        return None
    return when + timedelta(days=days)


def still_cooling(decided_at: Any, retry_days: Any, *, at: datetime | None = None) -> Any:
    """The moment they may ask again, or None when they already may."""
    until = retry_at(decided_at, retry_days)
    if until is None:
        return None
    return until if until > (at or datetime.now(UTC)) else None


def clamp(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _ledger(bot: Any) -> dict[tuple[int, int, int, str], float]:
    found = getattr(bot, LEDGER_ATTR, None)
    if found is None:
        found = {}
        setattr(bot, LEDGER_ATTR, found)
    return found


def remember_change(bot: Any, guild_id: int, user_id: int, role_ids: Any, direction: str) -> None:
    """What Black Bloc is about to do, so its own edit never reads as a by-hand one."""
    book = _ledger(bot)
    deadline = time.monotonic() + LEDGER_SECONDS
    for role_id in role_ids or ():
        book[(int(guild_id), int(user_id), int(role_id), direction)] = deadline


def forget_change(bot: Any, guild_id: int, user_id: int, role_ids: Any, direction: str) -> None:
    book = _ledger(bot)
    for role_id in role_ids or ():
        book.pop((int(guild_id), int(user_id), int(role_id), direction), None)


def was_ours(bot: Any, guild_id: int, user_id: int, role_id: int, direction: str) -> bool:
    """True once per remembered change; entries older than ~30 s never count."""
    book = _ledger(bot)
    now = time.monotonic()
    for key, deadline in list(book.items()):
        if deadline <= now:
            book.pop(key, None)
    return book.pop((int(guild_id), int(user_id), int(role_id), direction), None) is not None


async def create_request(
    db: Any, guild_id: int, menu_id: int, user_id: int, role_id: int
) -> int | None:
    """The new request's id, or None when one is already open for that member and role."""
    if await open_request(db, menu_id, user_id, role_id) is not None:
        return None
    cur = await db.conn.execute(
        "INSERT INTO role_requests(guild_id, menu_id, user_id, role_id, requested_at, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (guild_id, menu_id, user_id, role_id, now_iso(), PENDING),
    )
    await db.conn.commit()
    return cur.lastrowid


async def get_request(db: Any, request_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM role_requests WHERE id = ?", (request_id,))
    return await cur.fetchone()


async def open_request(db: Any, menu_id: int, user_id: int, role_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM role_requests WHERE menu_id = ? AND user_id = ? AND role_id = ? "
        "AND status = ?",
        (menu_id, user_id, role_id, PENDING),
    )
    return await cur.fetchone()


async def open_requests_for(db: Any, guild_id: int, user_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM role_requests WHERE guild_id = ? AND user_id = ? AND status = ? "
        "ORDER BY id",
        (guild_id, user_id, PENDING),
    )
    return list(await cur.fetchall())


async def open_request_for_role(db: Any, guild_id: int, user_id: int, role_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM role_requests WHERE guild_id = ? AND user_id = ? AND role_id = ? "
        "AND status = ? ORDER BY id DESC LIMIT 1",
        (guild_id, user_id, role_id, PENDING),
    )
    return await cur.fetchone()


async def last_denial(db: Any, menu_id: int, user_id: int, role_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM role_requests WHERE menu_id = ? AND user_id = ? AND role_id = ? "
        "AND status = ? ORDER BY id DESC LIMIT 1",
        (menu_id, user_id, role_id, DENIED),
    )
    return await cur.fetchone()


async def requests_by_status(db: Any, guild_id: int, statuses: Any = None) -> list[Any]:
    """Pending first, newest first inside each group — the order the queue is worked in."""
    wanted = tuple(statuses or REQUEST_STATUSES)
    marks = ", ".join("?" for _ in wanted)
    cur = await db.conn.execute(
        f"SELECT * FROM role_requests WHERE guild_id = ? AND status IN ({marks}) "
        "ORDER BY (status = 'pending') DESC, id DESC",
        (guild_id, *wanted),
    )
    return list(await cur.fetchall())


async def open_requests(db: Any, guild_id: int) -> list[Any]:
    return await requests_by_status(db, guild_id, (PENDING,))


async def set_request_card(
    db: Any, request_id: int, channel_id: int | None, message_id: int | None
) -> None:
    await db.conn.execute(
        "UPDATE role_requests SET channel_id = ?, message_id = ? WHERE id = ?",
        (channel_id, message_id, request_id),
    )
    await db.conn.commit()


async def decide_request(
    db: Any,
    request_id: int,
    status: str,
    *,
    decided_by: int | None = None,
    deny_reason: str | None = None,
) -> bool:
    """One writer wins: the update only lands while the request is still pending."""
    cur = await db.conn.execute(
        "UPDATE role_requests SET status = ?, decided_by = ?, decided_at = ?, deny_reason = ? "
        "WHERE id = ? AND status = ?",
        (status, decided_by, now_iso(), deny_reason, request_id, PENDING),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def add_grant(
    db: Any,
    guild_id: int,
    user_id: int,
    role_id: int,
    source: str,
    *,
    granted_by: int | None = None,
    until: str | None = None,
) -> int | None:
    if source not in SOURCES:
        raise ValueError(f"source must be one of {SOURCES}")
    cur = await db.conn.execute(
        "INSERT INTO role_grants(guild_id, user_id, role_id, source, granted_by, granted_at, "
        "expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (guild_id, user_id, role_id, source, granted_by, now_iso(), until),
    )
    await db.conn.commit()
    return cur.lastrowid


async def get_grant(db: Any, grant_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM role_grants WHERE id = ?", (grant_id,))
    return await cur.fetchone()


async def open_grant(db: Any, guild_id: int, user_id: int, role_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM role_grants WHERE guild_id = ? AND user_id = ? AND role_id = ? "
        "AND removed_at IS NULL ORDER BY id DESC LIMIT 1",
        (guild_id, user_id, role_id),
    )
    return await cur.fetchone()


async def open_grants(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM role_grants WHERE guild_id = ? AND removed_at IS NULL ORDER BY id",
        (guild_id,),
    )
    return list(await cur.fetchall())


async def grants_for(
    db: Any,
    guild_id: int,
    *,
    user_id: int | None = None,
    role_id: int | None = None,
    limit: int = 200,
) -> list[Any]:
    """Open grants first, then the closed ones newest first."""
    sql = "SELECT * FROM role_grants WHERE guild_id = ?"
    args: tuple[Any, ...] = (guild_id,)
    if user_id is not None:
        sql += " AND user_id = ?"
        args += (user_id,)
    if role_id is not None:
        sql += " AND role_id = ?"
        args += (role_id,)
    cur = await db.conn.execute(
        sql + " ORDER BY (removed_at IS NULL) DESC, id DESC LIMIT ?", (*args, limit)
    )
    return list(await cur.fetchall())


async def due_grants(db: Any, before: str) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM role_grants WHERE removed_at IS NULL AND expires_at IS NOT NULL "
        "AND expires_at <= ? ORDER BY id",
        (before,),
    )
    return list(await cur.fetchall())


async def end_grant(db: Any, grant_id: int, reason: str) -> bool:
    cur = await db.conn.execute(
        "UPDATE role_grants SET removed_at = ?, removed_reason = ? "
        "WHERE id = ? AND removed_at IS NULL",
        (now_iso(), reason, grant_id),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def extend_grant(db: Any, grant_id: int, until: str) -> bool:
    cur = await db.conn.execute(
        "UPDATE role_grants SET expires_at = ? WHERE id = ? AND removed_at IS NULL",
        (until, grant_id),
    )
    await db.conn.commit()
    return bool(cur.rowcount)


async def record_added(
    db: Any,
    guild_id: int,
    user_id: int,
    role_ids: Any,
    source: str,
    *,
    granted_by: int | None = None,
    until: str | None = None,
) -> None:
    """One open grant per member and role; a second add just leaves the first standing."""
    for role_id in role_ids or ():
        if await open_grant(db, guild_id, user_id, role_id) is None:
            await add_grant(
                db, guild_id, user_id, role_id, source, granted_by=granted_by, until=until
            )


async def record_removed(db: Any, guild_id: int, user_id: int, role_ids: Any, reason: str) -> None:
    for role_id in role_ids or ():
        row = await open_grant(db, guild_id, user_id, role_id)
        if row is not None:
            await end_grant(db, row["id"], reason)


__all__ = [
    "ADDED",
    "APPROVAL",
    "APPROVED",
    "BY_HAND",
    "DENIED",
    "EXPIRED",
    "GIVEN_UP",
    "GRANTED_BY_HAND",
    "MANUAL",
    "MENU",
    "PENDING",
    "REMOVED",
    "REQUEST_STATUSES",
    "SOURCES",
    "STAFF",
    "WITHDRAWN",
    "add_grant",
    "create_request",
    "decide_request",
    "due_grants",
    "end_grant",
    "expires_at",
    "extend_grant",
    "forget_change",
    "get_grant",
    "get_request",
    "grants_for",
    "last_denial",
    "open_grant",
    "open_grants",
    "open_request",
    "open_requests",
    "pushed_back",
    "record_added",
    "record_removed",
    "remember_change",
    "requests_by_status",
    "set_request_card",
    "stamp",
    "still_cooling",
    "was_ours",
]
