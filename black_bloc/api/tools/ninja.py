from __future__ import annotations

from dataclasses import replace
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import ninja as rules
from ... import ninja_store as store
from ...logkinds import VIA_WEBSITE
from ..auth import Refused, staff_dependency
from ..names import resolve_one, site_words
from ..writes import actor_for, require_db, require_guild, wanted_id, writer_dependency


def mark_row(guild: Any, row: Any) -> dict[str, Any]:
    by = row["made_by"]
    return {
        "id": int(row["id"]),
        "user_id": str(row["user_id"]),
        "user_name": resolve_one(guild, row["user_id"])["display_name"],
        "channel_id": str(row["channel_id"]),
        "channel_name": resolve_one(guild, row["channel_id"])["display_name"],
        "emoji": row["emoji"],
        "posts_left": row["posts_left"],
        "until": row["until"],
        "made_by": str(by) if by else None,
        "made_by_name": resolve_one(guild, by)["display_name"] if by else None,
        "made_at": row["made_at"],
        "ended_at": row["ended_at"],
        "ended_because": row["ended_because"],
    }


async def index(bot: Any, guild: Any) -> dict[str, Any]:
    posts, minutes = rules.default_limits(bot.store, guild.id)
    channel = rules.default_channel(bot.store, guild.id)
    return {
        "mode": rules.mode_of(bot.store, guild.id),
        "emoji": rules.emoji_of(bot.store, guild.id),
        "default_channel_id": str(channel) if channel else None,
        "default_posts": posts,
        "default_minutes": minutes,
        "active": [mark_row(guild, row) for row in await store.active(bot.db, guild.id)],
        "ended": [mark_row(guild, row) for row in await store.recent_ended(bot.db, guild.id)],
    }


def answered(guild: Any, outcome: Any) -> dict[str, Any]:
    outcome = replace(outcome, message=site_words(guild, outcome.message))
    if not outcome.ok:
        raise Refused(outcome.status or 409, outcome.code or "refused", outcome.message)
    return {"ok": True, "message": outcome.message, "value": outcome.value}


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/ninja", tags=["ninja"], dependencies=[Depends(staff_dependency(bot))]
    )

    def ready() -> Any:
        guild = require_guild(bot)
        require_db(bot)
        return guild

    @router.get("")
    async def ninja_index() -> dict[str, Any]:
        return await index(bot, ready())

    @router.post("")
    async def ninja_mark(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        given = payload.get("user_ids")
        outcome = await rules.mark(
            bot,
            guild,
            actor_for(bot, who, guild),
            given if isinstance(given, list) else [],
            payload.get("channel_id"),
            payload.get("posts"),
            payload.get("minutes"),
            via=VIA_WEBSITE,
        )
        return answered(guild, outcome)

    @router.delete("/{mark_id}")
    async def ninja_end(request: Request, mark_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = ready()
        outcome = await rules.end(
            bot, guild, actor_for(bot, who, guild), wanted_id(mark_id), via=VIA_WEBSITE
        )
        return answered(guild, outcome)

    return router
