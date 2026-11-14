from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from ... import rolegrants as grants
from ... import rolemenus as menus
from ... import timed_roles as timed
from ... import timed_roles_fill as fill
from ... import timed_roles_list as roster
from ...cogs.community.role_menus import (
    ROLEMENU_ENDED_TEXT_KEY,
    MarathonTakenError,
    MenuLimitError,
    add_timed_role,
    attach_marathon,
    bindable_marathons,
    change_menu,
    check_label,
    check_title,
    default_buffer,
    delete_refusal,
    drop_menu,
    drop_timed_role,
    end_label,
    end_menu_now,
    end_now_question,
    end_plan,
    event_name,
    failure_count,
    failure_lines,
    fill_from_schedule,
    fill_preview,
    follow_marathon_end,
    get_menu,
    get_options,
    give_event_role,
    held_is_past,
    local_moment,
    make_event,
    marathon_name_of,
    marathon_row,
    members_of,
    menu_value,
    part_word,
    removable,
    role_labels,
    role_name,
    set_menu_end,
    take_event_role,
    timed_role_refusal,
    use_held_end,
    use_held_question,
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

END_FIELDS = ("ends_source", "ends_marathon_id", "ends_at", "buffer_days")


def site_when(bot: Any, guild_id: int, at: Any) -> str:
    return local_moment(bot, guild_id, at)


def said(bot: Any, guild_id: int, key: str, **fields: Any) -> str:
    return word(bot, guild_id, key, **fields)


def no_such_event(bot: Any, guild_id: int, name: str) -> Refused:
    return Refused(
        404, "no_such_menu", said(bot, guild_id, "rolemenu_no_such_event_said", name=name)
    )


def no_such_marathon(bot: Any, guild_id: int) -> Refused:
    return Refused(404, "no_such_marathon", said(bot, guild_id, "rolemenu_end_no_marathon_said"))


def taken(exc: MarathonTakenError) -> Refused:
    return Refused(409, "marathon_taken", str(exc))


def menu_row(menu: Any) -> dict[str, Any]:
    return {
        "name": menu["name"],
        "title": menu["title"],
        "open": not menu_value(menu, "ended_at"),
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


def site_end_label(bot: Any, guild_id: int, menu: Any, marathon_name: Any) -> str:
    """The end in words with no Discord tokens; a typed date says it has no marathon."""
    label = end_label(bot, guild_id, menu, marathon_name, site_when)
    if menus.end_source(menu) == menus.DATE_END:
        return said(bot, guild_id, "rolemenu_end_date_only_text", end=label)
    return label


async def menu_payload(bot: Any, guild: Any, menu: Any, options: Any) -> dict:
    """One event: its end, who is assigned per role, and the confirms' counts from the plan."""
    row = menu_row(menu)
    is_open = row["open"]
    marathon = await marathon_name_of(bot, guild.id, menu)
    by_role = await timed.assigned_by_role(bot.db, guild.id, menu["id"])
    row["marathon_name"] = marathon
    row["assigned"] = await timed.assigned_people(bot.db, guild.id, menu["id"])
    row["assigned_by_role"] = [
        {
            "role_id": str(one["role_id"]),
            "label": one["label"],
            "count": by_role.get(int(one["role_id"]), 0),
        }
        for one in options
    ]
    row["buffer_default"] = menus.buffer_of({}, default_buffer(bot, guild.id))
    row["end_label"] = site_end_label(bot, guild.id, menu, marathon)
    held = menu_value(menu, "ends_held_at")
    row["held_label"] = site_when(bot, guild.id, held) if held else None
    row["held_past"] = held_is_past(menu)
    following = row["ends_source"] == menus.MARATHON_END and row["ends_marathon_id"] is not None
    row["can_fill"] = bool(is_open and following and options)
    row["can_attach"] = bool(is_open and not following)
    plan = await end_plan(bot, guild, menu) if is_open else None
    row["held_question"] = (
        use_held_question(bot, guild.id, menu, plan, site_when) if is_open else None
    )
    row["end_now_question"] = end_now_question(bot, guild.id, plan) if is_open else None
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
    following = await timed.event_for_marathon(bot.db, guild_id, row["id"])
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "ends_at": row["ends_at"],
        "label": label,
        "event": following["name"] if following is not None else None,
        "event_title": following["title"] if following is not None else None,
    }


def wanted_role(bot: Any, guild: Any, role_id: Any) -> Any:
    role = guild.get_role(as_id(role_id)) if as_id(role_id) is not None else None
    if role is None:
        raise Refused(
            404,
            "no_such_role",
            said(bot, guild.id, "rolemenu_no_such_role_said", role_id=str(role_id)[:40]),
        )
    return role


def within_limits(check: Any, value: Any) -> Any:
    try:
        return check(value)
    except MenuLimitError as exc:
        raise Refused(400, "too_long", str(exc)) from None


def wanted_title(given: Any) -> str:
    return within_limits(check_title, str(given or "").strip())


async def read_menu(bot: Any, guild: Any, name: str) -> tuple[Any, list[Any]]:
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        raise no_such_event(bot, guild.id, name)
    return menu, await get_options(bot.db, menu["id"])


def refuse_ended(bot: Any, guild_id: int, menu: Any) -> None:
    if menu_value(menu, "ended_at"):
        raise Refused(
            409,
            "event_ended",
            said(bot, guild_id, "rolemenu_event_ended_said", menu=event_name(menu)),
        )


def refuse_guard(bot: Any) -> None:
    """A role change is a side effect the HTTP guard cannot see, so the route asks it."""
    guard = guard_of(bot)
    if guard is not None:
        refuse_guarded(guard.refusal_message())


def wanted_buffer(bot: Any, guild_id: int, given: Any) -> int | None:
    """None or blank is the server's default; anything but 0-365 whole days is refused."""
    if given is None or str(given).strip() == "":
        return None
    typed = str(given).strip()
    if isinstance(given, bool) or not typed.isdigit() or int(typed) > menus.BUFFER_MAX:
        raise Refused(
            400, "bad_buffer", said(bot, guild_id, "rolemenu_end_bad_buffer_said", given=typed[:40])
        )
    return int(typed)


def wanted_moment(bot: Any, guild_id: int, given: Any) -> datetime:
    """A typed `YYYY-MM-DD` (23:59 guild-local), `YYYY-MM-DD HH:MM`, or a full ISO moment."""
    text = str(given or "").strip()
    when = menus.typed_end(text, bot.store.get(guild_id, "default_timezone")) or parse_ts(text)
    if when is None:
        raise Refused(
            400, "bad_date", said(bot, guild_id, "rolemenu_end_bad_date_said", given=text[:40])
        )
    if when <= datetime.now(UTC):
        raise Refused(
            400,
            "past_date",
            said(bot, guild_id, "rolemenu_end_past_said", when=site_when(bot, guild_id, when)),
        )
    return when


async def wanted_marathon(bot: Any, guild_id: int, given: Any) -> Any:
    marathon_id = as_id(given)
    found = await marathon_row(bot.db, guild_id, marathon_id) if marathon_id is not None else None
    if found is None:
        raise no_such_marathon(bot, guild_id)
    return found


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
                said(bot, guild.id, "rolemenu_buffer_needs_marathon_said", menu=event_name(menu)),
            )
        source = current
    if source not in menus.END_SOURCES:
        raise Refused(
            400,
            "bad_end_source",
            said(
                bot,
                guild.id,
                "rolemenu_bad_end_source_said",
                given=str(source)[:40],
                known=", ".join(menus.END_SOURCES),
            ),
        )
    if source == menus.NO_END:
        return {"source": source}
    if source == menus.DATE_END:
        return {"source": source, "ends_at": wanted_moment(bot, guild.id, payload.get("ends_at"))}
    marathon = await wanted_marathon(
        bot, guild.id, payload.get("ends_marathon_id", menu_value(menu, "ends_marathon_id"))
    )
    if "buffer_days" in payload:
        buffer = wanted_buffer(bot, guild.id, payload.get("buffer_days"))
    else:
        buffer = menu_value(menu, "buffer_days") if current == menus.MARATHON_END else None
    return {
        "source": source,
        "marathon_id": int(marathon["id"]),
        "buffer_days": buffer,
        "buffer_given": "buffer_days" in payload,
    }


