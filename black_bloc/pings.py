from __future__ import annotations

import logging
from dataclasses import dataclass
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
from .golive import now_iso
from .logkinds import VIA_DISCORD, kind_via
from .panels import panel_minutes as library_panel_minutes
from .panels import site_page_url as library_site_page_url
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
NOT_A_STREAMER = (
    "Black Bloc does not know you stream yet, so there is nothing to make a role for. Link your "
    "channel first — run `/golive` and press **Link my Twitch channel** — or ask an Auntie/Uncle "
    "to set one up for you from `/pings` ▸ **Streamers…**."
)
STAFF_ONLY_CREATION = (
    "Only staff start a streamer's ping role on this server, so nothing was made. Ask an "
    "Auntie/Uncle to start one for you from `/pings` ▸ **Streamers…** — or a Lead can change who "
    "may with `/settings set-value pings_fan_role_creation self`."
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
    "Post the panel with `/rolemenu post {menu}` if it is not up yet."
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
        kind_via("pings.fan_role_created", via),
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
        kind_via("pings.fan_role_removed", via),
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
FEED_WORDS = {
    BOTH_FEEDS: "Go-live and event pings",
    GOLIVE_FEED: "Go-live pings",
    EVENTS_FEED: "Event pings",
}
FEED_SAID = {
    BOTH_FEEDS: "go-live and event pings",
    GOLIVE_FEED: "go-live pings",
    EVENTS_FEED: "event pings",
}

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
    "Nobody has a ping role yet, so there is nothing to follow. A streamer starts one with "
    "**Start my own ping role**, and staff can start one for anybody from **Streamers…**."
)
NO_SUCH_STREAMER = (
    "**{given}** is not somebody with a ping role here any more, so nothing was changed. Press "
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
FANS_OFF_NONE = "You have no ping role, so there was nothing to take away."
STREAMER_LIST_EMPTY = (
    "Nobody has a ping role on this server yet. Start one for somebody with **Give somebody a "
    "ping role…**, or let a streamer start their own from `/pings`."
)
STREAMER_LINE = "• **{name}** — <@&{role_id}> · {count}"
FOLLOWERS_KNOWN = "{count} follower(s)"
FOLLOWERS_UNKNOWN = "the role is gone from the server"
COUNTS_LINE = "**{streamers}** streamer(s) · **{with_role}** with a role Discord still has"
CAPPED_FOLLOW = "{shown} of {total} — the rest are on the *Streamer pings* panels"
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
)

EVENTS_ADD = "events_add"
EVENTS_DROP = "events_drop"
OWN_ADD = "own_add"
OWN_DROP = "own_drop"
REFRESH = "refresh"
BACK = "back"
STREAMERS = "streamers"
SETUP = "setup"
SETTINGS = "settings"
LOGS = "logs"
CARD_REMOVE = "card_remove"
CARD_REMAKE = "card_remake"
NAMES = "names"
DELETE_TOGGLE = "delete_toggle"

OWN_DROP_QUESTION = (
    "Take your own ping role away? The people who follow you stop being pinged when you go live."
)
OWN_DROP_YES = "Yes, take it away"
CARD_REMOVE_QUESTION = (
    "Take **{name}**'s ping role away? Everybody who followed them simply stops being pinged."
)
CARD_REMOVE_YES = "Yes, take it away"
KEEP_IT = "Keep it"

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


class PanelState(NamedTuple):
    mode_on: bool
    events: tuple[tuple[str, str], ...]
    own_role: bool
    creation: str
    streams: bool
    followed: int
    unfollowed: int


OWN_ADD_MOVE = PanelMove(OWN_ADD, "Start my own ping role", "primary")
OWN_DROP_MOVE = PanelMove(
    OWN_DROP,
    "Take my ping role away",
    "danger",
    question=OWN_DROP_QUESTION,
    yes=OWN_DROP_YES,
)
REFRESH_MOVE = PanelMove(REFRESH, "Refresh")
BACK_MOVE = PanelMove(BACK, "Back")
STREAMERS_MOVE = PanelMove(STREAMERS, "Streamers…", row=3)
SETUP_MOVE = PanelMove(SETUP, "Set up the Events role", row=3)
SETTINGS_MOVE = PanelMove(SETTINGS, "Settings", row=3)
LOGS_MOVE = PanelMove(LOGS, "Logs", row=3)
STAFF_MOVES = (STREAMERS_MOVE, SETUP_MOVE, SETTINGS_MOVE, LOGS_MOVE)
CARD_REMOVE_MOVE = PanelMove(
    CARD_REMOVE, "Remove their ping role", "danger", row=0, yes=CARD_REMOVE_YES
)
CARD_REMAKE_MOVE = PanelMove(CARD_REMAKE, "Make the role again", "primary", row=0)
CARD_BACK_MOVE = PanelMove(BACK, "Back", row=0)

