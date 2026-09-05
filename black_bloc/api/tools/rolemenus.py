from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import rolegrants as grants
from ... import rolemenu_panels as panels
from ...cogs.community.role_menus import (
    MODES,
    NO_SUCH_MEMBER,
    NOTHING_ON_THIS_MENU,
    ROLE_MENUS_OFF,
    STAFF_MODE,
    UNSET,
    MenuLimitError,
    add_option,
    apply_request_decision,
    change_menu,
    check_description,
    check_label,
    check_option_count,
    check_title,
    drop_menu,
    expires_days_of,
    get_menu,
    get_menu_by_id,
    get_options,
    list_menus,
    make_menu,
    needs_approval,
    picking_is_on,
    post_menu,
    remove_option,
    retry_days_of,
    seed_menus,
    seed_summary,
    staff_assign,
)
from ...logkinds import VIA_WEBSITE
from ..auth import Refused, staff_dependency
from ..names import as_id, avatar_url, resolve_one
from ..writes import (
    actor_for,
    guard_of,
    refuse_guarded,
    require_db,
    require_guild,
    writer_dependency,
)

log = logging.getLogger(__name__)

NO_SUCH_MENU = (
    "This server has no role menu called **{name}**, so nothing was changed. The role menus page "
    "lists the ones that exist."
)
NAME_TAKEN = (
    "This server already has a role menu called **{name}**, so nothing was created. Pick another "
    "name, or edit that one."
)
NEEDS_A_NAME = (
    "A role menu needs a short name and a heading, so nothing was created. Fill both in and try "
    "again."
)
BAD_MODE = (
    "**{given}** is not a way a role menu can work, so nothing was changed. It is one of "
    "{modes} — multiple lets people pick several, single allows one, staff hands them out."
)
NO_SUCH_ROLE = (
    "**{role_id}** is not a role in this server any more, so the menu was left as it was. Refresh "
    "the page and pick the roles again."
)
UNASSIGNABLE = (
    "Black Bloc cannot hand out **{name}**, so it was not added. That role is either above Black "
    "Bloc's own role in Server Settings → Roles, or managed by another app. Ask an admin to move "
    "Black Bloc's role above it, then try again."
)
STAFF_MENU_NOT_POSTED = (
    "**{name}** is a staff-assigned menu, so there is no panel to post — nobody gives these roles "
    "to themselves."
)
NOTHING_TO_POST = (
    "**{name}** has no roles on it yet, so there is nothing to post. Add one first."
)
NO_SUCH_CHANNEL = (
    "**{channel_id}** is not a channel Black Bloc can see, so nothing was posted. Pick one from "
    "the list and try again."
)
BAD_OPTION = (
    "One of the roles on that menu arrived in a shape Black Bloc could not read, so nothing was "
    "changed. It is a fault in the page rather than in what you picked — reload the role menus "
    "page and try again."
)
UNKNOWN_STATUS = (
    "**{given}** is not a state a role request can be in, so nothing was listed. They are {known}."
)
BAD_APPROVAL = (
    "**{given}** is not on or off, so nothing was changed. It is a fault in the page rather than "
    "in what you picked — reload the role menus page and try again."
)
BAD_DAYS = (
    "**{given}** is not a number of days, so nothing was changed. Send a whole number from 0 to "
    "{limit} — 0 means the role never runs out."
).replace("{limit}", str(grants.DAYS_MAX))
NOT_POSTED_YET = (
    "**{name}** is not posted anywhere yet, so there is no panel to move. Post it from the Post "
    "a menu section to choose where it goes."
)
PANEL_NOT_MOVED = (
    "Black Bloc could not take **{name}**'s old panel down, so it is still where it was and "
    "nothing was posted in the new channel. It needs to see the old channel and be able to "
    "delete its own message there."
)
DENY_NEEDS_A_REASON = (
    "A denied request needs one line the member is sent, so nothing was done. Say why and send "
    "it again."
)
NOTHING_TO_UNPOST = (
    "**{name}** has no panel up right now, so there was nothing to take down. Post it from the "
    "Post a menu section first."
)
PANEL_STUCK = (
    "Black Bloc could not take **{name}**'s panel down, so it is still where it was. It needs to "
    "see that channel and be able to delete its own message there — ask a Lead to check both, "
    "then try again."
)
PANEL_TAKEN_DOWN = (
    "**{name}**'s panel is down. The menu and its roles are untouched and nobody loses a role — "
    "post it again whenever you want it back."
)


def option_row(row: Any) -> dict[str, Any]:
    return {
        "role_id": str(row["role_id"]),
        "label": row["label"],
        "emoji": row["emoji"],
        "position": int(row["position"]),
    }


