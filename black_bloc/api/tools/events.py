from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...events import (
    APPROVED,
    CANCEL_NOTE_LIMIT,
    DENIED,
    PENDING,
    STATUSES,
    apply_decision,
    cancel_for,
    cell,
    checked_fields,
    checked_where,
    clamp,
    delete_room,
    describe_duration,
    duration_minutes,
    ends_at,
    events_by_status,
    get_event,
    make_forum,
    move_room_to_forum,
    moved_words,
    read_where,
    rename_channel,
    review_kind,
    update_event,
    where_said,
)
from ...logkinds import VIA_WEBSITE
from ...settings_store import DEFAULT_TIMEZONE_KEY
from ...timezones import get_timezone, is_known
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import actor_for, note, require_db, require_guild, writer_dependency

log = logging.getLogger(__name__)

REASON_LIMIT = 400

NO_SUCH_EVENT = (
    "Black Bloc has no event **#{event_id}** any more, so nothing was done. The events page lists "
    "the ones it has."
)
UNKNOWN_STATUS = (
    "**{given}** is not a state an event can be in, so nothing was listed. They are {known}."
)
DENY_NEEDS_A_REASON = (
    "A denied event needs one line the requester is sent, so nothing was done. Say why and send "
    "it again."
)
NOT_CANCELLABLE = (
    "Event **#{event_id}** is **{status}** already, so there was nothing to cancel."
)
NOT_EDITABLE = (
    "Event **#{event_id}** is **{status}**, so its details cannot be changed — only an event "
    "still waiting for a decision or already approved can be edited. Ask the person who wants it "
    "to propose it again."
)
EDITABLE = (PENDING, APPROVED)
ANNOUNCEMENT_STALE = (
    "The public announcement still says what it said before; Black Bloc does not rewrite one it "
    "has already posted. Say so in the channel, or cancel and let them propose it again."
)
SCHEDULED_STALE = (
    "The Discord scheduled event still has the old details — nothing here edits one that was "
    "already made."
)
EDITED = "Saved, and the review channel's name follows the title."
NO_ROOM = (
    "Event **#{event_id}** has no room of its own any more, so there was nothing to remove."
)
NO_POST = (
    "Event **#{event_id}** has no post of its own any more, so there was nothing to remove."
)
NO_PLACE: dict[str, str] = {"room": NO_ROOM, "post": NO_POST}


def event_row(guild: Any, row: Any) -> dict[str, Any]:
    where = read_where(row)
    channel = guild.get_channel(where.channel_id) if where.channel_id else None
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "location": row["location"],
        "where_kind": where.kind,
        "where_channel_id": str(where.channel_id) if where.channel_id else None,
        "where_label": where_said(where, channel),
        "starts_at": row["starts_at"],
        "ends_at": row["ends_at"],
        "minutes": duration_minutes(row),
        "duration": describe_duration(duration_minutes(row)),
        "status": row["status"],
        "moved_to": cell(row, "moved_to"),
        "moved_word": moved_words(cell(row, "moved_to")),
        "editable": row["status"] in EDITABLE,
        "announced": bool(row["announce_message_id"]),
        "scheduled": bool(row["scheduled_event_id"]),
        "requester_id": str(row["requester_id"]),
        "requester_name": resolve_one(guild, row["requester_id"])["display_name"],
        "decided_by_id": str(row["decided_by"]) if row["decided_by"] else None,
        "decided_by_name": (
            resolve_one(guild, row["decided_by"])["display_name"] if row["decided_by"] else None
        ),
        "decided_at": row["decided_at"],
        "deny_reason": row["deny_reason"],
        "review_channel_id": (
            str(row["review_channel_id"]) if row["review_channel_id"] else None
        ),
        "review_kind": review_kind(row),
        "created_at": row["created_at"],
    }


