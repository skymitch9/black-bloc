from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends

from ...cogs.community.birthdays import members_of
from ...modcases import count_cases_for
from ...settings_store import member_is_staff
from ..auth import staff_dependency
from ..names import avatar_url
from ..writes import reader_dependency, require_guild

log = logging.getLogger(__name__)

PER_PAGE = 50
PER_PAGE_MAX = 100
NEW_DAYS = 7
ROLES_SHOWN = 5
FILTERS = ("all", "staff", "bots", "new")
SORTS = ("joined_desc", "joined_asc", "name")


def hex_colour(role: Any) -> str | None:
    colour = getattr(role, "color", None)
    if colour is None:
        colour = getattr(role, "colour", None)
    value = getattr(colour, "value", colour)
    if isinstance(value, str):
        return value or None
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return None
    return f"#{value:06x}"


def top_roles(member: Any) -> list[dict[str, Any]]:
    found = [
        role
        for role in getattr(member, "roles", ()) or ()
        if not (getattr(role, "is_default", None) and role.is_default())
        and getattr(role, "id", None) != getattr(getattr(member, "guild", None), "id", None)
    ]
    found.sort(key=lambda role: -int(getattr(role, "position", 0) or 0))
    return [
        {
            "id": str(role.id),
            "name": str(getattr(role, "name", "") or ""),
            "color": hex_colour(role),
        }
        for role in found[:ROLES_SHOWN]
    ]


def joined_iso(member: Any) -> str | None:
    at = getattr(member, "joined_at", None)
    if at is None:
        return None
    try:
        return at.isoformat()
    except AttributeError:
        return str(at) or None


def joined_at(member: Any) -> datetime | None:
    at = getattr(member, "joined_at", None)
    if not isinstance(at, datetime):
        return None
    return at if at.tzinfo is not None else at.replace(tzinfo=UTC)


def is_new(member: Any, cutoff: datetime) -> bool:
    at = joined_at(member)
    return at is not None and at >= cutoff


def matches(member: Any, query: str) -> bool:
    if not query:
        return True
    haystack = " ".join(
        str(part or "").lower()
        for part in (
            getattr(member, "display_name", None),
            getattr(member, "name", None),
            getattr(member, "global_name", None),
        )
    )
    return query in haystack


def wanted_one(given: Any, allowed: tuple[str, ...]) -> str:
    found = str(given or "").strip().lower()
    return found if found in allowed else allowed[0]


def wanted_page(given: Any) -> int:
    try:
        return max(1, int(given))
    except (TypeError, ValueError):
        return 1


def wanted_per_page(given: Any) -> int:
    try:
        return max(1, min(int(given), PER_PAGE_MAX))
    except (TypeError, ValueError):
        return PER_PAGE


def sorted_members(members: list[Any], how: str) -> list[Any]:
    """A member Discord gave no join date for sorts last whichever way the list runs."""
    if how == "name":
        return sorted(members, key=lambda m: str(getattr(m, "display_name", "") or "").lower())
    dated = [member for member in members if joined_at(member) is not None]
    undated = [member for member in members if joined_at(member) is None]
    dated.sort(key=joined_at, reverse=how == "joined_desc")
    return dated + undated


def member_row(member: Any, *, staff: bool, cases: int) -> dict[str, Any]:
    name = str(getattr(member, "name", "") or "")
    return {
        "id": str(member.id),
        "name": str(getattr(member, "display_name", None) or name or member.id),
        "username": name or str(member.id),
        "bot": bool(getattr(member, "bot", False)),
        "joined_at": joined_iso(member),
        "roles": top_roles(member),
        "staff": staff,
        "cases": cases,
        "avatar": avatar_url(member),
    }


def build_router(bot: Any) -> APIRouter:
    router = APIRouter(
        prefix="/api",
        tags=["members"],
        dependencies=[Depends(staff_dependency(bot)), Depends(reader_dependency(bot))],
    )

    @router.get("/members")
    async def members(
        q: str = "",
        filter: str = "all",
        page: str = "1",
        per_page: str = str(PER_PAGE),
        sort: str = "joined_desc",
    ) -> dict[str, Any]:
        guild = require_guild(bot)
        everyone = await members_of(guild)
        cutoff = datetime.now(UTC) - timedelta(days=NEW_DAYS)
        staff_ids = bot.store.staff_role_ids(guild)
        is_staff = {
            member.id: member_is_staff(member, staff_ids) and not getattr(member, "bot", False)
            for member in everyone
        }

        wanted = wanted_one(filter, FILTERS)
        query = str(q or "").strip().lower()
        found = [member for member in everyone if matches(member, query)]
        if wanted == "staff":
            found = [member for member in found if is_staff.get(member.id)]
        elif wanted == "bots":
            found = [member for member in found if getattr(member, "bot", False)]
        elif wanted == "new":
            found = [member for member in found if is_new(member, cutoff)]

        at = wanted_page(page)
        size = wanted_per_page(per_page)
        shown = sorted_members(found, wanted_one(sort, SORTS))[(at - 1) * size : at * size]
        cases = await count_cases_for(getattr(bot, "db", None), guild.id, [m.id for m in shown])

        return {
            "total": int(getattr(guild, "member_count", 0) or len(everyone)),
            "humans": sum(1 for m in everyone if not getattr(m, "bot", False)),
            "bots": sum(1 for m in everyone if getattr(m, "bot", False)),
            "staff": sum(1 for m in everyone if is_staff.get(m.id)),
            "new_7d": sum(1 for m in everyone if is_new(m, cutoff)),
            "page": at,
            "per_page": size,
            "shown": len(shown),
            "members": [
                member_row(m, staff=bool(is_staff.get(m.id)), cases=cases.get(m.id, 0))
                for m in shown
            ],
        }

    return router
