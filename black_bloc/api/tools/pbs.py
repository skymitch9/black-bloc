from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import pb_moves, pb_store
from ...logkinds import VIA_WEBSITE
from ...pb_feed import mode_of
from ...settings_store import PB_FEED_INTERVAL
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import actor_for, require_db, require_guild, wanted_id, writer_dependency

log = logging.getLogger(__name__)

POSTS_DEFAULT = 20
PEOPLE_LIMIT = 500
PERSON_FIELDS = {
    "matched_from": "twitch_login",
    "state": "state",
    "state_by": "state_by",
    "source": "source",
    "runner": "src_name",
    "runner_id": "src_user_id",
    "runner_link": "src_weblink",
    "reason": "reason",
    "matched_at": "matched_at",
    "checked_at": "checked_at",
    "baseline_at": "baseline_at",
    "looked_at": "looked_at",
    "look_error": "look_error",
    "last_pb_at": "last_pb_at",
}


def person_row(guild: Any, user_id: int, row: Any, login: str | None) -> dict[str, Any]:
    found = {
        "user_id": str(user_id),
        "name": resolve_one(guild, user_id)["display_name"],
        "here": guild.get_member(int(user_id)) is not None,
        "twitch_login": login,
    }
    for name, column in PERSON_FIELDS.items():
        found[name] = row[column] if row is not None else None
    return found


def post_row(guild: Any, row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": str(row["user_id"]),
        "name": resolve_one(guild, row["user_id"])["display_name"],
        "run_id": row["run_id"],
        "runner": row["src_name"],
        "game": row["game"],
        "category": row["category"],
        "seconds": row["seconds"],
        "place": row["place"],
        "link": row["weblink"],
        "verified_at": row["verified_at"],
        "outcome": row["outcome"],
        "reason": row["reason"],
        "channel_id": str(row["channel_id"]) if row["channel_id"] else None,
        "aimed_at": str(row["aimed_at"]) if row["aimed_at"] else None,
        "message_id": str(row["message_id"]) if row["message_id"] else None,
        "at": row["at"],
    }


def look_row(looked: Any) -> dict[str, Any] | None:
    if looked is None:
        return None
    return {
        "at": looked["last_at"],
        "ok_at": looked["last_ok_at"],
        "outcome": looked["outcome"],
        "reason": looked["reason"],
        "asks_again_at": looked["backoff_until"],
    }


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/pbs", tags=["pbs"], dependencies=[Depends(staff_dependency(bot))]
    )

    async def one(guild: Any, user_id: int) -> dict[str, Any]:
        row = await pb_store.match(bot.db, guild.id, user_id)
        login = (await pb_store.links(bot.db)).get(int(user_id))
        return person_row(guild, user_id, row, login)

    async def answered(guild: Any, user_id: int, outcome: Any) -> dict[str, Any]:
        if not outcome.ok:
            raise Refused(outcome.status or 400, outcome.code, outcome.message)
        return {"person": await one(guild, user_id), "message": outcome.message}

    @router.get("")
    async def pbs_index(posts: int = POSTS_DEFAULT) -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        rows = {int(row["user_id"]): row for row in await pb_store.matches(bot.db, guild.id)}
        links = await pb_store.links(bot.db)
        people = [
            person_row(guild, user_id, rows.get(user_id), links.get(user_id))
            for user_id in sorted(set(rows) | set(links))
            if user_id in rows or guild.get_member(user_id) is not None
        ][:PEOPLE_LIMIT]
        wanted = max(1, min(int(posts), pb_store.POSTS_LIMIT))
        listed = await pb_store.posts(bot.db, guild.id, wanted)
        return {
            "mode": mode_of(bot.store, guild.id),
            "interval_minutes": bot.store.get(guild.id, PB_FEED_INTERVAL),
            "last_look": look_row(await pb_store.looks(bot.db, guild.id)),
            "people": sorted(people, key=lambda person: str(person["name"]).casefold()),
            "posts": [post_row(guild, row) for row in listed],
        }

    @router.put("/{user_id}")
    async def pbs_set(request: Request, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(user_id)
        outcome = await pb_moves.set_by_hand(
            bot, guild, wanted, payload.get("runner"), actor_for(bot, who, guild), via=VIA_WEBSITE
        )
        return await answered(guild, wanted, outcome)

    async def moved(request: Request, user_id: str, move: Any) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(user_id)
        outcome = await move(bot, guild, wanted, actor_for(bot, who, guild), via=VIA_WEBSITE)
        return await answered(guild, wanted, outcome)

    @router.delete("/{user_id}")
    async def pbs_unmatch(request: Request, user_id: str) -> dict[str, Any]:
        return await moved(request, user_id, pb_moves.unmatch)

    @router.post("/{user_id}/block")
    async def pbs_block(request: Request, user_id: str) -> dict[str, Any]:
        return await moved(request, user_id, pb_moves.block)

    @router.post("/{user_id}/unblock")
    async def pbs_unblock(request: Request, user_id: str) -> dict[str, Any]:
        return await moved(request, user_id, pb_moves.unblock)

    @router.post("/{user_id}/optin")
    async def pbs_optin(request: Request, user_id: str) -> dict[str, Any]:
        return await moved(request, user_id, pb_moves.clear_opt_out)

    @router.post("/{user_id}/look")
    async def pbs_look(request: Request, user_id: str) -> dict[str, Any]:
        return await moved(request, user_id, pb_moves.look_now)

    return router
