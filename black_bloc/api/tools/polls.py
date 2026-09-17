from __future__ import annotations

import csv
import io
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from ...cogs.community.polls import (
    POLLS_OFF,
    cancel_poll,
    close_poll,
    delete_recurrence,
    get_poll,
    get_recurrence,
    options_of,
    panel_counts,
    pause_recurrence,
    poll_plan,
    polls_are_on,
    polls_by_status,
    post_poll,
    recurrences,
    results_of,
    resume_recurrence,
    save_recurrence,
    send_review_card,
    set_status,
    store_poll,
    votes_of,
    where_it_went,
)
from ...cogs.community.polls import (
    apply_decision as decide_poll,
)
from ...logkinds import VIA_WEBSITE
from ...polls import (
    CANCELLED,
    CLOSED,
    DATE,
    DENIED,
    LIVE,
    OPEN,
    PANEL,
    PENDING_REVIEW,
    RECUR_NOT_A_DATE,
    RECURRING,
    STATUSES,
    cadence_token,
    cadence_trouble,
    clamp,
    counts_from_options,
    describe_cadence,
    in_shadow,
    next_occurrence,
    winners,
)
from ...timezones import DEFAULT_TZ
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import (
    actor_for,
    guard_of,
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
NO_CHANNEL_PICKED = (
    "Black Bloc has nowhere to put this poll, so nothing was posted. Pick a channel on the form, "
    "or set a default one in the Settings section below."
)
COULD_NOT_POST = (
    "Discord would not take the poll, so nothing went up and the draft is marked cancelled — the "
    "log says exactly what came back (`{reason}`). Tell a Lead, then start it again."
)
CREATED_POSTED = "**{question}** is up in <#{channel_id}>."
CREATED_HELD = (
    "**{question}** is in — a Lead has to approve it before it posts, and the person who asked is "
    "DM'd either way."
)
CREATED_NO_CARD = (
    "**{question}** is in, but Black Bloc could not post the review card — the log says why, and "
    "a Lead can still decide it from the Pending review section here."
)
NO_REVIEW_CHANNEL = (
    "Staff review is on but Black Bloc has nowhere to send a poll for it, so nothing was saved. "
    "Point `staff_channel_id` at the staff channel, or turn `poll_review_mode` off."
)
RECUR_NOT_A_RECURRENCE = (
    "Black Bloc has no repeating poll **#{poll_id}**, so nothing was done. It may have been "
    "deleted already."
)
RECUR_PAUSED_SAID = "**{question}** is paused. Nothing opens until it is started again."
RECUR_RESUMED_SAID = "**{question}** is running again."
RECUR_DELETED_SAID = "**{question}** will not run again. Polls it already opened are untouched."
RECUR_UNREADABLE = (
    "Black Bloc cannot work out when **{question}** would next run, so it was left paused. Delete "
    "it and set it up again."
)
RECUR_NOT_WORKED_OUT = (
    "Black Bloc could not work out when that would next come round, so nothing was saved. Check "
    "the day, the time of day and the timezone, then send it again."
)
RECUR_CREATED_SAID = (
    "**{question}** will run {cadence}. Nothing is posted yet — the Repeating section above says "
    "when the first one opens, and Pause stops it at any time."
)


def _id(value: Any) -> str | None:
    return str(value) if value is not None else None


def poll_row(
    guild: Any, row: Any, options: Any, stored: Any = None, counts: Any = None
) -> dict[str, Any]:
    counts = counts_from_options(options) if counts is None else list(counts)
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
        "schedule_id": _id(row["schedule_id"]),
    }


def recurrence_row(guild: Any, row: Any, options: Any) -> dict[str, Any]:
    """A template is not a poll, so it gets a shape of its own rather than a poll with holes."""
    return {
        "id": row["id"],
        "question": row["question"],
        "kind": row["kind"],
        "surface": row["surface"],
        "hours": int(row["hours"]),
        "anonymous": bool(row["anonymous"]),
        "results": row["results"],
        "creator_id": str(row["creator_id"]),
        "creator_name": resolve_one(guild, row["creator_id"])["display_name"],
        "channel_id": _id(row["channel_id"]),
        "cadence": row["recurrence"],
        "cadence_said": describe_cadence(row["recurrence"], row["recur_at"], row["recur_tz"]),
        "at": row["recur_at"],
        "tz": row["recur_tz"],
        "next_at": row["recur_next_at"],
        "paused": row["recur_next_at"] is None,
        "options": [
            {"position": int(item["position"]), "label": str(item["label"]), "votes": 0}
            for item in options
        ],
        "created_at": row["created_at"],
    }


def wanted_options(payload: Any) -> Any:
    """The form sends a list; the slash command sends `A | B`. Both mean the same thing."""
    given = payload.get("options")
    if isinstance(given, list):
        return " | ".join(str(one) for one in given)
    return given


