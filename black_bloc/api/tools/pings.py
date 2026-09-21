from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import pings
from ... import pings_onboarding as onboarding
from ... import spotlight as spot
from ...cogs.content.spotlight import channel_by_id, channels_for
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


MEMBER_KIND = "member"
SPOTLIGHT_KIND = "spotlight"


def streamer_row(guild: Any, row: Any) -> dict[str, Any]:
    """One line of the Pings table; `followers` is null — never 0 — when the role has gone.

    A channel's row has no `member_id` at all, which is how the page tells the kinds apart.
    """
    role = guild.get_role(int(row["role_id"])) if guild is not None else None
    by = row["created_by"]
    channel = pings.is_spotlight(row)
    if channel:
        return {
            "kind": SPOTLIGHT_KIND,
            "member_id": None,
            "member": pings.spotlight_name(row),
            "spotlight_id": pings.spotlight_of(row),
            "spotlight_login": pings.row_value(row, "spotlight_login"),
            "role_id": str(row["role_id"]),
            "role": role.name if role is not None else None,
            "followers": len(getattr(role, "members", ()) or ()) if role is not None else None,
            "created_at": row["created_at"],
            "created_by": str(by) if by is not None else None,
            "created_by_name": resolve_one(guild, by)["display_name"] if by is not None else None,
        }
    return {
        "kind": MEMBER_KIND,
        "member_id": str(row["user_id"]),
        "member": resolve_one(guild, row["user_id"])["display_name"],
        "spotlight_id": None,
        "spotlight_login": None,
        "role_id": str(row["role_id"]),
        "role": role.name if role is not None else None,
        "followers": len(getattr(role, "members", ()) or ()) if role is not None else None,
        "created_at": row["created_at"],
        "created_by": str(by) if by is not None else None,
        "created_by_name": resolve_one(guild, by)["display_name"] if by is not None else None,
    }


def listing_row(guild: Any, row: Any, held: Any) -> dict[str, Any]:
    """One line of the streamer list; `followers` is null — never 0 — when there is no role."""
    role = (
        guild.get_role(int(held["role_id"])) if held is not None and guild is not None else None
    )
    hidden_by = pings.row_value(row, "hidden_by")
    return {
        "kind": MEMBER_KIND,
        "spotlight_id": None,
        "member_id": str(row["user_id"]),
        "member": resolve_one(guild, row["user_id"])["display_name"],
        "listed": bool(row["listed"]),
        "hidden_by": str(hidden_by) if hidden_by is not None else None,
        "hidden_by_name": (
            resolve_one(guild, hidden_by)["display_name"] if hidden_by is not None else None
        ),
        "hidden_at": pings.row_value(row, "hidden_at"),
        "first_live_at": row["first_live_at"],
        "last_live_at": row["last_live_at"],
        "live_count": int(row["live_count"]),
        "platform": pings.row_value(row, "platform"),
        "login": pings.row_value(row, "login"),
        "role_id": str(held["role_id"]) if held is not None else None,
        "role": role.name if role is not None else None,
        "followers": len(getattr(role, "members", ()) or ()) if role is not None else None,
    }


def spotlight_listing_row(guild: Any, row: Any, held: Any) -> dict[str, Any]:
    """A spotlighted channel on the same list: no member, never hidden, its role beside it."""
    role = (
        guild.get_role(int(held["role_id"])) if held is not None and guild is not None else None
    )
    return {
        "kind": SPOTLIGHT_KIND,
        "spotlight_id": int(row["id"]),
        "member_id": None,
        "member": str(row["display_name"] or row["twitch_login"]),
        "listed": True,
        "hidden_by": None,
        "hidden_by_name": None,
        "hidden_at": None,
        "first_live_at": row["added_at"],
        "last_live_at": None,
        "live_count": 0,
        "platform": spot.PLATFORM,
        "login": row["twitch_login"],
        "role_id": str(held["role_id"]) if held is not None else None,
        "role": role.name if role is not None else None,
        "followers": len(getattr(role, "members", ()) or ()) if role is not None else None,
    }


