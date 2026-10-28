from __future__ import annotations

from dataclasses import replace
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import bluesky_moves as moves
from ...logkinds import VIA_WEBSITE
from ..auth import Refused, staff_dependency
from ..names import site_words
from ..writes import actor_for, require_db, require_guild, writer_dependency


def answered(guild: Any, outcome: Any) -> dict[str, Any]:
    if not outcome.ok:
        raise Refused(
            outcome.status or 409, outcome.code or "refused", site_words(guild, outcome.message)
        )
    done = replace(outcome, message=site_words(guild, outcome.message))
    return {"ok": True, "message": done.message, "value": done.value}


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/bluesky", tags=["bluesky"], dependencies=[Depends(staff_dependency(bot))]
    )

    def ready() -> Any:
        guild = require_guild(bot)
        require_db(bot)
        return guild

    @router.get("")
    async def bluesky_status() -> dict[str, Any]:
        return await moves.status(bot, ready())

    @router.post("/read")
    async def bluesky_read(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await moves.read_now(bot, guild, actor_for(bot, who, guild), via=VIA_WEBSITE)
        return answered(guild, outcome)

    @router.post("/rehearse")
    async def bluesky_rehearse(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await moves.rehearse(bot, guild, actor_for(bot, who, guild), via=VIA_WEBSITE)
        return answered(guild, outcome)

    @router.post("/post-latest")
    async def bluesky_post_latest(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await moves.post_latest(
            bot,
            guild,
            actor_for(bot, who, guild),
            payload.get("count"),
            payload.get("where"),
            via=VIA_WEBSITE,
        )
        return answered(guild, outcome)

    return router
