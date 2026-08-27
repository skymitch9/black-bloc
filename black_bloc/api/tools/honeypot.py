from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...cogs.moderation.honeypot import ban_hit, make_trap_channel, recent_hits
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import actor_for, note, require_db, require_guild, writer_dependency

log = logging.getLogger(__name__)

HITS_DEFAULT_LIMIT = 50
HITS_MAX_LIMIT = 200

BAN_REFUSED = {
    "no_such_hit": (404, "no_such_hit"),
    "already": (409, "already_banned"),
    "test_mode": (409, "test_mode"),
    "refused": (502, "discord_refused"),
}
SETUP_REFUSED = {
    "already": "already_a_trap",
    "no_test_channel": "no_test_channel",
    "refused": "discord_refused",
}


def hit_row(guild: Any, row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": str(row["user_id"]),
        "user_name": resolve_one(guild, row["user_id"])["display_name"],
        "channel_id": str(row["channel_id"]),
        "channel_name": resolve_one(guild, row["channel_id"])["display_name"],
        "message_id": str(row["message_id"]) if row["message_id"] else None,
        "content": row["content"],
        "at": row["at"],
        "mode": row["mode"],
        "action": row["action"],
    }


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/honeypot", tags=["honeypot"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("/hits")
    async def honeypot_hits(limit: int = HITS_DEFAULT_LIMIT) -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        wanted = max(1, min(int(limit), HITS_MAX_LIMIT))
        return [hit_row(guild, row) for row in await recent_hits(bot.db, guild.id, wanted)]

    @router.post("/hits/{hit_id}/ban")
    async def honeypot_ban(request: Request, hit_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        outcome, said = await ban_hit(
            bot, guild, hit_id, actor_for(bot, who, guild), "web"
        )
        if outcome != "banned":
            status, error = BAN_REFUSED.get(outcome, (409, "ban_refused"))
            raise Refused(status, error, said)
        await note(bot, guild, "web.honeypot.ban", who, details={"hit_id": hit_id})
        return {"banned": True, "hit_id": hit_id, "message": said}

    @router.post("/setup")
    async def honeypot_setup(
        request: Request, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        name = str((payload or {}).get("name") or "").strip() or None
        outcome, said = await make_trap_channel(bot, guild, actor_for(bot, who, guild), name)
        if outcome != "created":
            raise Refused(409, SETUP_REFUSED.get(outcome, "setup_refused"), said)
        await note(bot, guild, "web.honeypot.setup", who, details={"name": name})
        return {"created": True, "message": said}

    return router
