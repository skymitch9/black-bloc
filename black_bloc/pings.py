from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple

from . import rolemenu_panels as panels
from .actionlog import log_action
from .cogs.community.role_menus import (
    OPTIONS_MAX,
    add_option,
    create_menu,
    delete_menu,
    get_menu,
    get_options,
    list_menus,
    remove_option,
)
from .golive import now_iso, parse_ts
from .logkinds import VIA_DISCORD, kind_via
from .panels import KEEP_IT as KEEP_IT
from .panels import panel_minutes as library_panel_minutes
from .panels import site_page_url as library_site_page_url
from .settings_store import PINGS_FAN_ROLE_TEMPLATE, SettingError, coerce_value

log = logging.getLogger(__name__)

MODE_KEY = "pings_mode"
CREATION_KEY = "pings_fan_role_creation"
STALE_DAYS_KEY = "pings_streamer_stale_days"
EMPTY_ROLE_DAYS_KEY = "pings_empty_role_days"
ONBOARDING_MANAGED_KEY = "pings_onboarding_managed"
ONBOARDING_TITLE_KEY = "pings_onboarding_prompt_title"
ONBOARDING_CAP_KEY = "pings_onboarding_option_cap"
RAIDTRAIN_PING_KEY = "raidtrain_ping_role_id"
RAIDTRAIN_ROLE_NAME = "Raid trains"
TEMPLATE_KEY = "pings_fan_role_template"
UNLINK_KEY = "pings_fan_role_on_unlink"
DELETE_KEY = "pings_fan_role_delete"
EVENTS_NAME_KEY = "pings_events_role_name"
GOLIVE_PING_KEY = "golive_ping_role_id"
EVENTS_PING_KEY = "events_ping_role_id"

SELF = "self"
STAFF = "staff"
AUTO = "auto"
FOLLOW = "follow"
KEEP = "keep"
DELETE = "delete"

ROLE_NAME_LIMIT = 100
DUPLICATE_CODE = "duplicate_role"
BLANK_NAME_CODE = "blank_role_name"
ROLE_GONE_CODE = "fan_role_gone"
SPOTLIGHT_REF = "spotlight:"
SPOTLIGHT_WORD = "channel"
FAN_ROLE_SELECT = (
    "SELECT r.*, s.twitch_login AS spotlight_login, s.display_name AS spotlight_name "
    "FROM golive_fan_roles r LEFT JOIN spotlight_channels s ON s.id = r.spotlight_id"
)
STREAMERS_MENU = "streamers"
STREAMERS_TITLE = "Streamer pings"
NOTIFICATIONS_MENU = "notifications"
NOTIFICATIONS_TITLE = "Notifications"
EVENTS_OPTION_LABEL = "Events — go-live and event pings"
EVENTS_OPTION_EMOJI = "🔔"
ROLE_REASON = "Black Bloc pings"

OFF = (
    "Ping roles are turned off right now, so nothing was changed and nobody was pinged. A Lead "
    "turns them on from the dashboard's Go-live tab, or `/settings` ▸ **Turn a feature back on…**."
)
NO_EVENTS_ROLE = (
    "Staff have not set up the Events role yet, so there is nothing to opt in to. Ask an "
    "Auntie/Uncle to press **Set up the Events role** on `/pings`, or on the dashboard's Go-live "
    "tab."
)
EVENTS_ROLE_GONE = (
    "The Events role is set to **{role_id}**, and that is not a role in this server any more, so "
    "nothing was changed. Ask an Auntie/Uncle to press **Set up the Events role** on `/pings` "
    "again to make a fresh one."
)
FORBIDDEN = (
    "Discord refused the role change, so nothing was changed. Black Bloc needs the Manage Roles "
    "permission and its own role has to sit ABOVE **{role}** in Server Settings ▸ Roles. Ask an "
    "admin to move it up, then try again."
)
CANNOT_MAKE_ROLE = (
    "Discord refused to make the role **{name}**, so nothing was set up. Black Bloc needs the "
    "Manage Roles permission, and a server cannot hold more than 250 roles. Ask an admin to check "
    "both, then run this again."
)
ROLE_UNASSIGNABLE = (
    "Black Bloc cannot hand out **{name}**, so it was not used. That role is either above Black "
    "Bloc's own role in Server Settings ▸ Roles, or managed by another app. Ask an admin to move "
    "Black Bloc's role above it, then try again."
)
DUPLICATE_ROLE = (
    "A role named **{name}** already exists in this server, so nothing was made — pick it as the "
    "existing role, or choose another name."
)
BLANK_ROLE_NAME = (
    "A ping role needs a name, so nothing was made. Type the name the role should have, or pick "
    "one that is already here as the existing role."
)
FAN_ROLE_GONE = (
    "**{name}**'s ping role is set to **{role_id}**, and that is not a role in this server any "
    "more, so there was nothing to rename. Take the ping role away and give them a fresh one."
)
RENAMED = (
    "**{name}**'s ping role is called **{now}** from now on — it was **{was}**. Nobody was added "
    "to it or taken off it, and the *{menu}* panel says the new name."
)
NOT_A_STREAMER = (
    "Black Bloc does not know you stream yet, so there is nothing to make a role for. Link your "
    "channel first — run `/golive` and press **Link my Twitch channel** — or ask an Auntie/Uncle "
    "to set one up for you from `/pings` ▸ **Streamers…**."
)
STAFF_ONLY_CREATION = (
    "Only staff start a streamer's ping role on this server, so nothing was made. Ask an "
    "Auntie/Uncle to start one for you from `/pings` ▸ **Streamers…** — or a Lead can change who "
    "may with `/settings` ▸ **A setting group…** ▸ pings."
)
ALREADY_HAS_ONE = (
    "**{name}** already has a ping role — <@&{role_id}>. Nothing was changed; people follow it "
    "with **Follow a streamer…** on `/pings`."
)
NO_FAN_ROLE = (
    "**{name}** has no ping role, so there was nothing to take away. `/pings` ▸ **Streamers…** "
    "shows who has one."
)
CREATED = (
    "Made **{role}** and put it on the *{menu}* panel. People pick it there, or with **Follow a "
    "streamer…** on `/pings`, and Black Bloc mentions it in front of their go-live announcement. "
    "Open `/rolemenu`, pick *{menu}* and press **Post it** if it is not up yet."
)
REUSED = (
    "Used the role **{role}** for **{name}** and put it on the *{menu}* panel. People pick it "
    "there, or with **Follow a streamer…** on `/pings`."
)
REMOVED_KEPT = (
    "**{name}** no longer has a ping role here, and the Discord role **{role}** was left on the "
    "server for you to tidy up. Nobody was announced differently in the meantime."
)
REMOVED_DELETED = (
    "**{name}** no longer has a ping role, and the Discord role **{role}** is gone from the "
    "server. Everybody who followed them simply stops being pinged."
)
REMOVED_ALREADY_GONE = (
    "**{name}** no longer has a ping role here. The Discord role had already been deleted by "
    "hand, so there was nothing to take off the server."
)
CREATED_CHANNEL = (
    "Made **{role}** for the channel **{name}**. People pick it with **Follow a streamer…** on "
    "`/pings`, and Black Bloc mentions it in front of that channel's spotlight announcement."
)
REUSED_CHANNEL = (
    "Used the role **{role}** for the channel **{name}**. People pick it with **Follow a "
    "streamer…** on `/pings`, and it is mentioned in front of that channel's announcement."
)
NO_SUCH_SPOTLIGHT = (
    "**{given}** is not a spotlighted channel on this server, so nothing was changed. The "
    "Go-live page's Streamers list shows which channels are spotlighted."
)
SETUP_CREATED = "Made the role **{role}** and pointed go-live and event pings at it."
SETUP_REUSED = "Used the role **{role}** that was already here and pointed both feeds at it."
SETUP_UNCHANGED = "Both feeds already pointed at **{role}**, so nothing was changed."
SETUP_MENU_ADDED = " Put it on the *{menu}* panel — `/rolemenu` ▸ *{menu}* ▸ **Post it**."
SETUP_MENU_THERE = " It is already on the *{menu}* panel."
SETUP_STILL_OFF = (
    " Ping roles are still off, so nobody can opt in yet — turn them on with `/settings` ▸ "
    "pings_mode on` or from the dashboard's Go-live tab."
)


@dataclass(frozen=True)
class Outcome:
    ok: bool
    message: str
    role_id: int | None = None
    created: bool = False
    code: str = ""


def mode_of(bot: Any, guild_id: int) -> str:
    return bot.store.get(guild_id, MODE_KEY)


def is_on(bot: Any, guild_id: int) -> bool:
    return mode_of(bot, guild_id) == "on"


def fan_role_name(template: Any, name: str) -> str:
    """A streamer's role name from the staff-set template; a broken one falls back, never raises."""
    try:
        found = str(template).format(name=name)
    except Exception as exc:
        log.warning(
            "pings: fan role template %r could not be rendered (%s); using the default",
            template,
            exc,
        )
        found = PINGS_FAN_ROLE_TEMPLATE.format(name=name)
    found = " ".join(found.split())[:ROLE_NAME_LIMIT]
    return found or PINGS_FAN_ROLE_TEMPLATE.format(name=name)[:ROLE_NAME_LIMIT]


