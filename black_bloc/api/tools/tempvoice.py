from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...cogs.community.tempvoice import (
    CHANNEL_GONE,
    LOBBY_FORGOTTEN,
    NOT_A_LOBBY,
    OUTSIDE_TEST_ROOM,
    Doer,
    connected_ids,
    do_limit,
    do_privacy,
    do_rename,
    forget_creator,
    get_row,
    make_creator_channel,
    may_act_in,
    parse_limit,
    privacy_of,
    rows_for_guild,
)
from ...logkinds import VIA_WEBSITE
from ..auth import Refused, staff_dependency
from ..names import resolve_one
from ..writes import (
    actor_for,
    require_db,
    require_guild,
    wanted_id,
    writer_dependency,
)

log = logging.getLogger(__name__)

SETUP_DONE = ("created", "repaired", "adopted")
SETUP_REFUSED = {
    "no_test_channel": "no_test_channel",
    "refused": "discord_refused",
    "repair_refused": "discord_refused",
    "outside_test_category": "outside_test_category",
}

NO_SUCH_ROOM = (
    "Black Bloc is not keeping track of a temporary voice channel with that id, so nothing was "
    "changed. The Open now list on this page is the ones it knows about."
)
NO_NAME = (
    "A channel needs a name, so nothing was changed. Type what it should be called and save "
    "again."
)
BAD_LIMIT = (
    "**{given}** is not a number of people Black Bloc can use, so nothing was changed. Pick a "
    "whole number from 0 to 99 — 0 means no limit."
)


def channel_row(bot: Any, guild: Any, row: Any) -> dict[str, Any]:
    live = guild.get_channel(row["channel_id"])
    locked, hidden = privacy_of(live) if live is not None else (False, False)
    return {
        "channel_id": str(row["channel_id"]),
        "name": getattr(live, "name", None),
        "gone": live is None,
        "owner_id": str(row["owner_id"]),
        "owner_name": resolve_one(guild, row["owner_id"])["display_name"],
        "creator_id": str(row["creator_id"]),
        "created_at": row["created_at"],
        "connected": len(connected_ids(live)) if live is not None else 0,
        "user_limit": int(getattr(live, "user_limit", 0) or 0),
        "locked": locked,
        "hidden": hidden,
    }


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/tempvoice", tags=["tempvoice"], dependencies=[Depends(staff_dependency(bot))]
    )

    def doer(guild: Any, who: dict[str, Any]) -> Doer:
        return Doer(bot, guild, actor_for(bot, who, guild), VIA_WEBSITE)

    async def room(guild: Any, given: Any) -> tuple[Any, Any]:
        row = await get_row(bot.db, wanted_id(given))
        if row is None or int(row["guild_id"]) != int(guild.id):
            raise Refused(404, "no_such_room", NO_SUCH_ROOM)
        channel = guild.get_channel(int(row["channel_id"]))
        if channel is None:
            raise Refused(404, "channel_gone", CHANNEL_GONE)
        if not may_act_in(bot, channel):
            raise Refused(409, "test_mode", OUTSIDE_TEST_ROOM.format(name=channel.name))
        return row, channel

    async def answered(guild: Any, channel: Any, said: Any) -> dict[str, Any]:
        if not said.ok:
            raise Refused(409, "discord_refused", str(said))
        return {
            "room": channel_row(bot, guild, await get_row(bot.db, channel.id)),
            "message": str(said),
        }

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
        outcome, said = await make_creator_channel(
            bot, guild, actor_for(bot, who, guild), name, via=VIA_WEBSITE
        )
        if outcome not in SETUP_DONE:
            raise Refused(409, SETUP_REFUSED.get(outcome, "setup_refused"), said)
        return {"created": True, "outcome": outcome, "message": said}

    @router.post("/forget")
    async def tempvoice_forget(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(payload.get("channel_id"))
        actor = actor_for(bot, who, guild)
        if not await forget_creator(bot, guild, wanted, actor, via=VIA_WEBSITE):
            raise Refused(404, "not_a_lobby", NOT_A_LOBBY.format(channel_id=wanted))
        return {
            "forgotten": True,
            "channel_id": str(wanted),
            "message": LOBBY_FORGOTTEN.format(channel_id=wanted),
        }

    @router.post("/rooms/{channel_id}/rename")
    async def tempvoice_room_rename(
        request: Request, channel_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row, channel = await room(guild, channel_id)
        wanted = str(payload.get("name") or "").strip()
        if not wanted:
            raise Refused(400, "no_name", NO_NAME)
        said = await do_rename(doer(guild, who), channel, row, wanted)
        return await answered(guild, channel, said)

    @router.post("/rooms/{channel_id}/limit")
    async def tempvoice_room_limit(
        request: Request, channel_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row, channel = await room(guild, channel_id)
        given = payload.get("limit")
        value = parse_limit(str(given if given is not None else ""))
        if value is None:
            raise Refused(400, "bad_limit", BAD_LIMIT.format(given=str(given)[:40]))
        said = await do_limit(doer(guild, who), channel, row, value)
        return await answered(guild, channel, said)

    @router.post("/rooms/{channel_id}/lock")
    async def tempvoice_room_lock(
        request: Request, channel_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row, channel = await room(guild, channel_id)
        want = bool(payload.get("locked", True))
        said = await do_privacy(doer(guild, who), channel, row, "connect", want)
        return await answered(guild, channel, said)

    @router.post("/rooms/{channel_id}/hide")
    async def tempvoice_room_hide(
        request: Request, channel_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row, channel = await room(guild, channel_id)
        want = bool(payload.get("hidden", True))
        said = await do_privacy(doer(guild, who), channel, row, "view_channel", want)
        return await answered(guild, channel, said)

    return router
