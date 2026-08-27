from __future__ import annotations

import csv
import io
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from ...cogs.community.polls import (
    apply_decision as decide_poll,
)
from ...cogs.community.polls import (
    cancel_poll,
    close_poll,
    get_poll,
    options_of,
    polls_by_status,
    results_of,
    votes_of,
)
from ...polls import (
    CLOSED,
    DENIED,
    OPEN,
    PENDING_REVIEW,
    STATUSES,
    clamp,
    counts_from_options,
    winners,
)
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import (
    actor_for,
    guard_of,
    note,
    refuse_guarded,
    require_db,
    require_guild,
    writer_dependency,
)

log = logging.getLogger(__name__)

REASON_LIMIT = 400
PER_PAGE = 25
PER_PAGE_MAX = 100
CSV_MEDIA_TYPE = "text/csv"

NO_SUCH_POLL = (
    "Black Bloc has no poll **#{poll_id}** any more, so nothing was done. The polls page lists "
    "the ones it has."
)
UNKNOWN_STATUS = (
    "**{given}** is not a state a poll can be in, so nothing was listed. They are {known}."
)
NOT_CLOSEABLE = "Poll **#{poll_id}** is **{status}** already, so there was nothing to close."
NOT_CANCELLABLE = "Poll **#{poll_id}** is **{status}** already, so there was nothing to cancel."
NOT_WAITING = (
    "Poll **#{poll_id}** is **{status}**, so it is not waiting on a decision any more. Somebody "
    "may have got there first."
)
DENY_NEEDS_A_REASON = (
    "A denied poll needs one line the person who asked is sent, so nothing was done. Say why and "
    "send it again."
)
CLOSED_NO_RESULT = (
    "Poll #{poll_id} is marked closed, but Black Bloc could not read the final count back from "
    "Discord — the log says why, and the numbers on the message itself are the real ones."
)
CLOSED_SAID = "Poll #{poll_id} is closed and the result is posted."
CANCELLED_SAID = "Poll #{poll_id} is cancelled. No result was published."
VOTES_ARE_ANONYMOUS = (
    "This poll was run without a voter list, so there is nothing per-person to export. The "
    "totals below are everything Black Bloc has."
)
VOTES_WERE_DROPPED = (
    "This poll has been archived and its per-voter rows were dropped, which is what "
    "`poll_archive_drop_votes` asks for. The totals below are kept forever."
)
NO_CREATE_YET = (
    "Starting a poll from the dashboard arrives with the next update — the create form and the "
    "panel surface ship together. Use `/poll create` in Discord until then."
)


def _id(value: Any) -> str | None:
    return str(value) if value is not None else None


def poll_row(guild: Any, row: Any, options: Any, stored: Any = None) -> dict[str, Any]:
    counts = counts_from_options(options)
    top = winners(counts)
    return {
        "id": row["id"],
        "question": row["question"],
        "kind": row["kind"],
        "surface": row["surface"],
        "status": row["status"],
        "results": row["results"],
        "multi": bool(row["multi"]),
        "anonymous": bool(row["anonymous"]),
        "auto_thread": bool(row["auto_thread"]),
        "hours": int(row["hours"]),
        "creator_id": str(row["creator_id"]),
        "creator_name": resolve_one(guild, row["creator_id"])["display_name"],
        "channel_id": _id(row["channel_id"]),
        "message_id": _id(row["message_id"]),
        "thread_id": _id(row["thread_id"]),
        "ping_role_id": _id(row["ping_role_id"]),
        "opens_at": row["opens_at"],
        "closes_at": row["closes_at"],
        "reminded_at": row["reminded_at"],
        "closed_at": row["closed_at"],
        "archived_at": row["archived_at"],
        "total_votes": row["total_votes"],
        "decided_by_id": _id(row["decided_by"]),
        "decided_by_name": (
            resolve_one(guild, row["decided_by"])["display_name"] if row["decided_by"] else None
        ),
        "decided_at": row["decided_at"],
        "deny_reason": row["deny_reason"],
        "created_at": row["created_at"],
        "options": counts,
        "winner_position": int(top[0]["position"]) if len(top) == 1 else None,
        "votes_dropped": int(stored["votes_dropped"]) if stored is not None else 0,
    }


