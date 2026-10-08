from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import sticky as rules
from ...logkinds import VIA_WEBSITE
from ...sticky_posts import desk_of
from ..auth import Refused, staff_dependency
from ..names import resolve_one, site_words
from ..writes import actor_for, require_db, require_guild, wanted_id, writer_dependency

log = logging.getLogger(__name__)


def sticky_row(bot: Any, guild: Any, row: Any) -> dict[str, Any]:
    channel = guild.get_channel(int(row["channel_id"]))
    posted_in = row["posted_channel_id"]
    return {
        "channel_id": str(row["channel_id"]),
        "channel_name": getattr(channel, "name", None),
        "gone": channel is None,
        "text": row["text"],
        "paused": bool(row["paused"]),
        "trouble": site_words(guild, row["trouble"]),
        "state": rules.state_of(row, rules.mode_of(bot.store, guild.id)),
        "message_id": str(row["message_id"]) if row["message_id"] else None,
        "posted_channel_id": str(posted_in) if posted_in else None,
        "posted_at": row["posted_at"],
        "reposts": int(row["reposts"] or 0),
        "updated_by": str(row["updated_by"]) if row["updated_by"] else None,
        "updated_by_name": (
            resolve_one(guild, row["updated_by"])["display_name"] if row["updated_by"] else None
        ),
        "updated_at": row["updated_at"],
    }


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/sticky", tags=["sticky"], dependencies=[Depends(staff_dependency(bot))]
    )

    def said(guild: Any, outcome: Any) -> str:
        if not outcome.ok:
            raise Refused(outcome.status or 400, outcome.code, site_words(guild, outcome.message))
        return site_words(guild, outcome.message)

    def answered(guild: Any, outcome: Any) -> dict[str, Any]:
        message = said(guild, outcome)
        return {"sticky": sticky_row(bot, guild, outcome.value), "message": message}

    @router.get("")
    async def sticky_list() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [
            sticky_row(bot, guild, row) for row in await rules.rows_for_guild(bot.db, guild.id)
        ]

    @router.put("/{channel_id}")
    async def sticky_save(
        request: Request, channel_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        outcome = await desk_of(bot).save(
            guild,
            wanted_id(channel_id),
            payload.get("text"),
            actor_for(bot, who, guild),
            via=VIA_WEBSITE,
        )
        return answered(guild, outcome)

    @router.post("/{channel_id}/pause")
    async def sticky_pause(request: Request, channel_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        outcome = await desk_of(bot).pause(
            guild, wanted_id(channel_id), actor_for(bot, who, guild), via=VIA_WEBSITE
        )
        return answered(guild, outcome)

    @router.post("/{channel_id}/resume")
    async def sticky_resume(request: Request, channel_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        outcome = await desk_of(bot).resume(
            guild, wanted_id(channel_id), actor_for(bot, who, guild), via=VIA_WEBSITE
        )
        return answered(guild, outcome)

    @router.delete("/{channel_id}")
    async def sticky_remove(request: Request, channel_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(channel_id)
        outcome = await desk_of(bot).remove(
            guild, wanted, actor_for(bot, who, guild), via=VIA_WEBSITE
        )
        return {"removed": True, "channel_id": str(wanted), "message": said(guild, outcome)}

    return router
