from __future__ import annotations

import csv
import io
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from ...cogs.community.requests import apply_decision, notify, resume_request
from ...logkinds import VIA_WEBSITE
from ...requests import (
    API_PAGE,
    COMMENT_LIMIT,
    COMMENT_NEEDS_TEXT,
    DECLINED,
    HOLD,
    NEEDS_A_REASON,
    NO_SUCH_REQUEST,
    NOT_YOURS,
    NOTES_LIMIT,
    OPEN,
    REASON_LIMIT,
    REASON_NEEDED,
    REQUESTS_OFF,
    SEARCH_LIMIT,
    STAFF_ONLY_FILES,
    STATUS_WORDS,
    TOO_LATE_TO_WITHDRAW,
    UNASSIGNED,
    WITHDRAWABLE,
    WITHDRAWN,
    WITHDRAWN_SAID,
    RequestError,
    add_comment,
    checked_fields,
    clamp,
    comment_counts,
    comments_for,
    count_requests,
    create_request,
    everyone_may_file,
    get_comment,
    get_request,
    held_words,
    list_requests,
    moves_from,
    requests_are_on,
    resume_target,
    row_value,
    set_fields,
    set_status,
    wanted_priority,
    wanted_status,
    wanted_statuses,
)
from ..auth import Refused
from ..names import as_id, avatar_url, resolve_one
from ..writes import (
    actor_for,
    member_dependency,
    note,
    reader_dependency,
    require_db,
    require_guild,
    writer_dependency,
)

log = logging.getLogger(__name__)

CSV_MEDIA_TYPE = "text/csv"
NAME_MATCH_LIMIT = 200
CSV_COLUMNS = (
    "id",
    "status",
    "what",
    "why",
    "due_on",
    "priority",
    "requester_id",
    "requester_name",
    "assignee_id",
    "assignee_name",
    "created_at",
    "decided_by",
    "decided_at",
    "decline_reason",
    "held_from",
    "done_at",
    "comments",
)

FILED_SAID = "Filed as **#{request_id}** — staff will see it on this page."
SET_SAID = "Request **#{request_id}** is now **{status}**."
SAVED_SAID = "Request **#{request_id}** is saved."
COMMENT_SAID = "Your comment is on request **#{request_id}**."
NOTHING_TO_SAVE = (
    "That change arrived with nothing in it, so nothing was saved. It is a fault in the page "
    "rather than in what you typed — reload the requests page and try again."
)
BAD_ASSIGNEE = (
    "**{given}** is not somebody Black Bloc can see in this server, so nothing was changed. Pick "
    "a name from the list."
)


def person(guild: Any, user_id: Any) -> dict[str, Any] | None:
    number = as_id(user_id)
    if number is None:
        return None
    member = guild.get_member(number) if guild is not None else None
    return {
        "id": str(number),
        "name": resolve_one(guild, number)["display_name"] or str(number),
        "avatar": avatar_url(member) if member is not None else None,
    }


def request_row(guild: Any, row: Any, comments: int = 0) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "what": row["what"],
        "why": row["why"],
        "due_on": row["due_on"],
        "status": row["status"],
        "status_word": STATUS_WORDS.get(row["status"], row["status"]),
        "priority": row["priority"],
        "notes": row["notes"],
        "requester": person(guild, row["user_id"]),
        "assignee": person(guild, row["assignee_id"]),
        "comment_count": int(comments),
        "created_at": row["created_at"],
        "decided_by": str(row["decided_by"]) if row["decided_by"] else None,
        "decided_by_name": (
            resolve_one(guild, row["decided_by"])["display_name"] if row["decided_by"] else None
        ),
        "decided_at": row["decided_at"],
        "decline_reason": row["decline_reason"],
        "held_from": row_value(row, "held_from"),
        "held_word": held_words(row),
        "moves": list(moves_from(row["status"])),
        "resume_to": resume_target(row) if row["status"] == HOLD else None,
        "done_at": row["done_at"],
    }


def comment_row(guild: Any, row: Any) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "request_id": str(row["request_id"]),
        "author": person(guild, row["author_id"]),
        "text": row["text"],
        "at": row["at"],
    }


def refused(exc: RequestError) -> Refused:
    return Refused(400, "request_refused", str(exc))