def menu_row(menu: Any, options: Any) -> dict[str, Any]:
    return {
        "name": menu["name"],
        "title": menu["title"],
        "description": menu["description"],
        "mode": menu["mode"],
        "channel_id": str(menu["channel_id"]) if menu["channel_id"] else None,
        "message_id": str(menu["message_id"]) if menu["message_id"] else None,
        "approval": needs_approval(menu),
        "expires_days": expires_days_of(menu),
        "retry_days": retry_days_of(menu),
        "options": [option_row(row) for row in options],
    }


def request_row(guild: Any, row: Any, menu_name: Any = None) -> dict[str, Any]:
    by = row["decided_by"]
    member = guild.get_member(row["user_id"]) if guild is not None else None
    return {
        "id": row["id"],
        "menu_id": str(row["menu_id"]),
        "menu_name": menu_name,
        "user_id": str(row["user_id"]),
        "user_name": resolve_one(guild, row["user_id"])["display_name"],
        "user_avatar": avatar_url(member) if member is not None else None,
        "role_id": str(row["role_id"]),
        "role_name": resolve_one(guild, row["role_id"])["display_name"],
        "requested_at": row["requested_at"],
        "status": row["status"],
        "decided_by_id": str(by) if by else None,
        "decided_by_name": resolve_one(guild, by)["display_name"] if by else None,
        "decided_at": row["decided_at"],
        "deny_reason": row["deny_reason"],
    }


def wanted_statuses(given: Any) -> tuple[str, ...]:
    wanted = tuple(part for part in str(given or "").split(",") if part)
    for part in wanted:
        if part not in grants.REQUEST_STATUSES:
            raise Refused(
                400,
                "unknown_status",
                UNKNOWN_STATUS.format(
                    given=part, known=", ".join(grants.REQUEST_STATUSES)
                ),
            )
    return wanted or grants.REQUEST_STATUSES


def wanted_approval(given: Any) -> bool | None:
    if given is None:
        return None
    if not isinstance(given, bool):
        raise Refused(400, "bad_approval", BAD_APPROVAL.format(given=str(given)[:40]))
    return given


def wanted_days(given: Any, *, blank: Any) -> Any:
    """`blank` is what an absent field means: UNSET to leave it, None to clear it."""
    if given is None:
        return blank
    try:
        number = int(given)
    except (TypeError, ValueError):
        raise Refused(400, "bad_days", BAD_DAYS.format(given=str(given)[:40])) from None
    if number < 0 or number > grants.DAYS_MAX:
        raise Refused(400, "bad_days", BAD_DAYS.format(given=str(given)[:40]))
    return number


def checked_mode(given: Any) -> str | None:
    if given is None:
        return None
    if str(given) not in MODES:
        raise Refused(400, "bad_mode", BAD_MODE.format(given=given, modes=", ".join(MODES)))
    return str(given)


def wanted_role(guild: Any, role_id: Any) -> Any:
    role = guild.get_role(as_id(role_id)) if as_id(role_id) is not None else None
    if role is None:
        raise Refused(400, "no_such_role", NO_SUCH_ROLE.format(role_id=role_id))
    assignable = getattr(role, "is_assignable", None)
    if callable(assignable) and not assignable():
        raise Refused(400, "role_refused", UNASSIGNABLE.format(name=role.name))
    return role


def within_limits(check: Any, value: Any) -> Any:
    try:
        return check(value)
    except MenuLimitError as exc:
        raise Refused(400, "too_long", str(exc)) from None


def wanted_title(given: Any) -> str:
    return within_limits(check_title, str(given or "").strip())


def wanted_description(given: Any) -> str | None:
    """None means 'leave it as it is'; the empty string is how a description is cleared."""
    if given is None:
        return None
    return within_limits(check_description, str(given).strip())


def wanted_option(guild: Any, item: Any) -> tuple[Any, str, Any]:
    if not isinstance(item, dict):
        raise Refused(400, "bad_option", BAD_OPTION)
    role = wanted_role(guild, item.get("role_id"))
    label = within_limits(check_label, str(item.get("label") or role.name))
    return role, label, item.get("emoji")


def wanted_options(guild: Any, items: Any) -> list[tuple[Any, str, Any]]:
    within_limits(check_option_count, len(items))
    return [wanted_option(guild, item) for item in items]


async def read_menu(bot: Any, guild: Any, name: str) -> tuple[Any, list[Any]]:
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        raise Refused(404, "no_such_menu", NO_SUCH_MENU.format(name=name))
    return menu, await get_options(bot.db, menu["id"])


async def sync_options(bot: Any, menu: Any, wanted: list[tuple[Any, str, Any]]) -> None:
    """The menu ends up holding exactly the options `wanted_options` passed, in that order."""
    for role, label, emoji in wanted:
        await add_option(bot.db, menu["id"], role.id, label, emoji)
    kept = {role.id for role, _, _ in wanted}
    for row in await get_options(bot.db, menu["id"]):
        if row["role_id"] not in kept:
            await remove_option(bot.db, menu["id"], row["role_id"])


