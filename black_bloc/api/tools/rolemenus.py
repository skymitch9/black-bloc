from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import rolemenus as menus
from ...cogs.community.role_menus import (
    NO_SUCH_MEMBER,
    NOTHING_ON_THIS_MENU,
    ROLEMENU_ENDED_TEXT_KEY,
    STAFF_MODE,
    MenuLimitError,
    add_option,
    bindable_marathons,
    change_menu,
    check_description,
    check_label,
    check_option_count,
    check_title,
    default_buffer,
    delete_refusal,
    drop_menu,
    end_label,
    end_menu_now,
    expires_days_of,
    failure_count,
    get_menu,
    get_options,
    held_is_past,
    list_menus,
    local_moment,
    make_menu,
    marathon_name_of,
    marathon_row,
    members_of,
    menu_value,
    needs_approval,
    remove_option,
    retry_days_of,
    set_menu_end,
    staff_assign,
    stamp_grants,
    use_held_end,
    use_held_question,
    wearing_count,
    word,
)
from ...golive import parse_ts
from ...logkinds import VIA_WEBSITE
from ...settings_store import ROLEMENU_RETIRED_KEY
from ..auth import Refused, staff_dependency
from ..names import as_id
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
NO_SUCH_ROLE = (
    "**{role_id}** is not a role in this server any more, so the menu was left as it was. Refresh "
    "the page and pick the roles again."
)
BAD_OPTION = (
    "One of the roles on that menu arrived in a shape Black Bloc could not read, so nothing was "
    "changed. It is a fault in the page rather than in what you picked — reload the role menus "
    "page and try again."
)
BAD_END_SOURCE = (
    "**{given}** is not a way a role menu can end, so nothing was changed. It is one of "
    "{known} — a fault in the page rather than in what you picked, so reload it and try again."
)
END_FIELDS = ("ends_source", "ends_marathon_id", "ends_at", "buffer_days")


def option_row(row: Any) -> dict[str, Any]:
    return {
        "role_id": str(row["role_id"]),
        "label": row["label"],
        "emoji": row["emoji"],
        "position": int(row["position"]),
    }


def site_when(bot: Any, guild_id: int, at: Any) -> str:
    return local_moment(bot, guild_id, at)


def menu_row(menu: Any, options: Any) -> dict[str, Any]:
    """The stored menu; the retired self-pick fields stay readable until the page stops reading."""
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
        "ends_source": menus.end_source(menu),
        "ends_marathon_id": (
            str(menu_value(menu, "ends_marathon_id"))
            if menu_value(menu, "ends_marathon_id") is not None
            else None
        ),
        "buffer_days": menu_value(menu, "buffer_days"),
        "ends_at": menu_value(menu, "ends_at"),
        "ended_at": menu_value(menu, "ended_at"),
        "ends_held_at": menu_value(menu, "ends_held_at"),
        "ends_set_by": (
            str(menu_value(menu, "ends_set_by")) if menu_value(menu, "ends_set_by") else None
        ),
        "ends_set_at": menu_value(menu, "ends_set_at"),
        "last_pass": {
            "passes": int(menu_value(menu, "end_passes", 0)),
            "members": int(menu_value(menu, "end_members", 0)),
            "failures": failure_count(menu),
            "ended_at": menu_value(menu, "ended_at"),
        },
    }


async def menu_payload(bot: Any, guild: Any, menu: Any, options: Any, members: Any) -> dict:
    row = menu_row(menu, options)
    wearing = wearing_count(bot, guild.id, members, [one["role_id"] for one in options])
    row["wearing"] = wearing if isinstance(wearing, int) else None
    row["buffer_default"] = menus.buffer_of({}, default_buffer(bot, guild.id))
    row["end_label"] = end_label(
        bot, guild.id, menu, await marathon_name_of(bot, guild.id, menu), site_when
    )
    held = menu_value(menu, "ends_held_at")
    row["held_label"] = site_when(bot, guild.id, held) if held else None
    row["held_past"] = held_is_past(menu)
    counted = wearing if isinstance(wearing, int) else wearing_count(bot, guild.id, None, ())
    row["held_question"] = use_held_question(
        bot, guild.id, menu, len(options), counted, site_when
    )
    row["end_now_question"] = word(
        bot, guild.id, "rolemenu_end_now_question", roles=len(options), members=counted
    )
    return row


