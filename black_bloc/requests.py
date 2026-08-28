from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

log = logging.getLogger(__name__)

PENDING = "pending"
APPROVED = "approved"
PLANNED = "planned"
IN_PROGRESS = "in_progress"
DONE = "done"
DECLINED = "declined"
WITHDRAWN = "withdrawn"

STATUSES = (PENDING, APPROVED, PLANNED, IN_PROGRESS, DONE, DECLINED, WITHDRAWN)
STAFF_STATUSES = (APPROVED, PLANNED, IN_PROGRESS, DONE, DECLINED)
OPEN_STATUSES = (PENDING, APPROVED, PLANNED, IN_PROGRESS)
DM_STATUSES = (APPROVED, DECLINED, DONE)

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
    PENDING: "waiting on staff",
    APPROVED: "approved",
    PLANNED: "planned",
    IN_PROGRESS: "being worked on",
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
NOT_PENDING = (
    "Request **#{request_id}** is already **{status}**, so there was nothing to withdraw. Ask "
    "staff if you want it stopped."
)
ALREADY_THAT = "Request **#{request_id}** is already **{status}**, so nothing was changed."
UNKNOWN_STATUS = (
    "**{given}** is not a state a request can be in, so nothing was changed. They are {known}."
)
DECLINE_NEEDS_A_REASON = (
    "A declined request needs one line the person who asked is sent, so nothing was changed. Say "
    "why and send it again."
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
    "Filed as **#{request_id}** — staff will see it on the site. You will get a DM when somebody "
    "decides on it."
)
FILED_APPROVED = (
    "Filed as **#{request_id}**, and approved straight away because you are staff. It is on the "
    "pending features list now."
)
NOTHING_FILED_YET = "Nothing has been filed yet — `/request` puts the first one in."
NOTHING_PENDING = "Nothing is waiting on a decision."
NOTHING_OF_YOURS = "You have not filed a request yet — `/request` puts one in."

DM_APPROVED = (
    "Your request **#{request_id}** on **{guild}** was approved. It is on the pending features "
    "list now: {what}"
)
DM_DECLINED = (
    "Your request **#{request_id}** on **{guild}** was declined — {reason}\n\nWhat you asked for: "
    "{what}"
)
DM_DONE = "Your request **#{request_id}** on **{guild}** is done: {what}"
DM_TEXT: dict[str, str] = {APPROVED: DM_APPROVED, DECLINED: DM_DECLINED, DONE: DM_DONE}

NOTIFY_LINE = "New request **#{request_id}** from {who}: {what}"


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


def due_stamp(due_on: Any) -> str | None:
    if not due_on:
        return None
    try:
        found = date.fromisoformat(str(due_on))
    except ValueError:
        return None
    at = datetime(found.year, found.month, found.day, 12, 0, tzinfo=UTC)
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


def wanted_status(given: Any) -> str:
    text = str(given or "").strip().lower()
    if text not in STAFF_STATUSES:
        raise RequestError(
            UNKNOWN_STATUS.format(given=clamp(given, 40), known=", ".join(STAFF_STATUSES))
        )
    return text


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


def auto_approves(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, "request_auto_approve_staff"))


def dms_on_decision(store: Any, guild_id: int) -> bool:
    return bool(store.get(guild_id, "request_dm_on_decision"))


def summary_line(row: Any) -> str:
    due = due_stamp(row["due_on"])
    when = f" · due {due}" if due else ""
    where = STATUS_WORDS.get(row["status"], row["status"])
    return f"**#{row['id']}** {clamp(row['what'], 70)} — {where}{when}"


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
    status: str = PENDING,
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


def _where(
    guild_id: int,
    *,
    statuses: Any = None,
    assignee_id: int | None = None,
    user_id: int | None = None,
    query: str = "",
) -> tuple[str, list[Any]]:
    clauses = ["guild_id = ?"]
    params: list[Any] = [guild_id]
    if statuses:
        clauses.append(f"status IN ({', '.join('?' for _ in statuses)})")
        params.extend(statuses)
    if assignee_id is not None:
        clauses.append("assignee_id = ?")
        params.append(assignee_id)
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if query:
        clauses.append("(what LIKE ? OR why LIKE ? OR notes LIKE ?)")
        like = f"%{query}%"
        params.extend([like, like, like])
    return (" AND ".join(clauses), params)


async def list_requests(
    db: Any,
    guild_id: int,
    *,
    statuses: Any = None,
    assignee_id: int | None = None,
    user_id: int | None = None,
    query: str = "",
    limit: int | None = None,
    offset: int = 0,
) -> list[Any]:
    """Pending first, then newest; the order the requests page and `/request list` both show."""
    where, params = _where(
        guild_id, statuses=statuses, assignee_id=assignee_id, user_id=user_id, query=query
    )
    tail = ""
    if limit is not None:
        tail = " LIMIT ? OFFSET ?"
        params = [*params, int(limit), int(offset)]
    cur = await db.conn.execute(
        f"SELECT * FROM requests WHERE {where} "
        f"ORDER BY (status <> '{PENDING}'), id DESC{tail}",
        tuple(params),
    )
    return list(await cur.fetchall())


async def count_requests(
    db: Any,
    guild_id: int,
    *,
    statuses: Any = None,
    assignee_id: int | None = None,
    user_id: int | None = None,
    query: str = "",
) -> int:
    where, params = _where(
        guild_id, statuses=statuses, assignee_id=assignee_id, user_id=user_id, query=query
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
) -> None:
    at = now_iso()
    await db.conn.execute(
        "UPDATE requests SET status = ?, decided_by = COALESCE(?, decided_by), "
        "decided_at = COALESCE(?, decided_at), decline_reason = ?, "
        "done_at = CASE WHEN ? = ? THEN ? ELSE done_at END WHERE id = ?",
        (
            status,
            decided_by,
            at if decided_by is not None else None,
            decline_reason if status == DECLINED else None,
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


async def pending_count(db: Any, guild_id: int) -> int:
    return await count_requests(db, guild_id, statuses=(PENDING,))


__all__ = [
    "APPROVED",
    "DECLINED",
    "DM_STATUSES",
    "DONE",
    "IN_PROGRESS",
    "OPEN_STATUSES",
    "PENDING",
    "PLANNED",
    "STAFF_STATUSES",
    "STATUSES",
    "WITHDRAWN",
    "RequestError",
    "add_comment",
    "checked_fields",
    "clamp",
    "comment_counts",
    "comments_for",
    "count_requests",
    "create_request",
    "due_stamp",
    "get_comment",
    "get_request",
    "list_requests",
    "page_of",
    "parse_due",
    "pending_count",
    "set_fields",
    "set_message",
    "set_status",
    "wanted_priority",
    "wanted_status",
    "wanted_statuses",
]