def typed_role_name(given: Any) -> str:
    """What Discord will take of a name somebody typed; empty when they typed nothing."""
    return " ".join(str(given or "").split())[:ROLE_NAME_LIMIT]


def display_name(member: Any) -> str:
    return str(getattr(member, "display_name", None) or getattr(member, "name", None) or
               getattr(member, "id", "somebody"))


def is_spotlight(row: Any) -> bool:
    return row_value(row, "spotlight_id") is not None


def spotlight_of(row: Any) -> int | None:
    found = row_value(row, "spotlight_id")
    return None if found is None else int(found)


def spotlight_ref(spotlight_id: Any) -> str:
    return f"{SPOTLIGHT_REF}{int(spotlight_id)}"


def spotlight_from_ref(value: Any) -> int | None:
    """`spotlight:12` out of a select's value; a plain member id reads as None."""
    given = str(value or "")
    if not given.startswith(SPOTLIGHT_REF):
        return None
    rest = given[len(SPOTLIGHT_REF):]
    return int(rest) if rest.isdigit() else None


def spotlight_name(row: Any) -> str:
    """What a spotlight's ping role is named after: its display name, else its Twitch login."""
    return str(
        row_value(row, "spotlight_name")
        or row_value(row, "display_name")
        or row_value(row, "spotlight_login")
        or row_value(row, "twitch_login")
        or spotlight_of(row)
        or ""
    )


async def set_fan_role(
    db: Any,
    guild_id: int,
    user_id: int | None,
    role_id: int,
    created_by: int | None,
    *,
    spotlight_id: int | None = None,
) -> None:
    await db.conn.execute(
        "INSERT OR REPLACE INTO golive_fan_roles(guild_id, user_id, role_id, created_at, "
        "created_by, spotlight_id) VALUES (?, ?, ?, ?, ?, ?)",
        (
            int(guild_id),
            None if user_id is None else int(user_id),
            int(role_id),
            now_iso(),
            created_by,
            None if spotlight_id is None else int(spotlight_id),
        ),
    )
    await db.conn.commit()


async def get_fan_role(db: Any, guild_id: int, user_id: int) -> Any:
    cur = await db.conn.execute(
        f"{FAN_ROLE_SELECT} WHERE r.guild_id = ? AND r.user_id = ?",
        (int(guild_id), int(user_id)),
    )
    return await cur.fetchone()


async def get_spotlight_fan_role(db: Any, guild_id: int, spotlight_id: int) -> Any:
    cur = await db.conn.execute(
        f"{FAN_ROLE_SELECT} WHERE r.guild_id = ? AND r.spotlight_id = ?",
        (int(guild_id), int(spotlight_id)),
    )
    return await cur.fetchone()


async def all_fan_roles(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        f"{FAN_ROLE_SELECT} WHERE r.guild_id = ? ORDER BY r.created_at, r.user_id, r.spotlight_id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def member_fan_roles(db: Any, guild_id: int) -> list[Any]:
    return [row for row in await all_fan_roles(db, guild_id) if not is_spotlight(row)]


async def spotlight_fan_roles(db: Any, guild_id: int) -> list[Any]:
    return [row for row in await all_fan_roles(db, guild_id) if is_spotlight(row)]


async def forget_fan_role(db: Any, guild_id: int, user_id: int) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM golive_fan_roles WHERE guild_id = ? AND user_id = ?",
        (int(guild_id), int(user_id)),
    )
    await db.conn.commit()
    return cur.rowcount > 0


async def forget_spotlight_fan_role(db: Any, guild_id: int, spotlight_id: int) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM golive_fan_roles WHERE guild_id = ? AND spotlight_id = ?",
        (int(guild_id), int(spotlight_id)),
    )
    await db.conn.commit()
    return cur.rowcount > 0


async def owner_of(db: Any, guild_id: int, role_id: int) -> int | None:
    cur = await db.conn.execute(
        "SELECT user_id FROM golive_fan_roles WHERE guild_id = ? AND role_id = ? LIMIT 1",
        (int(guild_id), int(role_id)),
    )
    row = await cur.fetchone()
    return None if row is None or row["user_id"] is None else int(row["user_id"])


async def announced_fan_role(
    bot: Any, guild: Any, user_id: int, *, notice: bool = True
) -> int | None:
    """The role a go-live announcement mentions for this streamer, or None with a log line."""
    if not is_on(bot, guild.id) or not getattr(bot.db, "is_connected", False):
        return None
    row = await get_fan_role(bot.db, guild.id, user_id)
    if row is None:
        return None
    role_id = int(row["role_id"])
    if guild.get_role(role_id) is not None:
        return role_id
    log.warning("pings: fan role %s for %s is not in this server any more", role_id, user_id)
    if not notice:
        return None
    await log_action(
        bot,
        guild,
        "pings.fan_role_missing",
        target=user_id,
        details={"role_id": role_id, "user_id": user_id},
    )
    return None


async def announced_spotlight_fan_role(
    bot: Any, guild: Any, spotlight_id: int, *, notice: bool = True
) -> int | None:
    """What a spotlight announcement mentions for its channel, or None with a log line."""
    if not is_on(bot, guild.id) or not getattr(bot.db, "is_connected", False):
        return None
    row = await get_spotlight_fan_role(bot.db, guild.id, spotlight_id)
    if row is None:
        return None
    role_id = int(row["role_id"])
    if guild.get_role(role_id) is not None:
        return role_id
    log.warning(
        "pings: fan role %s for spotlight %s is not in this server any more",
        role_id,
        spotlight_id,
    )
    if not notice:
        return None
    await log_action(
        bot,
        guild,
        "pings.fan_role_missing",
        target=int(spotlight_id),
        details={
            "role_id": role_id,
            "spotlight_id": int(spotlight_id),
            "spotlight": row_value(row, "spotlight_login"),
        },
    )
    return None


def named_role(guild: Any, name: str) -> Any:
    wanted = str(name or "").casefold().strip()
    if not wanted:
        return None
    for role in getattr(guild, "roles", ()):
        if str(getattr(role, "name", "")).casefold().strip() == wanted:
            return role
    return None


def assignable(role: Any) -> bool:
    check = getattr(role, "is_assignable", None)
    return True if not callable(check) else bool(check())


async def make_role(guild: Any, name: str) -> tuple[Any, str | None]:
    """A fresh, plain, unmentionable role, or (None, the sentence that says why not)."""
    try:
        role = await guild.create_role(
            name=name, mentionable=False, reason=ROLE_REASON
        )
    except Exception as exc:
        log.warning("pings: could not make the role %r — %s: %s", name, type(exc).__name__, exc)
        return None, CANNOT_MAKE_ROLE.format(name=name)
    return role, None


async def wear(bot: Any, guild: Any, member: Any, role: Any, *, add: bool) -> str | None:
    """Put a ping role on somebody or take it off; the sentence to say when Discord refuses."""
    try:
        if add:
            await member.add_roles(role, reason=ROLE_REASON)
        else:
            await member.remove_roles(role, reason=ROLE_REASON)
    except Exception as exc:
        log.warning(
            "pings: could not %s %s for %s — %s: %s",
            "add" if add else "remove",
            getattr(role, "id", role),
            getattr(member, "id", member),
            type(exc).__name__,
            exc,
        )
        await log_action(
            bot,
            guild,
            "pings.forbidden",
            target=member,
            details={
                "role_id": getattr(role, "id", None),
                "action": "add" if add else "remove",
                "reason": f"{type(exc).__name__}: {exc}",
            },
        )
        return FORBIDDEN.format(role=getattr(role, "name", getattr(role, "id", "that role")))
    return None


def menu_name(page: int) -> str:
    return STREAMERS_MENU if page == 0 else f"{STREAMERS_MENU}-{page + 1}"


def menu_title(page: int) -> str:
    return STREAMERS_TITLE if page == 0 else f"{STREAMERS_TITLE} ({page + 1})"


def pages_of(rows: list[Any]) -> list[list[Any]]:
    """Discord shows at most 25 options in one select, so the roles run over onto more menus."""
    if not rows:
        return []
    return [rows[at : at + OPTIONS_MAX] for at in range(0, len(rows), OPTIONS_MAX)]


def option_label(guild: Any, row: Any) -> str:
    role = guild.get_role(int(row["role_id"]))
    if role is not None:
        return str(role.name)
    if is_spotlight(row):
        return spotlight_name(row)
    member = guild.get_member(int(row["user_id"]))
    return display_name(member) if member is not None else str(row["user_id"])


async def sync_streamer_menus(bot: Any, guild: Any) -> list[str]:
    """Rebuild the Streamer pings panels from the fan-role rows; the names that now exist."""
    rows = [row for row in await all_fan_roles(bot.db, guild.id) if guild.get_role(row["role_id"])]
    labelled = sorted(
        ((option_label(guild, row), row) for row in rows), key=lambda pair: pair[0].casefold()
    )
    wanted = pages_of(labelled)
    names = [menu_name(page) for page in range(len(wanted))]
    for page, entries in enumerate(wanted):
        await _fill_menu(bot, guild, menu_name(page), menu_title(page), entries)
    await _drop_spare_menus(bot, guild, keep=set(names))
    for name in names:
        await _refresh(bot, guild, name)
    return names


