from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

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
from .golive import now_iso
from .logkinds import VIA_DISCORD, VIA_WEBSITE, WEB
from .settings_store import PINGS_FAN_ROLE_TEMPLATE

log = logging.getLogger(__name__)

MODE_KEY = "pings_mode"
CREATION_KEY = "pings_fan_role_creation"
TEMPLATE_KEY = "pings_fan_role_template"
UNLINK_KEY = "pings_fan_role_on_unlink"
DELETE_KEY = "pings_fan_role_delete"
EVENTS_NAME_KEY = "pings_events_role_name"
GOLIVE_PING_KEY = "golive_ping_role_id"
EVENTS_PING_KEY = "events_ping_role_id"

SELF = "self"
STAFF = "staff"
AUTO = "auto"
KEEP = "keep"
DELETE = "delete"

ROLE_NAME_LIMIT = 100
STREAMERS_MENU = "streamers"
STREAMERS_TITLE = "Streamer pings"
NOTIFICATIONS_MENU = "notifications"
NOTIFICATIONS_TITLE = "Notifications"
EVENTS_OPTION_LABEL = "Events — go-live and event pings"
EVENTS_OPTION_EMOJI = "🔔"
ROLE_REASON = "Black Bloc pings"

OFF = (
    "Ping roles are turned off right now, so nothing was changed and nobody was pinged. A Lead "
    "turns them on from the dashboard's Go-live tab or with `/settings set-value pings_mode on`."
)
NO_EVENTS_ROLE = (
    "Staff have not set up the Events role yet, so there is nothing to opt in to. Ask an "
    "Auntie/Uncle to run `/pingroles setup`, or to press *Set up the Events role* on the "
    "dashboard's Go-live tab."
)
EVENTS_ROLE_GONE = (
    "The Events role is set to **{role_id}**, and that is not a role in this server any more, so "
    "nothing was changed. Ask an Auntie/Uncle to run `/pingroles setup` again to make a fresh one."
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
NOT_A_STREAMER = (
    "Black Bloc does not know you stream yet, so there is nothing to make a role for. Link your "
    "channel with `/twitch link <your twitch channel name>` first — or ask an Auntie/Uncle to set "
    "one up for you with `/pingroles streamer add`."
)
STAFF_ONLY_CREATION = (
    "Only staff start a streamer's ping role on this server, so nothing was made. Ask an "
    "Auntie/Uncle to run `/pingroles streamer add` for you — or a Lead can change who may with "
    "`/settings set-value pings_fan_role_creation self`."
)
ALREADY_HAS_ONE = (
    "**{name}** already has a ping role — <@&{role_id}>. Nothing was changed; people follow it "
    "with `/pings follow`."
)
NO_FAN_ROLE = (
    "**{name}** has no ping role, so there was nothing to take away. `/pingroles streamer list` "
    "shows who has one."
)
CREATED = (
    "Made **{role}** and put it on the *{menu}* panel. People pick it there, or with `/pings "
    "follow`, and Black Bloc mentions it in front of their go-live announcement. Post the panel "
    "with `/rolemenu post {menu}` if it is not up yet."
)
REUSED = (
    "Used the role **{role}** for **{name}** and put it on the *{menu}* panel. People pick it "
    "there, or with `/pings follow`."
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
SETUP_CREATED = "Made the role **{role}** and pointed go-live and event pings at it."
SETUP_REUSED = "Used the role **{role}** that was already here and pointed both feeds at it."
SETUP_UNCHANGED = "Both feeds already pointed at **{role}**, so nothing was changed."
SETUP_MENU_ADDED = " Put it on the *{menu}* panel — post that with `/rolemenu post {menu}`."
SETUP_MENU_THERE = " It is already on the *{menu}* panel."
SETUP_STILL_OFF = (
    " Ping roles are still off, so nobody can opt in yet — turn them on with `/settings set-value "
    "pings_mode on` or from the dashboard's Go-live tab."
)


@dataclass(frozen=True)
class Outcome:
    ok: bool
    message: str
    role_id: int | None = None
    created: bool = False


def head(via: str) -> str:
    return f"{WEB}." if via == VIA_WEBSITE else ""


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


def display_name(member: Any) -> str:
    return str(getattr(member, "display_name", None) or getattr(member, "name", None) or
               getattr(member, "id", "somebody"))


async def set_fan_role(
    db: Any, guild_id: int, user_id: int, role_id: int, created_by: int | None
) -> None:
    await db.conn.execute(
        "INSERT OR REPLACE INTO golive_fan_roles(guild_id, user_id, role_id, created_at, "
        "created_by) VALUES (?, ?, ?, ?, ?)",
        (int(guild_id), int(user_id), int(role_id), now_iso(), created_by),
    )
    await db.conn.commit()


async def get_fan_role(db: Any, guild_id: int, user_id: int) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM golive_fan_roles WHERE guild_id = ? AND user_id = ?",
        (int(guild_id), int(user_id)),
    )
    return await cur.fetchone()


async def all_fan_roles(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM golive_fan_roles WHERE guild_id = ? ORDER BY created_at, user_id",
        (int(guild_id),),
    )
    return list(await cur.fetchall())


async def forget_fan_role(db: Any, guild_id: int, user_id: int) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM golive_fan_roles WHERE guild_id = ? AND user_id = ?",
        (int(guild_id), int(user_id)),
    )
    await db.conn.commit()
    return cur.rowcount > 0


