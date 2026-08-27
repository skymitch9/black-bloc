from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...cogs.community.tempvoice import connected_ids, make_creator_channel, rows_for_guild
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import actor_for, note, require_db, require_guild, writer_dependency

log = logging.getLogger(__name__)

SETUP_REFUSED = {
    "already": "already_a_lobby",
    "no_test_channel": "no_test_channel",
    "refused": "discord_refused",
}


def channel_row(bot: Any, guild: Any, row: Any) -> dict[str, Any]:
    live = guild.get_channel(row["channel_id"])
    return {
        "channel_id": str(row["channel_id"]),
        "name": getattr(live, "name", None),
        "gone": live is None,
        "owner_id": str(row["owner_id"]),
        "owner_name": resolve_one(guild, row["owner_id"])["display_name"],
        "creator_id": str(row["creator_id"]),
        "created_at": row["created_at"],
        "connected": len(connected_ids(live)) if live is not None else 0,
    }


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/tempvoice", tags=["tempvoice"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("/channels")
    async def tempvoice_channels() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [
            channel_row(bot, guild, row) for row in await rows_for_guild(bot.db, guild.id)
        ]

    @router.post("/setup")
    async def tempvoice_setup(
        request: Request, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        name = str((payload or {}).get("name") or "").strip() or None
        outcome, said = await make_creator_channel(bot, guild, actor_for(bot, who, guild), name)
        if outcome != "created":
            raise Refused(409, SETUP_REFUSED.get(outcome, "setup_refused"), said)
        await note(bot, guild, "web.tempvoice.setup", who, details={"name": name})
        return {"created": True, "message": said}

    return router
