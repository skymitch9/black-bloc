from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from .timezones import DEFAULT_TZ, zone

log = logging.getLogger(__name__)

OPEN = "open"
IN_PROGRESS = "in_progress"
HOLD = "hold"
DONE = "done"
DECLINED = "declined"
WITHDRAWN = "withdrawn"

STATUSES = (OPEN, IN_PROGRESS, HOLD, DONE, DECLINED, WITHDRAWN)

TRANSITIONS: dict[str, frozenset[str]] = {
    OPEN: frozenset({IN_PROGRESS, HOLD, DECLINED}),
    IN_PROGRESS: frozenset({DONE, HOLD, DECLINED}),
    HOLD: frozenset({IN_PROGRESS, DECLINED}),
    DONE: frozenset(),
    DECLINED: frozenset(),
    WITHDRAWN: frozenset(),
}
WITHDRAWABLE = (OPEN, HOLD)
STAFF_STATUSES = tuple(
    sorted({one for moves in TRANSITIONS.values() for one in moves})
)
OPEN_STATUSES = (OPEN, IN_PROGRESS, HOLD)
FINAL_STATUSES = tuple(one for one in STATUSES if not TRANSITIONS[one])
NEEDS_A_REASON = (HOLD, DECLINED)
DM_STATUSES = (IN_PROGRESS, HOLD, DONE, DECLINED)

WHAT_LIMIT = 1000
WHY_LIMIT = 1000
REASON_LIMIT = 400
NOTES_LIMIT = 1000
COMMENT_LIMIT = 1000
PRIORITY_MAX = 5
DUE_SHAPE = "YYYY-MM-DD"
LIST_PAGE = 10
API_PAGE = 20
SEARCH_LIMIT = 80

STATUS_WORDS: dict[str, str] = {
    OPEN: "open",
    IN_PROGRESS: "being worked on",
    HOLD: "on hold",
    DONE: "done",
    DECLINED: "declined",
    WITHDRAWN: "withdrawn",
}

REQUESTS_OFF = (
    "Requests are turned off on this server, so nothing was filed. A Lead turns them back on "
    "with `/settings set request_mode on` — ask one if you have something to ask for."
)
STAFF_ONLY_FILES = (
    "Only staff may file a request on this server at the moment, so nothing was filed. Ask a Lead "
    "to put it in for you, or to set `request_who_can_file` to everyone."
)
NEEDS_WHAT = (
    "A request needs a line saying what you are asking for, so nothing was filed. Fill the What "
    "box in and send it again."
)
NEEDS_WHY = (
    "A request needs a line saying why it is worth doing, so nothing was filed. That is the part "
    "staff read first — fill the Why box in and send it again."
)
BAD_DUE = (
    "**{given}** is not a date Black Bloc can read, so nothing was filed. Write it as "
    f"`{DUE_SHAPE}` — `2026-09-15`, say — or leave the box empty if there is no deadline."
)
NO_SUCH_REQUEST = (
    "Black Bloc has no request **#{request_id}**, so nothing was done. `/request list` shows the "
    "ones it has."
)
NOT_YOURS = (
    "Request **#{request_id}** is not yours, so nothing was withdrawn. Only the person who filed "
    "it can take it back; staff decline one instead."
)
TOO_LATE_TO_WITHDRAW = (
    "Request **#{request_id}** is **{status}**, so there was nothing to withdraw. You can take "
    "back one that is still open or on hold; ask staff if you want this one stopped."
)
ALREADY_THAT = "Request **#{request_id}** is already **{status}**, so nothing was changed."
UNKNOWN_STATUS = (
    "**{given}** is not a state a request can be in, so nothing was changed. They are {known}."
)
NO_SUCH_MOVE = (
    "Request **#{request_id}** is **{status}**, and staff cannot move it to **{wanted}** from "
    "there, so nothing was changed. {allowed}"
)
MOVES_ARE = "From **{status}** it can go to {moves}."
NO_MOVES_LEFT = "**{status}** is where a request finishes — nothing moves it now."
DECLINE_NEEDS_A_REASON = (
    "A declined request needs one line the person who asked is sent, so nothing was changed. Say "
    "why and send it again."
)
HOLD_NEEDS_A_REASON = (
    "A request put on hold needs one line the person who asked is sent, so nothing was changed. "
    "Say why it is waiting and send it again."
)
REASON_NEEDED: dict[str, str] = {
    DECLINED: DECLINE_NEEDS_A_REASON,
    HOLD: HOLD_NEEDS_A_REASON,
}
NOT_ON_HOLD = (
    "Request **#{request_id}** is **{status}**, not on hold, so there was nothing to resume. "
    "`/request set` moves it from where it is."
)
BAD_PRIORITY = (
    "**{given}** is not a priority Black Bloc can read, so nothing was changed. Send a whole "
    f"number from 0 to {PRIORITY_MAX}, or nothing at all to leave it unranked."
)
COMMENT_NEEDS_TEXT = (
    "There is nothing to add, so no comment was left. Type what you want on the request and send "
    "it again."
)
WITHDRAWN_SAID = "Request **#{request_id}** is withdrawn. Nobody will pick it up now."
FILED = (
    "Filed as **#{request_id}** — staff will see it on the site. You will get a DM every time it "
    "moves."
)
NOTHING_FILED_YET = "Nothing has been filed yet — `/request` puts the first one in."
NOTHING_OPEN = "Nothing is open — every request has been finished, declined or withdrawn."
NOTHING_OF_YOURS = "You have not filed a request yet — `/request` puts one in."

