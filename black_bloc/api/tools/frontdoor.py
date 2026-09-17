from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...cogs.community.frontdoor import post_door, take_door_down, where_the_door_is
from ...frontdoor import DOOR_NO_CHANNEL
from ...logkinds import VIA_WEBSITE
from ..auth import Refused, staff_dependency
from ..writes import (
    actor_for,
    require_db,
    require_guild,
    wanted_id,
    writer_dependency,
)

log = logging.getLogger(__name__)


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/frontdoor",
        tags=["frontdoor"],
        dependencies=[Depends(staff_dependency(bot))],
    )

    @router.post("/panel")
    async def frontdoor_post(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        channel_id = wanted_id(payload.get("channel_id")) if payload.get("channel_id") else 0
        target = guild.get_channel(channel_id) if channel_id else None
        if target is None:
            raise Refused(400, "no_such_channel", DOOR_NO_CHANNEL)
        outcome = await post_door(
            bot, guild, actor_for(bot, who, guild), target, via=VIA_WEBSITE
        )
        if not outcome.ok:
            raise Refused(outcome.status or 400, outcome.code, outcome.message)
        return {
            "posted": True,
            "channel_id": str(target.id),
            "message_id": str(outcome.value),
            "message": outcome.message,
        }

    @router.delete("/panel")
    async def frontdoor_down(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        channel, message_id = where_the_door_is(bot, guild)
        outcome = await take_door_down(
            bot, guild, actor_for(bot, who, guild), via=VIA_WEBSITE
        )
        return {
            "taken_down": outcome.ok,
            "channel_id": str(channel.id) if channel is not None else None,
            "message_id": str(message_id) if message_id else None,
            "message": outcome.message,
        }

    return router