async def write_end(bot: Any, guild: Any, actor: Any, menu: Any, end: dict[str, Any]) -> None:
    """A dated event that starts following a marathon attaches, so an earlier end is held."""
    given = end.pop("buffer_given", False)
    try:
        if end["source"] == menus.MARATHON_END and menus.end_source(menu) != menus.MARATHON_END:
            await follow_marathon_end(bot, guild, actor, menu, end["marathon_id"], via=VIA_WEBSITE)
            fresh = await get_menu(bot.db, guild.id, menu["name"])
            if not (given and end["buffer_days"] is not None) or menu_value(fresh, "ends_held_at"):
                return
            menu = fresh
        await set_menu_end(bot, guild, actor, menu, via=VIA_WEBSITE, **end)
    except MarathonTakenError as exc:
        raise taken(exc) from None


def retired(bot: Any, guild_id: int) -> None:
    raise Refused(410, "rolemenu_retired", word(bot, guild_id, ROLEMENU_RETIRED_KEY))


async def timed_row(bot: Any, guild: Any, row: Any, members: Any) -> dict[str, Any]:
    role_id = int(row["role_id"])
    return {
        "role_id": str(role_id),
        "label": row["label"],
        "emoji": row["emoji"],
        "position": int(row["position"]),
        "role_name": role_name(guild, role_id),
        "wearing": len(menus.wearers(members, [role_id])) if members is not None else None,
        "assigned": await timed.assigned_count(bot.db, guild.id, role_id),
        "removable": removable(guild, role_id),
        "added_by": str(row["added_by"]) if row["added_by"] else None,
        "added_at": row["added_at"],
    }