async def marathon_choice(bot: Any, guild_id: int, row: Any) -> dict[str, Any]:
    known = parse_ts(row["ends_at"]) is not None
    label = (
        word(
            bot,
            guild_id,
            "rolemenu_marathon_option",
            name=row["name"],
            date=local_moment(bot, guild_id, row["ends_at"], "%Y-%m-%d"),
        )
        if known
        else word(bot, guild_id, "rolemenu_marathon_option_unknown", name=row["name"])
    )
    return {"id": str(row["id"]), "name": row["name"], "ends_at": row["ends_at"], "label": label}


def wanted_role(bot: Any, guild: Any, role_id: Any) -> Any:
    """A role the end of the menu could not take off is refused here, not discovered then."""
    role = guild.get_role(as_id(role_id)) if as_id(role_id) is not None else None
    if role is None:
        raise Refused(400, "no_such_role", NO_SUCH_ROLE.format(role_id=role_id))
    assignable = getattr(role, "is_assignable", None)
    if callable(assignable) and not assignable():
        raise Refused(
            400, "role_refused", word(bot, guild.id, "rolemenu_cannot_strip_said", name=role.name)
        )
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


def wanted_option(bot: Any, guild: Any, item: Any) -> tuple[Any, str, Any]:
    if not isinstance(item, dict):
        raise Refused(400, "bad_option", BAD_OPTION)
    role = wanted_role(bot, guild, item.get("role_id"))
    label = within_limits(check_label, str(item.get("label") or role.name))
    return role, label, item.get("emoji")


def wanted_options(bot: Any, guild: Any, items: Any) -> list[tuple[Any, str, Any]]:
    within_limits(check_option_count, len(items))
    return [wanted_option(bot, guild, item) for item in items]


async def read_menu(bot: Any, guild: Any, name: str) -> tuple[Any, list[Any]]:
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        raise Refused(404, "no_such_menu", NO_SUCH_MENU.format(name=name))
    return menu, await get_options(bot.db, menu["id"])


async def sync_options(bot: Any, menu: Any, wanted: list[tuple[Any, str, Any]]) -> None:
    """Exactly the options given, in order; grants on every role that came or went re-stamped."""
    before = {int(row["role_id"]) for row in await get_options(bot.db, menu["id"])}
    for role, label, emoji in wanted:
        await add_option(bot.db, menu["id"], role.id, label, emoji)
    kept = {role.id for role, _, _ in wanted}
    for row in await get_options(bot.db, menu["id"]):
        if row["role_id"] not in kept:
            await remove_option(bot.db, menu["id"], row["role_id"])
    moved = sorted(before ^ {int(one) for one in kept})
    if moved:
        await stamp_grants(bot.db, menu["guild_id"], moved, was=(menu_value(menu, "ends_at"),))


def wanted_buffer(bot: Any, guild_id: int, given: Any) -> int | None:
    """None or blank is the server's default; anything but 0-365 whole days is refused."""
    if given is None or str(given).strip() == "":
        return None
    typed = str(given).strip()
    if isinstance(given, bool) or not typed.isdigit() or int(typed) > menus.BUFFER_MAX:
        raise Refused(
            400,
            "bad_buffer",
            word(bot, guild_id, "rolemenu_end_bad_buffer_said", given=typed[:40]),
        )
    return int(typed)


