from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import rolegrants as grants
from ...cogs.community.role_menus import change_roles
from ..auth import Refused, staff_dependency
from ..names import as_id, resolve_one
from ..writes import note, require_db, require_guild, wanted_id, writer_dependency

log = logging.getLogger(__name__)

GRANTS_LIMIT = 200

NO_SUCH_GRANT = (
    "Black Bloc has no timed role **#{grant_id}** any more, so nothing was changed. The role "
    "menus page lists the ones it has."
)
ALREADY_ENDED = (
    "That timed role ended on {when}, so there was nothing to change. Give it again with the "
    "Grant button if they should have it back."
)
NO_END_DATE = (
    "That role has no end date, so there is nothing to push back. End it now instead, or take it "
    "off in Discord."
)
NO_SUCH_MEMBER = (
    "**{user_id}** is not somebody Black Bloc can see in this server, so nothing was granted. "
    "Pick them from the member list and try again."
)
NO_SUCH_ROLE = (
    "**{role_id}** is not a role in this server any more, so nothing was granted. Refresh the "
    "page and pick the role again."
)
BAD_DAYS = (
    "**{given}** is not a number of days, so nothing was changed. Send a whole number — or leave "
    "it out for a role with no end date."
)
DAYS_NEEDED = (
    "Extending a role needs a number of days, so nothing was changed. Send how many to add."
)
CANNOT_ADD = (
    "Discord refused to add **{label}**, so **{name}** was left exactly as they were. Black Bloc "
    "needs Manage Roles and its own role has to sit above that one in Server Settings → Roles."
)
CANNOT_REMOVE = (
    "Discord refused to take **{label}** off **{name}**, so nothing was changed and the timed "
    "role is still open. Black Bloc needs Manage Roles and its own role has to sit above that one."
)


def grant_row(guild: Any, row: Any) -> dict[str, Any]:
    by = row["granted_by"]
    return {
        "id": row["id"],
        "user_id": str(row["user_id"]),
        "user_name": resolve_one(guild, row["user_id"])["display_name"],
        "role_id": str(row["role_id"]),
        "role_name": resolve_one(guild, row["role_id"])["display_name"],
        "source": row["source"],
        "granted_by_id": str(by) if by else None,
        "granted_by_name": resolve_one(guild, by)["display_name"] if by else None,
        "granted_at": row["granted_at"],
        "expires_at": row["expires_at"],
        "removed_at": row["removed_at"],
        "removed_reason": row["removed_reason"],
        "open": row["removed_at"] is None,
    }


def wanted_days(given: Any, *, required: bool) -> int | None:
    """None means 'no end date'; a number that is not one is refused rather than guessed."""
    if given is None or (isinstance(given, str) and not given.strip()):
        if required:
            raise Refused(400, "no_days", DAYS_NEEDED)
        return None
    try:
        number = int(given)
    except (TypeError, ValueError):
        raise Refused(400, "bad_days", BAD_DAYS.format(given=str(given)[:40])) from None
    if number < 0:
        raise Refused(400, "bad_days", BAD_DAYS.format(given=str(given)[:40]))
    return number


async def wanted_grant(bot: Any, guild: Any, grant_id: int) -> Any:
    row = await grants.get_grant(bot.db, grant_id)
    if row is None or row["guild_id"] != guild.id:
        raise Refused(404, "no_such_grant", NO_SUCH_GRANT.format(grant_id=grant_id))
    return row


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/roles", tags=["roles"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("/grants")
    async def grants_index(
        user_id: str = "", role_id: str = "", limit: int = GRANTS_LIMIT
    ) -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        rows = await grants.grants_for(
            bot.db,
            guild.id,
            user_id=as_id(user_id) if user_id else None,
            role_id=as_id(role_id) if role_id else None,
            limit=max(1, min(int(limit), GRANTS_LIMIT)),
        )
        return [grant_row(guild, row) for row in rows]

    @router.post("/grants")
    async def grant_create(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        member = guild.get_member(wanted_id(payload.get("user_id")))
        if member is None:
            raise Refused(
                404, "no_such_member", NO_SUCH_MEMBER.format(user_id=payload.get("user_id"))
            )
        role = guild.get_role(wanted_id(payload.get("role_id")))
        if role is None:
            raise Refused(
                404, "no_such_role", NO_SUCH_ROLE.format(role_id=payload.get("role_id"))
            )
        days = wanted_days(payload.get("days"), required=False)
        reason = grants.clamp(payload.get("reason"), grants.REASON_LIMIT) or None
        held = any(r.id == role.id for r in member.roles)
        if not held and not await change_roles(
            bot, member, guild, {role.id}, set(), f"Black Bloc dashboard grant by {who['id']}"
        ):
            raise Refused(
                409,
                "role_refused",
                CANNOT_ADD.format(label=role.name, name=member.display_name),
            )
        until = grants.expires_at(days)
        open_row = await grants.open_grant(bot.db, guild.id, member.id, role.id)
        if open_row is not None:
            await grants.extend_grant(bot.db, open_row["id"], until)
            grant_id = open_row["id"]
        else:
            grant_id = await grants.add_grant(
                bot.db,
                guild.id,
                member.id,
                role.id,
                grants.STAFF,
                granted_by=int(who["id"]),
                until=until,
            )
        await note(
            bot,
            guild,
            "web.role.granted",
            who,
            target=member,
            reason=reason,
            details={"grant_id": grant_id, "role_id": role.id, "expires_at": until},
        )
        return grant_row(guild, await grants.get_grant(bot.db, grant_id))

    @router.post("/grants/{grant_id}/extend")
    async def grant_extend(
        request: Request, grant_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_grant(bot, guild, grant_id)
        if row["removed_at"]:
            raise Refused(409, "already_ended", ALREADY_ENDED.format(when=row["removed_at"]))
        if not row["expires_at"]:
            raise Refused(409, "no_end_date", NO_END_DATE)
        days = wanted_days(payload.get("days"), required=True)
        until = grants.pushed_back(row["expires_at"], max(int(days or 0), 1))
        await grants.extend_grant(bot.db, grant_id, until)
        await note(
            bot,
            guild,
            "web.role.extended",
            who,
            target=row["user_id"],
            details={"grant_id": grant_id, "role_id": row["role_id"], "expires_at": until},
        )
        return grant_row(guild, await grants.get_grant(bot.db, grant_id))

    @router.delete("/grants/{grant_id}")
    async def grant_end(request: Request, grant_id: int) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await wanted_grant(bot, guild, grant_id)
        if row["removed_at"]:
            raise Refused(409, "already_ended", ALREADY_ENDED.format(when=row["removed_at"]))
        member = guild.get_member(row["user_id"])
        if member is not None and any(r.id == row["role_id"] for r in member.roles):
            if not await change_roles(
                bot,
                member,
                guild,
                set(),
                {row["role_id"]},
                f"Black Bloc dashboard ended a timed role, by {who['id']}",
            ):
                raise Refused(
                    409,
                    "role_refused",
                    CANNOT_REMOVE.format(
                        label=resolve_one(guild, row["role_id"])["display_name"],
                        name=member.display_name,
                    ),
                )
        await grants.end_grant(bot.db, grant_id, grants.ENDED_BY_STAFF)
        await note(
            bot,
            guild,
            "web.role.ended",
            who,
            target=row["user_id"],
            details={"grant_id": grant_id, "role_id": row["role_id"]},
        )
        return grant_row(guild, await grants.get_grant(bot.db, grant_id))

    return router