async def wanted_target(bot: Any, guild: Any, menu: Any, options: Any, channel_id: Any) -> Any:
    """Every refusal the post path gives, in the order a panel meets them."""
    if menu["mode"] == STAFF_MODE:
        raise Refused(400, "staff_menu", STAFF_MENU_NOT_POSTED.format(name=menu["name"]))
    if not options:
        raise Refused(400, "no_options", NOTHING_TO_POST.format(name=menu["name"]))
    if not picking_is_on(bot, guild.id):
        raise Refused(409, "rolemenu_off", ROLE_MENUS_OFF)
    target = guild.get_channel(channel_id) if channel_id else None
    if target is None:
        raise Refused(400, "no_such_channel", NO_SUCH_CHANNEL.format(channel_id=channel_id))
    guard = guard_of(bot)
    if guard is not None and not guard.allows_channel(target.id):
        refuse_guarded(guard.refusal_message())
    return target


async def can_move(bot: Any, guild: Any, menu: Any, options: Any, channel_id: Any) -> None:
    """Asked BEFORE an edit is written, so a refused move does not leave a half-saved menu."""
    if not menu["message_id"]:
        raise Refused(400, "not_posted", NOT_POSTED_YET.format(name=menu["name"]))
    await wanted_target(bot, guild, menu, options, channel_id)


