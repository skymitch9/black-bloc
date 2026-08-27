from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...cogs.community.events import (
    apply_decision,
    cancel_event,
    duration_minutes,
    events_by_status,
    get_event,
)
from ...events import APPROVED, DENIED, STATUSES, clamp
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


def event_row(guild: Any, row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "location": row["location"],
        "starts_at": row["starts_at"],
        "ends_at": row["ends_at"],
        "minutes": duration_minutes(row),
        "status": row["status"],
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
            bot, guild, event_id, status, actor_for(bot, who, guild), reason
        )
        if fresh is None:
            raise Refused(409, "already_decided", said)
        await note(
            bot,
            guild,
            f"web.event.{status}",
            who,
            target=fresh["requester_id"],
            reason=reason,
            details={"event_id": event_id},
        )
        return {"event": event_row(guild, fresh), "message": said}

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
        if not await cancel_event(bot, guild, row, reason, by=int(who["id"])):
            raise Refused(
                409,
                "not_cancellable",
                NOT_CANCELLABLE.format(event_id=event_id, status=row["status"]),
            )
        fresh = await wanted_event(bot, guild, event_id)
        await note(
            bot,
            guild,
            "web.event.cancel",
            who,
            target=fresh["requester_id"],
            reason=reason,
            details={"event_id": event_id},
        )
        return {"event": event_row(guild, fresh), "message": "Cancelled."}

    return router