DM_IN_PROGRESS = "Your request **#{request_id}** on **{guild}** is being worked on: {what}"
DM_HOLD = (
    "Your request **#{request_id}** on **{guild}** is on hold — {reason}\n\nIt was: {held_from}"
    "\n\nWhat you asked for: {what}"
)
DM_DECLINED = (
    "Your request **#{request_id}** on **{guild}** was declined — {reason}\n\nWhat you asked for: "
    "{what}"
)
DM_DONE = "Your request **#{request_id}** on **{guild}** is done: {what}"
DM_TEXT: dict[str, str] = {
    IN_PROGRESS: DM_IN_PROGRESS,
    HOLD: DM_HOLD,
    DECLINED: DM_DECLINED,
    DONE: DM_DONE,
}

NOTIFY_LINE = "New request **#{request_id}** from {who}: {what}"
NOTIFY_IN_PROGRESS = "Request **#{request_id}** from {who} is being worked on: {what}"
NOTIFY_HOLD = "Request **#{request_id}** from {who} is on hold — {reason}"
NOTIFY_DONE = "Request **#{request_id}** from {who} is done: {what}"
NOTIFY_DECLINED = "Request **#{request_id}** from {who} was declined — {reason}"
NOTIFY_MOVE: dict[str, str] = {
    IN_PROGRESS: NOTIFY_IN_PROGRESS,
    HOLD: NOTIFY_HOLD,
    DONE: NOTIFY_DONE,
    DECLINED: NOTIFY_DECLINED,
}
NOTIFY_SKIPPED_KIND = "request.notify_skipped_test_mode"
NOTIFY_FAILED_KIND = "request.notify_failed"
STATUS_CHANNEL_KEY = "request_status_channel_id"
NOTIFY_CHANNEL_KEY = "request_notify_channel_id"


class RequestError(ValueError):
    """Something a person typed cannot be stored; the message is the sentence they see."""


def clamp(text: Any, limit: int) -> str:
    return str(text or "").strip()[:limit]


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def parse_due(raw: Any) -> str | None:
    """`YYYY-MM-DD` or nothing; anything else is a sentence, never a silent drop."""
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        found = date.fromisoformat(text)
    except ValueError:
        raise RequestError(BAD_DUE.format(given=clamp(text, 40))) from None
    return found.isoformat()


def due_stamp(due_on: Any, tz_name: Any = DEFAULT_TZ) -> str | None:
    """`<t:…:D>` from local midnight in the server's zone; the stored value stays a date."""
    if not due_on:
        return None
    try:
        found = date.fromisoformat(str(due_on))
    except ValueError:
        return None
    at = datetime(found.year, found.month, found.day, tzinfo=zone(tz_name) or UTC)
    return f"<t:{int(at.timestamp())}:D>"


