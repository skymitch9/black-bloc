from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...cogs.content.golive import all_links, all_optouts, recent_sessions, remove_link
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import note, require_db, require_guild, wanted_id, writer_dependency

log = logging.getLogger(__name__)

SESSIONS_DEFAULT_LIMIT = 50
SESSIONS_MAX_LIMIT = 200

NOT_LINKED = (
    "**{user_id}** has no Twitch account linked, so there was nothing to unlink. The links table "
    "shows who has one."
)


def with_name(guild: Any, user_id: Any) -> dict[str, Any]:
    return {
        "user_id": str(user_id),
        "user_name": resolve_one(guild, user_id)["display_name"],
    }


def link_row(guild: Any, row: Any) -> dict[str, Any]:
    return with_name(guild, row["user_id"]) | {
        "twitch_login": row["twitch_login"],
        "twitch_user_id": row["twitch_user_id"],
        "linked_at": row["linked_at"],
    }


def session_row(guild: Any, row: Any) -> dict[str, Any]:
    return with_name(guild, row["user_id"]) | {
        "id": row["id"],
        "source": row["source"],
        "url": row["url"],
        "game": row["game"],
        "title": row["title"],
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
        "mode": row["mode"],
        "announced_message_id": (
            str(row["announced_message_id"]) if row["announced_message_id"] else None
        ),
    }


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/golive", tags=["golive"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("/links")
    async def golive_links() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [link_row(guild, row) for row in await all_links(bot.db)]

    @router.delete("/links/{user_id}")
    async def golive_unlink(request: Request, user_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(user_id)
        if not await remove_link(bot.db, wanted):
            raise Refused(404, "not_linked", NOT_LINKED.format(user_id=wanted))
        await note(bot, guild, "web.golive.unlink", who, target=wanted)
        return {"unlinked": True, "user_id": str(wanted)}

    @router.get("/optouts")
    async def golive_optouts() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [
            with_name(guild, row["user_id"]) | {"at": row["at"]}
            for row in await all_optouts(bot.db)
        ]

    @router.get("/sessions")
    async def golive_sessions(limit: int = SESSIONS_DEFAULT_LIMIT) -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        wanted = max(1, min(int(limit), SESSIONS_MAX_LIMIT))
        return [
            session_row(guild, row) for row in await recent_sessions(bot.db, guild.id, wanted)
        ]

    return router
