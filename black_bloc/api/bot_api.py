from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from .. import restart
from .auth import Refused, staff_dependency
from .writes import note, require_guild, writer_dependency

log = logging.getLogger(__name__)

NOT_A_LEAD_CODE = "not_a_lead"
CANNOT_RESTART_CODE = "cannot_restart"


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/bot", tags=["bot"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.post("/restart")
    async def restart_bot(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        if not restart.manages_guild(guild.get_member(int(who["id"]))):
            raise Refused(403, NOT_A_LEAD_CODE, restart.NOT_A_LEAD)
        if not restart.can_restart(bot):
            raise Refused(503, CANNOT_RESTART_CODE, restart.CANNOT_RESTART)
        log.warning("restart: asked for by %s from the website", who["id"])
        await note(
            bot,
            guild,
            "web.core.restart_requested",
            who,
            details={"seconds": restart.DOWN_SECONDS},
        )
        restart.schedule(bot)
        return {
            "message": restart.restarting_said(),
            "seconds": restart.DOWN_SECONDS,
        }

    return router