def wanted_priority(given: Any) -> int | None:
    if given is None or given == "":
        return None
    try:
        number = int(given)
    except (TypeError, ValueError):
        raise RequestError(BAD_PRIORITY.format(given=clamp(given, 40))) from None
    if isinstance(given, bool) or number < 0 or number > PRIORITY_MAX:
        raise RequestError(BAD_PRIORITY.format(given=clamp(given, 40)))
    return number


def moves_from(status: Any) -> tuple[str, ...]:
    """The one table every path asks — slash, web and tests alike."""
    return tuple(sorted(TRANSITIONS.get(str(status or ""), frozenset())))


def can_move(status: Any, wanted: Any) -> bool:
    return str(wanted or "") in TRANSITIONS.get(str(status or ""), frozenset())


def moves_sentence(status: Any) -> str:
    """A refusal always says where a request CAN go from where it is."""
    found = moves_from(status)
    if not found:
        return NO_MOVES_LEFT.format(status=STATUS_WORDS.get(str(status), str(status)))
    return MOVES_ARE.format(
        status=STATUS_WORDS.get(str(status), str(status)),
        moves=", ".join(f"**{one}**" for one in found),
    )


def wanted_status(given: Any) -> str:
    text = str(given or "").strip().lower()
    if text not in STAFF_STATUSES:
        raise RequestError(
            UNKNOWN_STATUS.format(given=clamp(given, 40), known=", ".join(STAFF_STATUSES))
        )
    return text


def checked_move(request_id: Any, status: Any, wanted: Any, reason: Any = "") -> str:
    """The whole gate in one place: known state, a legal move, and a reason where one is owed."""
    where = str(status or "")
    to = wanted_status(wanted)
    if where == to:
        raise RequestError(
            ALREADY_THAT.format(
                request_id=request_id, status=STATUS_WORDS.get(where, where)
            )
        )
    if not can_move(where, to):
        raise RequestError(
            NO_SUCH_MOVE.format(
                request_id=request_id,
                status=STATUS_WORDS.get(where, where),
                wanted=to,
                allowed=moves_sentence(where),
            )
        )
    if to in NEEDS_A_REASON and not str(reason or "").strip():
        raise RequestError(REASON_NEEDED[to])
    return to


def wanted_statuses(given: Any) -> tuple[str, ...]:
    wanted = tuple(part.strip() for part in str(given or "").split(",") if part.strip())
    for part in wanted:
        if part not in STATUSES:
            raise RequestError(
                UNKNOWN_STATUS.format(given=clamp(part, 40), known=", ".join(STATUSES))
            )
    return wanted or STATUSES


def checked_fields(what: Any, why: Any, due: Any) -> tuple[str, str, str | None]:
    """The three the modal and the site both send, refused in the order a person meets them."""
    kept_what = clamp(what, WHAT_LIMIT)
    if not kept_what:
        raise RequestError(NEEDS_WHAT)
    kept_why = clamp(why, WHY_LIMIT)
    if not kept_why:
        raise RequestError(NEEDS_WHY)
    return kept_what, kept_why, parse_due(due)


def requests_are_on(store: Any, guild_id: int) -> bool:
    return store.get(guild_id, "request_mode") != "off"


def everyone_may_file(store: Any, guild_id: int) -> bool:
    return store.get(guild_id, "request_who_can_file") != "staff"


def dms_on_decision(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, "request_dm_on_decision"))


def status_channel_id(store: Any, guild_id: int) -> Any:
    """Its own channel if the server set one, otherwise the one filings already go to."""
    return store.get(guild_id, STATUS_CHANNEL_KEY) or store.get(guild_id, NOTIFY_CHANNEL_KEY)


def held_words(row: Any) -> str:
    found = row_value(row, "held_from")
    return STATUS_WORDS.get(str(found or ""), str(found or "")) if found else ""


def row_value(row: Any, name: str, fallback: Any = None) -> Any:
    """A column a schema-22 file has not grown yet reads as nothing, never as a crash."""
    try:
        return row[name]
    except (KeyError, IndexError, TypeError):
        return fallback