async def timed_role_id(bot: Any, guild: Any, given: Any) -> int:
    """A role on the server's timed list, or the refusal that says which it is not."""
    role = wanted_role(bot, guild, given)
    if not await timed.is_timed(bot.db, guild.id, role.id):
        raise Refused(
            409,
            "not_timed",
            said(bot, guild.id, "rolemenu_timed_not_listed_said", name=role.name),
        )
    return int(role.id)


def wanted_lines(bot: Any, guild_id: int, payload: dict[str, Any]) -> list[str]:
    typed = roster.lines_of(payload.get("lines"))
    ticked = [f"<@{as_id(one)}>" for one in payload.get("user_ids") or () if as_id(one) is not None]
    lines = typed + [one for one in ticked if one not in typed]
    if not lines:
        raise Refused(400, "nobody_named", said(bot, guild_id, "rolemenu_list_empty_said"))
    if len(lines) > roster.LINES_MAX:
        raise Refused(
            400,
            "list_too_long",
            said(
                bot,
                guild_id,
                "rolemenu_list_too_long_said",
                count=len(lines),
                most=roster.LINES_MAX,
            ),
        )
    return lines


def list_member_row(member: Any, typed: str, note: str | None) -> dict[str, Any]:
    return {
        "user_id": str(member.id),
        "name": str(getattr(member, "display_name", None) or getattr(member, "name", member.id)),
        "typed": typed,
        "note": note,
    }


async def list_preview(
    bot: Any, guild: Any, menu: Any, role_id: int, lines: list[str], remove: bool
) -> dict[str, Any]:
    """Who the lines name, and which of them the save would change; nothing is written."""
    members = list(getattr(guild, "members", ()) or ())
    matched, unmatched = roster.match(members, lines)
    here = {
        int(row["user_id"])
        for row in await timed.event_grants(bot.db, guild.id, menu["id"])
        if int(row["role_id"]) == role_id
    }
    rows, to_save = [], []
    for one in matched:
        user_id = int(one.member.id)
        wears = any(int(r.id) == role_id for r in getattr(one.member, "roles", ()) or ())
        if remove:
            note = None if (user_id in here or wears) else "not_assigned"
        else:
            note = "already" if user_id in here else None
        rows.append(list_member_row(one.member, one.typed, note))
        if note is None:
            to_save.append(str(user_id))
    return {
        "role_id": str(role_id),
        "role_name": role_name(guild, role_id),
        "remove": remove,
        "matched": rows,
        "unmatched": [{"typed": one.typed, "why": one.why} for one in unmatched],
        "to_save": to_save,
    }


def fill_row(bot: Any, guild: Any, line: Any) -> dict[str, Any]:
    names = list(line.unmatched)
    return {
        "part": line.part,
        "part_label": part_word(bot, guild.id, line.part),
        "setting": fill.ROLE_KEYS[line.part],
        "role_id": str(line.role_id) if line.role_id is not None else None,
        "role_name": role_name(guild, line.role_id) if line.role_id is not None else None,
        "timed": line.timed,
        "matched": len(line.matched),
        "missing": len(line.missing),
        "unmatched": names[: fill.NAMES_SHOWN],
        "unmatched_count": len(names),
    }