def wanted_moment(bot: Any, guild_id: int, given: Any) -> datetime:
    """A typed `YYYY-MM-DD` (23:59 guild-local), `YYYY-MM-DD HH:MM`, or a full ISO moment."""
    text = str(given or "").strip()
    when = menus.typed_end(text, bot.store.get(guild_id, "default_timezone")) or parse_ts(text)
    if when is None:
        raise Refused(
            400, "bad_date", word(bot, guild_id, "rolemenu_end_bad_date_said", given=text[:40])
        )
    if when <= datetime.now(UTC):
        raise Refused(
            400,
            "past_date",
            word(
                bot, guild_id, "rolemenu_end_past_said", when=site_when(bot, guild_id, when)
            ),
        )
    return when


async def wanted_end(bot: Any, guild: Any, menu: Any, payload: dict[str, Any]) -> dict | None:
    """The end a PUT asks for, checked before any write; None when the body names no end field."""
    if not any(key in payload for key in END_FIELDS):
        return None
    source = payload.get("ends_source")
    current = menus.end_source(menu)
    if source is None:
        if current != menus.MARATHON_END or "buffer_days" not in payload:
            raise Refused(
                400,
                "buffer_needs_marathon",
                word(bot, guild.id, "rolemenu_buffer_needs_marathon_said", menu=menu["name"]),
            )
        source = current
    if source not in menus.END_SOURCES:
        raise Refused(
            400,
            "bad_end_source",
            BAD_END_SOURCE.format(given=str(source)[:40], known=", ".join(menus.END_SOURCES)),
        )
    if source == menus.NO_END:
        return {"source": source}
    if source == menus.DATE_END:
        return {"source": source, "ends_at": wanted_moment(bot, guild.id, payload.get("ends_at"))}
    given = payload.get("ends_marathon_id", menu_value(menu, "ends_marathon_id"))
    marathon_id = as_id(given)
    if marathon_id is None or await marathon_row(bot.db, guild.id, marathon_id) is None:
        raise Refused(
            400, "no_such_marathon", word(bot, guild.id, "rolemenu_end_no_marathon_said")
        )
    if "buffer_days" in payload:
        buffer = wanted_buffer(bot, guild.id, payload.get("buffer_days"))
    else:
        buffer = menu_value(menu, "buffer_days") if current == menus.MARATHON_END else None
    return {"source": source, "marathon_id": marathon_id, "buffer_days": buffer}