def vote_row(guild: Any, row: Any) -> dict[str, Any]:
    return {
        "user_id": str(row["user_id"]),
        "user_name": resolve_one(guild, row["user_id"])["display_name"],
        "position": row["position"],
        "label": row["label"],
        "at": row["at"],
    }


def wanted_page(given: Any) -> int:
    text = str(given or "1").strip()
    return max(int(text), 1) if text.isdigit() else 1


def wanted_per_page(given: Any) -> int:
    text = str(given or PER_PAGE).strip()
    return min(max(int(text), 1), PER_PAGE_MAX) if text.isdigit() else PER_PAGE


def wanted_statuses(given: Any) -> tuple[str, ...]:
    found = tuple(part for part in str(given or "").split(",") if part)
    for part in found:
        if part not in STATUSES:
            raise Refused(
                400, "unknown_status", UNKNOWN_STATUS.format(given=part, known=", ".join(STATUSES))
            )
    return found or STATUSES


def export_csv(guild: Any, row: Any, options: Any, votes: Any, stored: Any) -> str:
    """Totals always; one row per voter only when the poll kept them."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["poll_id", "question", "status", "closed_at", "total_votes"])
    writer.writerow(
        [row["id"], row["question"], row["status"], row["closed_at"] or "", row["total_votes"] or 0]
    )
    writer.writerow([])
    writer.writerow(["position", "option", "votes"])
    for count in counts_from_options(options):
        writer.writerow([count["position"], count["label"], count["votes"]])
    writer.writerow([])
    if row["anonymous"]:
        writer.writerow(["note", VOTES_ARE_ANONYMOUS])
        return out.getvalue()
    if not votes and stored is not None and int(stored["votes_dropped"] or 0):
        writer.writerow(["note", VOTES_WERE_DROPPED])
        return out.getvalue()
    writer.writerow(["user_id", "user_name", "position", "option", "at"])
    for vote in votes:
        writer.writerow(
            [
                str(vote["user_id"]),
                resolve_one(guild, vote["user_id"])["display_name"],
                vote["position"],
                vote["label"],
                vote["at"],
            ]
        )
    return out.getvalue()


async def wanted_poll(bot: Any, guild: Any, poll_id: int) -> Any:
    row = await get_poll(bot.db, poll_id)
    if row is None or row["guild_id"] != guild.id:
        raise Refused(404, "no_such_poll", NO_SUCH_POLL.format(poll_id=poll_id))
    return row


def refuse_outside_the_test_channel(bot: Any, row: Any) -> None:
    """`end_poll` is not behind the HTTP patch, so the route asks the guard itself."""
    guard = guard_of(bot)
    if guard is None or not row["channel_id"]:
        return
    if not guard.allows_channel(row["channel_id"]):
        refuse_guarded(guard.refusal_message())


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/polls", tags=["polls"], dependencies=[Depends(staff_dependency(bot))]
    )

    async def _shown(guild: Any, row: Any) -> dict[str, Any]:
        return poll_row(
            guild, row, await options_of(bot.db, row["id"]), await results_of(bot.db, row["id"])
        )

    @router.get("")
    async def polls_index(
        status: str = "", page: str = "1", per_page: str = str(PER_PAGE)
    ) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        rows = await polls_by_status(bot.db, guild.id, wanted_statuses(status))
        at, size = wanted_page(page), wanted_per_page(per_page)
        window = rows[(at - 1) * size : at * size]
        return {
            "polls": [await _shown(guild, row) for row in window],
            "total": len(rows),
            "shown": len(window),
            "page": at,
            "per_page": size,
            "notes": [NO_CREATE_YET],
        }

    @router.get("/requests")
    async def poll_requests() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        rows = await polls_by_status(bot.db, guild.id, (PENDING_REVIEW,))
        return [await _shown(guild, row) for row in rows]

    async def _decide(
        request: Request, poll_id: int, status: str, reason: Any
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_poll(bot, guild, poll_id)
        if row["status"] != PENDING_REVIEW:
            raise Refused(
                409, "not_waiting", NOT_WAITING.format(poll_id=poll_id, status=row["status"])
            )
        if status == OPEN:
            refuse_outside_the_test_channel(bot, row)
        said, fresh = await decide_poll(
            bot, guild, poll_id, status, actor_for(bot, who, guild), reason
        )
        if fresh is None:
            raise Refused(409, "already_decided", said)
        await note(
            bot,
            guild,
            "web.poll.approved" if status == OPEN else "web.poll.denied",
            who,
            target=fresh["creator_id"],
            reason=reason,
            details={"poll_id": poll_id},
        )
        return {"poll": await _shown(guild, fresh), "message": said}

    @router.post("/requests/{poll_id}/approve")
    async def poll_approve(request: Request, poll_id: int) -> dict[str, Any]:
        return await _decide(request, poll_id, OPEN, None)

    @router.post("/requests/{poll_id}/deny")
    async def poll_deny(
        request: Request, poll_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        reason = clamp(payload.get("reason"), REASON_LIMIT)
        if not reason:
            raise Refused(400, "no_reason", DENY_NEEDS_A_REASON)
        return await _decide(request, poll_id, DENIED, reason)

    @router.get("/{poll_id}")
    async def poll_one(poll_id: int) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_poll(bot, guild, poll_id)
        found = await _shown(guild, row)
        votes = [] if row["anonymous"] else await votes_of(bot.db, poll_id)
        return {"poll": found, "votes": [vote_row(guild, vote) for vote in votes]}

    @router.post("/{poll_id}/end")
    async def poll_end(request: Request, poll_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_poll(bot, guild, poll_id)
        if row["status"] != OPEN:
            raise Refused(
                409, "not_closeable", NOT_CLOSEABLE.format(poll_id=poll_id, status=row["status"])
            )
        refuse_outside_the_test_channel(bot, row)
        closed, written = await close_poll(
            bot, guild, row, reason="web", actor=actor_for(bot, who, guild)
        )
        if not closed:
            fresh = await wanted_poll(bot, guild, poll_id)
            raise Refused(
                409, "not_closeable", NOT_CLOSEABLE.format(poll_id=poll_id, status=fresh["status"])
            )
        await note(
            bot,
            guild,
            "web.poll.end",
            who,
            target=row["creator_id"],
            details={"poll_id": poll_id},
        )
        fresh = await wanted_poll(bot, guild, poll_id)
        said = CLOSED_SAID if written else CLOSED_NO_RESULT
        return {"poll": await _shown(guild, fresh), "message": said.format(poll_id=poll_id)}

    @router.post("/{poll_id}/cancel")
    async def poll_cancel(request: Request, poll_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_poll(bot, guild, poll_id)
        refuse_outside_the_test_channel(bot, row)
        if not await cancel_poll(bot, guild, row, by=actor_for(bot, who, guild)):
            raise Refused(
                409,
                "not_cancellable",
                NOT_CANCELLABLE.format(poll_id=poll_id, status=row["status"]),
            )
        await note(
            bot,
            guild,
            "web.poll.cancel",
            who,
            target=row["creator_id"],
            details={"poll_id": poll_id},
        )
        fresh = await wanted_poll(bot, guild, poll_id)
        return {
            "poll": await _shown(guild, fresh),
            "message": CANCELLED_SAID.format(poll_id=poll_id),
        }

    @router.get("/{poll_id}/export.csv")
    async def poll_export(poll_id: int) -> PlainTextResponse:
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_poll(bot, guild, poll_id)
        votes = [] if row["anonymous"] else await votes_of(bot.db, poll_id)
        body = export_csv(
            guild,
            row,
            await options_of(bot.db, poll_id),
            votes,
            await results_of(bot.db, poll_id),
        )
        return PlainTextResponse(
            body,
            media_type=CSV_MEDIA_TYPE,
            headers={"Content-Disposition": f'attachment; filename="poll-{poll_id}.csv"'},
        )

    return router


__all__ = ["CLOSED", "build_router", "export_csv", "poll_row", "vote_row"]