def onboarding_card(guild: Any, result: Any, *, managed: bool, last: Any) -> dict[str, Any]:
    return {
        "community": onboarding.is_community(guild),
        "managed": bool(managed),
        "last_synced_at": last,
        "more_on_pings": int(result.more),
        "foreign_prompts": int(result.foreign),
        "prompts": [
            {
                "title": one.title,
                "options": [title for title, _roles, _note in one.options],
            }
            for one in result.wanted
        ],
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

    async def wanted_spotlight(spotlight_id: Any) -> Any:
        row = await channel_by_id(bot.db, wanted_id(spotlight_id))
        guild = require_guild(bot)
        if row is None or int(row["guild_id"]) != int(guild.id):
            raise Refused(
                404,
                "no_such_spotlight",
                pings.NO_SUCH_SPOTLIGHT.format(given=str(spotlight_id)[:40]),
            )
        return row

    @router.post("/streamers")
    async def pings_streamer_add(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        if payload.get("spotlight_id") not in (None, ""):
            row = await wanted_spotlight(payload.get("spotlight_id"))
            outcome = await pings.ensure_fan_role(
                bot,
                guild,
                None,
                by=int(who["id"]),
                existing_role=wanted_role(guild, payload.get("role_id")),
                staff=True,
                via=VIA_WEBSITE,
                spotlight=row,
            )
            if not outcome.ok:
                raise Refused(409, "not_created", outcome.message)
            held = await pings.get_spotlight_fan_role(bot.db, guild.id, row["id"])
            return streamer_row(guild, held) | {"message": outcome.message}
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

    @router.delete("/streamers/spotlight/{spotlight_id}")
    async def pings_spotlight_remove(request: Request, spotlight_id: str) -> dict[str, Any]:
        """Staff always get the final say: the move that reverses the POST above."""
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_spotlight(spotlight_id)
        outcome = await pings.remove_fan_role(
            bot,
            guild,
            by=int(who["id"]),
            via=VIA_WEBSITE,
            spotlight=row,
            because=spot.FAN_ROLE_TAKEN,
        )
        if not outcome.ok:
            raise Refused(404, "no_fan_role", outcome.message)
        return {
            "removed": True,
            "member_id": None,
            "spotlight_id": int(row["id"]),
            "role_id": str(outcome.role_id) if outcome.role_id else None,
            "message": outcome.message,
        }

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
            "spotlight_id": None,
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

    @router.post("/raidtrain-role")
    async def pings_raidtrain_setup(
        request: Request, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        outcome = await pings.setup_raidtrain_role(
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
            "message": outcome.message,
        }

    @router.get("/list")
    async def pings_list() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        held = await pings.all_fan_roles(bot.db, guild.id)
        found = [
            listing_row(guild, row, pings.row_for(held, row["user_id"]))
            for row in await pings.all_streamers(bot.db, guild.id)
        ]
        return found + [
            spotlight_listing_row(guild, row, pings.spotlight_row_for(held, row["id"]))
            for row in await channels_for(bot.db, guild.id)
        ]

    @router.post("/list/{member_id}")
    async def pings_list_set(
        request: Request, member_id: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Staff always get the final say: one route hides and restores, both ways."""
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = wanted_id(member_id)
        listed = bool((payload or {}).get("listed", True))
        move = pings.restore_streamer if listed else pings.hide_streamer
        outcome = await move(bot, guild, wanted, by=int(who["id"]), via=VIA_WEBSITE)
        if not outcome.ok:
            raise Refused(409, "not_changed", outcome.message)
        row = await pings.get_streamer(bot.db, guild.id, wanted)
        held = pings.row_for(await pings.all_fan_roles(bot.db, guild.id), wanted)
        return listing_row(guild, row, held) | {"message": outcome.message}

    @router.get("/onboarding")
    async def pings_onboarding_card() -> dict[str, Any]:
        guild = require_guild(bot)
        require_db(bot)
        wanted, more = await onboarding.wanted_prompts(bot, guild)
        result = onboarding.Result(
            True, onboarding.UNCHANGED_REASON, "", wanted=list(wanted), more=more
        )
        return onboarding_card(
            guild,
            result,
            managed=onboarding.managed(bot, guild.id),
            last=await onboarding.last_sync(bot, guild.id),
        )

    @router.post("/onboarding/sync")
    async def pings_onboarding_sync(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        result = await onboarding.reconcile(
            bot, guild, by=int(who["id"]), via=VIA_WEBSITE, asked=True
        )
        if not result.ok:
            raise Refused(409, result.reason, result.message)
        return {"wrote": result.wrote, "message": result.message}

    return router