def retired(bot: Any, guild_id: int) -> None:
    raise Refused(410, "rolemenu_retired", word(bot, guild_id, ROLEMENU_RETIRED_KEY))


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/rolemenus", tags=["rolemenus"], dependencies=[Depends(staff_dependency(bot))]
    )

    async def one_payload(guild: Any, name: str) -> dict[str, Any]:
        menu, options = await read_menu(bot, guild, name)
        return await menu_payload(bot, guild, menu, options, await members_of(guild))

    @router.get("")
    async def rolemenus_index() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        rows = await list_menus(bot.db, guild.id)
        members = await members_of(guild) if rows else []
        return [
            await menu_payload(bot, guild, menu, await get_options(bot.db, menu["id"]), members)
            for menu in rows
        ]

    @router.get("/marathons")
    async def rolemenu_marathons() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [
            await marathon_choice(bot, guild.id, row)
            for row in await bindable_marathons(bot.db, guild.id)
        ]

    @router.post("/seed")
    async def rolemenu_seed() -> dict[str, Any]:
        retired(bot, require_guild(bot).id)
        return {}

    @router.get("/requests")
    async def rolemenu_requests() -> list[dict[str, Any]]:
        retired(bot, require_guild(bot).id)
        return []

    @router.post("/requests/{request_id}/approve")
    async def request_approve(request_id: int) -> dict[str, Any]:
        retired(bot, require_guild(bot).id)
        return {}

    @router.post("/requests/{request_id}/deny")
    async def request_deny(request_id: int) -> dict[str, Any]:
        retired(bot, require_guild(bot).id)
        return {}

    @router.post("")
    async def rolemenu_create(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        name = str(payload.get("name") or "").strip()
        title = wanted_title(payload.get("title"))
        if not name or not title:
            raise Refused(400, "bad_request", NEEDS_A_NAME)
        description = wanted_description(payload.get("description"))
        menu_id = await make_menu(
            bot,
            guild,
            actor_for(bot, who, guild),
            name,
            title,
            description or None,
            STAFF_MODE,
            via=VIA_WEBSITE,
        )
        if menu_id is None:
            raise Refused(400, "name_taken", NAME_TAKEN.format(name=name))
        return await one_payload(guild, name)

    @router.put("/{name}")
    async def rolemenu_update(
        request: Request, name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Words/roles: one `edit` row; an end: one `end_set` row; retired fields are ignored."""
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, _ = await read_menu(bot, guild, name)
        title = wanted_title(payload.get("title")) if payload.get("title") else None
        description = wanted_description(payload.get("description"))
        wanted = payload.get("options")
        options = wanted_options(bot, guild, wanted) if isinstance(wanted, list) else None
        end = await wanted_end(bot, guild, menu, payload)
        actor = actor_for(bot, who, guild)
        if title is not None or description is not None or options is not None:
            await change_menu(
                bot, guild, actor, name, title=title, description=description, via=VIA_WEBSITE
            )
        if options is not None:
            await sync_options(bot, menu, options)
        if end is not None:
            fresh, _ = await read_menu(bot, guild, name)
            await set_menu_end(bot, guild, actor, fresh, via=VIA_WEBSITE, **end)
        return await one_payload(guild, name)

    @router.post("/{name}/end-now")
    async def rolemenu_end_now(request: Request, name: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, options = await read_menu(bot, guild, name)
        guard = guard_of(bot)
        if guard is not None:
            refuse_guarded(guard.refusal_message())
        details = await end_menu_now(
            bot, guild, actor_for(bot, who, guild), menu, via=VIA_WEBSITE
        )
        if details is None:
            raise Refused(
                409,
                "members_not_loaded",
                word(bot, guild.id, "rolemenu_end_now_not_run_said", menu=name),
            )
        payload = await one_payload(guild, name)
        payload["message"] = word(
            bot,
            guild.id,
            ROLEMENU_ENDED_TEXT_KEY,
            menu=name,
            roles=len(options),
            members=details["members"],
            failures=details["failures"],
        )
        payload["pass"] = {
            key: details[key] for key in ("members", "this_pass", "failures", "passes", "ended")
        }
        return payload

    @router.post("/{name}/end-earlier")
    async def rolemenu_end_earlier(request: Request, name: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, _ = await read_menu(bot, guild, name)
        if not menu_value(menu, "ends_held_at"):
            raise Refused(
                409, "nothing_held", word(bot, guild.id, "rolemenu_no_held_said", menu=name)
            )
        await use_held_end(bot, guild, actor_for(bot, who, guild), menu, via=VIA_WEBSITE)
        return await one_payload(guild, name)

    @router.delete("/{name}")
    async def rolemenu_delete(request: Request, name: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu = await get_menu(bot.db, guild.id, name)
        refused = await delete_refusal(bot, guild, menu, site_when)
        if refused:
            raise Refused(409, "menu_still_ends", refused)
        if not await drop_menu(bot, guild, actor_for(bot, who, guild), name, via=VIA_WEBSITE):
            raise Refused(404, "no_such_menu", NO_SUCH_MENU.format(name=name))
        return {"deleted": True, "name": name}

    @router.post("/{name}/post")
    async def rolemenu_post(name: str) -> dict[str, Any]:
        retired(bot, require_guild(bot).id)
        return {}

    @router.post("/{name}/unpost")
    async def rolemenu_unpost(name: str) -> dict[str, Any]:
        retired(bot, require_guild(bot).id)
        return {}

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

    return router