def build_router(bot: Any) -> APIRouter:
    writer = writer_dependency(bot)
    router = APIRouter(
        prefix="/api/rolemenus", tags=["rolemenus"], dependencies=[Depends(staff_dependency(bot))]
    )

    async def one_payload(guild: Any, name: str) -> dict[str, Any]:
        menu, options = await read_menu(bot, guild, name)
        return await menu_payload(bot, guild, menu, options)

    @router.get("")
    async def rolemenus_index() -> list[dict[str, Any]]:
        """Every event: the open ones soonest end first, then the ended ones, latest first."""
        guild = require_guild(bot)
        require_db(bot)
        rows = [
            *await timed.open_events(bot.db, guild.id),
            *await timed.ended_events(bot.db, guild.id),
        ]
        options = await get_options(bot.db, rows[0]["id"]) if rows else []
        return [await menu_payload(bot, guild, menu, options) for menu in rows]

    @router.get("/marathons")
    async def rolemenu_marathons() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        return [
            await marathon_choice(bot, guild.id, row)
            for row in await bindable_marathons(bot.db, guild.id)
        ]

    @router.get("/timed-roles")
    async def timed_roles_index() -> list[dict[str, Any]]:
        guild = require_guild(bot)
        require_db(bot)
        rows = await timed.listed(bot.db, guild.id)
        members = await members_of(guild) if rows else []
        return [await timed_row(bot, guild, row, members) for row in rows]

    @router.post("/timed-roles")
    async def timed_role_add(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        """Refused by cause: a role Black Bloc could not strip, a `/pings` role, a full list,
        or one already on it — each 409 with its own code and sentence."""
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        role = wanted_role(bot, guild, payload.get("role_id"))
        label = within_limits(check_label, str(payload.get("label") or "").strip())
        refused = await timed_role_refusal(bot, guild, role)
        if refused:
            raise Refused(409, refused[0], refused[1])
        refusal = await add_timed_role(
            bot, guild, actor_for(bot, who, guild), role, label=label or None, via=VIA_WEBSITE
        )
        if refusal:
            raise Refused(409, "already_timed", refusal)
        [row] = [one for one in await timed.listed(bot.db, guild.id) if one["role_id"] == role.id]
        return await timed_row(bot, guild, row, await members_of(guild))

    @router.delete("/timed-roles/{role_id}")
    async def timed_role_drop(request: Request, role_id: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        wanted = as_id(role_id)
        if wanted is None or not await timed.is_timed(bot.db, guild.id, wanted):
            raise Refused(
                404,
                "not_timed",
                said(
                    bot,
                    guild.id,
                    "rolemenu_timed_not_listed_said",
                    name=role_name(guild, wanted) if wanted is not None else role_id[:40],
                ),
            )
        refused = await drop_timed_role(
            bot, guild, actor_for(bot, who, guild), wanted, via=VIA_WEBSITE
        )
        if refused:
            raise Refused(409, "role_assigned", refused)
        return {"removed": True, "role_id": str(wanted)}

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
        """New event: a marathon (its name unless one is typed), or a name and a date, or a name."""
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        actor = actor_for(bot, who, guild)
        marathon = None
        if payload.get("marathon_id") not in (None, ""):
            marathon = await wanted_marathon(bot, guild.id, payload.get("marathon_id"))
        title = wanted_title(payload.get("title")) or (marathon["name"] if marathon else "")
        if not title:
            raise Refused(400, "needs_name", said(bot, guild.id, "rolemenu_event_needs_name_said"))
        ends_at = None
        if marathon is None and str(payload.get("ends_at") or "").strip():
            ends_at = wanted_moment(bot, guild.id, payload.get("ends_at"))
        try:
            menu = await make_event(
                bot,
                guild,
                actor,
                title,
                marathon_id=int(marathon["id"]) if marathon else None,
                ends_at=ends_at,
                via=VIA_WEBSITE,
            )
        except MarathonTakenError as exc:
            raise taken(exc) from None
        except MenuLimitError as exc:
            raise Refused(400, "too_long", str(exc)) from None
        return await one_payload(guild, menu["name"])

    @router.get("/{name}")
    async def rolemenu_one(name: str) -> dict[str, Any]:
        """One event as it stands now: what a confirm reads just before it asks."""
        guild = require_guild(bot)
        require_db(bot)
        return await one_payload(guild, name)

    @router.put("/{name}")
    async def rolemenu_update(
        request: Request, name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """A new name: one `edit` row; an end: one `end_set` row; roles sent here answer 410."""
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, _ = await read_menu(bot, guild, name)
        if "options" in payload:
            raise Refused(410, "options_moved", said(bot, guild.id, "rolemenu_options_moved_said"))
        title = wanted_title(payload.get("title")) if payload.get("title") else None
        end = await wanted_end(bot, guild, menu, payload)
        actor = actor_for(bot, who, guild)
        if title is not None:
            await change_menu(bot, guild, actor, name, title=title, via=VIA_WEBSITE)
        if end is not None:
            fresh, _ = await read_menu(bot, guild, name)
            await write_end(bot, guild, actor, fresh, end)
        return await one_payload(guild, name)

    @router.post("/{name}/attach")
    async def rolemenu_attach(
        request: Request, name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """A dated event starts following a marathon; an earlier end it brings is held."""
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, _ = await read_menu(bot, guild, name)
        refuse_ended(bot, guild.id, menu)
        if menus.end_source(menu) == menus.MARATHON_END:
            raise Refused(
                409,
                "already_follows",
                said(bot, guild.id, "rolemenu_already_follows_said", menu=event_name(menu)),
            )
        marathon = await wanted_marathon(bot, guild.id, payload.get("marathon_id"))
        try:
            await attach_marathon(
                bot, guild, actor_for(bot, who, guild), menu, marathon["id"], via=VIA_WEBSITE
            )
        except MarathonTakenError as exc:
            raise taken(exc) from None
        return await one_payload(guild, name)

    @router.post("/{name}/end-now")
    async def rolemenu_end_now(request: Request, name: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, options = await read_menu(bot, guild, name)
        refuse_guard(bot)
        details = await end_menu_now(bot, guild, actor_for(bot, who, guild), menu, via=VIA_WEBSITE)
        if details is None:
            raise Refused(
                409,
                "members_not_loaded",
                word(bot, guild.id, "rolemenu_end_now_not_run_said", menu=event_name(menu)),
            )
        payload = await one_payload(guild, name)
        payload["message"] = word(
            bot,
            guild.id,
            ROLEMENU_ENDED_TEXT_KEY,
            menu=event_name(menu),
            roles=len(options),
            members=details["members"],
            failures=details["failures"],
        )
        payload["pass"] = {
            key: details[key] for key in ("members", "this_pass", "failures", "passes", "ended")
        }
        payload["pass"]["left"] = failure_lines(
            bot, guild, details["left"], await role_labels(bot.db, guild, menu["id"])
        )
        return payload

    @router.post("/{name}/end-earlier")
    async def rolemenu_end_earlier(request: Request, name: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, _ = await read_menu(bot, guild, name)
        if not menu_value(menu, "ends_held_at"):
            raise Refused(
                409,
                "nothing_held",
                word(bot, guild.id, "rolemenu_no_held_said", menu=event_name(menu)),
            )
        try:
            await use_held_end(bot, guild, actor_for(bot, who, guild), menu, via=VIA_WEBSITE)
        except MarathonTakenError as exc:
            raise taken(exc) from None
        return await one_payload(guild, name)

    @router.delete("/{name}")
    async def rolemenu_delete(request: Request, name: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu = await get_menu(bot.db, guild.id, name)
        if menu is None:
            raise no_such_event(bot, guild.id, name)
        refused = await delete_refusal(bot, guild, menu, site_when)
        if refused:
            raise Refused(409, "menu_still_ends", refused)
        if not await drop_menu(bot, guild, actor_for(bot, who, guild), name, via=VIA_WEBSITE):
            raise no_such_event(bot, guild.id, name)
        return {"deleted": True, "name": name}

    @router.post("/{name}/list/preview")
    async def rolemenu_list_preview(name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Matched and unmatched before anything is written; this call writes and logs nothing."""
        guild = require_guild(bot)
        require_db(bot)
        menu, _ = await read_menu(bot, guild, name)
        remove = bool(payload.get("remove"))
        if not remove:
            refuse_ended(bot, guild.id, menu)
        role_id = await timed_role_id(bot, guild, payload.get("role_id"))
        lines = wanted_lines(bot, guild.id, payload)
        return await list_preview(bot, guild, menu, role_id, lines, remove)

    @router.post("/{name}/list")
    async def rolemenu_list_save(
        request: Request, name: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """The ids the preview matched: given (source `site_list`) or taken off this event."""
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, _ = await read_menu(bot, guild, name)
        remove = bool(payload.get("remove"))
        if not remove:
            refuse_ended(bot, guild.id, menu)
        role_id = await timed_role_id(bot, guild, payload.get("role_id"))
        ids = [as_id(one) for one in payload.get("user_ids") or ()]
        ids = list(dict.fromkeys(one for one in ids if one is not None))
        if not ids:
            raise Refused(400, "nobody_named", said(bot, guild.id, "rolemenu_list_empty_said"))
        if len(ids) > roster.LINES_MAX:
            raise Refused(
                400,
                "list_too_long",
                said(
                    bot,
                    guild.id,
                    "rolemenu_list_too_long_said",
                    count=len(ids),
                    most=roster.LINES_MAX,
                ),
            )
        refuse_guard(bot)
        people = [guild.get_member(one) for one in ids]
        gone = [str(one) for one, member in zip(ids, people, strict=True) if member is None]
        present = [member for member in people if member is not None]
        actor = actor_for(bot, who, guild)
        if remove:
            found = await take_event_role(
                bot, guild, actor, menu, role_id, present, via=VIA_WEBSITE
            )
        else:
            found = await give_event_role(
                bot,
                guild,
                actor,
                menu,
                role_id,
                present,
                source=grants.SITE_LIST,
                via=VIA_WEBSITE,
            )
        counts = {
            key: len(found.get(key, ())) for key in ("given", "had", "already", "refused", "kept")
        }
        return {
            **counts,
            "gone": gone,
            "message": found["said"],
            "event": await one_payload(guild, name),
        }

    @router.get("/{name}/fill")
    async def rolemenu_fill_preview(name: str) -> dict[str, Any]:
        """The schedule's people against the event, per part; nothing is written."""
        guild = require_guild(bot)
        require_db(bot)
        menu, _ = await read_menu(bot, guild, name)
        refuse_no_fill(bot, guild.id, menu)
        lines = await fill_preview(bot, guild, menu)
        return {
            "name": menu["name"],
            "marathon_name": await marathon_name_of(bot, guild.id, menu),
            "lines": [fill_row(bot, guild, line) for line in lines],
            "missing": fill.missing_count(lines),
        }

    @router.post("/{name}/fill")
    async def rolemenu_fill(request: Request, name: str) -> dict[str, Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        menu, _ = await read_menu(bot, guild, name)
        refuse_no_fill(bot, guild.id, menu)
        refuse_guard(bot)
        totals = await fill_from_schedule(
            bot, guild, actor_for(bot, who, guild), menu, via=VIA_WEBSITE
        )
        key = "rolemenu_fill_done_said" if any(totals.values()) else "rolemenu_fill_nothing_said"
        return {
            **totals,
            "message": said(bot, guild.id, key, **totals),
            "event": await one_payload(guild, name),
        }

    @router.post("/{name}/post")
    async def rolemenu_post(name: str) -> dict[str, Any]:
        retired(bot, require_guild(bot).id)
        return {}

    @router.post("/{name}/unpost")
    async def rolemenu_unpost(name: str) -> dict[str, Any]:
        retired(bot, require_guild(bot).id)
        return {}

    @router.post("/{name}/assign")
    async def rolemenu_assign(name: str) -> dict[str, Any]:
        """One member on one event is Give from a list now (`/{name}/list`)."""
        retired(bot, require_guild(bot).id)
        return {}

    def refuse_no_fill(bot_: Any, guild_id: int, menu: Any) -> None:
        refuse_ended(bot_, guild_id, menu)
        if (
            menus.end_source(menu) != menus.MARATHON_END
            or menu_value(menu, "ends_marathon_id") is None
        ):
            raise Refused(
                409,
                "no_marathon",
                said(bot_, guild_id, "rolemenu_no_fill_marathon_said", menu=event_name(menu)),
            )

    return router