async def _fill_menu(
    bot: Any, guild: Any, name: str, title: str, entries: list[tuple[str, Any]]
) -> None:
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        await create_menu(bot.db, guild.id, name, title, None, "multiple")
        menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        return
    for existing in await get_options(bot.db, menu["id"]):
        await remove_option(bot.db, menu["id"], existing["role_id"])
    for label, row in entries:
        await add_option(bot.db, menu["id"], int(row["role_id"]), label, None)


async def _drop_spare_menus(bot: Any, guild: Any, *, keep: set[str]) -> None:
    for menu in await list_menus(bot.db, guild.id):
        name = str(menu["name"])
        if name in keep or not (name == STREAMERS_MENU or name.startswith(f"{STREAMERS_MENU}-")):
            continue
        if menu["message_id"]:
            await panels.unpost(bot, menu, None)
        await delete_menu(bot.db, guild.id, name)


async def _refresh(bot: Any, guild: Any, name: str) -> None:
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None or not menu["message_id"]:
        return
    await panels.repost(bot, menu, None)


async def ensure_fan_role(
    bot: Any,
    guild: Any,
    member: Any,
    *,
    by: int | None,
    existing_role: Any = None,
    name: str | None = None,
    staff: bool = False,
    via: str = VIA_DISCORD,
    spotlight: Any = None,
) -> Outcome:
    """The one path that gives a streamer a role of their own, member or channel."""
    if not staff and not is_on(bot, guild.id):
        return Outcome(False, OFF)
    channel = spotlight is not None
    who = spotlight_name(spotlight) if channel else display_name(member)
    held = (
        await get_spotlight_fan_role(bot.db, guild.id, spotlight["id"])
        if channel
        else await get_fan_role(bot.db, guild.id, member.id)
    )
    if held is not None and guild.get_role(int(held["role_id"])) is not None:
        return Outcome(
            False, ALREADY_HAS_ONE.format(name=who, role_id=held["role_id"]),
            role_id=int(held["role_id"]),
        )
    role, refusal = existing_role, None
    if role is not None and not assignable(role):
        return Outcome(False, ROLE_UNASSIGNABLE.format(name=role.name))
    reused = role is not None
    if role is None and name is not None:
        wanted = typed_role_name(name)
        if not wanted:
            return Outcome(False, BLANK_ROLE_NAME, code=BLANK_NAME_CODE)
        if named_role(guild, wanted) is not None:
            return Outcome(False, DUPLICATE_ROLE.format(name=wanted), code=DUPLICATE_CODE)
        role, refusal = await make_role(guild, wanted)
    elif role is None:
        wanted = fan_role_name(bot.store.get(guild.id, TEMPLATE_KEY), who)
        there = named_role(guild, wanted)
        if there is not None and assignable(there):
            role, reused = there, True
        else:
            role, refusal = await make_role(guild, wanted)
    if role is None:
        return Outcome(False, refusal or CANNOT_MAKE_ROLE.format(name=who))
    await set_fan_role(
        bot.db,
        guild.id,
        None if channel else member.id,
        role.id,
        by,
        spotlight_id=spotlight["id"] if channel else None,
    )
    details = {"role_id": role.id, "role": role.name, "reused": reused, "via": via}
    if channel:
        details |= {
            "spotlight_id": int(spotlight["id"]),
            "spotlight": str(spotlight["twitch_login"]),
        }
    await log_action(
        bot,
        guild,
        kind_via("pings.fan_role_created", via),
        actor=by,
        target=int(spotlight["id"]) if channel else member,
        details=details,
    )
    await sync_streamer_menus(bot, guild)
    if channel:
        said = REUSED_CHANNEL if reused else CREATED_CHANNEL
    else:
        said = REUSED if reused else CREATED
    return Outcome(
        True,
        said.format(role=role.name, name=who, menu=STREAMERS_MENU),
        role_id=int(role.id),
        created=not reused,
    )