PANEL_MOVES = (
    OWN_ADD_MOVE,
    OWN_DROP_MOVE,
    REFRESH_MOVE,
    BACK_MOVE,
    *STAFF_MOVES,
    CARD_REMOVE_MOVE,
    CARD_REMAKE_MOVE,
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
    return next((row for row in rows or () if int(row["user_id"]) == int(user_id)), None)


def feed_role_id(bot: Any, guild_id: int, feed: str = BOTH_FEEDS) -> int | None:
    if feed == GOLIVE_FEED:
        return bot.store.get(guild_id, GOLIVE_PING_KEY) or None
    if feed == EVENTS_FEED:
        return bot.store.get(guild_id, EVENTS_PING_KEY) or None
    return events_role_id(bot, guild_id)


def events_feeds(bot: Any, guild_id: int) -> tuple[tuple[str, int | None], ...]:
    """I2: one toggle while the two keys agree, two labelled ones once the feeds are split."""
    golive = bot.store.get(guild_id, GOLIVE_PING_KEY) or None
    events = bot.store.get(guild_id, EVENTS_PING_KEY) or None
    if not golive or not events or int(golive) == int(events):
        return ((BOTH_FEEDS, golive or events),)
    return ((GOLIVE_FEED, golive), (EVENTS_FEED, events))


def wear_state(guild: Any, member: Any, role_id: Any) -> str:
    if not role_id:
        return UNSET
    if role_of(guild, role_id) is None:
        return GONE
    return WORN if wears(member, role_id) else NOT_WORN


def panel_state(bot: Any, guild: Any, member: Any, rows: Any, *, streams: bool) -> PanelState:
    found = list(rows or ())
    resolved = [row for row in found if role_of(guild, row["role_id"]) is not None]
    worn = [row for row in resolved if wears(member, row["role_id"])]
    return PanelState(
        mode_on=is_on(bot, guild.id),
        events=tuple(
            (feed, wear_state(guild, member, role_id))
            for feed, role_id in events_feeds(bot, guild.id)
        ),
        own_role=row_for(found, getattr(member, "id", 0)) is not None,
        creation=bot.store.get(guild.id, CREATION_KEY),
        streams=bool(streams),
        followed=len(worn),
        unfollowed=len(resolved) - len(worn),
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


def panel_buttons(state: PanelState, *, staff: bool = False) -> tuple[PanelMove, ...]:
    """The §C table as data — the state is a tuple of booleans, never a status word."""
    found: list[PanelMove] = []
    if state.mode_on:
        found += [
            events_move(feed, wear == WORN)
            for feed, wear in state.events
            if wear in (WORN, NOT_WORN)
        ]
        if state.own_role:
            found.append(OWN_DROP_MOVE)
        elif state.creation != STAFF and state.streams:
            found.append(OWN_ADD_MOVE)
    found.append(REFRESH_MOVE)
    if staff:
        found += list(STAFF_MOVES)
    return tuple(found)


def card_buttons(*, role_gone: bool) -> tuple[PanelMove, ...]:
    """Staff always get the final say: a role somebody tidied away is repairable, not stuck."""
    found = [CARD_REMOVE_MOVE]
    if role_gone:
        found.append(CARD_REMAKE_MOVE)
    found.append(CARD_BACK_MOVE)
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
    mine = [row for row in rows or () if wears(member, row["role_id"])]
    if not mine:
        lines.append(LIST_NONE)
    lines += [
        LIST_ONE.format(name=option_label(guild, row), role_id=row["role_id"]) for row in mine
    ]
    return lines


def streamer_lines(guild: Any, rows: Any) -> list[str]:
    found = list(rows or ())
    if not found:
        return [STREAMER_LIST_EMPTY]
    return [
        STREAMER_LINE.format(
            name=option_label(guild, row),
            role_id=row["role_id"],
            count=followers_word(guild, row["role_id"]),
        )
        for row in found
    ]


def counts_of(rows: Any, guild: Any) -> dict[str, int]:
    found = list(rows or ())
    return {
        "streamers": len(found),
        "with_role": sum(1 for row in found if role_of(guild, row["role_id"]) is not None),
    }


def counts_line(rows: Any, guild: Any) -> str:
    return COUNTS_LINE.format(**counts_of(rows, guild))


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
        details={"role_id": role.id, "streamer_id": int(row["user_id"]), "via": via},
    )
    if add:
        return FOLLOWING.format(role=role.name, name=name)
    return UNFOLLOWED.format(name=name)


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
        return NO_EVENTS_ROLE
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