def export_csv(guild: Any, rows: Any, counts: dict[int, int]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        shown = request_row(guild, row, counts.get(int(row["id"]), 0))
        assignee = shown["assignee"] or {}
        writer.writerow(
            [
                shown["id"],
                shown["status"],
                shown["what"],
                shown["why"],
                shown["due_on"] or "",
                "" if shown["priority"] is None else shown["priority"],
                (shown["requester"] or {}).get("id", ""),
                (shown["requester"] or {}).get("name", ""),
                assignee.get("id", ""),
                assignee.get("name", ""),
                shown["created_at"],
                shown["decided_by"] or "",
                shown["decided_at"] or "",
                shown["decline_reason"] or "",
                shown["held_from"] or "",
                shown["done_at"] or "",
                shown["comment_count"],
            ]
        )
    return out.getvalue()


def wanted_filter(given: Any) -> Any:
    """The board's Unassigned column sends `assignee=none`; anything else is an id."""
    text = str(given or "").strip()
    if not text:
        return None
    return UNASSIGNED if text.lower() == UNASSIGNED else as_id(text)


def members_matching(guild: Any, query: str) -> list[int]:
    """`q` reaches the requester's NAME, which lives in the gateway cache and not in SQL."""
    if not query:
        return []
    lowered = query.lower()
    found: list[int] = []
    for member in list(getattr(guild, "members", ()) or ()):
        haystack = " ".join(
            str(part or "").lower()
            for part in (
                getattr(member, "name", None),
                getattr(member, "display_name", None),
                getattr(member, "global_name", None),
            )
        )
        if lowered in haystack:
            found.append(int(member.id))
        if len(found) >= NAME_MATCH_LIMIT:
            break
    return found


def wanted_assignee(guild: Any, given: Any) -> Any:
    """`...` leaves it alone, an empty one clears it, an id Discord does not know is a sentence."""
    if given is ...:
        return ...
    if given is None or given == "":
        return None
    number = as_id(given)
    if number is None or guild.get_member(number) is None:
        raise Refused(400, "no_such_member", BAD_ASSIGNEE.format(given=clamp(given, 40)))
    return number


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    reader = reader_dependency(bot)
    signed_in_member = member_dependency(bot)
    router = APIRouter(prefix="/api/requests", tags=["requests"])

    async def _shown(guild: Any, row: Any) -> dict[str, Any]:
        counts = await comment_counts(bot.db, [row["id"]])
        return request_row(guild, row, counts.get(int(row["id"]), 0))

    async def _rows(guild: Any, rows: Any) -> list[dict[str, Any]]:
        counts = await comment_counts(bot.db, [row["id"] for row in rows])
        return [request_row(guild, row, counts.get(int(row["id"]), 0)) for row in rows]

    async def _wanted(guild: Any, request_id: int) -> Any:
        row = await get_request(bot.db, request_id)
        if row is None or row["guild_id"] != guild.id:
            raise Refused(404, "no_such_request", NO_SUCH_REQUEST.format(request_id=request_id))
        return row

    def _may_file(guild: Any, who: dict[str, Any]) -> None:
        """Nothing approves itself any more — a staff filing arrives open like anybody's."""
        if not requests_are_on(bot.store, guild.id):
            raise Refused(409, "requests_off", REQUESTS_OFF)
        if not everyone_may_file(bot.store, guild.id) and not who["staff"]:
            raise Refused(403, "staff_only", STAFF_ONLY_FILES)

    async def _decide(
        request: Request, request_id: int, status: str, reason: Any
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await _wanted(guild, request_id)
        said, fresh = await apply_decision(
            bot,
            guild,
            request_id,
            status,
            actor_for(bot, who, guild),
            reason=reason,
            via=VIA_WEBSITE,
        )
        if fresh is None:
            raise Refused(409, "not_decided", said)
        return {"request": await _shown(guild, fresh), "message": said}

    @router.get("", dependencies=[Depends(reader)])
    async def requests_index(
        status: str = "", assignee: str = "", q: str = "", page: int = 1
    ) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        try:
            statuses = wanted_statuses(status)
        except RequestError as exc:
            raise refused(exc) from exc
        wanted_by = wanted_filter(assignee)
        query = clamp(q, SEARCH_LIMIT)
        named = members_matching(guild, query)
        total = await count_requests(
            bot.db,
            guild.id,
            statuses=statuses,
            assignee_id=wanted_by,
            query=query,
            named=named,
        )
        pages = max(1, -(-total // API_PAGE))
        at = max(1, min(int(page or 1), pages))
        rows = await list_requests(
            bot.db,
            guild.id,
            statuses=statuses,
            assignee_id=wanted_by,
            query=query,
            named=named,
            limit=API_PAGE,
            offset=(at - 1) * API_PAGE,
        )
        return {
            "requests": await _rows(guild, rows),
            "total": total,
            "page": at,
            "pages": pages,
            "per_page": API_PAGE,
            "open": await count_requests(bot.db, guild.id, statuses=(OPEN,)),
        }

    @router.post("")
    async def request_file(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        """The site's one non-staff write: any signed-in member of the server may file."""
        who = await signed_in_member(request)
        guild = require_guild(bot)
        require_db(bot)
        _may_file(guild, who)
        try:
            what, why, due_on = checked_fields(
                payload.get("what"), payload.get("why"), payload.get("due_on")
            )
        except RequestError as exc:
            raise refused(exc) from exc
        user_id = int(who["id"])
        request_id = await create_request(
            bot.db,
            guild.id,
            user_id,
            what=what,
            why=why,
            due_on=due_on,
            status=OPEN,
        )
        await note(
            bot,
            guild,
            "web.request.filed",
            who,
            target=user_id,
            details={"request_id": request_id},
        )
        row = await get_request(bot.db, request_id)
        await notify(bot, guild, row, actor_for(bot, who, guild))
        fresh = await get_request(bot.db, request_id)
        return {
            "request": await _shown(guild, fresh),
            "message": FILED_SAID.format(request_id=request_id),
        }

    @router.get("/mine")
    async def requests_mine(request: Request, page: int = 1) -> dict[str, Any]:
        """A member's own rows in every state — the only read that is not staff-gated."""
        who = await signed_in_member(request)
        guild = require_guild(bot)
        require_db(bot)
        user_id = int(who["id"])
        total = await count_requests(bot.db, guild.id, user_id=user_id)
        pages = max(1, -(-total // API_PAGE))
        at = max(1, min(int(page or 1), pages))
        rows = await list_requests(
            bot.db,
            guild.id,
            user_id=user_id,
            limit=API_PAGE,
            offset=(at - 1) * API_PAGE,
        )
        return {
            "requests": await _rows(guild, rows),
            "total": total,
            "page": at,
            "pages": pages,
            "per_page": API_PAGE,
        }

    @router.get("/export.csv", dependencies=[Depends(reader)])
    async def requests_export(status: str = "", q: str = "") -> PlainTextResponse:
        guild = require_guild(bot)
        require_db(bot)
        try:
            statuses = wanted_statuses(status)
        except RequestError as exc:
            raise refused(exc) from exc
        query = clamp(q, SEARCH_LIMIT)
        rows = await list_requests(
            bot.db,
            guild.id,
            statuses=statuses,
            query=query,
            named=members_matching(guild, query),
        )
        body = export_csv(
            guild, rows, await comment_counts(bot.db, [row["id"] for row in rows])
        )
        return PlainTextResponse(
            body,
            media_type=CSV_MEDIA_TYPE,
            headers={"Content-Disposition": 'attachment; filename="requests.csv"'},
        )

    @router.get("/{request_id}", dependencies=[Depends(reader)])
    async def request_one(request_id: int) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        row = await _wanted(guild, request_id)
        comments = await comments_for(bot.db, request_id)
        return {
            "request": request_row(guild, row, len(comments)),
            "comments": [comment_row(guild, one) for one in comments],
        }

    @router.post("/{request_id}/decline")
    async def request_decline(
        request: Request, request_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        reason = clamp(payload.get("reason"), REASON_LIMIT)
        if not reason:
            raise Refused(400, "no_reason", REASON_NEEDED[DECLINED])
        return await _decide(request, request_id, DECLINED, reason)

    @router.post("/{request_id}/hold")
    async def request_hold(
        request: Request, request_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        reason = clamp(payload.get("reason"), REASON_LIMIT)
        if not reason:
            raise Refused(400, "no_reason", REASON_NEEDED[HOLD])
        return await _decide(request, request_id, HOLD, reason)

    @router.post("/{request_id}/resume")
    async def request_resume(
        request: Request, request_id: int, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Back where it was held from; the button on a hold card and `/request resume`."""
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await _wanted(guild, request_id)
        said, fresh = await resume_request(
            bot, guild, request_id, actor_for(bot, who, guild), via=VIA_WEBSITE
        )
        if fresh is None:
            raise Refused(409, "not_on_hold", said)
        return {"request": await _shown(guild, fresh), "message": said}

    @router.post("/{request_id}/status")
    async def request_status(
        request: Request, request_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Status, assignee, priority and notes in one save; the status moves last."""
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await _wanted(guild, request_id)
        try:
            status = wanted_status(payload["status"]) if payload.get("status") else None
            priority = (
                wanted_priority(payload.get("priority"))
                if "priority" in payload
                else ...
            )
        except RequestError as exc:
            raise refused(exc) from exc
        assignee = wanted_assignee(
            guild, payload["assignee_id"] if "assignee_id" in payload else ...
        )
        notes = clamp(payload["notes"], NOTES_LIMIT) or None if "notes" in payload else ...
        reason = clamp(payload.get("reason"), REASON_LIMIT)
        if status in NEEDS_A_REASON and not reason:
            raise Refused(400, "no_reason", REASON_NEEDED[status])
        changed = await set_fields(
            bot.db, request_id, assignee_id=assignee, priority=priority, notes=notes
        )
        if status is None and not changed:
            raise Refused(400, "nothing_to_save", NOTHING_TO_SAVE)
        said = SAVED_SAID.format(request_id=request_id)
        if changed:
            await note(
                bot,
                guild,
                "web.request.updated",
                who,
                details={"request_id": request_id, "changed": sorted(changed)},
            )
        if status is not None:
            moved, fresh = await apply_decision(
                bot,
                guild,
                request_id,
                status,
                actor_for(bot, who, guild),
                reason=reason or None,
                via=VIA_WEBSITE,
            )
            if fresh is None:
                raise Refused(409, "not_decided", moved)
            said = moved
        fresh = await _wanted(guild, request_id)
        return {"request": await _shown(guild, fresh), "message": said}

    @router.post("/{request_id}/withdraw")
    async def request_withdraw(request: Request, request_id: int) -> dict[str, Any]:
        """The person who filed it takes it back; staff decline instead."""
        who = await signed_in_member(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await _wanted(guild, request_id)
        if row["user_id"] != int(who["id"]):
            raise Refused(403, "not_yours", NOT_YOURS.format(request_id=request_id))
        if row["status"] not in WITHDRAWABLE:
            raise Refused(
                409,
                "too_late_to_withdraw",
                TOO_LATE_TO_WITHDRAW.format(
                    request_id=request_id,
                    status=STATUS_WORDS.get(row["status"], row["status"]),
                ),
            )
        await set_status(bot.db, request_id, WITHDRAWN)
        await note(
            bot,
            guild,
            "web.request.withdrawn",
            who,
            target=row["user_id"],
            details={"request_id": request_id},
        )
        fresh = await _wanted(guild, request_id)
        return {
            "request": await _shown(guild, fresh),
            "message": WITHDRAWN_SAID.format(request_id=request_id),
        }

    @router.post("/{request_id}/comments")
    async def request_comment(
        request: Request, request_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await _wanted(guild, request_id)
        text = clamp(payload.get("text"), COMMENT_LIMIT)
        if not text:
            raise Refused(400, "no_text", COMMENT_NEEDS_TEXT)
        comment_id = await add_comment(bot.db, request_id, int(who["id"]), text)
        await note(
            bot,
            guild,
            "web.request.comment",
            who,
            details={"request_id": request_id, "comment_id": comment_id},
        )
        return {
            "comment": comment_row(guild, await get_comment(bot.db, comment_id)),
            "message": COMMENT_SAID.format(request_id=request_id),
        }

    return router


__all__ = ["build_router", "comment_row", "export_csv", "person", "request_row"]
