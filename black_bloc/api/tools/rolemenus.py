from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from ...cogs.community.role_menus import (
    MODES,
    STAFF_MODE,
    MenuLimitError,
    add_option,
    check_description,
    check_label,
    check_option_count,
    check_title,
    create_menu,
    delete_menu,
    get_menu,
    get_options,
    list_menus,
    post_panel,
    remove_option,
    update_menu,
)
from ..auth import Refused, staff_dependency
from ..names import as_id
from ..writes import (
    guard_of,
    note,
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
        "options": [option_row(row) for row in options],
    }


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
        menu_id = await create_menu(bot.db, guild.id, name, title, description or None, mode)
        if menu_id is None:
            raise Refused(400, "name_taken", NAME_TAKEN.format(name=name))
        await note(bot, guild, "web.rolemenu.create", who, details={"menu": name, "mode": mode})
        menu, options = await read_menu(bot, guild, name)
        return menu_row(menu, options)

    @router.put("/{name}")
    async def rolemenu_update(
        request: Request, name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, _ = await read_menu(bot, guild, name)
        mode = checked_mode(payload.get("mode"))
        title = wanted_title(payload.get("title")) if payload.get("title") else None
        description = wanted_description(payload.get("description"))
        given = payload.get("options")
        options = wanted_options(guild, given) if isinstance(given, list) else None
        await update_menu(
            bot.db, guild.id, name, title=title, description=description, mode=mode
        )
        if options is not None:
            await sync_options(bot, menu, options)
        await note(bot, guild, "web.rolemenu.edit", who, details={"menu": name})
        fresh, options = await read_menu(bot, guild, name)
        return menu_row(fresh, options)

    @router.delete("/{name}")
    async def rolemenu_delete(request: Request, name: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        if not await delete_menu(bot.db, guild.id, name):
            raise Refused(404, "no_such_menu", NO_SUCH_MENU.format(name=name))
        await note(bot, guild, "web.rolemenu.delete", who, details={"menu": name})
        return {"deleted": True, "name": name}

    @router.post("/{name}/post")
    async def rolemenu_post(
        request: Request, name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, options = await read_menu(bot, guild, name)
        if menu["mode"] == STAFF_MODE:
            raise Refused(400, "staff_menu", STAFF_MENU_NOT_POSTED.format(name=name))
        if not options:
            raise Refused(400, "no_options", NOTHING_TO_POST.format(name=name))
        channel_id = as_id(payload.get("channel_id")) or bot.store.get(
            guild.id, "role_menu_channel_id"
        )
        target = guild.get_channel(channel_id) if channel_id else None
        if target is None:
            raise Refused(400, "no_such_channel", NO_SUCH_CHANNEL.format(channel_id=channel_id))
        guard = guard_of(bot)
        if guard is not None and not guard.allows_channel(target.id):
            refuse_guarded(guard.refusal_message())
        message = await post_panel(bot, menu, options, target)
        await note(
            bot,
            guild,
            "web.rolemenu.post",
            who,
            details={"menu": name, "channel_id": target.id, "message_id": message.id},
        )
        return {
            "posted": True,
            "name": name,
            "channel_id": str(target.id),
            "message_id": str(message.id),
        }

    return router