def summary_line(row: Any) -> str:
    due = due_stamp(row["due_on"])
    when = f" · due {due}" if due else ""
    where = STATUS_WORDS.get(row["status"], row["status"])
    was = held_words(row)
    held = f" (was: {was})" if row["status"] == HOLD and was else ""
    return f"**#{row['id']}** {clamp(row['what'], 70)} — {where}{held}{when}"


def page_of(rows: list[Any], page: int, per_page: int = LIST_PAGE) -> tuple[list[Any], int, int]:
    """(the rows on that page, the page actually shown, how many pages there are)."""
    pages = max(1, -(-len(rows) // per_page))
    at = max(1, min(int(page or 1), pages))
    start = (at - 1) * per_page
    return (rows[start : start + per_page], at, pages)


async def create_request(
    db: Any,
    guild_id: int,
    user_id: int,
    *,
    what: str,
    why: str,
    due_on: str | None,
    status: str = OPEN,
    decided_by: int | None = None,
) -> int | None:
    decided_at = now_iso() if decided_by is not None else None
    cur = await db.conn.execute(
        "INSERT INTO requests(guild_id, user_id, what, why, due_on, status, created_at, "
        "decided_by, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (guild_id, user_id, what, why, due_on, status, now_iso(), decided_by, decided_at),
    )
    await db.conn.commit()
    return cur.lastrowid


async def get_request(db: Any, request_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,))
    return await cur.fetchone()


UNASSIGNED = "none"


def _where(
    guild_id: int,
    *,
    statuses: Any = None,
    assignee_id: Any = None,
    user_id: int | None = None,
    query: str = "",
    named: Any = None,
) -> tuple[str, list[Any]]:
    """`assignee_id=UNASSIGNED` is the board's Unassigned column; `named` are id matches for `q`."""
    clauses = ["guild_id = ?"]
    params: list[Any] = [guild_id]
    if statuses:
        clauses.append(f"status IN ({', '.join('?' for _ in statuses)})")
        params.extend(statuses)
    if assignee_id == UNASSIGNED:
        clauses.append("assignee_id IS NULL")
    elif assignee_id is not None:
        clauses.append("assignee_id = ?")
        params.append(assignee_id)
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if query:
        like = f"%{query}%"
        found = [int(one) for one in named or ()]
        by_name = f" OR user_id IN ({', '.join('?' for _ in found)})" if found else ""
        clauses.append(f"(what LIKE ? OR why LIKE ? OR notes LIKE ?{by_name})")
        params.extend([like, like, like, *found])
    return (" AND ".join(clauses), params)


async def list_requests(
    db: Any,
    guild_id: int,
    *,
    statuses: Any = None,
    assignee_id: Any = None,
    user_id: int | None = None,
    query: str = "",
    named: Any = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Any]:
    """Pending first, then newest; the order the requests page and `/request list` both show."""
    where, params = _where(
        guild_id,
        statuses=statuses,
        assignee_id=assignee_id,
        user_id=user_id,
        query=query,
        named=named,
    )
    tail = ""
    if limit is not None:
        tail = " LIMIT ? OFFSET ?"
        params = [*params, int(limit), int(offset)]
    cur = await db.conn.execute(
        f"SELECT * FROM requests WHERE {where} "
        f"ORDER BY (status <> '{OPEN}'), id DESC{tail}",
        tuple(params),
    )
    return list(await cur.fetchall())


async def count_requests(
    db: Any,
    guild_id: int,
    *,
    statuses: Any = None,
    assignee_id: Any = None,
    user_id: int | None = None,
    query: str = "",
    named: Any = None,
) -> int:
    where, params = _where(
        guild_id,
        statuses=statuses,
        assignee_id=assignee_id,
        user_id=user_id,
        query=query,
        named=named,
    )
    cur = await db.conn.execute(
        f"SELECT COUNT(*) AS found FROM requests WHERE {where}", tuple(params)
    )
    row = await cur.fetchone()
    return int(row["found"]) if row is not None else 0


async def set_status(
    db: Any,
    request_id: int,
    status: str,
    *,
    decided_by: int | None = None,
    decline_reason: str | None = None,
    was: str | None = None,
) -> None:
    """`held_from` is written on the way into hold and cleared on the way out — one home."""
    at = now_iso()
    held_from = str(was or "") if status == HOLD else None
    await db.conn.execute(
        "UPDATE requests SET status = ?, decided_by = COALESCE(?, decided_by), "
        "decided_at = COALESCE(?, decided_at), decline_reason = ?, held_from = ?, "
        "done_at = CASE WHEN ? = ? THEN ? ELSE done_at END WHERE id = ?",
        (
            status,
            decided_by,
            at if decided_by is not None else None,
            decline_reason if status in NEEDS_A_REASON else None,
            held_from or None,
            status,
            DONE,
            at,
            request_id,
        ),
    )
    await db.conn.commit()


async def set_fields(
    db: Any,
    request_id: int,
    *,
    assignee_id: Any = ...,
    priority: Any = ...,
    notes: Any = ...,
) -> list[str]:
    """Only the fields actually sent are written; `...` means 'leave it as it is'."""
    sets: list[str] = []
    params: list[Any] = []
    for name, value in (("assignee_id", assignee_id), ("priority", priority), ("notes", notes)):
        if value is ...:
            continue
        sets.append(f"{name} = ?")
        params.append(value)
    if not sets:
        return []
    params.append(request_id)
    await db.conn.execute(f"UPDATE requests SET {', '.join(sets)} WHERE id = ?", tuple(params))
    await db.conn.commit()
    return [name for name, value in (
        ("assignee_id", assignee_id), ("priority", priority), ("notes", notes)
    ) if value is not ...]


async def set_message(db: Any, request_id: int, message_id: int | None) -> None:
    await db.conn.execute(
        "UPDATE requests SET message_id = ? WHERE id = ?", (message_id, request_id)
    )
    await db.conn.commit()


async def add_comment(db: Any, request_id: int, author_id: int, text: str) -> int | None:
    cur = await db.conn.execute(
        "INSERT INTO request_comments(request_id, author_id, text, at) VALUES (?, ?, ?, ?)",
        (request_id, author_id, text, now_iso()),
    )
    await db.conn.commit()
    return cur.lastrowid


async def get_comment(db: Any, comment_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM request_comments WHERE id = ?", (comment_id,))
    return await cur.fetchone()


async def comments_for(db: Any, request_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM request_comments WHERE request_id = ? ORDER BY id", (request_id,)
    )
    return list(await cur.fetchall())


async def comment_counts(db: Any, request_ids: Any) -> dict[int, int]:
    ids = [int(one) for one in request_ids]
    if not ids:
        return {}
    marks = ", ".join("?" for _ in ids)
    cur = await db.conn.execute(
        f"SELECT request_id, COUNT(*) AS found FROM request_comments "
        f"WHERE request_id IN ({marks}) GROUP BY request_id",
        tuple(ids),
    )
    return {int(row["request_id"]): int(row["found"]) for row in await cur.fetchall()}


async def open_count(db: Any, guild_id: int) -> int:
    return await count_requests(db, guild_id, statuses=(OPEN,))


def resume_target(row: Any) -> str:
    """Where Resume puts it: back where it was held from, or straight into progress."""
    found = str(row_value(row, "held_from") or "")
    return found if found in TRANSITIONS.get(HOLD, frozenset()) else IN_PROGRESS


__all__ = [
    "DECLINED",
    "DM_STATUSES",
    "DM_TEXT",
    "DONE",
    "FINAL_STATUSES",
    "HOLD",
    "IN_PROGRESS",
    "NEEDS_A_REASON",
    "NOTIFY_MOVE",
    "OPEN",
    "OPEN_STATUSES",
    "STAFF_STATUSES",
    "STATUSES",
    "STATUS_WORDS",
    "TRANSITIONS",
    "WITHDRAWABLE",
    "WITHDRAWN",
    "RequestError",
    "add_comment",
    "can_move",
    "checked_fields",
    "checked_move",
    "clamp",
    "comment_counts",
    "comments_for",
    "count_requests",
    "create_request",
    "due_stamp",
    "get_comment",
    "get_request",
    "held_words",
    "list_requests",
    "moves_from",
    "moves_sentence",
    "open_count",
    "page_of",
    "parse_due",
    "resume_target",
    "row_value",
    "set_fields",
    "set_message",
    "set_status",
    "status_channel_id",
    "wanted_priority",
    "wanted_status",
    "wanted_statuses",
]