def wanted_int(payload: Any, key: str) -> int | None:
    given = payload.get(key)
    if given is None or given == "":
        return None
    try:
        return int(given)
    except (TypeError, ValueError):
        return None


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
    """`end_poll` is not behind the HTTP patch, so the route asks the guard itself — about
    the channel the poll's message is IN, which for a rehearsal is the shadow home."""
    guard = guard_of(bot)
    where = where_it_went(bot, row)
    if guard is None or not where:
        return
    if not guard.allows_channel(where):
        refuse_guarded(guard.refusal_message())


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/polls", tags=["polls"], dependencies=[Depends(staff_dependency(bot))]
    )

    async def _shown(guild: Any, row: Any) -> dict[str, Any]:
        """An open panel's votes are ours, so its numbers come from the rows, not from `final`."""
        live = None
        if row["surface"] == PANEL and row["status"] == OPEN:
            live = (await panel_counts(bot.db, row["id"]))[0]
        return poll_row(
            guild,
            row,
            await options_of(bot.db, row["id"]),
            await results_of(bot.db, row["id"]),
            live,
        )

    def _refuse_outside_the_test_channel_id(guild: Any, channel_id: Any) -> None:
        """In shadow the poll is accepted and rehearsed, so a real channel is not refused."""
        guard = guard_of(bot)
        if in_shadow(bot.store, guild.id):
            return
        if guard is not None and channel_id and not guard.allows_channel(int(channel_id)):
            refuse_guarded(guard.refusal_message())

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
            "notes": [],
        }

    def _asked_for(guild: Any, payload: Any) -> dict[str, Any]:
        """The body both create routes read: the plan, and where the poll is to go."""
        plan, refusal = poll_plan(
            bot.store,
            guild.id,
            question=payload.get("question"),
            kind=payload.get("kind"),
            options=wanted_options(payload),
            hours=wanted_int(payload, "hours"),
            anonymous=bool(payload.get("anonymous")),
            results=payload.get("results") or LIVE,
            start=payload.get("start"),
            slots=wanted_int(payload, "slots"),
            step=wanted_int(payload, "step"),
            step_unit=payload.get("step_unit"),
        )
        if plan is None:
            raise Refused(400, "poll_refused", refusal)
        channel_id = payload.get("channel_id") or bot.store.get(guild.id, "poll_channel_id")
        if not channel_id:
            raise Refused(400, "no_channel", NO_CHANNEL_PICKED)
        _refuse_outside_the_test_channel_id(guild, channel_id)
        return {
            "plan": plan,
            "channel_id": int(channel_id),
            "ping_role_id": (
                int(payload["ping_role_id"])
                if payload.get("ping_role_id")
                else bot.store.get(guild.id, "poll_ping_role_id")
            ),
            "auto_thread": (
                bool(payload["auto_thread"])
                if payload.get("auto_thread") is not None
                else bool(bot.store.get(guild.id, "poll_auto_thread"))
            ),
        }

    @router.post("")
    async def poll_create(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        if not polls_are_on(bot.store, guild.id):
            raise Refused(409, "polls_off", POLLS_OFF)
        asked = _asked_for(guild, payload)
        plan, channel_id = asked["plan"], asked["channel_id"]
        row, reviewing = await store_poll(
            bot,
            guild,
            int(who["id"]),
            plan,
            channel_id=channel_id,
            ping_role_id=asked["ping_role_id"],
            auto_thread=asked["auto_thread"],
            via=VIA_WEBSITE,
        )
        said = await _open_or_hold(guild, row, reviewing, channel_id)
        fresh = await get_poll(bot.db, row["id"])
        return {
            "poll": await _shown(guild, fresh),
            "message": said,
            "note": plan["note"],
        }

    async def _open_or_hold(guild: Any, row: Any, reviewing: bool, channel_id: int) -> str:
        if reviewing:
            target, card = await send_review_card(bot, guild, row)
            if target is None:
                await set_status(bot.db, row["id"], CANCELLED, closed=True)
                raise Refused(409, "no_review_channel", NO_REVIEW_CHANNEL)
            said = CREATED_HELD if card is not None else CREATED_NO_CARD
            return said.format(question=clamp(row["question"], 80))
        message, why_not = await post_poll(bot, guild, row)
        if message is None:
            await set_status(bot.db, row["id"], CANCELLED, closed=True)
            raise Refused(409, "not_posted", COULD_NOT_POST.format(reason=why_not))
        return CREATED_POSTED.format(
            question=clamp(row["question"], 80), channel_id=channel_id
        )

    @router.get("/requests")
    async def poll_requests() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        rows = await polls_by_status(bot.db, guild.id, (PENDING_REVIEW,))
        return [await _shown(guild, row) for row in rows]

    @router.get("/recurrences")
    async def poll_recurrences() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [
            recurrence_row(guild, row, await options_of(bot.db, row["id"]))
            for row in await recurrences(bot.db, guild.id)
        ]

    def _wanted_cadence(payload: Any) -> tuple[str, str, str]:
        """Proved BEFORE any row is written, so a cadence nobody can read leaves no poll behind."""
        if str(payload.get("kind") or "") == DATE:
            raise Refused(400, "not_a_recurrence", RECUR_NOT_A_DATE)
        at_local = str(payload.get("at") or "").strip()
        tz_name = str(payload.get("tz") or DEFAULT_TZ).strip()
        trouble = cadence_trouble(payload.get("cadence"), payload.get("day"), at_local, tz_name)
        if trouble is not None:
            raise Refused(400, "not_a_recurrence", trouble)
        token = str(cadence_token(payload.get("cadence"), payload.get("day")))
        if next_occurrence(token, at_local, tz_name) is None:
            raise Refused(400, "not_a_recurrence", RECUR_NOT_WORKED_OUT)
        return (token, at_local, tz_name)

    @router.post("/recurrences")
    async def poll_recurrence_create(
        request: Request, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        if not polls_are_on(bot.store, guild.id):
            raise Refused(409, "polls_off", POLLS_OFF)
        token, at_local, tz_name = _wanted_cadence(payload)
        asked = _asked_for(guild, payload)
        row, _ = await store_poll(
            bot,
            guild,
            int(who["id"]),
            asked["plan"],
            channel_id=asked["channel_id"],
            ping_role_id=asked["ping_role_id"],
            auto_thread=asked["auto_thread"],
            status=RECURRING,
            via=VIA_WEBSITE,
        )
        _, fresh = await save_recurrence(
            bot,
            guild,
            row,
            token,
            at_local,
            tz_name,
            actor_for(bot, who, guild),
            via=VIA_WEBSITE,
        )
        if fresh is None:
            await set_status(bot.db, row["id"], CANCELLED, closed=True)
            raise Refused(
                409,
                "unreadable_cadence",
                RECUR_UNREADABLE.format(question=clamp(row["question"], 80)),
            )
        return {
            "recurrence": recurrence_row(guild, fresh, await options_of(bot.db, row["id"])),
            "message": RECUR_CREATED_SAID.format(
                question=clamp(row["question"], 80),
                cadence=describe_cadence(token, at_local, tz_name),
            ),
        }

    async def _wanted_recurrence(guild: Any, poll_id: int) -> Any:
        row = await get_recurrence(bot.db, guild.id, poll_id)
        if row is None:
            raise Refused(
                404, "no_such_recurrence", RECUR_NOT_A_RECURRENCE.format(poll_id=poll_id)
            )
        return row

    @router.post("/recurrences/{poll_id}/pause")
    async def poll_recurrence_pause(
        request: Request, poll_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await _wanted_recurrence(guild, poll_id)
        wanted = payload.get("paused")
        pausing = True if wanted is None else bool(wanted)
        move = pause_recurrence if pausing else resume_recurrence
        _, settled = await move(bot, guild, row, actor_for(bot, who, guild), via=VIA_WEBSITE)
        if settled is None:
            raise Refused(
                409,
                "unreadable_cadence",
                RECUR_UNREADABLE.format(question=clamp(row["question"], 80)),
            )
        fresh = await get_recurrence(bot.db, guild.id, poll_id)
        said = RECUR_PAUSED_SAID if pausing else RECUR_RESUMED_SAID
        return {
            "recurrence": recurrence_row(guild, fresh, await options_of(bot.db, poll_id)),
            "message": said.format(question=clamp(row["question"], 80)),
        }

    @router.delete("/recurrences/{poll_id}")
    async def poll_recurrence_delete(request: Request, poll_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await _wanted_recurrence(guild, poll_id)
        await delete_recurrence(bot, guild, row, actor_for(bot, who, guild), via=VIA_WEBSITE)
        return {
            "recurrence_id": str(poll_id),
            "message": RECUR_DELETED_SAID.format(question=clamp(row["question"], 80)),
        }

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
            bot, guild, poll_id, status, actor_for(bot, who, guild), reason, via=VIA_WEBSITE
        )
        if fresh is None:
            raise Refused(409, "already_decided", said)
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
            bot, guild, row, reason="web", actor=actor_for(bot, who, guild), via=VIA_WEBSITE
        )
        if not closed:
            fresh = await wanted_poll(bot, guild, poll_id)
            raise Refused(
                409, "not_closeable", NOT_CLOSEABLE.format(poll_id=poll_id, status=fresh["status"])
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
        if not await cancel_poll(
            bot, guild, row, by=actor_for(bot, who, guild), via=VIA_WEBSITE
        ):
            raise Refused(
                409,
                "not_cancellable",
                NOT_CANCELLABLE.format(poll_id=poll_id, status=row["status"]),
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
