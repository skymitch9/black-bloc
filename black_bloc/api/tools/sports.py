from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request

from ... import sports_names
from ...logkinds import VIA_WEBSITE
from ..auth import Refused, staff_dependency
from ..writes import (
    actor_for,
    member_read_dependency,
    note,
    require_db,
    require_guild,
    writer_dependency,
)

REFRESH_GRACE_SECONDS = 8.0
ALREADY_RUNNING = (
    "A names refresh is already running, so another was not started. The lists below update "
    "when it ends."
)
STARTED = "The names refresh is running; the lists below update when it ends."
FINISHED = "Names refreshed: {done} of {lists} lists answered."


def build_router(bot: Any) -> APIRouter:
    reader = member_read_dependency(bot)
    staff = staff_dependency(bot)
    writer = writer_dependency(bot)
    router = APIRouter(tags=["sports"])

    async def shown() -> dict[str, Any]:
        found = await sports_names.status(bot)
        return found | {"checked_at": datetime.now(UTC).isoformat(timespec="seconds")}

    @router.get("/api/ref/sports")
    async def ref_sports(
        request: Request, kind: str = "team", league: str = "", q: str = "", limit: int = 25
    ) -> list[dict[str, Any]]:
        await reader(request)
        require_db(bot)
        return await sports_names.search(bot.db, kind, league, q, limit)

    @router.get("/api/sports")
    async def sports_status(request: Request) -> dict[str, Any]:
        await staff(request)
        require_db(bot)
        return await shown()

    @router.post("/api/sports/refresh")
    async def sports_refresh(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        task = sports_names.start_refresh(
            bot,
            [guild],
            actor=actor_for(bot, who, guild),
            via=VIA_WEBSITE,
            fetch=getattr(bot, "sports_fetch", None),
        )
        if task is None:
            raise Refused(409, "refresh_running", ALREADY_RUNNING)
        await note(bot, guild, "web.sports.refresh", who)
        await asyncio.wait({task}, timeout=REFRESH_GRACE_SECONDS)
        message = STARTED
        if task.done() and not task.cancelled() and task.exception() is None:
            result = task.result()
            lists = len(result["refreshed"]) + len(result["failed"])
            message = FINISHED.format(done=len(result["refreshed"]), lists=lists)
        return await shown() | {"message": message}

    return router