async def rename_fan_role(
    bot: Any,
    guild: Any,
    row: Any,
    name: Any,
    *,
    by: int | None,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The one path that renames a streamer's ping role, member or channel."""
    channel = is_spotlight(row)
    if channel:
        who = spotlight_name(row)
        target: Any = spotlight_of(row)
    else:
        member = guild.get_member(int(row["user_id"]))
        who = display_name(member) if member is not None else str(row["user_id"])
        target = member if member is not None else int(row["user_id"])
    wanted = typed_role_name(name)
    if not wanted:
        return Outcome(False, BLANK_ROLE_NAME, code=BLANK_NAME_CODE)
    role_id = int(row["role_id"])
    role = guild.get_role(role_id)
    if role is None:
        return Outcome(
            False, FAN_ROLE_GONE.format(name=who, role_id=role_id), code=ROLE_GONE_CODE
        )
    if not assignable(role):
        return Outcome(False, ROLE_UNASSIGNABLE.format(name=role.name))
    clash = named_role(guild, wanted)
    if clash is not None and int(clash.id) != role_id:
        return Outcome(False, DUPLICATE_ROLE.format(name=wanted), code=DUPLICATE_CODE)
    was = str(role.name)
    try:
        await role.edit(name=wanted, reason=ROLE_REASON)
    except Exception as exc:
        log.warning(
            "pings: could not rename the role %s — %s: %s", role_id, type(exc).__name__, exc
        )
        return Outcome(False, FORBIDDEN.format(role=was))
    details: dict[str, Any] = {"role_id": role_id, "from": was, "to": wanted, "via": via}
    if channel:
        details |= {
            "spotlight_id": int(spotlight_of(row)),
            "spotlight": str(row_value(row, "spotlight_login") or ""),
        }
    else:
        details["user_id"] = int(row["user_id"])
    await log_action(
        bot,
        guild,
        kind_via("pings.fan_role_renamed", via),
        actor=by,
        target=target,
        details=details,
    )
    await sync_streamer_menus(bot, guild)
    return Outcome(
        True,
        RENAMED.format(name=who, was=was, now=wanted, menu=STREAMERS_MENU),
        role_id=role_id,
    )


async def remove_fan_role(
    bot: Any,
    guild: Any,
    user_id: int | None = None,
    *,
    by: int | None,
    via: str = VIA_DISCORD,
    spotlight: Any = None,
    because: str = "",
) -> Outcome:
    """Forget a streamer's role, and delete it from the server when the setting says so."""
    channel = spotlight is not None
    if channel:
        row = await get_spotlight_fan_role(bot.db, guild.id, spotlight["id"])
        member = None
        name = spotlight_name(spotlight)
    else:
        row = await get_fan_role(bot.db, guild.id, user_id)
        member = guild.get_member(int(user_id))
        name = display_name(member) if member is not None else str(user_id)
    if row is None:
        return Outcome(False, NO_FAN_ROLE.format(name=name))
    role_id = int(row["role_id"])
    role = guild.get_role(role_id)
    deleted = False
    if role is not None and bot.store.get(guild.id, DELETE_KEY):
        try:
            await role.delete(reason=ROLE_REASON)
            deleted = True
        except Exception as exc:
            log.warning(
                "pings: could not delete the role %s — %s: %s", role_id, type(exc).__name__, exc
            )
    details: dict[str, Any] = {"role_id": role_id, "deleted": deleted, "via": via}
    if because:
        details["because"] = because
    if channel:
        await forget_spotlight_fan_role(bot.db, guild.id, spotlight["id"])
        details |= {
            "spotlight_id": int(spotlight["id"]),
            "spotlight": str(spotlight["twitch_login"]),
        }
    else:
        await forget_fan_role(bot.db, guild.id, user_id)
        details["user_id"] = int(user_id)
    await log_action(
        bot,
        guild,
        kind_via("pings.fan_role_removed", via),
        actor=by,
        target=(
            int(spotlight["id"])
            if channel
            else (member if member is not None else int(user_id))
        ),
        details=details,
    )
    await sync_streamer_menus(bot, guild)
    if role is None:
        return Outcome(True, REMOVED_ALREADY_GONE.format(name=name), role_id=role_id)
    said = REMOVED_DELETED if deleted else REMOVED_KEPT
    return Outcome(True, said.format(name=name, role=role.name), role_id=role_id)


async def on_streamer_left(
    bot: Any, guild: Any, user_id: int, *, by: int | None, via: str = VIA_DISCORD
) -> Outcome | None:
    """`/golive`'s Unlink and opt-out buttons: keep the role, or drop it, as the setting says."""
    if bot.store.get(guild.id, UNLINK_KEY) != DELETE:
        return None
    if await get_fan_role(bot.db, guild.id, user_id) is None:
        return None
    return await remove_fan_role(bot, guild, user_id, by=by, via=via)


async def maybe_auto_create(
    bot: Any, guild: Any, member: Any, *, by: int | None, via: str = VIA_DISCORD
) -> Outcome | None:
    """A linked Twitch channel makes a ping role only while the setting asks for it."""
    if bot.store.get(guild.id, CREATION_KEY) != AUTO or not is_on(bot, guild.id):
        return None
    if await get_fan_role(bot.db, guild.id, member.id) is not None:
        return None
    return await ensure_fan_role(bot, guild, member, by=by, via=via)


def events_role_id(bot: Any, guild_id: int) -> int | None:
    return bot.store.get(guild_id, GOLIVE_PING_KEY) or bot.store.get(guild_id, EVENTS_PING_KEY)


async def ensure_notifications_menu(bot: Any, guild: Any, role: Any) -> bool:
    """Put the Events role on its own panel; True when the option was not already there."""
    menu = await get_menu(bot.db, guild.id, NOTIFICATIONS_MENU)
    if menu is None:
        await create_menu(
            bot.db, guild.id, NOTIFICATIONS_MENU, NOTIFICATIONS_TITLE, None, "multiple"
        )
        menu = await get_menu(bot.db, guild.id, NOTIFICATIONS_MENU)
    if menu is None:
        return False
    already = any(row["role_id"] == role.id for row in await get_options(bot.db, menu["id"]))
    await add_option(bot.db, menu["id"], role.id, EVENTS_OPTION_LABEL, EVENTS_OPTION_EMOJI)
    if menu["message_id"]:
        await _refresh(bot, guild, NOTIFICATIONS_MENU)
    return not already


async def setup_events_role(
    bot: Any, guild: Any, *, by: int | None, role: Any = None, via: str = VIA_DISCORD
) -> Outcome:
    """Setup, from the slash command or the site: find or make the role, point both feeds."""
    wanted_name = bot.store.get(guild.id, EVENTS_NAME_KEY)
    made = False
    if role is None:
        role = named_role(guild, wanted_name)
    if role is None:
        role, refusal = await make_role(guild, str(wanted_name))
        if role is None:
            return Outcome(False, refusal or CANNOT_MAKE_ROLE.format(name=wanted_name))
        made = True
    if not assignable(role):
        return Outcome(False, ROLE_UNASSIGNABLE.format(name=role.name))
    before = (
        bot.store.get(guild.id, GOLIVE_PING_KEY),
        bot.store.get(guild.id, EVENTS_PING_KEY),
    )
    for key in (GOLIVE_PING_KEY, EVENTS_PING_KEY):
        if bot.store.get(guild.id, key) != role.id:
            await bot.store.set(guild.id, key, int(role.id), by=by)
    added = await ensure_notifications_menu(bot, guild, role)
    await log_action(
        bot,
        guild,
        kind_via("pings.setup", via),
        actor=by,
        details={"role_id": role.id, "role": role.name, "created": made, "via": via},
    )
    if made:
        said = SETUP_CREATED.format(role=role.name)
    elif before == (role.id, role.id):
        said = SETUP_UNCHANGED.format(role=role.name)
    else:
        said = SETUP_REUSED.format(role=role.name)
    said += (SETUP_MENU_ADDED if added else SETUP_MENU_THERE).format(menu=NOTIFICATIONS_MENU)
    if not is_on(bot, guild.id):
        said += SETUP_STILL_OFF
    return Outcome(True, said, role_id=int(role.id), created=made)


PANEL_MINUTES_KEY = "pings_panel_minutes"
PANEL_TITLE = "Your pings"
PANEL_TIMEOUT_FOOTER = "This panel has gone quiet — run /pings again"
SELECT_CAP = 25
SITE_FEATURE = "pings"

GOLIVE_FEED = "golive"
EVENTS_FEED = "events"
BOTH_FEEDS = "both"
RAID_FEED = "raid"
FEED_WORDS = {
    BOTH_FEEDS: "Go-live and event pings",
    GOLIVE_FEED: "Go-live pings",
    EVENTS_FEED: "Event pings",
    RAID_FEED: "Raid-train pings",
}
FEED_SAID = {
    BOTH_FEEDS: "go-live and event pings",
    GOLIVE_FEED: "go-live pings",
    EVENTS_FEED: "event pings",
    RAID_FEED: "raid-train pings",
}
NO_RAID_ROLE = (
    "Staff have not set up the raid-train role yet, so there is nothing to opt in to. Ask an "
    "Auntie/Uncle to press **Set up the raid-train role** on `/pings`."
)

UNSET = "unset"
GONE = "gone"
WORN = "worn"
NOT_WORN = "not_worn"

PANEL_OFF_LINE = (
    "Ping roles are **off** for this server at the moment, so nobody can opt in and nobody is "
    "pinged. A Lead turns them on with **Settings** on this panel, or from the dashboard's "
    "Go-live tab. Anything you already wear can still be taken off."
)
NO_STREAMERS = (
    "Nobody has gone live here yet, so there is nobody to follow. Black Bloc puts somebody on "
    "the streamer list by itself the first time it sees them streaming."
)
NO_SUCH_STREAMER = (
    "**{given}** is not somebody with a ping role here any more, so nothing was changed. Press "
    "**Refresh** and pick again."
)
STAFF_ONLY_FOLLOW = (
    "**{name}** has no ping role yet, and on this server only staff start one, so nothing was "
    "changed. Ask an Auntie/Uncle to start one from `/pings` ▸ **Streamers…** — or a Lead can "
    "change who may with **Settings** on this panel."
)
NOT_ON_THE_LIST_ANY_MORE = (
    "**{given}** is not on this server's streamer list any more, so nothing was changed. Press "
    "**Refresh** and pick again."
)
ALREADY_FOLLOWING = (
    "You already follow **{name}**, so nothing was changed. **Stop following…** stops it."
)
NOT_FOLLOWING = "You do not follow **{name}**, so there was nothing to stop."
FOLLOWING = (
    "Done — you now wear **{role}**, so Black Bloc mentions you when **{name}** goes live. "
    "**Stop following…** stops it."
)
UNFOLLOWED = "Done — you no longer get **{name}**'s go-live pings."
EVENTS_ON = (
    "Done — you now wear **{role}**, so you get {what}. The same button turns them back off."
)
EVENTS_OFF = "Done — you no longer get {what}. The same button puts them back on."
EVENTS_ALREADY_ON = "You already wear **{role}**, so nothing was changed."
EVENTS_ALREADY_OFF = "You do not wear **{role}**, so there was nothing to take off."
LIST_EVENTS_ON = "• {what} — **on** (<@&{role_id}>)"
LIST_EVENTS_OFF = "• {what} — **off**; the button below turns them on"
LIST_EVENTS_UNSET = "• {what} — staff have not set up the Events role yet"
LIST_EVENTS_GONE = (
    "• {what} — the role staff picked (**{role_id}**) is not in this server any more"
)
LIST_NONE = "• You follow no streamers. **Follow a streamer…** picks one."
LIST_ONE = "• **{name}** — <@&{role_id}>"
LIST_YOURS_ON = (
    "• You are **on** the streamer list, so people can follow you from here. **Take me off the "
    "streamer list** takes you off."
)
LIST_YOURS_OFF = (
    "• You are **off** the streamer list, so nobody new can follow you and going live does not "
    "put you back."
)
STREAMERS_CAPPED = "{shown} of {total} — the rest are on the dashboard's Go-live tab"
STREAMERS_CAPPED_MEMBER = "{shown} of {total} — the rest are on Discord's onboarding screen"
FANS_OFF_NONE = "You have no ping role, so there was nothing to take away."
STREAMER_LIST_EMPTY = (
    "Black Bloc has not seen anybody streaming here yet, so the streamer list is empty. Nobody "
    "is added by hand — going live is what puts somebody on it."
)
STREAMER_LINE = "• **{name}** — {listed} · {role} · last live {when}"
LISTED_WORD = "listed"
HIDDEN_WORD = "**hidden**"
NO_ROLE_WORD = "no ping role yet"
FOLLOWERS_KNOWN = "{count} follower(s)"
FOLLOWERS_UNKNOWN = "the role is gone from the server"
COUNTS_LINE = (
    "**{streamers}** streamer(s) seen · **{listed}** on the list · **{with_role}** with a role "
    "Discord still has · **{channels}** spotlighted channel(s) with one"
)
CAPPED_FOLLOW = "{shown} of {total} — the rest are on Discord's onboarding screen"
TEMPLATE_OK = "Saved. A streamer's ping role will be called **{example}**."
TEMPLATE_BROKEN = (
    "Saved, but **{given}** is not something Black Bloc can fill in, so a ping role will be "
    "called **{example}** instead. `{{name}}` is the only field there is."
)
SETTINGS_NOTHING = "Nothing was given, so nothing changed."
SETTINGS_SAVED = "Saved — "
SETTINGS_ONE = "**{key}** is now `{value}`"

SETTINGS_KEYS = (
    MODE_KEY,
    CREATION_KEY,
    UNLINK_KEY,
    DELETE_KEY,
    EVENTS_NAME_KEY,
    TEMPLATE_KEY,
    PANEL_MINUTES_KEY,
    STALE_DAYS_KEY,
    EMPTY_ROLE_DAYS_KEY,
    ONBOARDING_MANAGED_KEY,
    ONBOARDING_TITLE_KEY,
    ONBOARDING_CAP_KEY,
)

EVENTS_ADD = "events_add"
EVENTS_DROP = "events_drop"
OWN_ADD = "own_add"
OWN_DROP = "own_drop"
LIST_OUT = "list_out"
LIST_IN = "list_in"
REFRESH = "refresh"
BACK = "back"
STREAMERS = "streamers"
SETUP = "setup"
RAID_SETUP = "raid_setup"
ONBOARDING = "onboarding"
ONBOARDING_SYNC = "onboarding_sync"
ONBOARDING_STOP = "onboarding_stop"
SETTINGS = "settings"
LOGS = "logs"
CARD_REMOVE = "card_remove"
CARD_REMAKE = "card_remake"
CARD_HIDE = "card_hide"
CARD_RESTORE = "card_restore"
NAMES = "names"
NUMBERS = "numbers"
DELETE_TOGGLE = "delete_toggle"

OWN_DROP_QUESTION = (
    "Take your own ping role away? The people who follow you stop being pinged when you go live."
)
OWN_DROP_YES = "Yes, take it away"
CARD_REMOVE_QUESTION = (
    "Take **{name}**'s ping role away? Everybody who followed them simply stops being pinged."
)
CARD_REMOVE_YES = "Yes, take it away"

EVENTS_ON_LABEL = "Turn event pings on"
EVENTS_OFF_LABEL = "Turn them off"
EVENTS_ON_LABEL_FEED = "Turn {what} on"
EVENTS_OFF_LABEL_FEED = "Turn {what} off"


class PanelMove(NamedTuple):
    action: str
    label: str
    style: str = "secondary"
    row: int = 2
    question: str = ""
    yes: str = ""
    feed: str = ""


LISTED_NEVER = ""
LISTED_ON = "on"
LISTED_OFF = "off"


class PanelState(NamedTuple):
    mode_on: bool
    events: tuple[tuple[str, str], ...]
    own_role: bool
    creation: str
    streams: bool
    followed: int
    unfollowed: int
    listed: str = LISTED_NEVER


MEMBER_ROW = 2
LAST_ROW = 4
PER_ROW = 5

LIST_OUT_QUESTION = (
    "Take yourself off the streamer list? Nobody new can follow you, going live does not put "
    "you back, and your ping role goes too if nobody is wearing it."
)
LIST_OUT_YES = "Yes, take me off"

OWN_ADD_MOVE = PanelMove(OWN_ADD, "Start my own ping role", "primary")
OWN_DROP_MOVE = PanelMove(
    OWN_DROP,
    "Take my ping role away",
    "danger",
    question=OWN_DROP_QUESTION,
    yes=OWN_DROP_YES,
)
LIST_OUT_MOVE = PanelMove(
    LIST_OUT,
    "Take me off the streamer list",
    "danger",
    question=LIST_OUT_QUESTION,
    yes=LIST_OUT_YES,
)
LIST_IN_MOVE = PanelMove(LIST_IN, "Put me back on the list", "success")
REFRESH_MOVE = PanelMove(REFRESH, "Refresh")
BACK_MOVE = PanelMove(BACK, "Back")
STREAMERS_MOVE = PanelMove(STREAMERS, "Streamers…", row=3)
SETUP_MOVE = PanelMove(SETUP, "Set up the Events role", row=3)
RAID_SETUP_MOVE = PanelMove(RAID_SETUP, "Set up the raid-train role", row=3)
ONBOARDING_MOVE = PanelMove(ONBOARDING, "Onboarding…", row=3)
SETTINGS_MOVE = PanelMove(SETTINGS, "Settings", row=3)
LOGS_MOVE = PanelMove(LOGS, "Logs", row=3)
STAFF_MOVES = (
    STREAMERS_MOVE,
    SETUP_MOVE,
    RAID_SETUP_MOVE,
    ONBOARDING_MOVE,
    SETTINGS_MOVE,
    LOGS_MOVE,
)
CARD_REMOVE_MOVE = PanelMove(
    CARD_REMOVE, "Remove their ping role", "danger", row=0, yes=CARD_REMOVE_YES
)
CARD_REMAKE_MOVE = PanelMove(CARD_REMAKE, "Make the role again", "primary", row=0)
CARD_HIDE_MOVE = PanelMove(CARD_HIDE, "Hide them from the list", "danger", row=1)
CARD_RESTORE_MOVE = PanelMove(CARD_RESTORE, "Put them back on the list", "success", row=1)
CARD_BACK_MOVE = PanelMove(BACK, "Back", row=1)
ONBOARDING_SYNC_MOVE = PanelMove(ONBOARDING_SYNC, "Sync now", "primary", row=0)
ONBOARDING_STOP_MOVE = PanelMove(ONBOARDING_STOP, "Stop managing onboarding", "danger", row=0)
ONBOARDING_START_MOVE = PanelMove(ONBOARDING_STOP, "Manage onboarding again", "success", row=0)
ONBOARDING_BACK_MOVE = PanelMove(BACK, "Back", row=0)

PANEL_MOVES = (
    OWN_ADD_MOVE,
    OWN_DROP_MOVE,
    LIST_OUT_MOVE,
    LIST_IN_MOVE,
    REFRESH_MOVE,
    BACK_MOVE,
    *STAFF_MOVES,
    CARD_REMOVE_MOVE,
    CARD_REMAKE_MOVE,
    CARD_HIDE_MOVE,
    CARD_RESTORE_MOVE,
    ONBOARDING_SYNC_MOVE,
    ONBOARDING_STOP_MOVE,
    ONBOARDING_START_MOVE,
)


def role_of(guild: Any, role_id: Any) -> Any:
    return guild.get_role(int(role_id)) if role_id else None


def wears(member: Any, role_id: Any) -> bool:
    return any(role.id == int(role_id) for role in getattr(member, "roles", ()))


def followers_word(guild: Any, role_id: Any) -> str:
    role = role_of(guild, role_id)
    if role is None:
        return FOLLOWERS_UNKNOWN
    return FOLLOWERS_KNOWN.format(count=len(getattr(role, "members", ()) or ()))


def row_for(rows: Any, user_id: Any) -> Any:
    """A spotlight's row has no member, so it never answers to a member id."""
    return next(
        (
            row
            for row in rows or ()
            if row_value(row, "user_id") is not None
            and int(row["user_id"]) == int(user_id)
        ),
        None,
    )


def spotlight_row_for(rows: Any, spotlight_id: Any) -> Any:
    return next(
        (row for row in rows or () if spotlight_of(row) == int(spotlight_id)),
        None,
    )


def streamer_name(guild: Any, row: Any) -> str:
    member = guild.get_member(int(row["user_id"]))
    if member is not None:
        return display_name(member)
    login = row_value(row, "login")
    return str(login) if login else str(row["user_id"])


def followable(guild: Any, member: Any, streamers: Any, roles: Any) -> list[Any]:
    """C4: the select is over the LIST — a streamer with no role yet is offered all the same."""
    mine = int(getattr(member, "id", 0) or 0)
    found = []
    for row in streamers or ():
        user_id = int(row["user_id"])
        if user_id == mine or not row["listed"]:
            continue
        held = row_for(roles, user_id)
        if held is not None and wears(member, held["role_id"]):
            continue
        found.append(row)
    return found


def followable_channels(guild: Any, member: Any, channels: Any, roles: Any) -> list[Any]:
    """The spotlighted channels a member could still follow; one with no role yet is offered."""
    found = []
    for row in channels or ():
        held = spotlight_row_for(roles, row["id"])
        if held is not None and wears(member, held["role_id"]):
            continue
        found.append(row)
    return found


def following(guild: Any, member: Any, roles: Any) -> list[Any]:
    """Stop following… is over the ROLES worn, so it works whatever the list says."""
    return [
        row
        for row in roles or ()
        if role_of(guild, row["role_id"]) is not None and wears(member, row["role_id"])
    ]


def feed_role_id(bot: Any, guild_id: int, feed: str = BOTH_FEEDS) -> int | None:
    if feed == GOLIVE_FEED:
        return bot.store.get(guild_id, GOLIVE_PING_KEY) or None
    if feed == EVENTS_FEED:
        return bot.store.get(guild_id, EVENTS_PING_KEY) or None
    if feed == RAID_FEED:
        return bot.store.get(guild_id, RAIDTRAIN_PING_KEY) or None
    return events_role_id(bot, guild_id)


def events_feeds(bot: Any, guild_id: int) -> tuple[tuple[str, int | None], ...]:
    """I2: one toggle while the two keys agree, two labelled ones once the feeds are split."""
    golive = bot.store.get(guild_id, GOLIVE_PING_KEY) or None
    events = bot.store.get(guild_id, EVENTS_PING_KEY) or None
    if not golive or not events or int(golive) == int(events):
        return ((BOTH_FEEDS, golive or events),)
    return ((GOLIVE_FEED, golive), (EVENTS_FEED, events))


def all_feeds(bot: Any, guild_id: int) -> tuple[tuple[str, int | None], ...]:
    """C4's three toggles: the events half (one button or two) and raid trains beside it."""
    return (*events_feeds(bot, guild_id), (RAID_FEED, feed_role_id(bot, guild_id, RAID_FEED)))


def wear_state(guild: Any, member: Any, role_id: Any) -> str:
    if not role_id:
        return UNSET
    if role_of(guild, role_id) is None:
        return GONE
    return WORN if wears(member, role_id) else NOT_WORN


def listed_state(row: Any) -> str:
    """Never seen streaming is a different thing from seen and taken off, and reads differently."""
    if row is None:
        return LISTED_NEVER
    return LISTED_ON if row["listed"] else LISTED_OFF


def panel_state(
    bot: Any,
    guild: Any,
    member: Any,
    rows: Any,
    *,
    streams: bool,
    streamers: Any = None,
    mine: Any = None,
    channels: Any = None,
) -> PanelState:
    found = list(rows or ())
    resolved = [row for row in found if role_of(guild, row["role_id"]) is not None]
    worn = [row for row in resolved if wears(member, row["role_id"])]
    offered = followable(guild, member, streamers, found) if streamers is not None else []
    offered += followable_channels(guild, member, channels, found)
    return PanelState(
        mode_on=is_on(bot, guild.id),
        events=tuple(
            (feed, wear_state(guild, member, role_id))
            for feed, role_id in all_feeds(bot, guild.id)
        ),
        own_role=row_for(found, getattr(member, "id", 0)) is not None,
        creation=bot.store.get(guild.id, CREATION_KEY),
        streams=bool(streams),
        followed=len(worn),
        unfollowed=len(offered) if streamers is not None else len(resolved) - len(worn),
        listed=listed_state(mine),
    )


def events_move(feed: str, worn: bool) -> PanelMove:
    if feed == BOTH_FEEDS:
        label = EVENTS_OFF_LABEL if worn else EVENTS_ON_LABEL
    else:
        said = (EVENTS_OFF_LABEL_FEED if worn else EVENTS_ON_LABEL_FEED)
        label = said.format(what=FEED_SAID[feed])
    return PanelMove(
        EVENTS_DROP if worn else EVENTS_ADD,
        label,
        "secondary" if worn else "success",
        feed=feed,
    )


def free_slot(moves: Any) -> tuple[int, int]:
    """Where the next button goes: its row, and how many are already on that row."""
    found = list(moves)
    if not found:
        return (MEMBER_ROW, 0)
    last = max(move.row for move in found)
    used = sum(1 for move in found if move.row == last)
    if used < PER_ROW:
        return (last, used)
    return (min(last + 1, LAST_ROW), 0)


def packed(moves: Any, start: int, used: int = 0) -> list[PanelMove]:
    """Discord holds five buttons a row and five rows; the table says the ORDER, not the row."""
    found: list[PanelMove] = []
    row, filled = start, used
    for move in moves:
        if filled >= PER_ROW:
            row, filled = min(row + 1, LAST_ROW), 0
        found.append(move._replace(row=row))
        filled += 1
    return found


def panel_buttons(state: PanelState, *, staff: bool = False) -> tuple[PanelMove, ...]:
    """The §C4 table as data — the state is a tuple of booleans, never a status word.

    Every 'stop' half works whatever the mode: an access-REDUCING move never needs a switch.
    """
    mine: list[PanelMove] = []
    for feed, wear in state.events:
        if wear == WORN:
            mine.append(events_move(feed, True))
        elif wear == NOT_WORN and state.mode_on:
            mine.append(events_move(feed, False))
    if state.mode_on and not state.own_role and state.creation != STAFF and state.streams:
        mine.append(OWN_ADD_MOVE)
    if state.own_role:
        mine.append(OWN_DROP_MOVE)
    if state.listed == LISTED_ON:
        mine.append(LIST_OUT_MOVE)
    elif state.listed == LISTED_OFF and state.mode_on:
        mine.append(LIST_IN_MOVE)
    mine.append(REFRESH_MOVE)
    found = packed(mine, MEMBER_ROW)
    if staff:
        found += packed(STAFF_MOVES, *free_slot(found))
    return tuple(found)


def site_row(moves: Any) -> int:
    return free_slot(moves)[0]


def card_buttons(*, role_gone: bool, listed: str = LISTED_NEVER) -> tuple[PanelMove, ...]:
    """Staff always get the final say: every stored decision here has a move that reverses it."""
    found = [CARD_REMOVE_MOVE]
    if role_gone:
        found.append(CARD_REMAKE_MOVE)
    if listed == LISTED_ON:
        found.append(CARD_HIDE_MOVE)
    elif listed == LISTED_OFF:
        found.append(CARD_RESTORE_MOVE)
    found.append(CARD_BACK_MOVE)
    return tuple(found)


def onboarding_buttons(*, managed: bool, community: bool) -> tuple[PanelMove, ...]:
    """P3: **Sync now** is absent where the write would refuse, and the embed says why."""
    found: list[PanelMove] = []
    if managed and community:
        found.append(ONBOARDING_SYNC_MOVE)
    found.append(ONBOARDING_STOP_MOVE if managed else ONBOARDING_START_MOVE)
    found.append(ONBOARDING_BACK_MOVE)
    return tuple(found)


def notification_lines(
    guild: Any, member: Any, rows: Any, feeds: tuple[tuple[str, int | None], ...]
) -> list[str]:
    lines: list[str] = []
    for feed, role_id in feeds:
        what = FEED_WORDS[feed]
        state = wear_state(guild, member, role_id)
        if state == UNSET:
            lines.append(LIST_EVENTS_UNSET.format(what=what))
        elif state == GONE:
            lines.append(LIST_EVENTS_GONE.format(what=what, role_id=role_id))
        elif state == WORN:
            lines.append(LIST_EVENTS_ON.format(what=what, role_id=role_id))
        else:
            lines.append(LIST_EVENTS_OFF.format(what=what))
    mine = following(guild, member, rows)
    if not mine:
        lines.append(LIST_NONE)
    lines += [
        LIST_ONE.format(name=option_label(guild, row), role_id=row["role_id"]) for row in mine
    ]
    return lines


def listed_line(state: str) -> str | None:
    if state == LISTED_ON:
        return LIST_YOURS_ON
    return LIST_YOURS_OFF if state == LISTED_OFF else None


def streamer_lines(guild: Any, streamers: Any, roles: Any = None) -> list[str]:
    """The staff list is the STREAMER list now; the role is a column on it, not the list."""
    found = list(streamers or ())
    if not found:
        return [STREAMER_LIST_EMPTY]
    lines = []
    for row in found:
        held = row_for(roles, row["user_id"])
        lines.append(
            STREAMER_LINE.format(
                name=streamer_name(guild, row),
                listed=LISTED_WORD if row["listed"] else HIDDEN_WORD,
                role=(
                    f"<@&{held['role_id']}> · {followers_word(guild, held['role_id'])}"
                    if held is not None
                    else NO_ROLE_WORD
                ),
                when=row["last_live_at"],
            )
        )
    return lines


def counts_of(streamers: Any, roles: Any, guild: Any) -> dict[str, int]:
    """A channel's role is counted apart from a person's — the two lists are different sizes."""
    found = list(streamers or ())
    held = [row for row in roles or () if role_of(guild, row["role_id"]) is not None]
    return {
        "streamers": len(found),
        "listed": sum(1 for row in found if row["listed"]),
        "with_role": sum(1 for row in held if not is_spotlight(row)),
        "channels": sum(1 for row in held if is_spotlight(row)),
    }


def counts_line(streamers: Any, roles: Any, guild: Any) -> str:
    return COUNTS_LINE.format(**counts_of(streamers, roles, guild))


def template_preview(template: Any, name: str) -> tuple[str, bool]:
    """What the template will actually produce, and whether it had to fall back (checklist 17)."""
    wanted = fan_role_name(template, name)
    try:
        rendered = " ".join(str(template).format(name=name).split())[:ROLE_NAME_LIMIT]
    except Exception:
        rendered = ""
    return (wanted, wanted != rendered)


def panel_minutes(store: Any, guild_id: int) -> int:
    return library_panel_minutes(store, guild_id, PANEL_MINUTES_KEY)


def site_page_url(origin: Any) -> str | None:
    return library_site_page_url(origin, SITE_FEATURE)


async def follow_streamer(
    bot: Any, guild: Any, member: Any, row: Any, *, add: bool, via: str = VIA_DISCORD
) -> str:
    """One streamer's ping role on or off for one member — one write, one log row."""
    name = option_label(guild, row)
    role = role_of(guild, row["role_id"])
    if role is None:
        return NO_SUCH_STREAMER.format(given=name[:60])
    if wears(member, role.id) == add:
        return (ALREADY_FOLLOWING if add else NOT_FOLLOWING).format(name=name)
    refusal = await wear(bot, guild, member, role, add=add)
    if refusal is not None:
        return refusal
    await log_action(
        bot,
        guild,
        kind_via("pings.follow" if add else "pings.unfollow", via),
        actor=member,
        target=member,
        details={
            "role_id": role.id,
            "streamer_id": (
                spotlight_ref(spotlight_of(row)) if is_spotlight(row) else int(row["user_id"])
            ),
            "via": via,
        },
    )
    if add:
        return FOLLOWING.format(role=role.name, name=name)
    return UNFOLLOWED.format(name=name)


async def follow_from_list(
    bot: Any, guild: Any, member: Any, streamer_id: int, *, via: str = VIA_DISCORD
) -> str:
    """C2: the first follow of a listed streamer is what MAKES their role, and the second does
    not. Everything else about following is `follow_streamer`, unchanged."""
    if not is_on(bot, guild.id):
        return OFF
    listing = await get_streamer(bot.db, guild.id, streamer_id)
    if listing is None or not listing["listed"]:
        return NOT_ON_THE_LIST_ANY_MORE.format(given=str(streamer_id))
    name = streamer_name(guild, listing)
    row = await get_fan_role(bot.db, guild.id, streamer_id)
    if row is None or role_of(guild, row["role_id"]) is None:
        streamer = guild.get_member(int(streamer_id))
        if streamer is None:
            return NO_SUCH_STREAMER.format(given=name[:60])
        if bot.store.get(guild.id, CREATION_KEY) == STAFF:
            return STAFF_ONLY_FOLLOW.format(name=name)
        made = await ensure_fan_role(bot, guild, streamer, by=getattr(member, "id", None), via=via)
        if not made.ok:
            return made.message
        row = await get_fan_role(bot.db, guild.id, streamer_id)
        if row is None:
            return NO_SUCH_STREAMER.format(given=name[:60])
    return await follow_streamer(bot, guild, member, row, add=True, via=via)


async def follow_spotlight(
    bot: Any, guild: Any, member: Any, spotlight: Any, *, via: str = VIA_DISCORD
) -> str:
    """A channel is followed exactly as a person is: the first follow makes the role."""
    if not is_on(bot, guild.id):
        return OFF
    if spotlight is None:
        return NO_SUCH_SPOTLIGHT.format(given="That channel")
    name = spotlight_name(spotlight)
    row = await get_spotlight_fan_role(bot.db, guild.id, spotlight["id"])
    if row is None or role_of(guild, row["role_id"]) is None:
        if bot.store.get(guild.id, CREATION_KEY) == STAFF:
            return STAFF_ONLY_FOLLOW.format(name=name)
        made = await ensure_fan_role(
            bot, guild, None, by=getattr(member, "id", None), via=via, spotlight=spotlight
        )
        if not made.ok:
            return made.message
        row = await get_spotlight_fan_role(bot.db, guild.id, spotlight["id"])
        if row is None:
            return NO_SUCH_SPOTLIGHT.format(given=name[:60])
    return await follow_streamer(bot, guild, member, row, add=True, via=via)


async def set_event_pings(
    bot: Any,
    guild: Any,
    member: Any,
    *,
    add: bool,
    feed: str = BOTH_FEEDS,
    via: str = VIA_DISCORD,
) -> str:
    role_id = feed_role_id(bot, guild.id, feed)
    if not role_id:
        return NO_RAID_ROLE if feed == RAID_FEED else NO_EVENTS_ROLE
    role = role_of(guild, role_id)
    if role is None:
        return EVENTS_ROLE_GONE.format(role_id=role_id)
    if wears(member, role.id) == add:
        return (EVENTS_ALREADY_ON if add else EVENTS_ALREADY_OFF).format(role=role.name)
    refusal = await wear(bot, guild, member, role, add=add)
    if refusal is not None:
        return refusal
    await log_action(
        bot,
        guild,
        kind_via("pings.events_on" if add else "pings.events_off", via),
        actor=member,
        target=member,
        details={"role_id": role.id, "feed": feed, "via": via},
    )
    what = FEED_SAID[feed]
    return EVENTS_ON.format(role=role.name, what=what) if add else EVENTS_OFF.format(what=what)


async def start_own_fan_role(
    bot: Any, guild: Any, member: Any, *, streams: bool, via: str = VIA_DISCORD
) -> Outcome:
    """`streams` is an argument, not a query — the link lives in the go-live cog (§F)."""
    if not is_on(bot, guild.id):
        return Outcome(False, OFF)
    if bot.store.get(guild.id, CREATION_KEY) == STAFF:
        return Outcome(False, STAFF_ONLY_CREATION)
    if not streams:
        return Outcome(False, NOT_A_STREAMER)
    return await ensure_fan_role(bot, guild, member, by=member.id, via=via)


async def stop_own_fan_role(
    bot: Any, guild: Any, member: Any, *, via: str = VIA_DISCORD
) -> Outcome:
    if await get_fan_role(bot.db, guild.id, member.id) is None:
        return Outcome(False, FANS_OFF_NONE)
    return await remove_fan_role(bot, guild, member.id, by=member.id, via=via)


async def save_settings(
    bot: Any, guild: Any, actor: Any, changes: Any, *, via: str = VIA_DISCORD
) -> str:
    """A dict so the panel and any later route write identically; the store keeps the audit."""
    wanted = {key: value for key, value in (changes or {}).items() if key in SETTINGS_KEYS}
    if not wanted:
        return SETTINGS_NOTHING
    for key, value in wanted.items():
        try:
            coerce_value(key, value)
        except SettingError as exc:
            return str(exc)
    by = int(getattr(actor, "id", actor) or 0) or None
    for key, value in wanted.items():
        await bot.store.set(guild.id, key, value, by=by)
    await log_action(
        bot,
        guild,
        kind_via("pings.settings", via),
        actor=actor,
        details={"changed": {key: str(value)[:80] for key, value in wanted.items()}, "via": via},
    )
    return settings_saved(wanted)


def settings_saved(changed: dict[str, Any]) -> str:
    return SETTINGS_SAVED + ", ".join(
        SETTINGS_ONE.format(key=key, value=value) for key, value in changed.items()
    )


# --- the streamer list (C1) ---------------------------------------------------------------------

STREAMER_SEEN = "pings.streamer_seen"
STREAMER_HIDDEN = "pings.streamer_hidden"
STREAMER_RESTORED = "pings.streamer_restored"
STREAMER_PRUNED = "pings.streamer_pruned"
ROLE_PRUNED = "pings.role_pruned"

NOT_ON_THE_LIST = (
    "Black Bloc has never seen you streaming, so you are not on the streamer list and there is "
    "nothing to take you off. You land on it by yourself the first time you go live."
)
ALREADY_HIDDEN = (
    "**{name}** is already off the streamer list, so nothing was changed. **Put me back on the "
    "list** puts them back."
)
ALREADY_LISTED = "**{name}** is already on the streamer list, so nothing was changed."
HIDDEN_SELF = (
    "Done — you are off the streamer list, so nobody new can follow you and going live does not "
    "put you back. **Put me back on the list** is how you come back."
)
HIDDEN_SELF_ROLE_GONE = " Nobody was following you, so your ping role **{role}** is gone too."
HIDDEN_STAFF = (
    "Done — **{name}** is off the streamer list, so nobody new can follow them and going live "
    "does not put them back. **Restore** on this panel puts them back."
)
RESTORED_SELF = (
    "Done — you are back on the streamer list, so people can follow you from `/pings` again."
)
RESTORED_STAFF = "Done — **{name}** is back on the streamer list."
NO_SUCH_LISTING = (
    "**{given}** is not somebody on this server's streamer list, so nothing was changed. Press "
    "**Refresh** and pick again."
)


async def get_streamer(db: Any, guild_id: int, user_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM streamers WHERE guild_id = ? AND user_id = ?",
        (int(guild_id), int(user_id)),
    )
    return await cur.fetchone()


async def all_streamers(db: Any, guild_id: int) -> list[Any]:
    """Everybody Black Bloc has ever seen streaming here, freshest first — hidden ones too."""
    cur = await db.conn.execute(
        "SELECT * FROM streamers WHERE guild_id = ? ORDER BY last_live_at DESC, user_id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def listed_streamers(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM streamers WHERE guild_id = ? AND listed = 1 "
        "ORDER BY last_live_at DESC, user_id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


def row_value(row: Any, name: str, fallback: Any = None) -> Any:
    try:
        found = row[name]
    except (KeyError, IndexError, TypeError):
        return fallback
    return fallback if found is None else found


def hidden_by_hand(row: Any) -> bool:
    """A person took them off; a staleness prune leaves `hidden_by` empty and can be undone."""
    return not row["listed"] and row_value(row, "hidden_by") is not None


async def saw_streaming(
    bot: Any, guild: Any, member: Any, platform: Any = None, login: Any = None
) -> bool:
    """One upsert per go-live. True only the first time somebody lands on the list."""
    if member is None or getattr(member, "bot", False):
        return False
    if not getattr(bot.db, "is_connected", False):
        return False
    when = now_iso()
    row = await get_streamer(bot.db, guild.id, member.id)
    if row is None:
        await bot.db.conn.execute(
            "INSERT INTO streamers(guild_id, user_id, first_live_at, last_live_at, live_count, "
            "platform, login, listed) VALUES (?, ?, ?, ?, 1, ?, ?, 1)",
            (int(guild.id), int(member.id), when, when, platform or None, login or None),
        )
        await bot.db.conn.commit()
        await log_action(
            bot,
            guild,
            STREAMER_SEEN,
            target=member,
            details={"platform": platform, "login": login, "user_id": int(member.id)},
        )
        return True
    relist = 1 if row["listed"] or not hidden_by_hand(row) else 0
    await bot.db.conn.execute(
        "UPDATE streamers SET last_live_at = ?, live_count = live_count + 1, "
        "platform = COALESCE(?, platform), login = COALESCE(?, login), listed = ? "
        "WHERE guild_id = ? AND user_id = ?",
        (when, platform or None, login or None, relist, int(guild.id), int(member.id)),
    )
    await bot.db.conn.commit()
    return False


async def set_listed(
    db: Any, guild_id: int, user_id: int, *, listed: bool, by: int | None
) -> None:
    await db.conn.execute(
        "UPDATE streamers SET listed = ?, hidden_by = ?, hidden_at = ? "
        "WHERE guild_id = ? AND user_id = ?",
        (
            1 if listed else 0,
            None if listed else (int(by) if by is not None else None),
            None if listed else now_iso(),
            int(guild_id),
            int(user_id),
        ),
    )
    await db.conn.commit()


def role_is_worn(guild: Any, role_id: Any) -> bool:
    role = role_of(guild, role_id)
    return role is not None and bool(getattr(role, "members", ()) or ())


async def drop_unworn_fan_role(bot: Any, guild: Any, user_id: int) -> str | None:
    """Delete a streamer's role only while nobody wears it; the role's name, or None."""
    row = await get_fan_role(bot.db, guild.id, user_id)
    if row is None:
        return None
    role = role_of(guild, row["role_id"])
    if role is not None and getattr(role, "members", ()):
        return None
    name = getattr(role, "name", None)
    if role is not None:
        try:
            await role.delete(reason=ROLE_REASON)
        except Exception as exc:
            log.warning(
                "pings: could not delete the unworn role %s — %s: %s",
                row["role_id"],
                type(exc).__name__,
                exc,
            )
            return None
    await forget_fan_role(bot.db, guild.id, user_id)
    await sync_streamer_menus(bot, guild)
    return name


async def hide_streamer(
    bot: Any, guild: Any, user_id: int, *, by: int | None, via: str = VIA_DISCORD
) -> Outcome:
    """The member's own opt-out and staff's hide are one path; staff always get the final say."""
    row = await get_streamer(bot.db, guild.id, user_id)
    member = guild.get_member(int(user_id))
    name = display_name(member) if member is not None else str(user_id)
    mine = by is not None and int(by) == int(user_id)
    if row is None:
        return Outcome(False, NOT_ON_THE_LIST if mine else NO_SUCH_LISTING.format(given=name[:60]))
    if not row["listed"]:
        return Outcome(False, ALREADY_HIDDEN.format(name=name))
    await set_listed(bot.db, guild.id, user_id, listed=False, by=by)
    dropped = await drop_unworn_fan_role(bot, guild, user_id)
    await log_action(
        bot,
        guild,
        kind_via(STREAMER_HIDDEN, via),
        actor=by,
        target=member if member is not None else int(user_id),
        details={"user_id": int(user_id), "role_deleted": dropped, "self": mine, "via": via},
    )
    if not mine:
        return Outcome(True, HIDDEN_STAFF.format(name=name))
    said = HIDDEN_SELF
    if dropped:
        said += HIDDEN_SELF_ROLE_GONE.format(role=dropped)
    return Outcome(True, said)


async def restore_streamer(
    bot: Any, guild: Any, user_id: int, *, by: int | None, via: str = VIA_DISCORD
) -> Outcome:
    row = await get_streamer(bot.db, guild.id, user_id)
    member = guild.get_member(int(user_id))
    name = display_name(member) if member is not None else str(user_id)
    mine = by is not None and int(by) == int(user_id)
    if row is None:
        return Outcome(False, NOT_ON_THE_LIST if mine else NO_SUCH_LISTING.format(given=name[:60]))
    if row["listed"]:
        return Outcome(False, ALREADY_LISTED.format(name=name))
    await set_listed(bot.db, guild.id, user_id, listed=True, by=by)
    await log_action(
        bot,
        guild,
        kind_via(STREAMER_RESTORED, via),
        actor=by,
        target=member if member is not None else int(user_id),
        details={"user_id": int(user_id), "self": mine, "via": via},
    )
    return Outcome(True, RESTORED_SELF if mine else RESTORED_STAFF.format(name=name))


def days_old(when: Any, now: Any, days: Any) -> bool:
    """True once `when` is at least `days` old; an unreadable timestamp is never old enough."""
    stamped = parse_ts(when)
    if stamped is None:
        return False
    return (now - stamped) >= timedelta(days=max(int(days or 0), 0))


async def prune_stale_streamers(bot: Any, guild: Any, *, now: Any = None) -> list[int]:
    """A streamer nobody has seen live for `pings_streamer_stale_days` leaves the list."""
    days = bot.store.get(guild.id, STALE_DAYS_KEY)
    when = now or datetime.now(UTC)
    pruned: list[int] = []
    for row in await listed_streamers(bot.db, guild.id):
        if not days_old(row["last_live_at"], when, days):
            continue
        user_id = int(row["user_id"])
        await set_listed(bot.db, guild.id, user_id, listed=False, by=None)
        dropped = await drop_unworn_fan_role(bot, guild, user_id)
        await log_action(
            bot,
            guild,
            STREAMER_PRUNED,
            target=guild.get_member(user_id) or user_id,
            details={
                "user_id": user_id,
                "days": int(days or 0),
                "last_live_at": row["last_live_at"],
                "role_deleted": dropped,
            },
        )
        pruned.append(user_id)
    return pruned


async def mark_unworn(db: Any, guild_id: int, user_id: int, when: Any) -> None:
    await db.conn.execute(
        "UPDATE golive_fan_roles SET unworn_since = ? WHERE guild_id = ? AND user_id = ?",
        (when, int(guild_id), int(user_id)),
    )
    await db.conn.commit()


async def prune_empty_roles(bot: Any, guild: Any, *, now: Any = None) -> list[int]:
    """A fan role NOBODY wears for `pings_empty_role_days` is deleted; a worn one never is."""
    days = bot.store.get(guild.id, EMPTY_ROLE_DAYS_KEY)
    when = now or datetime.now(UTC)
    stamp = when.isoformat()
    deleted: list[int] = []
    touched = False
    for row in await member_fan_roles(bot.db, guild.id):
        user_id = int(row["user_id"])
        role = role_of(guild, row["role_id"])
        if role is None:
            continue
        if getattr(role, "members", ()):
            if row_value(row, "unworn_since") is not None:
                await mark_unworn(bot.db, guild.id, user_id, None)
            continue
        since = row_value(row, "unworn_since")
        if since is None:
            await mark_unworn(bot.db, guild.id, user_id, stamp)
            continue
        if not days_old(since, when, days):
            continue
        try:
            await role.delete(reason=ROLE_REASON)
        except Exception as exc:
            log.warning(
                "pings: could not prune the role %s — %s: %s",
                row["role_id"],
                type(exc).__name__,
                exc,
            )
            continue
        await forget_fan_role(bot.db, guild.id, user_id)
        touched = True
        await log_action(
            bot,
            guild,
            ROLE_PRUNED,
            target=guild.get_member(user_id) or user_id,
            details={
                "user_id": user_id,
                "role_id": int(row["role_id"]),
                "role": role.name,
                "days": int(days or 0),
                "unworn_since": since,
            },
        )
        deleted.append(user_id)
    if touched:
        await sync_streamer_menus(bot, guild)
    return deleted


async def follower_counts(bot: Any, guild: Any) -> dict[int, int]:
    """How many people wear each streamer's role — what orders the onboarding prompt."""
    found: dict[int, int] = {}
    for row in await member_fan_roles(bot.db, guild.id):
        role = role_of(guild, row["role_id"])
        if role is not None:
            found[int(row["user_id"])] = len(getattr(role, "members", ()) or ())
    return found


async def setup_raidtrain_role(
    bot: Any, guild: Any, *, by: int | None, role: Any = None, via: str = VIA_DISCORD
) -> Outcome:
    """The Events role's sibling: make or reuse one role and point `raidtrain_ping_role_id`."""
    made = False
    if role is None:
        role = named_role(guild, RAIDTRAIN_ROLE_NAME)
    if role is None:
        role, refusal = await make_role(guild, RAIDTRAIN_ROLE_NAME)
        if role is None:
            return Outcome(False, refusal or CANNOT_MAKE_ROLE.format(name=RAIDTRAIN_ROLE_NAME))
        made = True
    if not assignable(role):
        return Outcome(False, ROLE_UNASSIGNABLE.format(name=role.name))
    before = bot.store.get(guild.id, RAIDTRAIN_PING_KEY)
    if before != role.id:
        await bot.store.set(guild.id, RAIDTRAIN_PING_KEY, int(role.id), by=by)
    await log_action(
        bot,
        guild,
        kind_via("pings.raidtrain_setup", via),
        actor=by,
        details={"role_id": role.id, "role": role.name, "created": made, "via": via},
    )
    if made:
        said = RAIDTRAIN_CREATED.format(role=role.name)
    elif before == role.id:
        said = RAIDTRAIN_UNCHANGED.format(role=role.name)
    else:
        said = RAIDTRAIN_REUSED.format(role=role.name)
    if not is_on(bot, guild.id):
        said += SETUP_STILL_OFF
    return Outcome(True, said, role_id=int(role.id), created=made)


RAIDTRAIN_CREATED = (
    "Made the role **{role}** and pointed raid-train pings at it. Members opt in with **Ping me "
    "for raid trains** on `/pings`."
)
RAIDTRAIN_REUSED = (
    "Used the role **{role}** that was already here and pointed raid-train pings at it. Members "
    "opt in with **Ping me for raid trains** on `/pings`."
)
RAIDTRAIN_UNCHANGED = "Raid-train pings already pointed at **{role}**, so nothing was changed."