async def owner_of(db: Any, guild_id: int, role_id: int) -> int | None:
    cur = await db.conn.execute(
        "SELECT user_id FROM golive_fan_roles WHERE guild_id = ? AND role_id = ? LIMIT 1",
        (int(guild_id), int(role_id)),
    )
    row = await cur.fetchone()
    return int(row["user_id"]) if row else None


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


async def wear(
    bot: Any, guild: Any, member: Any, role: Any, *, add: bool, via: str = VIA_DISCORD
) -> str | None:
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
            f"{head(via)}pings.forbidden",
            target=member,
            details={
                "role_id": getattr(role, "id", None),
                "action": "add" if add else "remove",
                "reason": f"{type(exc).__name__}: {exc}",
                "via": via,
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
    staff: bool = False,
    via: str = VIA_DISCORD,
) -> Outcome:
    """The one path that gives a streamer a role of their own, whoever asked for it."""
    if not staff and not is_on(bot, guild.id):
        return Outcome(False, OFF)
    name = display_name(member)
    row = await get_fan_role(bot.db, guild.id, member.id)
    if row is not None and guild.get_role(int(row["role_id"])) is not None:
        return Outcome(
            False, ALREADY_HAS_ONE.format(name=name, role_id=row["role_id"]),
            role_id=int(row["role_id"]),
        )
    role, refusal = existing_role, None
    if role is not None and not assignable(role):
        return Outcome(False, ROLE_UNASSIGNABLE.format(name=role.name))
    if role is None:
        wanted = fan_role_name(bot.store.get(guild.id, TEMPLATE_KEY), name)
        role, refusal = await make_role(guild, wanted)
    if role is None:
        return Outcome(False, refusal or CANNOT_MAKE_ROLE.format(name=name))
    await set_fan_role(bot.db, guild.id, member.id, role.id, by)
    await log_action(
        bot,
        guild,
        f"{head(via)}pings.fan_role_created",
        actor=by,
        target=member,
        details={"role_id": role.id, "role": role.name, "reused": existing_role is not None,
                 "via": via},
    )
    await sync_streamer_menus(bot, guild)
    said = REUSED if existing_role is not None else CREATED
    return Outcome(
        True,
        said.format(role=role.name, name=name, menu=STREAMERS_MENU),
        role_id=int(role.id),
        created=existing_role is None,
    )


async def remove_fan_role(
    bot: Any, guild: Any, user_id: int, *, by: int | None, via: str = VIA_DISCORD
) -> Outcome:
    """Forget a streamer's role, and delete it from the server when the setting says so."""
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
    await forget_fan_role(bot.db, guild.id, user_id)
    await log_action(
        bot,
        guild,
        f"{head(via)}pings.fan_role_removed",
        actor=by,
        target=member if member is not None else int(user_id),
        details={"role_id": role_id, "deleted": deleted, "user_id": int(user_id), "via": via},
    )
    await sync_streamer_menus(bot, guild)
    if role is None:
        return Outcome(True, REMOVED_ALREADY_GONE.format(name=name), role_id=role_id)
    said = REMOVED_DELETED if deleted else REMOVED_KEPT
    return Outcome(True, said.format(name=name, role=role.name), role_id=role_id)


async def on_streamer_left(
    bot: Any, guild: Any, user_id: int, *, by: int | None, via: str = VIA_DISCORD
) -> Outcome | None:
    """`/twitch unlink` and `/golive optout`: keep the role, or drop it, as the setting says."""
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
        f"{head(via)}pings.setup",
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