async def move_panel(bot: Any, guild: Any, name: str, channel_id: int, who: Any) -> Any:
    """The old panel comes down before the new one goes up, so a menu is never in two places."""
    menu, options = await read_menu(bot, guild, name)
    await can_move(bot, guild, menu, options, channel_id)
    target = await wanted_target(bot, guild, menu, options, channel_id)
    actor = actor_for(bot, who, guild)
    if not await panels.unpost(bot, menu, actor, via=VIA_WEBSITE):
        raise Refused(409, "panel_stuck", PANEL_NOT_MOVED.format(name=name))
    fresh, options = await read_menu(bot, guild, name)
    return await post_menu(bot, guild, actor, fresh, options, target, via=VIA_WEBSITE)


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/rolemenus", tags=["rolemenus"], dependencies=[Depends(staff_dependency(bot))]
    )

    @router.get("")
    async def rolemenus_index() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [
            menu_row(menu, await get_options(bot.db, menu["id"]))
            for menu in await list_menus(bot.db, guild.id)
        ]

    @router.post("/seed")
    async def rolemenu_seed(request: Request) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        created, skipped = await seed_menus(
            bot, guild, actor_for(bot, who, guild), via=VIA_WEBSITE
        )
        return {
            "created": created,
            "skipped": skipped,
            "message": seed_summary(created, skipped),
        }

    @router.get("/requests")
    async def rolemenu_requests(status: str = "") -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        rows = await grants.requests_by_status(bot.db, guild.id, wanted_statuses(status))
        named = {menu["id"]: menu["name"] for menu in await list_menus(bot.db, guild.id)}
        return [request_row(guild, row, named.get(row["menu_id"])) for row in rows]

    async def _decide(
        request: Request, request_id: int, status: str, reason: Any, days: Any
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        said, fresh = await apply_request_decision(
            bot,
            guild,
            request_id,
            status,
            actor_for(bot, who, guild),
            reason=reason,
            days=days,
            via=VIA_WEBSITE,
        )
        if fresh is None:
            raise Refused(409, "not_decided", said)
        menu = await get_menu_by_id(bot.db, fresh["menu_id"])
        return {
            "request": request_row(guild, fresh, menu["name"] if menu is not None else None),
            "message": said,
        }

    @router.post("/requests/{request_id}/approve")
    async def request_approve(
        request: Request, request_id: int, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        days = wanted_days((payload or {}).get("days"), blank=None)
        return await _decide(request, request_id, grants.APPROVED, None, days)

    @router.post("/requests/{request_id}/deny")
    async def request_deny(
        request: Request, request_id: int, payload: dict[str, Any]
    ) -> dict[str, Any]:
        reason = grants.clamp(payload.get("reason"), grants.REASON_LIMIT)
        if not reason:
            raise Refused(400, "no_reason", DENY_NEEDS_A_REASON)
        return await _decide(request, request_id, grants.DENIED, reason, None)

    @router.post("")
    async def rolemenu_create(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        name = str(payload.get("name") or "").strip()
        title = wanted_title(payload.get("title"))
        if not name or not title:
            raise Refused(400, "bad_request", NEEDS_A_NAME)
        mode = checked_mode(payload.get("mode")) or "multiple"
        description = wanted_description(payload.get("description"))
        menu_id = await make_menu(
            bot,
            guild,
            actor_for(bot, who, guild),
            name,
            title,
            description or None,
            mode,
            approval=wanted_approval(payload.get("approval")),
            expires_days=wanted_days(payload.get("expires_days"), blank=None),
            retry_days=wanted_days(payload.get("retry_days"), blank=None),
            via=VIA_WEBSITE,
        )
        if menu_id is None:
            raise Refused(400, "name_taken", NAME_TAKEN.format(name=name))
        menu, options = await read_menu(bot, guild, name)
        return menu_row(menu, options)

    @router.put("/{name}")
    async def rolemenu_update(
        request: Request, name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, held = await read_menu(bot, guild, name)
        given = payload.get("channel_id")
        moving = as_id(given) if given not in (None, "") else None
        if moving is not None and moving != menu["channel_id"]:
            await can_move(bot, guild, menu, held, moving)
        mode = checked_mode(payload.get("mode"))
        title = wanted_title(payload.get("title")) if payload.get("title") else None
        description = wanted_description(payload.get("description"))
        wanted = payload.get("options")
        options = wanted_options(guild, wanted) if isinstance(wanted, list) else None
        await change_menu(
            bot,
            guild,
            actor_for(bot, who, guild),
            name,
            title=title,
            description=description,
            mode=mode,
            approval=wanted_approval(payload.get("approval")),
            expires_days=wanted_days(payload.get("expires_days"), blank=UNSET),
            retry_days=wanted_days(payload.get("retry_days"), blank=None),
            via=VIA_WEBSITE,
        )
        if options is not None:
            await sync_options(bot, menu, options)
        if moving is not None and moving != menu["channel_id"]:
            await move_panel(bot, guild, name, moving, who)
        fresh, options = await read_menu(bot, guild, name)
        return menu_row(fresh, options)

    @router.delete("/{name}")
    async def rolemenu_delete(request: Request, name: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        if not await drop_menu(bot, guild, actor_for(bot, who, guild), name, via=VIA_WEBSITE):
            raise Refused(404, "no_such_menu", NO_SUCH_MENU.format(name=name))
        return {"deleted": True, "name": name}

    @router.post("/{name}/post")
    async def rolemenu_post(
        request: Request, name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, options = await read_menu(bot, guild, name)
        channel_id = as_id(payload.get("channel_id")) or bot.store.get(
            guild.id, "role_menu_channel_id"
        )
        target = await wanted_target(bot, guild, menu, options, channel_id)
        message = await post_menu(
            bot, guild, actor_for(bot, who, guild), menu, options, target, via=VIA_WEBSITE
        )
        return {
            "posted": True,
            "name": name,
            "channel_id": str(target.id),
            "message_id": str(message.id),
        }

    @router.post("/{name}/assign")
    async def rolemenu_assign(
        request: Request, name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, options = await read_menu(bot, guild, name)
        if not options:
            raise Refused(400, "no_options", NOTHING_ON_THIS_MENU.format(name=name))
        if not picking_is_on(bot, guild.id):
            raise Refused(409, "rolemenu_off", ROLE_MENUS_OFF)
        given = payload.get("user_id")
        member = guild.get_member(as_id(given)) if as_id(given) is not None else None
        if member is None:
            raise Refused(404, "no_such_member", NO_SUCH_MEMBER.format(user_id=given))
        remove = bool(payload.get("remove"))
        wanted = [as_id(one) for one in payload.get("role_ids") or ()]
        done, said = await staff_assign(
            bot,
            guild,
            actor_for(bot, who, guild),
            menu,
            options,
            member,
            [one for one in wanted if one is not None],
            remove=remove,
            via=VIA_WEBSITE,
        )
        if not done:
            raise Refused(409, "role_refused", said)
        return {
            "assigned": not remove,
            "name": name,
            "user_id": str(member.id),
            "message": said,
        }

    @router.post("/{name}/unpost")
    async def rolemenu_unpost(request: Request, name: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, _ = await read_menu(bot, guild, name)
        if not menu["message_id"]:
            raise Refused(400, "not_posted", NOTHING_TO_UNPOST.format(name=name))
        guard = guard_of(bot)
        blocked = guard is not None and not guard.allows_channel(menu["channel_id"])
        if not await panels.unpost(bot, menu, actor_for(bot, who, guild), via=VIA_WEBSITE):
            if blocked:
                refuse_guarded(guard.refusal_message())
            raise Refused(409, "panel_stuck", PANEL_STUCK.format(name=name))
        return {
            "unposted": True,
            "name": name,
            "channel_id": str(menu["channel_id"]) if menu["channel_id"] else None,
            "message": PANEL_TAKEN_DOWN.format(name=name),
        }

    return router
