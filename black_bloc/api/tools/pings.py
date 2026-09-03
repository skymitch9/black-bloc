from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import pings
from ...logkinds import VIA_WEBSITE
from ..auth import Refused, staff_dependency
from ..names import as_id, resolve_one
from ..writes import (
    require_db,
    require_guild,
    wanted_id,
    writer_dependency,
)

log = logging.getLogger(__name__)

NO_SUCH_MEMBER = (
    "**{member_id}** is not somebody Black Bloc can see in this server, so nothing was changed. "
    "Pick them from the list rather than typing an id."
)
NO_SUCH_ROLE = (
    "**{role_id}** is not a role in this server any more, so nothing was changed. Reload the page "
    "and pick the role again."
)


def streamer_row(guild: Any, row: Any) -> dict[str, Any]:
    """One line of the Pings table; `followers` is null — never 0 — when the role has gone."""
    role = guild.get_role(int(row["role_id"])) if guild is not None else None
    by = row["created_by"]
    return {
        "member_id": str(row["user_id"]),
        "member": resolve_one(guild, row["user_id"])["display_name"],
        "role_id": str(row["role_id"]),
        "role": role.name if role is not None else None,
        "followers": len(getattr(role, "members", ()) or ()) if role is not None else None,
        "created_at": row["created_at"],
        "created_by": str(by) if by is not None else None,
        "created_by_name": resolve_one(guild, by)["display_name"] if by is not None else None,
    }


def wanted_role(guild: Any, given: Any) -> Any:
    if given in (None, ""):
        return None
    role = guild.get_role(as_id(given)) if as_id(given) is not None else None
    if role is None:
        raise Refused(400, "no_such_role", NO_SUCH_ROLE.format(role_id=given))
    return role


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/pings", tags=["pings"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("/streamers")
    async def pings_streamers() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [
            streamer_row(guild, row) for row in await pings.all_fan_roles(bot.db, guild.id)
        ]

    @router.post("/streamers")
    async def pings_streamer_add(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        member_id = wanted_id(payload.get("member_id"))
        member = guild.get_member(member_id)
        if member is None:
            raise Refused(404, "no_such_member", NO_SUCH_MEMBER.format(member_id=member_id))
        outcome = await pings.ensure_fan_role(
            bot,
            guild,
            member,
            by=int(who["id"]),
            existing_role=wanted_role(guild, payload.get("role_id")),
            staff=True,
            via=VIA_WEBSITE,
        )
        if not outcome.ok:
            raise Refused(409, "not_created", outcome.message)
        row = await pings.get_fan_role(bot.db, guild.id, member_id)
        return streamer_row(guild, row) | {"message": outcome.message}

    @router.delete("/streamers/{member_id}")
    async def pings_streamer_remove(request: Request, member_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(member_id)
        outcome = await pings.remove_fan_role(
            bot, guild, wanted, by=int(who["id"]), via=VIA_WEBSITE
        )
        if not outcome.ok:
            raise Refused(404, "no_fan_role", outcome.message)
        return {
            "removed": True,
            "member_id": str(wanted),
            "role_id": str(outcome.role_id) if outcome.role_id else None,
            "message": outcome.message,
        }

    @router.post("/setup")
    async def pings_setup(
        request: Request, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        outcome = await pings.setup_events_role(
            bot,
            guild,
            by=int(who["id"]),
            role=wanted_role(guild, (payload or {}).get("role_id")),
            via=VIA_WEBSITE,
        )
        if not outcome.ok:
            raise Refused(409, "not_set_up", outcome.message)
        return {
            "role_id": str(outcome.role_id),
            "created": outcome.created,
            "menu": pings.NOTIFICATIONS_MENU,
            "message": outcome.message,
        }

    return router