async def wanted_event(bot: Any, guild: Any, event_id: int) -> Any:
    row = await get_event(bot.db, event_id)
    if row is None or row["guild_id"] != guild.id:
        raise Refused(404, "no_such_event", NO_SUCH_EVENT.format(event_id=event_id))
    return row


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/events", tags=["events"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.post("/forum")
    async def event_forum_make(request: Request) -> dict[str, Any]:
        """**Make the forum**, from the website — the same one path `/event` presses."""
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        outcome = await make_forum(bot, guild, actor_for(bot, who, guild), via=VIA_WEBSITE)
        if not outcome.ok:
            raise Refused(outcome.status or 400, outcome.code, outcome.message)
        return {
            "made": True,
            "channel_id": str(outcome.value),
            "message": outcome.message,
        }

    @router.get("")
    async def events_index(status: str = "") -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        wanted = [part for part in str(status or "").split(",") if part]
        for part in wanted:
            if part not in STATUSES:
                raise Refused(
                    400,
                    "unknown_status",
                    UNKNOWN_STATUS.format(given=part, known=", ".join(STATUSES)),
                )
        rows = await events_by_status(bot.db, guild.id, wanted or STATUSES)
        return [event_row(guild, row) for row in rows]

    async def _decide(request: Request, event_id: int, status: str, reason: Any) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        await wanted_event(bot, guild, event_id)
        said, fresh = await apply_decision(
            bot, guild, event_id, status, actor_for(bot, who, guild), reason, via=VIA_WEBSITE
        )
        if fresh is None:
            raise Refused(409, "already_decided", said)
        return {"event": event_row(guild, fresh), "message": said}

    @router.get("/{event_id}")
    async def event_detail(event_id: int) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        return {"event": event_row(guild, await wanted_event(bot, guild, event_id))}

    @router.put("/{event_id}")
    async def event_edit(
        request: Request, event_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_event(bot, guild, event_id)
        if row["status"] not in EDITABLE:
            raise Refused(
                409,
                "not_editable",
                NOT_EDITABLE.format(event_id=event_id, status=row["status"]),
            )
        given = str(payload.get("tz") or "")
        tz_name = (
            given
            if is_known(given)
            else await get_timezone(
                bot.db, int(who["id"]), bot.store.get(guild.id, DEFAULT_TIMEZONE_KEY)
            )
        )
        where, refused = checked_where(
            guild,
            payload.get("where_kind"),
            payload.get("where_channel_id"),
            payload.get("location"),
        )
        if where is None:
            raise Refused(400, "where_refused", refused)
        fields, why = checked_fields(
            title=payload.get("title"),
            description=payload.get("description"),
            where=where,
            start=payload.get("start"),
            duration=payload.get("duration"),
            tz_name=tz_name,
            now=datetime.now(UTC),
        )
        if fields is None:
            raise Refused(400, "event_refused", why)
        await update_event(
            bot.db,
            event_id,
            title=fields.title,
            description=fields.description,
            where=fields.where,
            starts_at=fields.starts,
            finishes_at=ends_at(fields.starts, fields.minutes),
        )
        fresh = await wanted_event(bot, guild, event_id)
        requester = guild.get_member(fresh["requester_id"])
        await rename_channel(
            bot,
            guild,
            fresh,
            fresh["status"],
            getattr(requester, "display_name", str(fresh["requester_id"])),
        )
        await note(
            bot,
            guild,
            "web.event.edited",
            who,
            target=fresh["requester_id"],
            details={"event_id": event_id, "title": fields.title, "tz": tz_name},
        )
        notes = []
        if fresh["announce_message_id"]:
            notes.append(ANNOUNCEMENT_STALE)
        if fresh["scheduled_event_id"]:
            notes.append(SCHEDULED_STALE)
        return {"event": event_row(guild, fresh), "message": EDITED, "notes": notes}

    @router.post("/{event_id}/approve")
    async def event_approve(request: Request, event_id: int) -> dict[str, Any]:
        return await _decide(request, event_id, APPROVED, None)

    @router.post("/{event_id}/deny")
    async def event_deny(
        request: Request, event_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        reason = clamp(payload.get("reason"), REASON_LIMIT)
        if not reason:
            raise Refused(400, "no_reason", DENY_NEEDS_A_REASON)
        return await _decide(request, event_id, DENIED, reason)

    @router.post("/{event_id}/cancel")
    async def event_cancel(
        request: Request, event_id: int, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_event(bot, guild, event_id)
        reason = clamp((payload or {}).get("reason"), REASON_LIMIT) or "staff"
        _, fresh = await cancel_for(
            bot, guild, row, int(who["id"]), reason=reason, via=VIA_WEBSITE
        )
        if fresh is None:
            raise Refused(
                409,
                "not_cancellable",
                NOT_CANCELLABLE.format(event_id=event_id, status=row["status"]),
            )
        return {"event": event_row(guild, fresh), "message": "Cancelled."}

    @router.post("/{event_id}/room/delete")
    async def event_room_delete(
        request: Request, event_id: int, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_event(bot, guild, event_id)
        if not row["review_channel_id"]:
            raise Refused(
                409, "no_room", NO_PLACE[review_kind(row)].format(event_id=event_id)
            )
        said, gone = await delete_room(
            bot,
            guild,
            row,
            by=actor_for(bot, who, guild),
            note=clamp((payload or {}).get("note"), CANCEL_NOTE_LIMIT) or None,
            via=VIA_WEBSITE,
        )
        if not gone:
            raise Refused(409, "room_kept", said)
        fresh = await wanted_event(bot, guild, event_id)
        return {"event": event_row(guild, fresh), "message": said}

    @router.post("/{event_id}/forum")
    async def event_move_to_forum(request: Request, event_id: int) -> dict[str, Any]:
        """**Move to the forum**, from the website — the same one path the room's card presses."""
        from ...cogs.community.events import handoff_review_view, room_notice_view

        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_event(bot, guild, event_id)
        outcome = await move_room_to_forum(
            bot,
            guild,
            actor_for(bot, who, guild),
            row,
            review_view=handoff_review_view(bot, guild),
            room_view=room_notice_view,
            via=VIA_WEBSITE,
        )
        if not outcome.ok:
            raise Refused(outcome.status or 400, outcome.code, outcome.message)
        fresh = await wanted_event(bot, guild, event_id)
        return {"event": event_row(guild, fresh), "message": outcome.message}

    return router
