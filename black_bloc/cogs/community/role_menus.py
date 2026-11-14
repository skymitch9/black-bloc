from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
from datetime import UTC, datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import rolegrants as grants
from ... import rolemenus as menus
from ... import timed_roles as timed
from ... import timed_roles_by_hand as hand
from ... import timed_roles_fill as fill
from ... import timezones
from ...actionlog import log_action, send_logs
from ...command_errors import NETWORK_ERRORS, AnswersErrors, SafeDynamicItem
from ...command_visibility import STAFF_ONLY
from ...golive import now_iso, parse_ts
from ...logkinds import VIA_DISCORD, kind_via
from ...loops import wait_ready
from ...panels import (
    Panel,
    answer,
    capped_placeholder,
    clamped,
    confirm,
    db_up,
    opened,
    retire,
    still_staff,
)
from ...panels import option_label as select_label
from ...settings_store import (
    DB_UNAVAILABLE,
    GUILD_ONLY,
    ROLEMENU_BY_HAND_CHANNEL_KEY,
    ROLEMENU_BY_HAND_POSTS_KEY,
    ROLEMENU_END_BUFFER_KEY,
    ROLEMENU_END_EARLIER_HOLDS_KEY,
    ROLEMENU_END_FAILURE_LINE_KEY,
    ROLEMENU_END_HELD_TEXT_KEY,
    ROLEMENU_END_MOVED_MINUTES_KEY,
    ROLEMENU_END_MOVED_NOTICE_KEY,
    ROLEMENU_END_MOVED_TEXT_KEY,
    ROLEMENU_END_NOT_KNOWN_KEY,
    ROLEMENU_END_UNBOUND_TEXT_KEY,
    ROLEMENU_ENDED_DM_KEY,
    ROLEMENU_ENDED_NOTICE_KEY,
    ROLEMENU_ENDED_TEXT_KEY,
    ROLEMENU_PICKING_RETIRED_KEY,
    ROLEMENU_PUSH_BACK_REFUSED_KEY,
    ROLEMENU_RETIRED_KEY,
    require_staff,
)

log = logging.getLogger(__name__)

PINGS_ROLE_KEY = "rolemenu_pings_role_said"
MODES = ("multiple", "single", "staff")
STAFF_MODE = "staff"
MODE_KEY = "rolemenu_mode"
APPROVAL_CHANNEL_KEY = "rolemenu_approval_channel_id"
APPROVER_ROLE_KEY = "rolemenu_approver_role_id"
JOY_GAMING = "<:JoyGAMING:1337948924844965931>"

REQUEST_TEMPLATE = r"rolereq:(?P<request_id>[0-9]+):(?P<action>approve|deny)"
EXPIRY_HOURS = 1
LOOP_NAMES = ("expiry",)
UNSET = object()

TITLE_MAX = 256
DESCRIPTION_MAX = 4096
LABEL_MAX = 100
OPTIONS_MAX = 25

SEED: tuple[tuple[str, str, str, tuple[tuple[str, str, int], ...]], ...] = (
    (
        "pronouns",
        "Pronouns",
        "multiple",
        (
            ("❤️", "He/Him", 1285785434131005474),
            ("💙", "She/Her", 1285785449541144607),
            ("💚", "He/They", 1285785451591897108),
            ("🤎", "She/They", 1285785453412220989),
            ("🤍", "They/He", 1285785455199260712),
            ("🧡", "They/She", 1285785456918925362),
            ("💜", "They/Them", 1285785458797711472),
            ("💛", "It/Its", 1285785460647526522),
            ("💞", "Ask my pronouns", 1285786169392762952),
        ),
    ),
    (
        "playstyle",
        "How do you enjoy games",
        "multiple",
        (
            ("🏎️", "Speedrunner", 1285790096536109077),
            ("🛻", "Challenge Runner", 1285790140538683464),
            ("🚋", "Score Attacker", 1285790163380867146),
            ("🚑", "Ranked Gamer", 1285790268192460810),
            ("🚲", "Casual", 1285790198646706286),
        ),
    ),
    (
        "mentoring",
        "Learn or mentor",
        "multiple",
        (
            ("🧙", "Mentor", 1075115919967273000),
            ("🥷", "Initiate", 1075117204447703040),
        ),
    ),
    (
        "interests",
        "Miscellaneous roles",
        "multiple",
        (
            ("🏈", "Sports", 1413642880790167653),
            ("🔢", "Squads", 1413643063145926666),
            ("📺", "Shows", 1413643112965738506),
            ("🎶", "Musichead", 1413643194511659102),
            ("🧑‍🍳", "Foodie", 1413643284064108544),
            ("🎲", "RPGer", 1413643323876573185),
            ("🪅", "Randos", 1456219128921718939),
            ("🍵", "QOTW", 1474849344644710441),
        ),
    ),
    (
        "event-alerts",
        "Event alerts",
        "multiple",
        ((JOY_GAMING, "Marathons", 1515068917628801135),),
    ),
    (
        "runner-status",
        "Runner status",
        STAFF_MODE,
        (
            (None, "Runner", 1285361896383320074),
            (None, "Live Runner", 1285365452666699837),
            (None, "Commentator", 1285361954860437516),
        ),
    ),
)

MODE_ON = (
    "Every menu that has a channel is posted there again in a few seconds. `/rolemenu` stays "
    "where it is either way."
)
MODE_OFF = (
    "The posted panels are taken down in a few seconds. Nobody loses a role, no menu is "
    "changed, and `/rolemenu` stays where it is — press the same button to put them back."
)
NOT_IN_GUILD = (
    "Role menus only work inside the server, and this click did not come from one, so no "
    "roles were changed. Open the panel in a server channel and try again."
)
CANNOT_EDIT_ROLES = (
    "Black Bloc could not change your roles because Discord refused the edit. It needs the "
    "Manage Roles permission and its own role has to sit above every role in this menu in "
    "Server Settings → Roles. Ask an admin to fix that, then click again."
)
PANEL_STUCK = (
    "Black Bloc could not take **{name}**'s panel down, so it is still where it was. It needs to "
    "see that channel and be able to delete its own message there — ask a Lead to check both, "
    "then try again."
)


TOO_LONG = (
    "That {what} is {given} characters and Discord will not show more than {limit}, so nothing "
    "was changed. Shorten it and try again — Black Bloc will not cut down words you typed."
)
TOO_MANY_OPTIONS = (
    "A role menu shows at most {limit} roles and that one would have {given}, so nothing was "
    "changed. Split it into two menus."
)
MENU_IS_GONE = (
    "The menu this panel belongs to has been deleted, so nothing was changed. Ask a Lead to take "
    "the panel down or post a fresh one."
)
NEEDS_APPROVAL_NOTE = (
    "Picking a role here asks staff first — you get a DM either way, and nothing changes until "
    "somebody says yes."
)
EXPIRES_NOTE = "A role from this menu lasts {days} day(s), then Black Bloc takes it back."
CARD_IN_TEST_CHANNEL = (
    " Test mode is on, so the card for staff is in the test channel rather than in the approval "
    "channel."
)
NOT_STAFFS_REQUEST = (
    "That request belongs to somebody else's server, so nothing was changed."
)
MEMBER_HAS_GONE = (
    "**{name}** is not in this server any more, so the role could not be handed over and the "
    "request is still waiting. Deny it if it should be closed."
)
ROLE_REFUSED_AFTER_DECISION = (
    "The request is marked approved, but Discord refused to add **{label}** — Black Bloc needs "
    "Manage Roles and its own role has to sit above it in Server Settings → Roles. Fix that, then "
    "hand it over from `/rolemenu` ▸ **Grants…** ▸ **Give somebody a role…**."
)
BAD_DAYS = (
    "**{given}** is not a number of days, so nothing was decided. Type a whole number, or 0 for a "
    "role that never runs out."
)
GRANT_STARTED_ON_A_ROLE_THEY_HAD = (
    " They already had it, so nothing was added — Black Bloc is only keeping time on it now."
)
CANNOT_ADD = (
    "Discord refused to add **{label}**, so **{name}** was left exactly as they were. Black Bloc "
    "needs Manage Roles and its own role has to sit above that one in Server Settings → Roles."
)
CANNOT_REMOVE = (
    "Discord refused to take **{label}** off **{name}**, so nothing was changed and the timed "
    "role is still open. Black Bloc needs Manage Roles and its own role has to sit above that one."
)
GRANT_ENDED = (
    "**{label}** is off **{name}** and the clock is closed. They were not sent a DM — the log "
    "records who ended it."
)


class MenuLimitError(ValueError):
    """A heading, line, label or option list is longer than Discord will show."""


class MarathonTakenError(MenuLimitError):
    """Another open event already ends with this marathon (one event per marathon)."""


def check_length(what: str, value: str, limit: int) -> str:
    if len(value) > limit:
        raise MenuLimitError(TOO_LONG.format(what=what, given=len(value), limit=limit))
    return value


def check_title(value: Any) -> str:
    return check_length("heading", str(value), TITLE_MAX)


def check_description(value: Any) -> str:
    return check_length("line under the heading", str(value), DESCRIPTION_MAX)


def check_label(value: Any) -> str:
    return check_length("option label", str(value), LABEL_MAX)


def check_option_count(count: int) -> int:
    if count > OPTIONS_MAX:
        raise MenuLimitError(TOO_MANY_OPTIONS.format(limit=OPTIONS_MAX, given=count))
    return count


def picking_is_on(bot: Any, guild_id: int) -> bool:
    """Retired 2026-11-13 (request #17): members pick roles in Discord's Channels & Roles."""
    _ = (bot, guild_id)
    return False


def custom_id_template() -> str:
    return r"rolemenu:(?P<menu_id>[0-9]+)"


def custom_id(menu_id: int) -> str:
    return f"rolemenu:{menu_id}"


def parse_custom_id(value: str) -> int | None:
    prefix, _, rest = value.partition(":")
    if prefix != "rolemenu" or not rest.isdigit():
        return None
    return int(rest)


def role_diff(
    current_ids: Any, menu_ids: Any, selected_ids: Any
) -> tuple[set[int], set[int]]:
    """Roles to add and to remove; only roles the menu owns are ever touched."""
    menu = set(menu_ids)
    selected = set(selected_ids) & menu
    current = set(current_ids)
    return selected - current, (current & menu) - selected


def select_emoji(value: Any) -> Any:
    """Custom emoji are stored as `<:name:id>` and only become a `PartialEmoji` here."""
    if not value:
        return None
    text = str(value)
    if not text.startswith("<"):
        return text
    try:
        partial = discord.PartialEmoji.from_str(text)
    except Exception:
        partial = None
    if partial is None or partial.id is None:
        log.warning("role menu: %r is not an emoji Discord will accept; showing none", text)
        return None
    return partial


def max_values_for(mode: str, option_count: int) -> int:
    if mode == "single":
        return 1
    return max(1, min(option_count, 25))


def summary(added: list[str], removed: list[str]) -> str:
    parts = []
    if added:
        parts.append("Added: " + ", ".join(added))
    if removed:
        parts.append("Removed: " + ", ".join(removed))
    if not parts:
        return "Nothing changed — you already had exactly the roles you picked."
    return " · ".join(parts)


def menu_heading(menu: Any) -> str:
    posted = "posted" if menu["message_id"] else "not posted"
    return f"**{menu['name']}** — {menu['title']} ({menu['mode']}, {posted})"


def option_line(row: Any) -> str:
    return f"{row['emoji'] or '•'} {row['label']} — <@&{row['role_id']}>"


def menu_value(menu: Any, key: str, default: Any = None) -> Any:
    """A column an older row may not carry yet; a fixture shaped like a dict works too."""
    try:
        found = menu[key]
    except (KeyError, IndexError, TypeError):
        return default
    return default if found is None else found


def positive_days(value: Any) -> int | None:
    """Days that mean a real end date; anything else means the role never runs out."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return min(number, grants.DAYS_MAX) if number > 0 else None


def whole_days(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return max(0, min(number, grants.DAYS_MAX))


def needs_approval(menu: Any) -> bool:
    return bool(menu_value(menu, "approval", 0))


def expires_days_of(menu: Any) -> int | None:
    return positive_days(menu_value(menu, "expires_days"))


def retry_days_of(menu: Any) -> int:
    days = whole_days(menu_value(menu, "retry_days", grants.RETRY_DAYS_DEFAULT))
    return grants.RETRY_DAYS_DEFAULT if days is None else days


def panel_note(menu: Any) -> str:
    parts = []
    if needs_approval(menu):
        parts.append(NEEDS_APPROVAL_NOTE)
    days = expires_days_of(menu)
    if days:
        parts.append(EXPIRES_NOTE.format(days=days))
    return " ".join(parts)


def panel_embed(menu: Any, options: Any) -> discord.Embed:
    embed = discord.Embed(title=menu["title"], description=menu["description"] or None)
    lines = [
        f"{row['emoji'] + ' ' if row['emoji'] else ''}{row['label']}" for row in options
    ]
    embed.add_field(name="Roles", value="\n".join(lines) or "none yet", inline=False)
    note = panel_note(menu)
    if note:
        embed.add_field(name="Before you pick", value=note, inline=False)
    return embed


async def dm(user: Any, text: str, embed: discord.Embed | None = None) -> bool:
    """Whether the person actually got told."""
    send = getattr(user, "send", None)
    if send is None:
        return False
    try:
        await send(text, embed=embed, allowed_mentions=discord.AllowedMentions.none())
    except Exception as exc:
        log.info("role menus: could not DM %s: %s", getattr(user, "id", "?"), exc)
        return False
    return True


async def get_menu(db: Any, guild_id: int, name: str) -> Any:
    cur = await db.conn.execute(
        "SELECT * FROM role_menus WHERE guild_id = ? AND name = ?", (guild_id, name)
    )
    return await cur.fetchone()


async def list_menus(db: Any, guild_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM role_menus WHERE guild_id = ? ORDER BY name", (guild_id,)
    )
    return list(await cur.fetchall())


async def posted_menus(db: Any) -> list[Any]:
    cur = await db.conn.execute("SELECT * FROM role_menus WHERE message_id IS NOT NULL")
    return list(await cur.fetchall())


async def unposted_menus(db: Any) -> list[Any]:
    """Menus that remember a channel but have no panel in it right now."""
    cur = await db.conn.execute(
        "SELECT * FROM role_menus WHERE message_id IS NULL AND channel_id IS NOT NULL"
    )
    return list(await cur.fetchall())


async def get_menu_by_id(db: Any, menu_id: int) -> Any:
    cur = await db.conn.execute("SELECT * FROM role_menus WHERE id = ?", (menu_id,))
    return await cur.fetchone()


async def menus_still_to_end(db: Any) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM role_menus WHERE ends_at IS NOT NULL AND ended_at IS NULL ORDER BY id"
    )
    return list(await cur.fetchall())


async def menus_bound_to(db: Any, guild_id: int, marathon_id: int) -> list[Any]:
    cur = await db.conn.execute(
        "SELECT * FROM role_menus WHERE guild_id = ? AND ends_source = ? AND ends_marathon_id = ? "
        "ORDER BY id",
        (int(guild_id), menus.MARATHON_END, int(marathon_id)),
    )
    return list(await cur.fetchall())


async def menus_ending_with(bot: Any, guild: Any, marathon_id: Any) -> list[dict[str, Any]]:
    """The open events that end with this marathon, with their roles and people assigned."""
    bound = [
        one for one in await menus_bound_to(bot.db, guild.id, marathon_id) if not one["ended_at"]
    ]
    if not bound:
        return []
    roles = len(await timed.role_ids(bot.db, guild.id))
    return [
        {
            "name": menu["name"],
            "title": menu["title"],
            "roles": roles,
            "assigned": await timed.assigned_people(bot.db, guild.id, menu["id"]),
        }
        for menu in bound
    ]


async def store_menu_end(
    db: Any,
    menu_id: int,
    *,
    source: str,
    marathon_id: Any,
    buffer_days: Any,
    ends_at: Any,
    by: Any,
) -> None:
    """A new end starts the menu over: nothing has ended, no pass has run, staff know the date."""
    await db.conn.execute(
        "UPDATE role_menus SET ends_source = ?, ends_marathon_id = ?, buffer_days = ?, "
        "ends_at = ?, ends_told_at = ?, ends_set_by = ?, ends_set_at = ?, ended_at = NULL, "
        "end_passes = 0, end_members = 0, end_failures = NULL, ends_held_at = NULL WHERE id = ?",
        (source, marathon_id, buffer_days, ends_at, ends_at, by, now_iso(), int(menu_id)),
    )
    await db.conn.commit()


async def restamp_menu_end(db: Any, menu_id: int, ends_at: Any, *, told: bool) -> None:
    await db.conn.execute(
        "UPDATE role_menus SET ends_at = ?, "
        "ends_told_at = CASE WHEN ? THEN ? ELSE ends_told_at END WHERE id = ?",
        (ends_at, int(told), ends_at, int(menu_id)),
    )
    await db.conn.commit()


async def unbind_menu_end(db: Any, menu_id: int, *, keeps_a_date: bool) -> None:
    await db.conn.execute(
        "UPDATE role_menus SET ends_source = ?, ends_marathon_id = NULL, ends_held_at = NULL "
        "WHERE id = ?",
        (menus.DATE_END if keeps_a_date else menus.NO_END, int(menu_id)),
    )
    await db.conn.commit()


async def record_end_pass(
    db: Any, menu_id: int, passes: int, members: int, *, ended_at: Any, failures: Any
) -> None:
    await db.conn.execute(
        "UPDATE role_menus SET end_passes = ?, end_members = ?, ended_at = ?, end_failures = ? "
        "WHERE id = ?",
        (int(passes), int(members), ended_at, failures, int(menu_id)),
    )
    await db.conn.commit()


async def marathon_row(db: Any, guild_id: int, marathon_id: Any) -> Any:
    try:
        wanted = int(marathon_id)
    except (TypeError, ValueError):
        return None
    cur = await db.conn.execute(
        "SELECT * FROM marathons WHERE id = ? AND guild_id = ?", (wanted, int(guild_id))
    )
    return await cur.fetchone()


async def option_label(db: Any, menu_id: int, role_id: int) -> str | None:
    cur = await db.conn.execute(
        "SELECT t.label FROM timed_roles t JOIN role_menus m ON m.guild_id = t.guild_id "
        "WHERE m.id = ? AND t.role_id = ?",
        (menu_id, role_id),
    )
    row = await cur.fetchone()
    return row["label"] if row is not None else None


def role_name(guild: Any, role_id: Any) -> str:
    role = guild.get_role(int(role_id)) if guild is not None else None
    return str(getattr(role, "name", None) or role_id)


async def label_for(db: Any, guild: Any, menu_id: Any, role_id: Any) -> str:
    """What to call a role: the menu's own wording first, the role's name after it."""
    if menu_id is not None:
        found = await option_label(db, int(menu_id), int(role_id))
        if found:
            return found
    return role_name(guild, role_id)


async def create_menu(
    db: Any,
    guild_id: int,
    name: str,
    title: str,
    description: str | None = None,
    mode: str = "multiple",
    *,
    approval: Any = None,
    expires_days: Any = None,
    retry_days: Any = None,
) -> int | None:
    """The menu's row id, or None when that name is already taken in this guild."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    check_title(title)
    if description is not None:
        check_description(description)
    if await get_menu(db, guild_id, name) is not None:
        return None
    waiting = whole_days(retry_days)
    cur = await db.conn.execute(
        "INSERT INTO role_menus(guild_id, name, title, description, mode, approval, "
        "expires_days, retry_days) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            guild_id,
            name,
            title,
            description,
            mode,
            int(bool(approval)),
            positive_days(expires_days),
            grants.RETRY_DAYS_DEFAULT if waiting is None else waiting,
        ),
    )
    await db.conn.commit()
    return cur.lastrowid


async def update_menu(
    db: Any,
    guild_id: int,
    name: str,
    *,
    title: str | None = None,
    description: Any = None,
    mode: str | None = None,
    approval: Any = None,
    expires_days: Any = UNSET,
    retry_days: Any = None,
) -> bool:
    """Change one menu; whatever is not given is left alone, and `expires_days=None` clears it."""
    menu = await get_menu(db, guild_id, name)
    if menu is None:
        return False
    if mode is not None and mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if title is not None:
        check_title(title)
    if description is not None:
        check_description(description)
    await db.conn.execute(
        "UPDATE role_menus SET title = COALESCE(?, title), description = ?, "
        "mode = COALESCE(?, mode), approval = COALESCE(?, approval), expires_days = ?, "
        "retry_days = COALESCE(?, retry_days) WHERE id = ?",
        (
            title,
            menu["description"] if description is None else (description or None),
            mode,
            None if approval is None else int(bool(approval)),
            (
                expires_days_of(menu)
                if expires_days is UNSET
                else positive_days(expires_days)
            ),
            whole_days(retry_days),
            menu["id"],
        ),
    )
    await db.conn.commit()
    return True


async def delete_menu(db: Any, guild_id: int, name: str) -> bool:
    menu = await get_menu(db, guild_id, name)
    if menu is None:
        return False
    await db.conn.execute(
        "UPDATE role_requests SET status = ?, decided_at = ? WHERE menu_id = ? AND status = ?",
        (grants.WITHDRAWN, now_iso(), menu["id"], grants.PENDING),
    )
    await db.conn.execute("DELETE FROM role_menu_options WHERE menu_id = ?", (menu["id"],))
    await db.conn.execute("DELETE FROM role_menus WHERE id = ?", (menu["id"],))
    await db.conn.commit()
    return True


async def get_options(db: Any, menu_id: int) -> list[Any]:
    """An event's roles: the one timed-role list of its server, shared by every event."""
    cur = await db.conn.execute(
        "SELECT t.* FROM timed_roles t JOIN role_menus m ON m.guild_id = t.guild_id "
        "WHERE m.id = ? ORDER BY t.position, t.role_id",
        (menu_id,),
    )
    return list(await cur.fetchall())


async def add_option(
    db: Any, menu_id: int, role_id: int, label: str, emoji: str | None = None
) -> None:
    check_label(label)
    cur = await db.conn.execute(
        "SELECT position FROM role_menu_options WHERE menu_id = ? AND role_id = ?",
        (menu_id, role_id),
    )
    existing = await cur.fetchone()
    if existing is None:
        cur = await db.conn.execute(
            "SELECT COUNT(*) AS n FROM role_menu_options WHERE menu_id = ?", (menu_id,)
        )
        position = check_option_count((await cur.fetchone())["n"] + 1) - 1
    else:
        position = existing["position"]
    await db.conn.execute(
        "INSERT OR REPLACE INTO role_menu_options(menu_id, role_id, label, emoji, position) "
        "VALUES (?, ?, ?, ?, ?)",
        (menu_id, role_id, label, emoji, position),
    )
    await db.conn.commit()


async def remove_option(db: Any, menu_id: int, role_id: int) -> bool:
    cur = await db.conn.execute(
        "DELETE FROM role_menu_options WHERE menu_id = ? AND role_id = ?", (menu_id, role_id)
    )
    await db.conn.commit()
    return cur.rowcount > 0


async def set_message(db: Any, menu_id: int, channel_id: int, message_id: int) -> None:
    await db.conn.execute(
        "UPDATE role_menus SET channel_id = ?, message_id = ? WHERE id = ?",
        (channel_id, message_id, menu_id),
    )
    await db.conn.commit()


async def clear_message(db: Any, menu_id: int) -> None:
    """Forget the panel, keep the channel it was in."""
    await db.conn.execute(
        "UPDATE role_menus SET message_id = NULL WHERE id = ?", (menu_id,)
    )
    await db.conn.commit()


async def seed_default_menus(db: Any, guild_id: int) -> tuple[list[str], list[str]]:
    """Create the six default menus; names that already exist are left alone."""
    created: list[str] = []
    skipped: list[str] = []
    for name, title, mode, options in SEED:
        menu_id = await create_menu(db, guild_id, name, title, None, mode)
        if menu_id is None:
            skipped.append(name)
            continue
        for emoji, label, role_id in options:
            await add_option(db, menu_id, role_id, label, emoji)
        created.append(name)
    return created, skipped


async def edit_existing(menu: Any, target: Any, embed: discord.Embed, view: Any) -> Any:
    if not menu["message_id"] or menu["channel_id"] != target.id:
        return None
    try:
        message = await target.fetch_message(menu["message_id"])
        await message.edit(embed=embed, view=view)
        return message
    except discord.HTTPException as exc:
        log.info("role menu %s: old panel gone (%s); posting a fresh one", menu["name"], exc)
        return None


async def post_panel(bot: Any, menu: Any, options: Any, target: Any) -> Any:
    """Put one menu's panel in a channel and keep its view alive, for slash and web alike."""
    view = RoleMenuView(menu["id"], options, menu["mode"])
    embed = panel_embed(menu, options)
    message = await edit_existing(menu, target, embed, view)
    if message is None:
        message = await target.send(embed=embed, view=view)
    await set_message(bot.db, menu["id"], target.id, message.id)
    bot.add_view(view, message_id=message.id)
    return message


async def apply_diff(member: Any, guild: Any, to_add: Any, to_remove: Any, reason: str) -> bool:
    """One `member.edit`, keeping every role this menu does not own."""
    keep = [r for r in member.roles if r.id != guild.id and r.id not in to_remove]
    gained = [role for role in (guild.get_role(i) for i in to_add) if role is not None]
    try:
        await member.edit(roles=keep + gained, reason=reason)
    except discord.HTTPException as exc:
        log.warning("role menu: could not edit %s's roles: %s", member.id, exc)
        return False
    return True


async def change_roles(
    bot: Any, member: Any, guild: Any, to_add: Any, to_remove: Any, reason: str
) -> bool:
    """Every role edit Black Bloc makes goes through here, so reconciliation knows it was us."""
    grants.remember_change(bot, guild.id, member.id, to_add, grants.ADDED)
    grants.remember_change(bot, guild.id, member.id, to_remove, grants.REMOVED)
    if await apply_diff(member, guild, to_add, to_remove, reason):
        return True
    grants.forget_change(bot, guild.id, member.id, to_add, grants.ADDED)
    grants.forget_change(bot, guild.id, member.id, to_remove, grants.REMOVED)
    return False


async def audit_actor(guild: Any, member: Any) -> Any:
    """Who changed the roles, when Discord will say; None — never a guess — when it will not."""
    me = getattr(guild, "me", None)
    perms = getattr(me, "guild_permissions", None)
    if perms is None or not getattr(perms, "view_audit_log", False):
        return None
    reader = getattr(guild, "audit_logs", None)
    if reader is None:
        return None
    try:
        async for entry in reader(limit=5, action=discord.AuditLogAction.member_role_update):
            if getattr(getattr(entry, "target", None), "id", None) == member.id:
                return entry.user
    except Exception as exc:
        log.info("role menus: could not read the audit log on %s: %s", guild.id, exc)
    return None


def approval_channel(bot: Any, guild: Any) -> Any:
    """Where requests wait: the setting, or the staff channel when it is not set."""
    channel_id = bot.store.get(guild.id, APPROVAL_CHANNEL_KEY) or bot.store.get(
        guild.id, "staff_channel_id"
    )
    if not channel_id:
        return None
    return bot.get_channel(channel_id) or guild.get_channel(channel_id)


def card_target(bot: Any, channel: Any) -> tuple[Any, str]:
    """(where the card goes, why) — the test channel stands in while the guard would refuse."""
    if channel is None:
        return None, "no_approval_channel"
    guard = getattr(bot, "guard", None)
    if guard is None or guard.allows_channel(channel.id):
        return channel, "approval_channel"
    home = bot.get_channel(guard.test_channel_id) if guard.test_channel_id else None
    return (home, "test_channel") if home is not None else (None, "no_test_channel")


def ping_mentions(role_id: Any) -> discord.AllowedMentions:
    if not role_id:
        return discord.AllowedMentions.none()
    return discord.AllowedMentions(
        everyone=False, users=False, roles=[discord.Object(id=int(role_id))]
    )


def request_id_for(request_id: int, action: str) -> str:
    return f"rolereq:{request_id}:{action}"


def request_view(request_id: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(RequestButton(request_id, "approve"))
    view.add_item(RequestButton(request_id, "deny"))
    return view


def request_card(row: Any, *, label: str, menu_name: str, days: int | None) -> discord.Embed:
    """One place turns a stored request into the card every surface shows."""
    embed = discord.Embed(
        title=grants.CARD_HEADING.format(request_id=row["id"]),
        description=f"<@{row['user_id']}> asked for <@&{row['role_id']}>",
    )
    embed.add_field(name="Role", value=label, inline=True)
    embed.add_field(name="Menu", value=menu_name, inline=True)
    embed.add_field(name="Asked", value=grants.stamp(row["requested_at"], "R"), inline=True)
    embed.add_field(name="Lasts", value=f"{days} day(s)" if days else "no end date", inline=True)
    embed.add_field(name="Status", value=row["status"], inline=True)
    if row["decided_by"]:
        embed.add_field(name="Decided by", value=f"<@{row['decided_by']}>", inline=True)
    if row["deny_reason"]:
        embed.add_field(name="Reason", value=str(row["deny_reason"])[:1024], inline=False)
    return embed


async def post_request_card(
    bot: Any, guild: Any, row: Any, menu: Any, label: str
) -> tuple[int | None, str]:
    """Where the request card actually went, so the member's reply can say so."""
    target, where = card_target(bot, approval_channel(bot, guild))
    details = {"request_id": row["id"], "role_id": row["role_id"]}
    if target is None:
        await log_action(
            bot, guild, "role.request_card_failed", details=details | {"reason": where}
        )
        return None, where
    role_id = bot.store.get(guild.id, APPROVER_ROLE_KEY)
    try:
        message = await target.send(
            f"<@&{role_id}>" if role_id else None,
            embed=request_card(
                row, label=label, menu_name=menu["name"], days=expires_days_of(menu)
            ),
            view=request_view(row["id"]),
            allowed_mentions=ping_mentions(role_id),
        )
    except Exception as exc:
        log.warning("role menus: could not post the card for request %s: %s", row["id"], exc)
        await log_action(
            bot,
            guild,
            "role.request_card_failed",
            details=details | {"reason": f"{type(exc).__name__}: {exc}"},
        )
        return None, "failed"
    await grants.set_request_card(bot.db, row["id"], target.id, message.id)
    return message.id, where


async def edit_request_card(bot: Any, guild: Any, row: Any, label: str, menu_name: str) -> None:
    """Cosmetic, and last: a failure here never undoes the decision above it."""
    if not row["message_id"] or not row["channel_id"]:
        return
    channel = bot.get_channel(row["channel_id"]) or guild.get_channel(row["channel_id"])
    if channel is None:
        log.info("role menus: request %s has no card channel any more", row["id"])
        return
    partial = getattr(channel, "get_partial_message", None)
    try:
        message = (
            partial(row["message_id"])
            if partial is not None
            else await channel.fetch_message(row["message_id"])
        )
        await message.edit(
            content=None,
            embed=request_card(row, label=label, menu_name=menu_name, days=None),
            view=None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except (*NETWORK_ERRORS, LookupError) as exc:
        log.warning("role menus: could not close the card for request %s: %s", row["id"], exc)


async def submit_request(bot: Any, guild: Any, member: Any, menu: Any, role_id: int) -> str:
    """The one place a member's request is written, carded and logged; returns what to say."""
    label = await label_for(bot.db, guild, menu["id"], role_id)
    if await grants.open_request(bot.db, menu["id"], member.id, role_id) is not None:
        return grants.ALREADY_ASKED.format(label=label)
    denial = await grants.last_denial(bot.db, menu["id"], member.id, role_id)
    if denial is not None:
        until = grants.still_cooling(denial["decided_at"], retry_days_of(menu))
        if until is not None:
            return grants.TOO_SOON.format(
                label=label,
                when=grants.stamp(denial["decided_at"], "D"),
                stamp=grants.stamp(until),
            )
    request_id = await grants.create_request(bot.db, guild.id, menu["id"], member.id, role_id)
    if request_id is None:
        return grants.ALREADY_ASKED.format(label=label)
    row = await grants.get_request(bot.db, request_id)
    message_id, where = await post_request_card(bot, guild, row, menu, label)
    await log_action(
        bot,
        guild,
        "role.requested",
        actor=member,
        target=member,
        details={
            "request_id": request_id,
            "menu": menu["name"],
            "role_id": role_id,
            "card": where,
        },
    )
    if message_id is None:
        return grants.CARD_NOT_POSTED.format(label=label)
    said = grants.REQUEST_SENT.format(label=label)
    return said + CARD_IN_TEST_CHANNEL if where == "test_channel" else said


async def withdraw_request(bot: Any, guild: Any, member: Any, menu: Any, role_id: int) -> str:
    label = await label_for(bot.db, guild, menu["id"], role_id)
    row = await grants.open_request(bot.db, menu["id"], member.id, role_id)
    if row is None:
        return grants.NOTHING_TO_APPROVE
    if not await grants.decide_request(
        bot.db, row["id"], grants.WITHDRAWN, decided_by=member.id
    ):
        return grants.ALREADY_DECIDED.format(status=(await grants.get_request(
            bot.db, row["id"]
        ))["status"])
    await log_action(
        bot,
        guild,
        "role.withdrawn",
        actor=member,
        target=member,
        details={"request_id": row["id"], "menu": menu["name"], "role_id": role_id},
    )
    fresh = await grants.get_request(bot.db, row["id"])
    await edit_request_card(bot, guild, fresh, label, menu["name"])
    return grants.WITHDRAWN_SAID.format(label=label)


def actor_id(actor: Any) -> int | None:
    found = getattr(actor, "id", actor)
    return int(found) if isinstance(found, int) else None


async def apply_request_decision(
    bot: Any,
    guild: Any,
    request_id: int,
    status: str,
    actor: Any,
    *,
    reason: str | None = None,
    days: Any = None,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    """Approve or deny, once, whoever wins the update: (what to say, the settled row)."""
    row = await grants.get_request(bot.db, request_id)
    if row is None:
        return grants.NOTHING_TO_APPROVE, None
    if row["guild_id"] != guild.id:
        return NOT_STAFFS_REQUEST, None
    if row["status"] != grants.PENDING:
        return grants.ALREADY_DECIDED.format(status=row["status"]), None
    menu = await get_menu_by_id(bot.db, row["menu_id"])
    menu_name = menu["name"] if menu is not None else "a deleted menu"
    label = await label_for(bot.db, guild, row["menu_id"], row["role_id"])
    member = guild.get_member(row["user_id"])
    if status == grants.DENIED:
        return await _deny_request(
            bot, guild, row, member, label, menu, menu_name, actor, reason, via=via
        )
    if member is None:
        return MEMBER_HAS_GONE.format(name=row["user_id"]), None
    return await _approve_request(
        bot, guild, row, member, label, menu, menu_name, actor, days, via=via
    )


async def _approve_request(
    bot: Any,
    guild: Any,
    row: Any,
    member: Any,
    label: str,
    menu: Any,
    menu_name: str,
    actor: Any,
    days: Any,
    *,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    wanted = days if days is not None else expires_days_of(menu)
    until = grants.expires_at(wanted)
    if not await grants.decide_request(
        bot.db, row["id"], grants.APPROVED, decided_by=actor_id(actor)
    ):
        fresh = await grants.get_request(bot.db, row["id"])
        return grants.ALREADY_DECIDED.format(status=fresh["status"]), None
    fresh = await grants.get_request(bot.db, row["id"])
    added = await change_roles(
        bot, member, guild, {row["role_id"]}, set(), f"Black Bloc role request approved by {actor}"
    )
    if not added:
        await log_action(
            bot,
            guild,
            "role.approve_failed",
            actor=actor,
            target=member,
            details={"request_id": row["id"], "role_id": row["role_id"]},
        )
        await edit_request_card(bot, guild, fresh, label, menu_name)
        return ROLE_REFUSED_AFTER_DECISION.format(label=label), fresh
    await grants.record_added(
        bot.db,
        guild.id,
        row["user_id"],
        [row["role_id"]],
        grants.APPROVAL,
        granted_by=actor_id(actor),
        until=until,
    )
    await log_action(
        bot,
        guild,
        kind_via("role.approved", via),
        actor=actor,
        target=member,
        details={
            "via": via,
            "request_id": row["id"],
            "menu": menu_name,
            "role_id": row["role_id"],
            "expires_at": until,
        },
    )
    extra = grants.EXPIRES_EXTRA.format(stamp=grants.stamp(until)) if until else ""
    await dm(member, grants.DM_APPROVED.format(label=label, guild=guild.name, extra=extra))
    await edit_request_card(bot, guild, fresh, label, menu_name)
    return (
        grants.APPROVED_SAID.format(
            name=getattr(member, "display_name", row["user_id"]), label=label, extra=extra
        ),
        fresh,
    )


async def _deny_request(
    bot: Any,
    guild: Any,
    row: Any,
    member: Any,
    label: str,
    menu: Any,
    menu_name: str,
    actor: Any,
    reason: str | None,
    *,
    via: str = VIA_DISCORD,
) -> tuple[str, Any]:
    said = grants.clamp(reason, grants.REASON_LIMIT) or "none given"
    if not await grants.decide_request(
        bot.db, row["id"], grants.DENIED, decided_by=actor_id(actor), deny_reason=said
    ):
        fresh = await grants.get_request(bot.db, row["id"])
        return grants.ALREADY_DECIDED.format(status=fresh["status"]), None
    fresh = await grants.get_request(bot.db, row["id"])
    await log_action(
        bot,
        guild,
        kind_via("role.denied", via),
        actor=actor,
        target=member if member is not None else row["user_id"],
        reason=said,
        details={
            "request_id": row["id"],
            "menu": menu_name,
            "role_id": row["role_id"],
            "via": via,
        },
    )
    until = grants.retry_at(fresh["decided_at"], retry_days_of(menu))
    await dm(
        member,
        grants.DM_DENIED.format(
            label=label,
            guild=guild.name,
            reason=said,
            stamp=grants.stamp(until) if until else "whenever you like",
        ),
    )
    await edit_request_card(bot, guild, fresh, label, menu_name)
    return grants.DENIED_SAID, fresh


async def request_context(interaction: discord.Interaction, request_id: int) -> Any:
    """This click's request row, or None once the clicker has been answered."""
    bot = interaction.client
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(interaction.channel_id):
        await interaction.response.send_message(guard.refusal_message(), ephemeral=True)
        return None
    if not await require_staff(interaction):
        return None
    if not bot.db.is_connected:
        await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
        return None
    row = await grants.get_request(bot.db, request_id)
    if row is None:
        await interaction.response.send_message(grants.NOTHING_TO_APPROVE, ephemeral=True)
        return None
    return row


async def decide_from_click(
    interaction: discord.Interaction,
    request_id: int,
    status: str,
    *,
    reason: str | None = None,
    days: Any = None,
) -> None:
    said, _ = await apply_request_decision(
        interaction.client,
        interaction.guild,
        request_id,
        status,
        interaction.user,
        reason=reason,
        days=days,
    )
    await answer(interaction, said)


class RequestDenyModal(AnswersErrors, discord.ui.Modal, title="Why not?"):
    reason = discord.ui.TextInput(
        label="One line the member will be sent",
        style=discord.TextStyle.paragraph,
        max_length=grants.REASON_LIMIT,
    )

    def __init__(self, request_id: int) -> None:
        super().__init__()
        self.request_id = request_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await decide_from_click(
            interaction, self.request_id, grants.DENIED, reason=str(self.reason)
        )


class RequestApproveModal(AnswersErrors, discord.ui.Modal, title="How long for?"):
    days = discord.ui.TextInput(
        label="Days, or 0 for a role that never runs out", max_length=5, required=False
    )

    def __init__(self, request_id: int, default_days: int) -> None:
        super().__init__()
        self.request_id = request_id
        self.days.default = str(default_days)
        self.days.placeholder = f"{default_days} — what this menu says"

    async def on_submit(self, interaction: discord.Interaction) -> None:
        typed = str(self.days).strip()
        if typed and not typed.isdigit():
            await answer(interaction, BAD_DAYS.format(given=typed[:40]))
            return
        await interaction.response.defer(ephemeral=True)
        await decide_from_click(
            interaction,
            self.request_id,
            grants.APPROVED,
            days=int(typed) if typed else None,
        )


class RequestButton(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=REQUEST_TEMPLATE
):
    def __init__(self, request_id: int, action: str) -> None:
        self.request_id = request_id
        self.action = action
        approving = action == "approve"
        super().__init__(
            discord.ui.Button(
                label="Approve" if approving else "Deny",
                style=discord.ButtonStyle.success if approving else discord.ButtonStyle.danger,
                custom_id=request_id_for(request_id, action),
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["request_id"]), match["action"])

    async def on_click(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        guild_id = interaction.guild.id if interaction.guild is not None else None
        await interaction.response.send_message(
            menus.said(bot.store, guild_id, ROLEMENU_RETIRED_KEY),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )


class RoleMenuSelect(discord.ui.Select):
    def __init__(self, menu_id: int, options: Any, mode: str) -> None:
        super().__init__(
            custom_id=custom_id(menu_id),
            placeholder="Pick the roles you want",
            min_values=0,
            max_values=max_values_for(mode, len(options)),
            options=[
                discord.SelectOption(
                    label=row["label"],
                    value=str(row["role_id"]),
                    emoji=select_emoji(row["emoji"]),
                )
                for row in options
            ],
        )
        self.menu_id = menu_id
        self.role_ids = [row["role_id"] for row in options]
        self.labels = {row["role_id"]: row["label"] for row in options}

    async def callback(self, interaction: discord.Interaction) -> None:
        await answer_retired_pick(interaction)

    async def ask_staff(
        self, interaction: discord.Interaction, bot: Any, guild: Any, member: Any, menu: Any
    ) -> None:
        """An approval menu never hands a role over; it asks, withdraws, or gives one up."""
        mine = set(self.role_ids)
        selected = {int(value) for value in self.values} & mine
        held = {role.id for role in member.roles} & mine
        pending = {
            row["role_id"]
            for row in await grants.open_requests_for(bot.db, guild.id, member.id)
        } & mine
        await interaction.response.defer(ephemeral=True)
        said: list[str] = []
        for role_id in sorted(selected & pending):
            said.append(await withdraw_request(bot, guild, member, menu, role_id))
        given_up = held - selected
        if given_up:
            said.append(await self.give_up(bot, guild, member, given_up))
        for role_id in sorted(selected - held - pending):
            said.append(await submit_request(bot, guild, member, menu, role_id))
        await answer(interaction, " ".join(said)[:2000] or summary([], []))

    async def give_up(self, bot: Any, guild: Any, member: Any, role_ids: set[int]) -> str:
        """Nobody needs permission to drop a role they already have."""
        if not await change_roles(
            bot, member, guild, set(), role_ids, "Black Bloc role menu — given up"
        ):
            return CANNOT_EDIT_ROLES
        removed = [self.labels.get(i, str(i)) for i in sorted(role_ids)]
        await grants.record_removed(bot.db, guild.id, member.id, role_ids, grants.GIVEN_UP)
        await log_action(
            bot,
            guild,
            "role_menu.update",
            actor=member,
            target=member,
            details={"menu_id": self.menu_id, "added": [], "removed": removed},
        )
        return summary([], removed)


async def answer_retired_pick(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    bot = interaction.client
    text = (
        menus.said(bot.store, guild.id, ROLEMENU_PICKING_RETIRED_KEY)
        if guild is not None
        else str(bot.store.default(ROLEMENU_PICKING_RETIRED_KEY))
    )
    await interaction.response.send_message(
        text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


class RetiredMenuPick(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Select], template=custom_id_template()
):
    """A panel posted before member self-pick was retired: it answers, and changes nothing."""

    def __init__(self, menu_id: int) -> None:
        self.menu_id = menu_id
        super().__init__(discord.ui.Select(custom_id=custom_id(menu_id), min_values=0))

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["menu_id"]))

    async def on_click(self, interaction: discord.Interaction) -> None:
        await answer_retired_pick(interaction)


class RoleMenuView(discord.ui.View):
    def __init__(self, menu_id: int, options: Any, mode: str) -> None:
        super().__init__(timeout=None)
        self.add_item(RoleMenuSelect(menu_id, options, mode))


# --- one function per move, one write, one log row; both doors call these ------------------------


async def make_menu(
    bot: Any,
    guild: Any,
    actor: Any,
    name: str,
    title: str,
    description: Any = None,
    mode: str = "multiple",
    *,
    approval: Any = None,
    expires_days: Any = None,
    retry_days: Any = None,
    via: str = VIA_DISCORD,
) -> int | None:
    menu_id = await create_menu(
        bot.db,
        guild.id,
        name,
        title,
        description,
        mode,
        approval=approval,
        expires_days=expires_days,
        retry_days=retry_days,
    )
    if menu_id is None:
        return None
    await log_action(
        bot,
        guild,
        kind_via("role_menu.create", via),
        actor=actor,
        details={"menu": name, "mode": mode, "via": via},
    )
    return menu_id


async def change_menu(
    bot: Any, guild: Any, actor: Any, name: str, *, via: str = VIA_DISCORD, **fields: Any
) -> Any:
    """The changed menu row, or None when this server has no menu by that name."""
    if not await update_menu(bot.db, guild.id, name, **fields):
        return None
    menu = await get_menu(bot.db, guild.id, name)
    await log_action(
        bot,
        guild,
        kind_via("role_menu.edit", via),
        actor=actor,
        details={
            "menu": name,
            "approval": needs_approval(menu),
            "expires_days": expires_days_of(menu),
            "retry_days": retry_days_of(menu),
            "via": via,
        },
    )
    return menu


async def drop_menu(bot: Any, guild: Any, actor: Any, name: str, *, via: str = VIA_DISCORD) -> bool:
    """An event goes; its assignments close, and nobody loses a role for it."""
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None or not await delete_menu(bot.db, guild.id, name):
        return False
    closed = await timed.close_event(bot.db, guild.id, menu["id"], grants.EVENT_DELETED)
    await log_action(
        bot,
        guild,
        kind_via("role_menu.delete", via),
        actor=actor,
        details={"menu": name, "assignments_closed": closed, "via": via},
    )
    return True


async def add_timed_role(
    bot: Any,
    guild: Any,
    actor: Any,
    role: Any,
    *,
    label: Any = None,
    emoji: Any = None,
    via: str = VIA_DISCORD,
) -> str | None:
    """A role joins the one timed list; None when it did, else why not, in words."""
    refused = await timed_role_refusal(bot, guild, role)
    if refused:
        return refused[1]
    wanted = str(label or "").strip() or str(role.name)
    if not await timed.add(bot.db, guild.id, role.id, wanted, emoji=emoji, by=actor_id(actor)):
        return word(bot, guild.id, "rolemenu_timed_already_said", name=role.name)
    await log_action(
        bot,
        guild,
        kind_via("role_menu.option_added", via),
        actor=actor,
        details={"role_id": int(role.id), "label": wanted, "via": via},
    )
    return None


async def timed_role_refusal(bot: Any, guild: Any, role: Any) -> tuple[str, str] | None:
    """(code, sentence) for a role that may not join the timed list; None when it may."""
    if not removable(guild, role.id):
        return "cannot_strip", word(bot, guild.id, "rolemenu_cannot_strip_said", name=role.name)
    refused = await pings_refusal(bot, guild, [role.id])
    if refused:
        return "pings_role", refused
    if await timed.is_timed(bot.db, guild.id, role.id):
        return "already_timed", word(bot, guild.id, "rolemenu_timed_already_said", name=role.name)
    if len(await timed.role_ids(bot.db, guild.id)) >= timed.LIST_MAX:
        return "list_full", word(
            bot, guild.id, "rolemenu_timed_list_full_said", limit=timed.LIST_MAX
        )
    return None


async def drop_timed_role(
    bot: Any, guild: Any, actor: Any, role_id: int, *, via: str = VIA_DISCORD
) -> str | None:
    """A role leaves the list; refused while any open event still assigns it."""
    count = await timed.assigned_count(bot.db, guild.id, role_id)
    if count:
        return word(
            bot,
            guild.id,
            "rolemenu_timed_remove_refused_said",
            name=role_name(guild, role_id),
            count=count,
        )
    if not await timed.remove(bot.db, guild.id, role_id):
        return word(bot, guild.id, "rolemenu_timed_not_listed_said", name=role_name(guild, role_id))
    await log_action(
        bot,
        guild,
        kind_via("role_menu.option_removed", via),
        actor=actor,
        details={"role_id": int(role_id), "via": via},
    )
    return None


async def post_menu(
    bot: Any,
    guild: Any,
    actor: Any,
    menu: Any,
    options: Any,
    target: Any,
    *,
    via: str = VIA_DISCORD,
) -> Any:
    message = await post_panel(bot, menu, options, target)
    await log_action(
        bot,
        guild,
        kind_via("role_menu.post", via),
        actor=actor,
        details={
            "menu": menu["name"],
            "channel_id": target.id,
            "message_id": message.id,
            "via": via,
        },
    )
    return message


async def seed_menus(
    bot: Any, guild: Any, actor: Any, *, via: str = VIA_DISCORD
) -> tuple[list[str], list[str]]:
    created, skipped = await seed_default_menus(bot.db, guild.id)
    await log_action(
        bot,
        guild,
        kind_via("role_menu.seeded", via),
        actor=actor,
        details={"created": created, "skipped": skipped, "via": via},
    )
    return created, skipped


async def grant_role(
    bot: Any,
    guild: Any,
    actor: Any,
    member: Any,
    role: Any,
    days: Any = None,
    *,
    reason: Any = None,
    via: str = VIA_DISCORD,
) -> tuple[Any, str]:
    """One timed role: `days` of None or 0 means it never runs out, as the website has always
    allowed. A role they already hold only starts the clock; an open grant has its clock reset."""
    if await timed.is_timed(bot.db, guild.id, role.id):
        return None, word(bot, guild.id, TIMED_NEEDS_EVENT_KEY, role=role.name)
    held = any(r.id == role.id for r in member.roles)
    if not held and not await change_roles(
        bot, member, guild, {role.id}, set(), f"Black Bloc timed role by {actor}"
    ):
        return None, CANNOT_ADD.format(label=role.name, name=member.display_name)
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
            granted_by=actor_id(actor),
            until=until,
        )
    await log_action(
        bot,
        guild,
        kind_via("role.granted", via),
        actor=actor,
        target=member,
        reason=reason,
        details={"grant_id": grant_id, "role_id": role.id, "expires_at": until, "via": via},
    )
    said = grants.GRANTED_SAID.format(
        name=member.display_name,
        label=role.name,
        until=f" until {grants.stamp(until)}" if until else "",
    )
    return grant_id, said + ("" if not held else GRANT_STARTED_ON_A_ROLE_THEY_HAD)


def grant_names(guild: Any, row: Any) -> tuple[str, str]:
    member = guild.get_member(row["user_id"]) if guild is not None else None
    name = str(getattr(member, "display_name", None) or row["user_id"])
    return name, role_name(guild, row["role_id"])


async def extend_role(
    bot: Any,
    guild: Any,
    actor: Any,
    row: Any,
    days: Any,
    *,
    via: str = VIA_DISCORD,
    when: Any = None,
) -> tuple[str | None, str]:
    """Pushes back from the later of now and its end; (None, why) when a menu's end owns it."""
    refused = await push_back_refusal(bot, guild, row, when)
    if refused:
        return None, refused
    wanted = max(int(days or 0), 1)
    until = grants.pushed_back(row["expires_at"], wanted)
    await grants.extend_grant(bot.db, row["id"], until)
    name, label = grant_names(guild, row)
    await log_action(
        bot,
        guild,
        kind_via("role.extended", via),
        actor=actor,
        target=row["user_id"],
        details={
            "grant_id": row["id"],
            "role_id": row["role_id"],
            "days": wanted,
            "expires_at": until,
            "via": via,
        },
    )
    return until, grants.EXTENDED_SAID.format(
        name=name, label=label, stamp=grants.stamp(until)
    )


async def revoke_grant(
    bot: Any, guild: Any, actor: Any, row: Any, *, via: str = VIA_DISCORD
) -> tuple[bool, str]:
    """The staff reversal every stored decision gets — the Discord half that never existed."""
    member = guild.get_member(row["user_id"]) if guild is not None else None
    name, label = grant_names(guild, row)
    kept = await kept_elsewhere(bot.db, guild.id, row)
    if not kept and member is not None and any(r.id == row["role_id"] for r in member.roles):
        if not await change_roles(
            bot, member, guild, set(), {row["role_id"]}, f"Black Bloc timed role ended by {actor}"
        ):
            return False, CANNOT_REMOVE.format(label=label, name=name)
    await grants.end_grant(bot.db, row["id"], grants.ENDED_BY_STAFF)
    await log_action(
        bot,
        guild,
        kind_via("role.ended", via),
        actor=actor,
        target=member if member is not None else row["user_id"],
        details={"grant_id": row["id"], "role_id": row["role_id"], "via": via},
    )
    if kept:
        return True, word(bot, guild.id, KEPT_THROUGH_KEY, role=label, name=name, menu=kept)
    return True, GRANT_ENDED.format(label=label, name=name)


# --- timed roles per event: giving and taking an event's roles --------------------------------


def event_name(menu: Any) -> str:
    return str(menu_value(menu, "title") or menu_value(menu, "name") or "?")


def outcome_said(bot: Any, guild_id: int, key: str, role: str, found: dict[str, list]) -> str:
    return word(
        bot,
        guild_id,
        key,
        role=role,
        given=len(found["given"]),
        had=len(found["had"]),
        already=len(found["already"]),
        refused=len(found["refused"]),
        kept=len(found.get("kept", ())),
    )


async def give_event_role(
    bot: Any,
    guild: Any,
    actor: Any,
    menu: Any,
    role_id: int,
    members: Any,
    *,
    source: str = grants.STAFF,
    via: str = VIA_DISCORD,
) -> dict[str, Any]:
    """One batch: each member wears the role and holds it through this event, once."""
    found: dict[str, Any] = {"given": [], "had": [], "already": [], "refused": []}
    role_id = int(role_id)
    label = role_name(guild, role_id)
    if menu_value(menu, "ended_at") or not await timed.is_timed(bot.db, guild.id, role_id):
        found["refused"] = [int(one.id) for one in members or ()]
        found["said"] = word(bot, guild.id, "rolemenu_give_refused_said", role=label)
        return found
    reason = f"Black Bloc: {event_name(menu)} by {actor}"
    async with end_lock(bot, menu["id"]), guild_lock(bot, guild.id):
        fresh = await get_menu_by_id(bot.db, menu["id"])
        until = menu_value(fresh, "ends_at")
        for member in members or ():
            if await timed.event_grant(bot.db, guild.id, member.id, role_id, menu["id"]):
                found["already"].append(int(member.id))
                continue
            wears = any(int(r.id) == role_id for r in member.roles)
            if not wears and not await change_roles(bot, member, guild, {role_id}, set(), reason):
                found["refused"].append(int(member.id))
                continue
            try:
                await grants.add_grant(
                    bot.db,
                    guild.id,
                    member.id,
                    role_id,
                    source,
                    granted_by=actor_id(actor),
                    until=until,
                    menu_id=int(menu["id"]),
                )
            except sqlite3.IntegrityError:
                found["already"].append(int(member.id))
                continue
            found["had" if wears else "given"].append(int(member.id))
    details = {
        "menu": menu["name"],
        "menu_id": int(menu["id"]),
        "role_id": role_id,
        "source": source,
        **{key: found[key] for key in ("given", "had", "already", "refused")},
        "via": via,
    }
    if found["given"] or found["had"] or found["already"]:
        await log_action(
            bot, guild, kind_via("role_menu.assign", via), actor=actor, details=details
        )
    if found["refused"]:
        await log_action(
            bot, guild, kind_via("role_menu.assign_failed", via), actor=actor, details=details
        )
    found["said"] = outcome_said(bot, guild.id, "rolemenu_give_said", label, found)
    return found


async def take_event_role(
    bot: Any,
    guild: Any,
    actor: Any,
    menu: Any,
    role_id: int,
    members: Any,
    *,
    via: str = VIA_DISCORD,
) -> dict[str, Any]:
    """Off this event; the role itself stays on anyone another open event still holds it for."""
    found: dict[str, Any] = {"given": [], "had": [], "already": [], "refused": [], "kept": []}
    role_id = int(role_id)
    label = role_name(guild, role_id)
    reason = f"Black Bloc: {event_name(menu)} taken off by {actor}"
    async with end_lock(bot, menu["id"]), guild_lock(bot, guild.id):
        keeping = await timed.keepers(bot.db, guild.id, menu["id"])
        for member in members or ():
            row = await timed.event_grant(bot.db, guild.id, member.id, role_id, menu["id"])
            wears = any(int(r.id) == role_id for r in member.roles)
            if (int(member.id), role_id) in keeping:
                if row is not None:
                    await grants.end_grant(bot.db, row["id"], grants.ENDED_BY_STAFF)
                found["kept"].append(int(member.id))
                continue
            if wears and not await change_roles(bot, member, guild, set(), {role_id}, reason):
                found["refused"].append(int(member.id))
                continue
            closed = await timed.close_member_roles(
                bot.db, guild.id, member.id, [role_id], grants.ENDED_BY_STAFF
            )
            if wears:
                await hand.retire_roles(bot.db, guild.id, member.id, [role_id])
            found["given" if wears or closed else "already"].append(int(member.id))
    details = {
        "menu": menu["name"],
        "menu_id": int(menu["id"]),
        "role_id": role_id,
        "taken": found["given"],
        "kept": found["kept"],
        "already": found["already"],
        "refused": found["refused"],
        "via": via,
    }
    if found["given"] or found["kept"] or found["already"]:
        await log_action(
            bot, guild, kind_via("role_menu.unassign", via), actor=actor, details=details
        )
    if found["refused"]:
        await log_action(
            bot, guild, kind_via("role_menu.unassign_failed", via), actor=actor, details=details
        )
    found["said"] = outcome_said(bot, guild.id, "rolemenu_take_said", label, found)
    return found


# --- temporary roles: a menu's end, and the pass that takes its roles off everyone -------------


END_REASON = "Black Bloc: {menu} ended"
NOTICE_LIMIT = 2000
END_LOCKS_ATTR = "_role_menu_end_locks"
GUILD_LOCKS_ATTR = "_role_menu_guild_locks"


def end_lock(bot: Any, menu_id: Any) -> asyncio.Lock:
    """One lock per menu, kept on the bot so every copy of this module shares it."""
    found = getattr(bot, END_LOCKS_ATTR, None)
    if found is None:
        found = {}
        setattr(bot, END_LOCKS_ATTR, found)
    return found.setdefault(int(menu_id), asyncio.Lock())


def guild_lock(bot: Any, guild_id: Any) -> asyncio.Lock:
    """Innermost, never nested: an end pass and a give or take on ANY event wait for each other."""
    found = getattr(bot, GUILD_LOCKS_ATTR, None)
    if found is None:
        found = {}
        setattr(bot, GUILD_LOCKS_ATTR, found)
    return found.setdefault(int(guild_id), asyncio.Lock())


def default_buffer(bot: Any, guild_id: int) -> Any:
    return bot.store.get(guild_id, ROLEMENU_END_BUFFER_KEY)


async def menu_ends_named(db: Any, guild_id: Any) -> dict[int, dict[str, str]]:
    """Each timed role's next end with that event's name; the Members chips' source."""
    return await timed.soonest_ends(db, guild_id)


async def kept_elsewhere(db: Any, guild_id: int, row: Any) -> str | None:
    """The name of another open event that holds this member's role, or None."""
    cur = await db.conn.execute(
        "SELECT m.title FROM role_grants g JOIN role_menus m ON m.id = g.menu_id "
        "WHERE g.guild_id = ? AND g.user_id = ? AND g.role_id = ? AND g.removed_at IS NULL "
        "AND m.ended_at IS NULL AND g.id != ? ORDER BY m.id LIMIT 1",
        (int(guild_id), int(row["user_id"]), int(row["role_id"]), int(row["id"])),
    )
    found = await cur.fetchone()
    return str(found["title"]) if found is not None else None


async def push_back_refusal(bot: Any, guild: Any, row: Any, when: Any = None) -> str | None:
    """An assignment ends with its event, and a timed role is only ever given from one."""
    menu_id = menu_value(row, "menu_id")
    event = await get_menu_by_id(bot.db, int(menu_id)) if menu_id is not None else None
    if event is not None:
        shown = when or (lambda _bot, _guild_id, at: grants.stamp(at, "D"))
        return menus.said(
            bot.store,
            guild.id,
            ROLEMENU_PUSH_BACK_REFUSED_KEY,
            role=role_name(guild, row["role_id"]),
            menu=event["title"],
            date=(
                shown(bot, guild.id, event["ends_at"])
                if parse_ts(event["ends_at"]) is not None
                else str(bot.store.get(guild.id, ROLEMENU_END_NOT_KNOWN_KEY))
            ),
        )
    if await timed.is_timed(bot.db, guild.id, row["role_id"]):
        return word(bot, guild.id, TIMED_NEEDS_EVENT_KEY, role=role_name(guild, row["role_id"]))
    return None


async def menu_role_ids(db: Any, menu_id: int) -> list[int]:
    return [int(row["role_id"]) for row in await get_options(db, menu_id)]


async def post_role_notice(bot: Any, guild: Any, text: str) -> bool:
    """Where role notices post, with the approver ping and nobody else's (checklist 11)."""
    target, where = card_target(bot, approval_channel(bot, guild))
    if target is None:
        await log_action(bot, guild, "role_menu.notice_failed", details={"reason": where})
        return False
    role_id = bot.store.get(guild.id, APPROVER_ROLE_KEY)
    content = f"<@&{role_id}> {text}" if role_id else text
    try:
        await target.send(content[:NOTICE_LIMIT], allowed_mentions=ping_mentions(role_id))
    except Exception as exc:
        await log_action(
            bot,
            guild,
            "role_menu.notice_failed",
            details={"reason": f"{type(exc).__name__}: {exc}"[:300]},
        )
        return False
    return True


async def set_menu_end(
    bot: Any,
    guild: Any,
    actor: Any,
    menu: Any,
    *,
    source: str,
    marathon_id: Any = None,
    ends_at: Any = None,
    buffer_days: Any = None,
    via: str = VIA_DISCORD,
) -> str | None:
    """Staff set (or clear) a menu's one end; open grants on its roles follow it."""
    if source not in menus.END_SOURCES:
        raise ValueError(f"source must be one of {menus.END_SOURCES}")
    marathon = None
    if source == menus.MARATHON_END:
        marathon = await marathon_row(bot.db, guild.id, marathon_id)
        if marathon is None:
            raise ValueError(f"no marathon {marathon_id!r} in this server")
        await refuse_taken_marathon(bot, guild, marathon, menu["id"])
    wanted = {
        "ends_source": source,
        "buffer_days": None if buffer_days is None else menus.buffer_of({}, buffer_days),
        "ends_at": menus.utc_iso(ends_at) if isinstance(ends_at, datetime) else ends_at,
    }
    end = menus.ends_at_of(wanted, marathon, default_buffer(bot, guild.id))
    async with end_lock(bot, menu["id"]):
        await store_menu_end(
            bot.db,
            menu["id"],
            source=source,
            marathon_id=int(marathon["id"]) if marathon is not None else None,
            buffer_days=wanted["buffer_days"],
            ends_at=end,
            by=actor_id(actor),
        )
    await timed.stamp_event(bot.db, guild.id, menu["id"], end)
    await log_action(
        bot,
        guild,
        kind_via("role_menu.end_set", via),
        actor=actor,
        details={
            "menu": menu["name"],
            "source": source,
            "marathon_id": marathon["id"] if marathon is not None else None,
            "buffer_days": wanted["buffer_days"],
            "was": menu["ends_at"],
            "ends_at": end,
            "via": via,
        },
    )
    return end


async def members_of(guild: Any) -> list[Any] | None:
    """Every member, chunking first when the cache is short; None when it stays short."""
    members = list(getattr(guild, "members", ()) or ())
    expected = int(getattr(guild, "member_count", 0) or 0)
    if expected and len(members) < expected:
        try:
            await guild.chunk()
        except Exception as exc:
            log.warning("role menus: could not fill the member cache of %s (%s)", guild.id, exc)
        members = list(getattr(guild, "members", ()) or ())
    return None if expected and len(members) < expected else members


def removable(guild: Any, role_id: int) -> bool:
    role = guild.get_role(int(role_id)) if guild is not None else None
    if role is None:
        return False
    assignable = getattr(role, "is_assignable", None)
    return not callable(assignable) or bool(assignable())


async def role_labels(db: Any, guild: Any, menu_id: int) -> dict[int, str]:
    return {
        int(row["role_id"]): str(row["label"] or role_name(guild, row["role_id"]))
        for row in await get_options(db, menu_id)
    }


def roles_said(labels: dict[int, str], role_ids: Any) -> str:
    return ", ".join(f"**{labels.get(int(one), one)}**" for one in role_ids)


async def end_menu(
    bot: Any, guild: Any, menu_id: Any, *, actor: Any = None, via: str = VIA_DISCORD
) -> dict[str, Any] | None:
    """One pass over a due menu, under its lock; None when there was nothing to run."""
    async with end_lock(bot, menu_id):
        menu = await get_menu_by_id(bot.db, int(menu_id))
        if menu is None or not menus.is_due(menu, datetime.now(UTC)):
            return None
        return await _end_pass(bot, guild, menu, actor, via)


async def end_menu_now(
    bot: Any, guild: Any, actor: Any, menu: Any, *, via: str = VIA_DISCORD
) -> dict[str, Any] | None:
    """Staff's End it now: the end becomes this moment, as a date, and the pass runs."""
    if getattr(bot, "guard", None) is not None:
        return await _end_pass(bot, guild, menu, actor, via)
    async with end_lock(bot, menu["id"]):
        await store_menu_end(
            bot.db,
            menu["id"],
            source=menus.DATE_END,
            marathon_id=None,
            buffer_days=menu_value(menu, "buffer_days"),
            ends_at=now_iso(),
            by=actor_id(actor),
        )
    fresh = await get_menu_by_id(bot.db, menu["id"])
    await timed.stamp_event(bot.db, guild.id, menu["id"], menu_value(fresh, "ends_at"))
    return await end_menu(bot, guild, menu["id"], actor=actor, via=via)


async def owned_by_pings(bot: Any, guild_id: int) -> set[int]:
    from ... import pings

    return await pings.owned_role_ids(bot, guild_id)


async def end_plan(bot: Any, guild: Any, menu: Any) -> timed.Plan | None:
    """What this event's end takes now; the pass and every confirm read this one count."""
    members = await members_of(guild)
    if members is None:
        return None
    role_ids = await timed.role_ids(bot.db, guild.id)
    return timed.plan(
        menus.wearers(members, role_ids),
        await timed.keepers(bot.db, guild.id, menu["id"]),
        await owned_by_pings(bot, guild.id),
    )


async def _end_pass(bot: Any, guild: Any, menu: Any, actor: Any, via: str) -> Any:
    if getattr(guild, "unavailable", False):
        return None
    async with guild_lock(bot, guild.id):
        done = await _take_off(bot, guild, menu, actor, via)
    if done is None:
        return None
    details, labels, taken, finished = done
    if finished:
        await log_action(bot, guild, kind_via("role_menu.ended", via), actor=actor, details=details)
        if bot.store.get(guild.id, ROLEMENU_ENDED_NOTICE_KEY):
            await post_role_notice(bot, guild, ended_notice(bot, guild, menu, details, labels))
    await tell_wearers(bot, guild, menu, taken, labels)
    return details


async def _take_off(bot: Any, guild: Any, menu: Any, actor: Any, via: str) -> Any:
    db = bot.db
    role_ids = await timed.role_ids(db, guild.id)
    base = {"menu": menu["name"], "menu_id": menu["id"], "via": via}
    plan = await end_plan(bot, guild, menu)
    if plan is None:
        await log_action(
            bot,
            guild,
            kind_via("role_menu.end_failed", via),
            actor=actor,
            details=base | {"roles": role_ids, "reason": "members_not_loaded"},
        )
        return None
    if getattr(bot, "guard", None) is not None:
        await log_action(
            bot,
            guild,
            "role_menu.would_end",
            actor=actor,
            details=base
            | {
                "roles": role_ids,
                "wearers": [[member.id, worn] for member, worn in plan.take],
                "kept": plan.keep,
            },
        )
        return None
    reason = END_REASON.format(menu=menu["name"])
    taken: list[tuple[Any, list[int]]] = []
    stuck: list[tuple[Any, list[int]]] = []
    for member, worn in plan.take:
        can = [one for one in worn if removable(guild, one)]
        done = bool(can) and await change_roles(bot, member, guild, set(), set(can), reason)
        if done:
            taken.append((member, can))
            await timed.close_member_roles(db, guild.id, member.id, can, grants.EXPIRED)
            await hand.retire_roles(db, guild.id, member.id, can)
        left = [one for one in worn if not done or one not in can]
        if left:
            stuck.append((member, left))
            await log_action(
                bot,
                guild,
                kind_via("role_menu.end_failed", via),
                actor=actor,
                target=member,
                details=base | {"user": member.id, "roles": left},
            )
    still_on = {(int(member.id), int(one)) for member, left in stuck for one in left}
    await timed.close_event(db, guild.id, menu["id"], grants.EXPIRED, keep=still_on)
    passes = int(menu_value(menu, "end_passes", 0)) + 1
    members = int(menu_value(menu, "end_members", 0)) + len(taken)
    finished = not stuck or passes >= menus.ROLE_MENU_END_RETRIES
    leftovers = [[int(member.id), left] for member, left in stuck]
    await record_end_pass(
        db,
        menu["id"],
        passes,
        members,
        ended_at=now_iso() if finished else None,
        failures=json.dumps(leftovers) if finished and leftovers else None,
    )
    details = base | {
        "roles": role_ids,
        "members": members,
        "this_pass": len(taken),
        "taken": [[int(member.id), can] for member, can in taken],
        "kept": plan.keep,
        "failures": len(stuck),
        "left": leftovers,
        "passes": passes,
        "ended": finished,
    }
    labels = await role_labels(db, guild, menu["id"])
    return details, labels, taken, finished


def ended_notice(
    bot: Any, guild: Any, menu: Any, details: dict[str, Any], labels: dict[int, str]
) -> str:
    lines = [
        menus.said(
            bot.store,
            guild.id,
            ROLEMENU_ENDED_TEXT_KEY,
            menu=event_name(menu),
            roles=len(labels),
            members=details["members"],
            failures=details["failures"],
        )
    ]
    return "\n".join(lines + failure_lines(bot, guild, details["left"], labels))


def failure_lines(bot: Any, guild: Any, left: Any, labels: dict[int, str]) -> list[str]:
    """One line per member who still wears a role the pass could not take off."""
    lines = []
    for user_id, roles in left or ():
        member = guild.get_member(int(user_id))
        lines.append(
            menus.said(
                bot.store,
                guild.id,
                ROLEMENU_END_FAILURE_LINE_KEY,
                name=str(getattr(member, "display_name", None) or user_id),
                roles=roles_said(labels, roles),
            )
        )
    return lines


async def tell_wearers(
    bot: Any, guild: Any, menu: Any, taken: Any, labels: dict[int, str]
) -> None:
    """One DM per member, naming every role that came off them."""
    marathon = None
    if menus.end_source(menu) == menus.MARATHON_END:
        marathon = await marathon_row(bot.db, guild.id, menu_value(menu, "ends_marathon_id"))
    what = menus.what_ended(menu, marathon["name"] if marathon is not None else None)
    for member, role_ids in taken:
        await dm(
            member,
            menus.said(
                bot.store,
                guild.id,
                ROLEMENU_ENDED_DM_KEY,
                roles=roles_said(labels, role_ids),
                guild=guild.name,
                what=what,
            ),
        )


async def follow_marathon(bot: Any, guild: Any, marathon_id: Any) -> int:
    """A marathon's new end moves its unfinished menus; one pulled EARLIER waits for staff."""
    rows = await menus_bound_to(bot.db, guild.id, marathon_id)
    bound = [one for one in rows if not one["ended_at"]]
    if not bound:
        return 0
    marathon = await marathon_row(bot.db, guild.id, marathon_id)
    floor = bot.store.get(guild.id, ROLEMENU_END_MOVED_MINUTES_KEY)
    holding = bool(bot.store.get(guild.id, ROLEMENU_END_EARLIER_HOLDS_KEY))
    moved = 0
    for menu in bound:
        async with end_lock(bot, menu["id"]):
            fresh = await get_menu_by_id(bot.db, menu["id"])
            if fresh is None or fresh["ended_at"]:
                continue
            end = menus.ends_at_of(fresh, marathon, default_buffer(bot, guild.id))
            held = menu_value(fresh, "ends_held_at")
            if holding and menus.pulls_earlier(
                fresh["ends_at"], fresh["ends_told_at"], end, floor
            ):
                if menus.end_moved(held, end):
                    await hold_menu_end(bot.db, fresh["id"], end)
                    await end_was_held(bot, guild, fresh, marathon_id, end, held, floor)
                continue
            if held:
                await hold_menu_end(bot.db, fresh["id"], None)
            if not menus.end_moved(fresh["ends_at"], end):
                if held:
                    await hold_cleared(bot, guild, fresh, marathon_id, held, end)
                continue
            told = menus.moved_far(fresh["ends_told_at"], end, floor)
            await restamp_menu_end(bot.db, fresh["id"], end, told=told)
        if held:
            await hold_cleared(bot, guild, fresh, marathon_id, held, end)
        await timed.stamp_event(bot.db, guild.id, fresh["id"], end)
        moved += 1
        if not told:
            continue
        await log_action(
            bot,
            guild,
            "role_menu.end_moved",
            details={
                "menu": fresh["name"],
                "marathon_id": int(marathon_id),
                "was": fresh["ends_told_at"],
                "to": end,
            },
        )
        if bot.store.get(guild.id, ROLEMENU_END_MOVED_NOTICE_KEY):
            await post_role_notice(
                bot,
                guild,
                menus.said(
                    bot.store,
                    guild.id,
                    ROLEMENU_END_MOVED_TEXT_KEY,
                    menu=event_name(fresh),
                    to=end_words(bot, guild.id, end),
                    was=end_words(bot, guild.id, fresh["ends_told_at"]),
                ),
            )
    return moved


async def hold_menu_end(db: Any, menu_id: int, candidate: Any) -> None:
    await db.conn.execute(
        "UPDATE role_menus SET ends_held_at = ? WHERE id = ?", (candidate, int(menu_id))
    )
    await db.conn.commit()


async def end_was_held(
    bot: Any, guild: Any, menu: Any, marathon_id: Any, end: Any, held: Any, floor: Any
) -> None:
    """One log row per new candidate; staff hear once, and again only past the floor."""
    await log_action(
        bot,
        guild,
        "role_menu.end_held",
        details={
            "menu": menu["name"],
            "marathon_id": int(marathon_id),
            "ends_at": menu["ends_at"],
            "held": end,
            "was_held": held,
        },
    )
    if held is not None and not menus.moved_far(held, end, floor):
        return
    await post_role_notice(
        bot,
        guild,
        menus.said(
            bot.store,
            guild.id,
            ROLEMENU_END_HELD_TEXT_KEY,
            menu=event_name(menu),
            to=end_words(bot, guild.id, end),
            was=end_words(bot, guild.id, menu["ends_at"]),
        ),
    )


async def hold_cleared(
    bot: Any, guild: Any, menu: Any, marathon_id: Any, held: Any, end: Any
) -> None:
    await log_action(
        bot,
        guild,
        "role_menu.end_hold_cleared",
        details={
            "menu": menu["name"],
            "marathon_id": int(marathon_id),
            "held": held,
            "ends_at": end,
        },
    )


async def use_held_end(
    bot: Any, guild: Any, actor: Any, menu: Any, *, via: str = VIA_DISCORD
) -> str | None:
    """Staff take the held earlier end: set again from the marathon; None when nothing is held."""
    fresh = await get_menu_by_id(bot.db, menu["id"])
    if (
        fresh is None
        or not menu_value(fresh, "ends_held_at")
        or menus.end_source(fresh) != menus.MARATHON_END
    ):
        return None
    return await set_menu_end(
        bot,
        guild,
        actor,
        fresh,
        source=menus.MARATHON_END,
        marathon_id=fresh["ends_marathon_id"],
        buffer_days=menu_value(fresh, "buffer_days"),
        via=via,
    )


async def unbind_marathon(bot: Any, guild: Any, marathon: Any) -> int:
    """A marathon leaving the list leaves its menus on the last end it gave them, as a date."""
    unbound = 0
    for menu in await menus_bound_to(bot.db, guild.id, marathon["id"]):
        async with end_lock(bot, menu["id"]):
            fresh = await get_menu_by_id(bot.db, menu["id"])
            if fresh is None or menus.end_source(fresh) != menus.MARATHON_END:
                continue
            await unbind_menu_end(bot.db, fresh["id"], keeps_a_date=bool(fresh["ends_at"]))
        unbound += 1
        await log_action(
            bot,
            guild,
            "role_menu.end_unbound",
            details={
                "menu": fresh["name"],
                "marathon_id": int(marathon["id"]),
                "marathon": marathon["name"],
                "ends_at": fresh["ends_at"],
            },
        )
        if fresh["ended_at"] or not bot.store.get(guild.id, ROLEMENU_END_MOVED_NOTICE_KEY):
            continue
        await post_role_notice(
            bot,
            guild,
            menus.said(
                bot.store,
                guild.id,
                ROLEMENU_END_UNBOUND_TEXT_KEY,
                menu=event_name(fresh),
                marathon=marathon["name"],
                to=end_words(bot, guild.id, fresh["ends_at"]),
            ),
        )
    return unbound


def end_words(bot: Any, guild_id: int, at: Any) -> str:
    return grants.stamp(at, "F") if at else str(bot.store.get(guild_id, ROLEMENU_END_NOT_KNOWN_KEY))


async def marathon_moved(bot: Any, guild: Any, marathon_id: Any) -> None:
    """The marathon cog's one call after a span write; a role-menu fault never stops a read."""
    try:
        if bot.db.is_connected:
            await follow_marathon(bot, guild, marathon_id)
    except Exception:
        log.exception("role menus: could not follow marathon %s", marathon_id)


async def marathon_gone(bot: Any, guild: Any, marathon: Any) -> None:
    """The marathon cog's one call after an archive or remove."""
    try:
        if bot.db.is_connected:
            await unbind_marathon(bot, guild, marathon)
    except Exception:
        log.exception("role menus: could not unbind marathon %s", marathon["id"])


# --- the panel: one command, one ephemeral window ------------------------------------------------


STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}

ROOT = "root"
MENU_VIEW = "menu"
HAND_VIEW = "hand"
ROLES_VIEW = "roles"
NEW_EVENT_VIEW = "new_event"
ENDED_VIEW = "ended"
ATTACH_VIEW = "attach"
FILL_VIEW = "fill"
PEOPLE_MAX = 25
GRANTS_VIEW = "grants"
NEW_GRANT_VIEW = "new_grant"
GRANT_VIEW = "grant"
SET_END_VIEW = "set_end"

SITE_BUTTON = "Open on the site"
NEW_GRANT_LINE = "Giving <@&{role_id}> to <@{user_id}>. **How long for…** finishes it."
NEW_GRANT_NOBODY = "Pick who gets it and which role, and Black Bloc will ask how long for."
GRANT_GONE = (
    "Black Bloc has no record of that timed role any more, so nothing was changed. Press "
    "**Refresh** and pick again."
)
MENU_GONE = (
    "This server has no role menu called **{name}** any more, so nothing was changed. Press "
    "**Refresh** and pick again."
)
MENU_DELETED = "Deleted **{name}**. Nobody loses a role they already have."
BAD_NUMBER = (
    "**{given}** is not a whole number of days, so nothing was changed. Type a number, or 0."
)
LOOP_COUNTS = "menus due {due} · ended {ended} · failures {failures}"

DAYS_TITLE = "How long for?"
PUSH_TITLE = "Push the end date back"

DAYS_LABEL = "Days, or 0 for a role that never runs out"
PUSH_LABEL = "Days to add"

MODAL_WORD_MAX = 45
PLACEHOLDER_MAX = 100
SELECT_PLACEHOLDER_MAX = 150
BUTTON_MAX = 80
DATE_TYPED_MAX = 16
BUFFER_TYPED_MAX = 3
DATE_SHOWN = "%Y-%m-%d"
MOMENT_SHOWN = "%Y-%m-%d %H:%M"
END_WORD_KEYS = {
    menus.SET_END: "rolemenu_set_end_button",
    menus.END_MENU: "rolemenu_end_now_button",
    menus.USE_HELD: "rolemenu_use_held_button",
    menus.TYPE_DATE: "rolemenu_type_date_button",
    menus.BUFFER: "rolemenu_buffer_button",
    menus.NO_END_MOVE_ACTION: "rolemenu_no_end_button",
    menus.NEW_EVENT: "rolemenu_new_event_button",
    menus.TIMED_ROLES: "rolemenu_timed_roles_button",
    menus.ENDED: "rolemenu_ended_button",
    menus.GIVE: "rolemenu_give_button",
    menus.FILL: "rolemenu_fill_button",
    menus.TAKE_OFF: "rolemenu_take_button",
    menus.ATTACH: "rolemenu_attach_button",
    menus.RENAME: "rolemenu_rename_button",
    menus.NO_MARATHON: "rolemenu_no_marathon_button",
    menus.FILL_YES: "rolemenu_fill_yes",
}
TIMED_NEEDS_EVENT_KEY = "rolemenu_timed_needs_event_said"
KEPT_THROUGH_KEY = "rolemenu_kept_through_said"


def minutes_for(bot: Any, guild_id: int) -> int:
    return menus.panel_minutes(bot.store, guild_id)


def word(bot: Any, guild_id: int, key: str, limit: int | None = None, **fields: Any) -> str:
    """A staff-editable word, filled; Discord's own cap cuts it where a modal or button would."""
    text = menus.said(bot.store, guild_id, key, **fields)
    return text[:limit] if limit else text


def end_moves(bot: Any, guild_id: int) -> dict[str, str]:
    """Every button word; `{count}` is left for the one label that carries a number."""
    return {
        action: word(bot, guild_id, key, BUTTON_MAX, count="{count}")
        for action, key in END_WORD_KEYS.items()
    }


def local_moment(bot: Any, guild_id: int, at: Any, shape: str = MOMENT_SHOWN) -> str:
    """A moment in the server's own zone, for places a Discord timestamp cannot render."""
    when = parse_ts(at)
    if when is None:
        return str(bot.store.get(guild_id, ROLEMENU_END_NOT_KNOWN_KEY))
    zone = timezones.zone(bot.store.get(guild_id, "default_timezone")) or timezones.zone("UTC")
    return when.astimezone(zone).strftime(shape)


def discord_moment(style: str) -> Any:
    return lambda bot, guild_id, at: grants.stamp(at, style)


def end_label(
    bot: Any, guild_id: int, menu: Any, marathon_name: Any, when: Any = None
) -> str:
    """One menu's end in words: none, a date, or a marathon plus its buffer."""
    shown = when or discord_moment("D")
    source = menus.end_source(menu)
    if source == menus.NO_END:
        return word(bot, guild_id, "rolemenu_no_end_text")
    at = menu_value(menu, "ends_at")
    moment = (
        shown(bot, guild_id, at)
        if parse_ts(at) is not None
        else str(bot.store.get(guild_id, ROLEMENU_END_NOT_KNOWN_KEY))
    )
    if source == menus.MARATHON_END:
        return word(
            bot,
            guild_id,
            "rolemenu_end_marathon_text",
            when=moment,
            marathon=marathon_name or "?",
            buffer=menus.buffer_of(menu, default_buffer(bot, guild_id)),
        )
    return word(bot, guild_id, "rolemenu_end_date_text", when=moment)


async def marathon_name_of(bot: Any, guild_id: int, menu: Any) -> Any:
    if menus.end_source(menu) != menus.MARATHON_END:
        return None
    found = await marathon_row(bot.db, guild_id, menu_value(menu, "ends_marathon_id"))
    return found["name"] if found is not None else None


def wearing_count(bot: Any, guild_id: int, members: Any, role_ids: Any) -> Any:
    if members is None:
        return word(bot, guild_id, "rolemenu_wearing_unknown_text")
    return len(menus.wearers(members, role_ids))


def held_is_past(menu: Any, at: datetime | None = None) -> bool:
    held = parse_ts(menu_value(menu, "ends_held_at"))
    return held is not None and held <= (at or datetime.now(UTC))


def plan_counts(bot: Any, guild_id: int, plan: Any) -> dict[str, Any]:
    """The confirm's numbers, from the plan the pass itself reads; `?` while members load."""
    if plan is None:
        unknown = word(bot, guild_id, "rolemenu_wearing_unknown_text")
        return {"roles": unknown, "members": unknown, "keep": unknown}
    return {"roles": plan.roles, "members": plan.members, "keep": plan.keep}


def end_now_question(bot: Any, guild_id: int, plan: Any) -> str:
    return word(bot, guild_id, "rolemenu_end_now_question", **plan_counts(bot, guild_id, plan))


def use_held_question(
    bot: Any, guild_id: int, menu: Any, plan: Any, when: Any = None
) -> str | None:
    """What Use the earlier end asks, with the plan's counts; None when no earlier end waits."""
    held = menu_value(menu, "ends_held_at")
    if not held:
        return None
    shown = when or discord_moment("F")
    return word(
        bot,
        guild_id,
        "rolemenu_use_held_past_question" if held_is_past(menu) else "rolemenu_use_held_question",
        menu=event_name(menu),
        when=shown(bot, guild_id, held),
        **plan_counts(bot, guild_id, plan),
    )


def failure_count(menu: Any) -> int:
    try:
        found = json.loads(menu_value(menu, "end_failures") or "[]")
    except (TypeError, ValueError):
        return 0
    return len(found) if isinstance(found, list) else 0


async def bindable_marathons(db: Any, guild_id: int, *, at: datetime | None = None) -> list[Any]:
    """Every marathon on the list (archived ones live elsewhere), still to end first."""
    cur = await db.conn.execute(
        "SELECT id, name, ends_at FROM marathons WHERE guild_id = ?", (int(guild_id),)
    )
    now = at or datetime.now(UTC)
    rows = list(await cur.fetchall())

    def order(row: Any) -> tuple[int, str, int]:
        end = parse_ts(row["ends_at"])
        if end is None:
            return (1, "", int(row["id"]))
        return (0 if end >= now else 2, end.astimezone(UTC).isoformat(), int(row["id"]))

    return sorted(rows, key=order)


async def pings_refusal(bot: Any, guild: Any, role_ids: Any) -> str | None:
    """A role members opt into from `/pings` never sits on a menu that ends; named in words."""
    from ... import pings

    owned = await pings.owned_role_ids(bot, guild.id)
    for role_id in role_ids or ():
        if int(role_id) in owned:
            return word(bot, guild.id, PINGS_ROLE_KEY, name=role_name(guild, role_id))
    return None


async def delete_refusal(bot: Any, guild: Any, menu: Any, when: Any = None) -> str | None:
    """Why an event with an end still to come and people assigned to it is not deleted."""
    if menu is None or menu_value(menu, "ended_at"):
        return None
    end = parse_ts(menu_value(menu, "ends_at"))
    if end is None or end <= datetime.now(UTC):
        return None
    count = await timed.assigned_people(bot.db, guild.id, menu["id"])
    if count == 0:
        return None
    shown = when or discord_moment("F")
    return word(
        bot,
        guild.id,
        "rolemenu_delete_refused_said",
        menu=event_name(menu),
        when=shown(bot, guild.id, menu["ends_at"]),
        members=count,
    )


def add_site_button(view: Any, bot: Any, row: int) -> None:
    """No origin, no button — a link that goes nowhere is worse than no link at all."""
    url = menus.site_page_url(getattr(getattr(bot, "settings", None), "origin", ""))
    if not url:
        return
    view.add_item(
        discord.ui.Button(style=discord.ButtonStyle.link, label=SITE_BUTTON, url=url, row=row)
    )


def who_is(guild: Any, user_id: Any) -> str:
    member = guild.get_member(int(user_id)) if guild is not None else None
    return str(getattr(member, "display_name", None) or user_id)


def grant_giver(row: Any) -> str:
    return f"<@{row['granted_by']}>" if row["granted_by"] else "Black Bloc"


class RoleMenuPanel(Panel):
    def __init__(self, minutes: int) -> None:
        super().__init__(minutes, footer=menus.PANEL_TIMEOUT_FOOTER)
        self.where = ROOT
        self.menu_name = ""
        self.grant_id: int | None = None
        self.member_id: int | None = None
        self.role_id: int | None = None
        self.removing: bool | None = None
        self.given = 0
        self.home: Any = None


SLUG = re.compile(r"[^a-z0-9]+")
NAME_MAX = 60


async def free_name(db: Any, guild_id: int, title: str) -> str:
    """The event's stored key: its name in lowercase dashes, numbered when already taken."""
    base = SLUG.sub("-", title.lower()).strip("-")[:NAME_MAX] or "event"
    found, n = base, 1
    while await get_menu(db, guild_id, found) is not None:
        n += 1
        found = f"{base}-{n}"
    return found


async def make_event(
    bot: Any,
    guild: Any,
    actor: Any,
    title: Any,
    *,
    marathon_id: Any = None,
    ends_at: Any = None,
    via: str = VIA_DISCORD,
) -> Any:
    """A new event: its name, and an end from a tracked marathon or a typed date."""
    wanted = check_title(str(title or "").strip())
    if not wanted:
        raise MenuLimitError(word(bot, guild.id, "rolemenu_event_needs_name_said"))
    if marathon_id is not None:
        marathon = await marathon_row(bot.db, guild.id, marathon_id)
        if marathon is None:
            raise ValueError(f"no marathon {marathon_id!r} in this server")
        await refuse_taken_marathon(bot, guild, marathon)
    name = await free_name(bot.db, guild.id, wanted)
    menu_id = await make_menu(bot, guild, actor, name, wanted, None, STAFF_MODE, via=via)
    menu = await get_menu_by_id(bot.db, menu_id)
    if marathon_id is not None:
        await set_menu_end(
            bot, guild, actor, menu, source=menus.MARATHON_END, marathon_id=marathon_id, via=via
        )
    elif ends_at is not None:
        await set_menu_end(bot, guild, actor, menu, source=menus.DATE_END, ends_at=ends_at, via=via)
    return await get_menu_by_id(bot.db, menu_id)


async def attach_marathon(
    bot: Any, guild: Any, actor: Any, menu: Any, marathon_id: Any, *, via: str = VIA_DISCORD
) -> str | None:
    """A dated event starts following a marathon; an earlier end it brings waits for staff."""
    marathon = await marathon_row(bot.db, guild.id, marathon_id)
    if marathon is None:
        raise ValueError(f"no marathon {marathon_id!r} in this server")
    await refuse_taken_marathon(bot, guild, marathon, menu["id"])
    candidate = menus.ends_at_of(
        {"ends_source": menus.MARATHON_END}, marathon, default_buffer(bot, guild.id)
    )
    current = menu_value(menu, "ends_at")
    floor = bot.store.get(guild.id, ROLEMENU_END_MOVED_MINUTES_KEY)
    holding = bool(bot.store.get(guild.id, ROLEMENU_END_EARLIER_HOLDS_KEY))
    if not (
        holding
        and current
        and menus.pulls_earlier(current, menu_value(menu, "ends_told_at"), candidate, floor)
    ):
        return await set_menu_end(
            bot, guild, actor, menu, source=menus.MARATHON_END, marathon_id=marathon_id, via=via
        )
    async with end_lock(bot, menu["id"]):
        await bot.db.conn.execute(
            "UPDATE role_menus SET ends_source = ?, ends_marathon_id = ?, buffer_days = NULL, "
            "ends_held_at = ?, ends_set_by = ?, ends_set_at = ? WHERE id = ?",
            (
                menus.MARATHON_END,
                int(marathon["id"]),
                candidate,
                actor_id(actor),
                now_iso(),
                int(menu["id"]),
            ),
        )
        await bot.db.conn.commit()
    await log_action(
        bot,
        guild,
        kind_via("role_menu.end_set", via),
        actor=actor,
        details={
            "menu": menu["name"],
            "source": menus.MARATHON_END,
            "marathon_id": int(marathon["id"]),
            "buffer_days": None,
            "was": current,
            "ends_at": current,
            "held": candidate,
            "via": via,
        },
    )
    fresh = await get_menu_by_id(bot.db, menu["id"])
    await end_was_held(bot, guild, fresh, marathon["id"], candidate, None, floor)
    return current


async def follow_marathon_end(
    bot: Any, guild: Any, actor: Any, menu: Any, marathon_id: Any, *, via: str = VIA_DISCORD
) -> str | None:
    """Change the end to a marathon: a dated event ATTACHES (an earlier end waits for staff); one
    already following a marathon switches and keeps its buffer."""
    if menus.end_source(menu) != menus.MARATHON_END:
        return await attach_marathon(bot, guild, actor, menu, marathon_id, via=via)
    return await set_menu_end(
        bot,
        guild,
        actor,
        menu,
        source=menus.MARATHON_END,
        marathon_id=marathon_id,
        buffer_days=menu_value(menu, "buffer_days"),
        via=via,
    )


async def fill_preview(bot: Any, guild: Any, menu: Any) -> list[Any]:
    """The schedule's people against the event: who is matched, who is still to give, who is not."""
    from ..content.marathon import runs_of

    marathon_id = menu_value(menu, "ends_marathon_id")
    if menus.end_source(menu) != menus.MARATHON_END or marathon_id is None:
        return []
    runs = await runs_of(bot.db, int(marathon_id))
    present = {int(member.id) for member in getattr(guild, "members", ()) or ()}
    roles = {part: bot.store.get(guild.id, key) for part, key in fill.ROLE_KEYS.items()}
    assigned = {
        (int(row["user_id"]), int(row["role_id"]))
        for row in await timed.event_grants(bot.db, guild.id, menu["id"])
    }
    return fill.plan_fill(
        fill.people_of(runs), roles, await timed.role_ids(bot.db, guild.id), present, assigned
    )


async def fill_from_schedule(
    bot: Any, guild: Any, actor: Any, menu: Any, *, via: str = VIA_DISCORD
) -> dict[str, int]:
    """The preview's missing people get their part's role on this event; a re-run adds only them."""
    totals = {"given": 0, "had": 0, "already": 0, "refused": 0}
    for line in await fill_preview(bot, guild, menu):
        people = [guild.get_member(user) for user in line.missing]
        people = [one for one in people if one is not None]
        if not people or line.role_id is None:
            continue
        found = await give_event_role(
            bot, guild, actor, menu, line.role_id, people, source=grants.SCHEDULE, via=via
        )
        for key in totals:
            totals[key] += len(found[key])
    return totals


def part_word(bot: Any, guild_id: int, part: str) -> str:
    return str(bot.store.get(guild_id, f"marathon_part_{part}") or part)


def fill_lines(bot: Any, guild_id: int, lines: Any) -> list[str]:
    said: list[str] = []
    for line in lines:
        part = part_word(bot, guild_id, line.part)
        if line.role_id is None:
            said.append(
                word(
                    bot,
                    guild_id,
                    "rolemenu_fill_no_role_line",
                    part=part,
                    setting=fill.ROLE_KEYS[line.part],
                )
            )
        elif not line.timed:
            said.append(
                word(bot, guild_id, "rolemenu_fill_not_timed_line", part=part, role_id=line.role_id)
            )
        else:
            said.append(
                word(
                    bot,
                    guild_id,
                    "rolemenu_fill_line",
                    part=part,
                    role_id=line.role_id,
                    matched=len(line.matched),
                    missing=len(line.missing),
                )
            )
        if line.unmatched:
            shown = ", ".join(line.unmatched[: fill.NAMES_SHOWN])
            more = len(line.unmatched) - fill.NAMES_SHOWN
            said.append(
                word(
                    bot,
                    guild_id,
                    "rolemenu_fill_unmatched_line",
                    part=part,
                    count=len(line.unmatched),
                    names=shown + (f" +{more}" if more > 0 else ""),
                )
            )
    return said


def event_moves(bot: Any, guild_id: int) -> dict[str, str]:
    return end_moves(bot, guild_id)


def end_text(bot: Any, guild_id: int, menu: Any, marathon_name: Any) -> str:
    if menus.end_source(menu) == menus.DATE_END:
        return word(
            bot,
            guild_id,
            "rolemenu_end_date_only_text",
            end=end_label(bot, guild_id, menu, marathon_name),
        )
    return end_label(bot, guild_id, menu, marathon_name)


async def root_line(bot: Any, guild: Any, menu: Any, members: Any = None) -> str:
    _ = members
    return word(
        bot,
        guild.id,
        "rolemenu_root_line",
        name=event_name(menu),
        roles=len(await timed.role_ids(bot.db, guild.id)),
        wearing=await timed.assigned_people(bot.db, guild.id, menu["id"]),
        end=end_text(bot, guild.id, menu, await marathon_name_of(bot, guild.id, menu)),
    )


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, RoleMenuPanel]:
    """The events still to end, one line each; the ended ones fold behind a count."""
    _ = actor
    rows = await timed.open_events(bot.db, guild.id)
    ended = await timed.ended_events(bot.db, guild.id)
    lines = [await root_line(bot, guild, menu) for menu in rows] or [
        word(bot, guild.id, "rolemenu_no_events_line")
    ]
    embed = discord.Embed(
        title=word(bot, guild.id, "rolemenu_panel_title", 256), description=clamped(lines)
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    if rows:
        view.add_item(EventPick(bot, guild.id, rows, row=0))
    for move in menus.root_buttons(ended=len(ended), words=event_moves(bot, guild.id)):
        view.add_item(MoveButton(move))
    add_site_button(view, bot, row=2)
    return (embed, view)


async def build_ended(bot: Any, guild: Any) -> tuple[discord.Embed, RoleMenuPanel]:
    rows = await timed.ended_events(bot.db, guild.id)
    lines = [
        word(
            bot,
            guild.id,
            "rolemenu_ended_event_line",
            name=event_name(menu),
            when=grants.stamp(menu["ended_at"], "D"),
            members=int(menu_value(menu, "end_members", 0)),
        )
        for menu in rows
    ] or [word(bot, guild.id, "rolemenu_no_events_line")]
    embed = discord.Embed(
        title=word(bot, guild.id, "rolemenu_ended_title", 256), description=clamped(lines)
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = ENDED_VIEW
    if rows:
        view.add_item(EventPick(bot, guild.id, rows, row=0))
    for move in menus.back_buttons():
        view.add_item(MoveButton(move))
    return (embed, view)


async def card_lines(bot: Any, guild: Any, menu: Any, options: Any) -> list[str]:
    assigned = await timed.assigned_by_role(bot.db, guild.id, menu["id"])
    lines = [f"**{event_name(menu)}**"]
    for row in options:
        lines.append(
            word(
                bot,
                guild.id,
                "rolemenu_event_role_line",
                label=row["label"],
                role_id=row["role_id"],
                assigned=assigned.get(int(row["role_id"]), 0),
            )
        )
    if not options:
        lines.append(word(bot, guild.id, "rolemenu_no_timed_roles_line"))
    lines.append(
        end_text(bot, guild.id, menu, await marathon_name_of(bot, guild.id, menu))
    )
    if menu_value(menu, "ends_set_by"):
        lines.append(
            word(
                bot,
                guild.id,
                "rolemenu_end_set_by_line",
                who=f"<@{menu['ends_set_by']}>",
                when=grants.stamp(menu_value(menu, "ends_set_at"), "R"),
            )
        )
    if menu_value(menu, "ended_at"):
        lines.append(
            word(
                bot,
                guild.id,
                "rolemenu_ended_line",
                when=grants.stamp(menu["ended_at"], "D"),
                members=int(menu_value(menu, "end_members", 0)),
                failures=failure_count(menu),
            )
        )
    held = menu_value(menu, "ends_held_at")
    if held:
        lines.append(word(bot, guild.id, "rolemenu_end_held_line", to=grants.stamp(held, "F")))
    return lines


async def build_menu(
    bot: Any, guild: Any, name: str
) -> tuple[discord.Embed | None, RoleMenuPanel | None]:
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        return (None, None)
    options = await get_options(bot.db, menu["id"])
    embed = discord.Embed(
        title=word(bot, guild.id, "rolemenu_event_title", 256, name=event_name(menu)),
        description=clamped(await card_lines(bot, guild, menu, options)),
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = MENU_VIEW
    view.menu_name = menu["name"]
    source = menus.end_source(menu)
    for move in menus.event_buttons(
        open_=not menu_value(menu, "ended_at"),
        roles=len(options),
        marathon=source == menus.MARATHON_END and menu_value(menu, "ends_marathon_id") is not None,
        attachable=source != menus.MARATHON_END,
        assigned=bool(await timed.event_grants(bot.db, guild.id, menu["id"])),
        held=bool(menu_value(menu, "ends_held_at")),
        words=event_moves(bot, guild.id),
    ):
        view.add_item(MoveButton(move))
    return (embed, view)


async def free_marathons(bot: Any, guild: Any, menu_id: Any = None) -> list[Any]:
    """Marathons with no open event yet, or followed by `menu_id` itself — one event each."""
    found = []
    for row in await bindable_marathons(bot.db, guild.id):
        taken = await timed.event_for_marathon(bot.db, guild.id, row["id"])
        if taken is None or (menu_id is not None and int(taken["id"]) == int(menu_id)):
            found.append(row)
    return found


async def taken_refusal(bot: Any, guild: Any, marathon: Any, menu_id: Any = None) -> str | None:
    """Why this marathon cannot take another event: the open one that already follows it."""
    taken = await timed.event_for_marathon(bot.db, guild.id, marathon["id"])
    if taken is None or (menu_id is not None and int(taken["id"]) == int(menu_id)):
        return None
    return word(
        bot,
        guild.id,
        "rolemenu_marathon_taken_said",
        marathon=marathon["name"],
        event=event_name(taken),
    )


async def refuse_taken_marathon(bot: Any, guild: Any, marathon: Any, menu_id: Any = None) -> None:
    refused = await taken_refusal(bot, guild, marathon, menu_id)
    if refused:
        raise MarathonTakenError(refused)


async def build_new_event(bot: Any, guild: Any) -> tuple[discord.Embed, RoleMenuPanel]:
    marathons = await free_marathons(bot, guild)
    embed = discord.Embed(title=word(bot, guild.id, "rolemenu_new_event_title", 256))
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = NEW_EVENT_VIEW
    if marathons:
        view.add_item(MarathonPick(bot, guild.id, marathons, None, row=0))
    for move in menus.new_event_buttons(event_moves(bot, guild.id)):
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_attach(
    bot: Any, guild: Any, name: str
) -> tuple[discord.Embed | None, RoleMenuPanel | None]:
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        return (None, None)
    marathons = await free_marathons(bot, guild)
    embed = discord.Embed(
        title=word(bot, guild.id, "rolemenu_attach_title", 256, name=event_name(menu)),
        description=end_text(bot, guild.id, menu, None),
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = ATTACH_VIEW
    view.menu_name = menu["name"]
    if marathons:
        view.add_item(MarathonPick(bot, guild.id, marathons, None, row=0))
    for move in menus.back_buttons():
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_timed_roles(bot: Any, guild: Any) -> tuple[discord.Embed, RoleMenuPanel]:
    rows = await timed.listed(bot.db, guild.id)
    members = await members_of(guild)
    lines = [
        word(
            bot,
            guild.id,
            "rolemenu_role_line",
            label=row["label"],
            role_id=row["role_id"],
            wearing=wearing_count(bot, guild.id, members, [row["role_id"]]),
        )
        for row in rows
    ] or [word(bot, guild.id, "rolemenu_no_timed_roles_line")]
    embed = discord.Embed(
        title=word(bot, guild.id, "rolemenu_timed_roles_title", 256), description=clamped(lines)
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = ROLES_VIEW
    if len(rows) < timed.LIST_MAX:
        view.add_item(
            TimedRoleAdd(word(bot, guild.id, "rolemenu_timed_add_pick", SELECT_PLACEHOLDER_MAX))
        )
    if rows:
        view.add_item(
            TimedRolePick(
                rows,
                word(bot, guild.id, "rolemenu_timed_remove_pick", SELECT_PLACEHOLDER_MAX),
                row=1,
            )
        )
    for move in menus.back_buttons():
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_hand_out(
    bot: Any, guild: Any, name: str, role_id: Any, removing: Any, given: int = 0
) -> tuple[discord.Embed | None, RoleMenuPanel | None]:
    """Give roles… / Take roles off…: a timed role, then up to 25 people a batch."""
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        return (None, None)
    options = await get_options(bot.db, menu["id"])
    title_key = "rolemenu_take_title" if removing else "rolemenu_give_title"
    lines = []
    if role_id:
        lines.append(
            word(
                bot,
                guild.id,
                "rolemenu_taken_line" if removing else "rolemenu_given_line",
                role_id=role_id,
                count=given,
            )
        )
    embed = discord.Embed(
        title=word(bot, guild.id, title_key, 256, name=event_name(menu)),
        description=clamped(lines) if lines else None,
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = HAND_VIEW
    view.menu_name = menu["name"]
    view.role_id = int(role_id) if role_id else None
    view.removing = bool(removing)
    view.given = int(given)
    if options:
        view.add_item(
            TimedRolePick(
                options,
                word(bot, guild.id, "rolemenu_pick_role_placeholder", SELECT_PLACEHOLDER_MAX),
                row=0,
                chosen=view.role_id,
            )
        )
    if view.role_id:
        view.add_item(
            PeoplePick(
                word(bot, guild.id, "rolemenu_pick_people_placeholder", SELECT_PLACEHOLDER_MAX)
            )
        )
    for move in menus.back_buttons():
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_fill(
    bot: Any, guild: Any, name: str
) -> tuple[discord.Embed | None, RoleMenuPanel | None]:
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        return (None, None)
    lines = await fill_preview(bot, guild, menu)
    embed = discord.Embed(
        title=word(bot, guild.id, "rolemenu_fill_title", 256, name=event_name(menu)),
        description=clamped(fill_lines(bot, guild.id, lines)) or None,
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = FILL_VIEW
    view.menu_name = menu["name"]
    for move in menus.fill_buttons(
        missing=fill.missing_count(lines), words=event_moves(bot, guild.id)
    ):
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_set_end(
    bot: Any, guild: Any, name: str
) -> tuple[discord.Embed | None, RoleMenuPanel | None]:
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        return (None, None)
    marathons = await free_marathons(bot, guild, menu["id"])
    line = end_label(
        bot, guild.id, menu, await marathon_name_of(bot, guild.id, menu), discord_moment("F")
    )
    embed = discord.Embed(
        title=word(bot, guild.id, "rolemenu_set_end_title", 256, name=event_name(menu)),
        description=line,
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = SET_END_VIEW
    view.menu_name = menu["name"]
    if marathons:
        view.add_item(MarathonPick(bot, guild.id, marathons, menu, row=0))
    for move in menus.set_end_buttons(
        source=menus.end_source(menu), words=end_moves(bot, guild.id)
    ):
        view.add_item(MoveButton(move))
    return (embed, view)


async def audit_rows(bot: Any, guild: Any, member_id: Any) -> tuple[list[Any], list[Any]]:
    """(audit lines, openable grant rows): every running grant, and timed roles worn by hand."""
    wanted = int(member_id) if member_id else None
    rows = await menus.active_grants(bot.db, guild.id, user_id=wanted)
    ends = await timed.soonest_ends(bot.db, guild.id)
    held = {(int(row["user_id"]), int(row["role_id"])) for row in rows}
    worn: list[Any] = []
    if ends:
        members = await members_of(guild) or list(getattr(guild, "members", ()) or ())
        for member, role_ids in menus.wearers(members, list(ends)):
            if wanted is not None and int(member.id) != wanted:
                continue
            for role_id in role_ids:
                if (int(member.id), role_id) not in held:
                    worn.append(
                        {
                            "user_id": int(member.id),
                            "role_id": role_id,
                            "expires_at": ends[role_id]["ends_at"],
                        }
                    )
    return sorted([*rows, *worn], key=menus.grant_order), rows


async def build_grants(
    bot: Any, guild: Any, member_id: Any
) -> tuple[discord.Embed, RoleMenuPanel]:
    lines, rows = await audit_rows(bot, guild, member_id)
    embed = discord.Embed(
        title=menus.GRANTS_TITLE,
        description=clamped(menus.grant_lines(lines, one_member=bool(member_id))),
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = GRANTS_VIEW
    view.member_id = int(member_id) if member_id else None
    view.add_item(WhoPick(menus.WHOSE_ROLES, row=0))
    if rows:
        view.add_item(GrantPick(rows, guild, row=1))
    for move in menus.grants_buttons():
        view.add_item(MoveButton(move))
    return (embed, view)


def build_new_grant(
    bot: Any, guild: Any, member_id: Any, role_id: Any
) -> tuple[discord.Embed, RoleMenuPanel]:
    line = (
        NEW_GRANT_LINE.format(role_id=role_id, user_id=member_id)
        if member_id and role_id
        else NEW_GRANT_NOBODY
    )
    embed = discord.Embed(title=menus.NEW_GRANT_TITLE, description=line)
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = NEW_GRANT_VIEW
    view.member_id = int(member_id) if member_id else None
    view.role_id = int(role_id) if role_id else None
    view.add_item(WhoPick(menus.WHO_GETS_IT, row=0))
    view.add_item(NewRolePick(row=1, placeholder=menus.WHICH_ROLE))
    for move in menus.new_grant_buttons(member=bool(member_id), role=bool(role_id)):
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_grant(
    bot: Any, guild: Any, grant_id: Any
) -> tuple[discord.Embed | None, RoleMenuPanel | None]:
    row = await grants.get_grant(bot.db, int(grant_id)) if grant_id else None
    if row is None or row["guild_id"] != guild.id:
        return (None, None)
    lines = [
        f"<@{row['user_id']}> · <@&{row['role_id']}>",
        f"Given by: {grant_giver(row)}",
        f"How it started: {row['source']}",
        f"Ends: {grants.stamp(row['expires_at']) if row['expires_at'] else menus.NO_END_DATE}",
    ]
    if row["removed_at"]:
        lines.append(f"Closed {grants.stamp(row['removed_at'])} — {row['removed_reason']}")
    refused = None if row["removed_at"] else await push_back_refusal(bot, guild, row)
    if refused:
        lines.append(refused)
    embed = discord.Embed(
        title=menus.GRANT_TITLE.format(grant_id=row["id"]), description=clamped(lines)
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = GRANT_VIEW
    view.grant_id = int(row["id"])
    for move in menus.grant_buttons(
        ends=bool(row["expires_at"]) and not refused, removed=bool(row["removed_at"])
    ):
        view.add_item(MoveButton(move))
    return (embed, view)


def confirm_panel(bot: Any, guild: Any, previous: Any) -> RoleMenuPanel:
    """The confirm card keeps the place it was raised from, so the way back lands there."""
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = getattr(previous, "where", ROOT)
    view.menu_name = getattr(previous, "menu_name", "")
    view.grant_id = getattr(previous, "grant_id", None)
    view.member_id = getattr(previous, "member_id", None)
    view.home = getattr(previous, "home", None)
    return view


# --- rendering -----------------------------------------------------------------------------------


async def render(interaction: discord.Interaction, embed: Any, view: Any, previous: Any) -> None:
    view.home = view.home or getattr(previous, "home", None)
    retire(previous)
    view.message = await interaction.edit_original_response(
        embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
    )


async def render_panel(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_panel(interaction.client, interaction.guild, interaction.user)
    await render(interaction, embed, view, previous)


async def render_built(
    interaction: discord.Interaction, built: Any, name: str, previous: Any
) -> None:
    """A card for one event, or the root with the reason once that event is gone."""
    embed, view = built
    if view is None:
        await render_panel(interaction, previous)
        await answer(interaction, MENU_GONE.format(name=name))
        return
    await render(interaction, embed, view, previous)


async def render_menu(interaction: discord.Interaction, name: str, previous: Any = None) -> None:
    built = await build_menu(interaction.client, interaction.guild, name)
    await render_built(interaction, built, name, previous)


async def render_set_end(
    interaction: discord.Interaction, name: str, previous: Any = None
) -> None:
    built = await build_set_end(interaction.client, interaction.guild, name)
    await render_built(interaction, built, name, previous)


async def render_attach(interaction: discord.Interaction, name: str, previous: Any = None) -> None:
    built = await build_attach(interaction.client, interaction.guild, name)
    await render_built(interaction, built, name, previous)


async def render_fill(interaction: discord.Interaction, name: str, previous: Any = None) -> None:
    built = await build_fill(interaction.client, interaction.guild, name)
    await render_built(interaction, built, name, previous)


async def render_hand_out(
    interaction: discord.Interaction,
    name: str,
    role_id: Any,
    removing: Any,
    previous: Any = None,
    given: int = 0,
) -> None:
    built = await build_hand_out(
        interaction.client, interaction.guild, name, role_id, removing, given
    )
    await render_built(interaction, built, name, previous)


async def render_timed_roles(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_timed_roles(interaction.client, interaction.guild)
    await render(interaction, embed, view, previous)


async def render_new_event(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_new_event(interaction.client, interaction.guild)
    await render(interaction, embed, view, previous)


async def render_ended(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_ended(interaction.client, interaction.guild)
    await render(interaction, embed, view, previous)


async def render_grants(
    interaction: discord.Interaction, member_id: Any, previous: Any = None
) -> None:
    embed, view = await build_grants(interaction.client, interaction.guild, member_id)
    await render(interaction, embed, view, previous)


async def render_new_grant(
    interaction: discord.Interaction, member_id: Any, role_id: Any, previous: Any = None
) -> None:
    embed, view = build_new_grant(interaction.client, interaction.guild, member_id, role_id)
    await render(interaction, embed, view, previous)


async def render_grant(
    interaction: discord.Interaction, grant_id: Any, previous: Any = None
) -> None:
    embed, view = await build_grant(interaction.client, interaction.guild, grant_id)
    if view is None:
        await render_grants(interaction, getattr(previous, "member_id", None), previous)
        await answer(interaction, GRANT_GONE)
        return
    await render(interaction, embed, view, previous)


async def guarded(interaction: discord.Interaction) -> bool:
    """`member.edit` is a side effect the HTTP guard cannot see, so the move asks it (item 1)."""
    guard = getattr(interaction.client, "guard", None)
    if guard is None or guard.allows_channel(interaction.channel_id):
        return True
    await answer(interaction, guard.refusal_message())
    return False


async def open_root(interaction: discord.Interaction, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_panel(interaction, previous)


async def open_menu(interaction: discord.Interaction, name: str, previous: Any = None) -> None:
    if not await opened(interaction):
        return
    await render_menu(interaction, name, previous)


async def open_grants(interaction: discord.Interaction, member_id: Any, previous: Any) -> None:
    if not await opened(interaction):
        return
    await render_grants(interaction, member_id, previous)


async def open_grants_from(interaction: discord.Interaction, previous: Any, home: Any) -> None:
    """Another panel's door onto the Grants console; `home` is what its Back presses."""
    if not await opened(interaction):
        return
    embed, view = await build_grants(interaction.client, interaction.guild, None)
    view.home = home
    await render(interaction, embed, view, previous)


async def open_grant(interaction: discord.Interaction, grant_id: Any, previous: Any) -> None:
    if not await opened(interaction):
        return
    await render_grant(interaction, grant_id, previous)


async def refresh_where(interaction: discord.Interaction, view: Any) -> None:
    if not await opened(interaction):
        return
    where, name = view.where, view.menu_name
    if where == MENU_VIEW:
        await render_menu(interaction, name, view)
    elif where == SET_END_VIEW:
        await render_set_end(interaction, name, view)
    elif where == ATTACH_VIEW:
        await render_attach(interaction, name, view)
    elif where == FILL_VIEW:
        await render_fill(interaction, name, view)
    elif where == HAND_VIEW:
        await render_hand_out(interaction, name, view.role_id, view.removing, view, view.given)
    elif where == ROLES_VIEW:
        await render_timed_roles(interaction, view)
    elif where == NEW_EVENT_VIEW:
        await render_new_event(interaction, view)
    elif where == ENDED_VIEW:
        await render_ended(interaction, view)
    elif where == GRANTS_VIEW:
        await render_grants(interaction, view.member_id, view)
    elif where == GRANT_VIEW:
        await render_grant(interaction, view.grant_id, view)
    elif where == NEW_GRANT_VIEW:
        await render_new_grant(interaction, view.member_id, view.role_id, view)
    else:
        await render_panel(interaction, view)


async def back_from(interaction: discord.Interaction, view: Any) -> None:
    if view.where == GRANTS_VIEW and view.home is not None:
        await view.home(interaction, view)
        return
    if not await opened(interaction):
        return
    if view.where in (HAND_VIEW, SET_END_VIEW, ATTACH_VIEW, FILL_VIEW):
        await render_menu(interaction, view.menu_name, view)
    elif view.where in (GRANT_VIEW, NEW_GRANT_VIEW):
        await render_grants(interaction, view.member_id, view)
    else:
        await render_panel(interaction, view)


# --- the moves, one function each ----------------------------------------------------------------


async def menu_or_gone(interaction: discord.Interaction, previous: Any) -> Any:
    """The event this card is about, or None once the root is back up with the reason."""
    name = previous.menu_name
    menu = await get_menu(interaction.client.db, interaction.guild.id, name)
    if menu is None:
        await render_panel(interaction, previous)
        await answer(interaction, MENU_GONE.format(name=name))
    return menu


async def said_end(interaction: discord.Interaction, menu: Any, end: Any) -> None:
    bot, guild = interaction.client, interaction.guild
    fresh = await get_menu_by_id(bot.db, menu["id"])
    if menus.end_source(fresh) == menus.NO_END:
        cleared = word(bot, guild.id, "rolemenu_end_cleared_said", menu=event_name(menu))
        await answer(interaction, cleared)
        return
    when = (
        grants.stamp(end, "F")
        if parse_ts(end) is not None
        else str(bot.store.get(guild.id, ROLEMENU_END_NOT_KNOWN_KEY))
    )
    said = word(bot, guild.id, "rolemenu_end_set_said", menu=event_name(menu), when=when)
    if menu_value(fresh, "ends_held_at"):
        said += " " + word(
            bot, guild.id, "rolemenu_end_held_line", to=grants.stamp(fresh["ends_held_at"], "F")
        )
    await answer(interaction, said)


async def run_new_event(
    interaction: discord.Interaction, previous: Any, *, title: Any, marathon_id: Any = None,
    typed: Any = None,
) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    ends_at = None
    if marathon_id is not None:
        marathon = await marathon_row(bot.db, guild.id, marathon_id)
        if marathon is None:
            await render_new_event(interaction, previous)
            await answer(interaction, word(bot, guild.id, "rolemenu_end_no_marathon_said"))
            return
        title = marathon["name"]
    else:
        refusal, ends_at = typed_refusal(bot, guild.id, typed)
        if refusal:
            await render_new_event(interaction, previous)
            await answer(interaction, refusal)
            return
    try:
        menu = await make_event(
            bot, guild, interaction.user, title, marathon_id=marathon_id, ends_at=ends_at
        )
    except MenuLimitError as exc:
        await render_new_event(interaction, previous)
        await answer(interaction, str(exc))
        return
    await render_menu(interaction, menu["name"], previous)
    await answer(
        interaction, word(bot, guild.id, "rolemenu_event_made_said", name=event_name(menu))
    )


def typed_refusal(bot: Any, guild_id: int, typed: Any) -> tuple[str | None, Any]:
    """(why not, the moment): a typed end that is unreadable or already gone is refused."""
    text = str(typed or "").strip()
    when = menus.typed_end(text, bot.store.get(guild_id, "default_timezone"))
    if when is None:
        return word(bot, guild_id, "rolemenu_end_bad_date_said", given=text[:40]), None
    if when <= datetime.now(UTC):
        return word(bot, guild_id, "rolemenu_end_past_said", when=grants.stamp(when, "F")), None
    return None, when


async def run_rename(interaction: discord.Interaction, typed: Any, previous: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    menu = await menu_or_gone(interaction, previous)
    if menu is None:
        return
    wanted = str(typed or "").strip()
    try:
        if not wanted:
            raise MenuLimitError(word(bot, guild.id, "rolemenu_event_needs_name_said"))
        await change_menu(bot, guild, interaction.user, menu["name"], title=wanted)
    except MenuLimitError as exc:
        await render_menu(interaction, menu["name"], previous)
        await answer(interaction, str(exc))
        return
    await render_menu(interaction, menu["name"], previous)
    await answer(interaction, word(bot, guild.id, "rolemenu_event_renamed_said", name=wanted))


async def run_add_timed(interaction: discord.Interaction, role_id: int, previous: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    role = guild.get_role(int(role_id))
    refused = (
        await add_timed_role(bot, guild, interaction.user, role)
        if role is not None
        else word(bot, guild.id, "rolemenu_timed_not_listed_said", name=role_id)
    )
    await render_timed_roles(interaction, previous)
    await answer(
        interaction,
        refused or word(bot, guild.id, "rolemenu_timed_added_said", name=role.name),
    )


async def run_drop_timed(interaction: discord.Interaction, role_id: int, previous: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    refused = await drop_timed_role(bot, guild, interaction.user, int(role_id))
    await render_timed_roles(interaction, previous)
    await answer(
        interaction,
        refused
        or word(bot, guild.id, "rolemenu_timed_removed_said", name=role_name(guild, role_id)),
    )


async def run_hand_out(interaction: discord.Interaction, users: Any, previous: Any) -> None:
    """One batch of up to 25; the card stays on the same role with the running count."""
    if not await guarded(interaction) or not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    menu = await menu_or_gone(interaction, previous)
    if menu is None:
        return
    people = [guild.get_member(int(getattr(one, "id", one))) for one in users or ()]
    people = [one for one in people if one is not None]
    move = take_event_role if previous.removing else give_event_role
    found = await move(bot, guild, interaction.user, menu, previous.role_id, people)
    count = previous.given + len(found["given"]) + len(found["had"])
    await render_hand_out(
        interaction, menu["name"], previous.role_id, previous.removing, previous, count
    )
    await answer(interaction, found["said"])


async def run_fill(interaction: discord.Interaction, previous: Any) -> None:
    if not await guarded(interaction) or not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    menu = await menu_or_gone(interaction, previous)
    if menu is None:
        return
    totals = await fill_from_schedule(bot, guild, interaction.user, menu)
    await render_fill(interaction, menu["name"], previous)
    key = "rolemenu_fill_done_said" if any(totals.values()) else "rolemenu_fill_nothing_said"
    await answer(interaction, word(bot, guild.id, key, **totals))


async def run_attach(interaction: discord.Interaction, marathon_id: int, previous: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    menu = await menu_or_gone(interaction, previous)
    if menu is None:
        return
    if await marathon_row(bot.db, guild.id, marathon_id) is None:
        await render_attach(interaction, menu["name"], previous)
        await answer(interaction, word(bot, guild.id, "rolemenu_end_no_marathon_said"))
        return
    try:
        end = await attach_marathon(bot, guild, interaction.user, menu, marathon_id)
    except MarathonTakenError as exc:
        await render_attach(interaction, menu["name"], previous)
        await answer(interaction, str(exc))
        return
    await render_menu(interaction, menu["name"], previous)
    await said_end(interaction, menu, end)


async def run_delete_menu(interaction: discord.Interaction, previous: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    name = previous.menu_name
    menu = await get_menu(bot.db, guild.id, name)
    refused = await delete_refusal(bot, guild, menu)
    if refused:
        await render_menu(interaction, name, previous)
        await answer(interaction, refused)
        return
    gone = await drop_menu(bot, guild, interaction.user, name)
    await render_panel(interaction, previous)
    await answer(
        interaction,
        MENU_DELETED.format(name=event_name(menu)) if gone else MENU_GONE.format(name=name),
    )


async def run_set_marathon(
    interaction: discord.Interaction, marathon_id: int, previous: Any
) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    menu = await menu_or_gone(interaction, previous)
    if menu is None:
        return
    if await marathon_row(bot.db, guild.id, marathon_id) is None:
        await render_set_end(interaction, menu["name"], previous)
        await answer(interaction, word(bot, guild.id, "rolemenu_end_no_marathon_said"))
        return
    try:
        end = await follow_marathon_end(bot, guild, interaction.user, menu, marathon_id)
    except MarathonTakenError as exc:
        await render_set_end(interaction, menu["name"], previous)
        await answer(interaction, str(exc))
        return
    await render_menu(interaction, menu["name"], previous)
    await said_end(interaction, menu, end)


async def run_typed_end(interaction: discord.Interaction, typed: Any, previous: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    menu = await menu_or_gone(interaction, previous)
    if menu is None:
        return
    refusal, when = typed_refusal(bot, guild.id, typed)
    if refusal:
        await render_set_end(interaction, menu["name"], previous)
        await answer(interaction, refusal)
        return
    end = await set_menu_end(
        bot, guild, interaction.user, menu, source=menus.DATE_END, ends_at=when
    )
    await render_menu(interaction, menu["name"], previous)
    await said_end(interaction, menu, end)


def read_buffer(value: Any) -> int | None:
    """Blank is the server's default; anything but 0-365 whole days is refused, never guessed."""
    typed = str(value or "").strip()
    if not typed:
        return None
    if not typed.isdigit() or int(typed) > menus.BUFFER_MAX:
        raise ValueError(typed)
    return int(typed)


async def run_buffer(interaction: discord.Interaction, typed: Any, previous: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    menu = await menu_or_gone(interaction, previous)
    if menu is None:
        return
    refusal = None
    try:
        days = read_buffer(typed)
    except ValueError as exc:
        days = None
        refusal = word(bot, guild.id, "rolemenu_end_bad_buffer_said", given=str(exc)[:40])
    if refusal is None and menus.end_source(menu) != menus.MARATHON_END:
        refusal = word(
            bot, guild.id, "rolemenu_buffer_needs_marathon_said", menu=event_name(menu)
        )
    if refusal is None and await marathon_row(bot.db, guild.id, menu["ends_marathon_id"]) is None:
        refusal = word(bot, guild.id, "rolemenu_end_no_marathon_said")
    if refusal:
        await render_set_end(interaction, menu["name"], previous)
        await answer(interaction, refusal)
        return
    try:
        end = await set_menu_end(
            bot,
            guild,
            interaction.user,
            menu,
            source=menus.MARATHON_END,
            marathon_id=menu["ends_marathon_id"],
            buffer_days=days,
        )
    except MarathonTakenError as exc:
        await render_set_end(interaction, menu["name"], previous)
        await answer(interaction, str(exc))
        return
    await render_menu(interaction, menu["name"], previous)
    await said_end(interaction, menu, end)


async def run_no_end(interaction: discord.Interaction, previous: Any) -> None:
    if not await opened(interaction):
        return
    menu = await menu_or_gone(interaction, previous)
    if menu is None:
        return
    end = await set_menu_end(
        interaction.client, interaction.guild, interaction.user, menu, source=menus.NO_END
    )
    await render_menu(interaction, menu["name"], previous)
    await said_end(interaction, menu, end)


async def run_end_now(interaction: discord.Interaction, previous: Any) -> None:
    if not await guarded(interaction) or not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    menu = await menu_or_gone(interaction, previous)
    if menu is None:
        return
    details = await end_menu_now(bot, guild, interaction.user, menu)
    await render_menu(interaction, menu["name"], previous)
    if details is None:
        guard = getattr(bot, "guard", None)
        await answer(
            interaction,
            guard.refusal_message()
            if guard is not None
            else word(bot, guild.id, "rolemenu_end_now_not_run_said", menu=event_name(menu)),
        )
        return
    await answer(
        interaction,
        word(
            bot,
            guild.id,
            ROLEMENU_ENDED_TEXT_KEY,
            menu=event_name(menu),
            roles=len(details["roles"]),
            members=details["members"],
            failures=details["failures"],
        ),
    )


async def run_use_held(interaction: discord.Interaction, previous: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    menu = await menu_or_gone(interaction, previous)
    if menu is None:
        return
    had = menu_value(menu, "ends_held_at")
    try:
        end = await use_held_end(bot, guild, interaction.user, menu) if had else None
    except MarathonTakenError as exc:
        await render_menu(interaction, menu["name"], previous)
        await answer(interaction, str(exc))
        return
    await render_menu(interaction, menu["name"], previous)
    if not had:
        await answer(
            interaction, word(bot, guild.id, "rolemenu_no_held_said", menu=event_name(menu))
        )
        return
    await said_end(interaction, menu, end)


async def run_grant(interaction: discord.Interaction, days: Any, previous: Any) -> None:
    if not await guarded(interaction) or not await opened(interaction):
        return
    guild = interaction.guild
    member = guild.get_member(int(previous.member_id)) if previous.member_id else None
    role = guild.get_role(int(previous.role_id)) if previous.role_id else None
    if member is None or role is None:
        await render_new_grant(interaction, previous.member_id, previous.role_id, previous)
        await answer(interaction, NEW_GRANT_NOBODY)
        return
    _, said = await grant_role(interaction.client, guild, interaction.user, member, role, days)
    await render_grants(interaction, previous.member_id, previous)
    await answer(interaction, said)


async def run_extend(interaction: discord.Interaction, days: Any, previous: Any) -> None:
    if not await opened(interaction):
        return
    row = await grants.get_grant(interaction.client.db, int(previous.grant_id))
    if row is None or row["removed_at"] or not row["expires_at"]:
        await render_grant(interaction, previous.grant_id, previous)
        await answer(interaction, GRANT_GONE)
        return
    _, said = await extend_role(
        interaction.client, interaction.guild, interaction.user, row, days
    )
    await render_grant(interaction, previous.grant_id, previous)
    await answer(interaction, said)


async def run_revoke(interaction: discord.Interaction, previous: Any) -> None:
    if not await guarded(interaction) or not await opened(interaction):
        return
    row = await grants.get_grant(interaction.client.db, int(previous.grant_id))
    if row is None or row["removed_at"]:
        await render_grant(interaction, previous.grant_id, previous)
        await answer(interaction, GRANT_GONE)
        return
    _, said = await revoke_grant(interaction.client, interaction.guild, interaction.user, row)
    await render_grant(interaction, previous.grant_id, previous)
    await answer(interaction, said)


# --- the controls --------------------------------------------------------------------------------


class MoveButton(discord.ui.Button):
    def __init__(self, move: Any) -> None:
        super().__init__(label=move.label[:BUTTON_MAX], style=STYLES[move.style], row=move.row)
        self.move = move

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        action = self.move.action
        if action == menus.REFRESH or action in (menus.KEEP, menus.LEAVE_IT):
            await refresh_where(interaction, view)
        elif action == menus.BACK:
            await back_from(interaction, view)
        elif action == menus.LOGS:
            await send_logs(interaction, "rolemenu")
        elif action in (menus.END_NOW, menus.END_MENU, menus.NO_END_MOVE_ACTION, menus.USE_HELD,
                        menus.DELETE):
            await self.ask_first(interaction, view, action)
        elif action in PLAIN_MOVES:
            await PLAIN_MOVES[action](interaction, view)
        else:
            await self.open_modal(interaction, view, action)

    async def ask_first(self, interaction: discord.Interaction, view: Any, action: str) -> None:
        """The moves nobody can undo ask once; every quieter move is one press."""
        if not await opened(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        if action == menus.END_NOW:
            row = await grants.get_grant(bot.db, int(view.grant_id))
            if row is None:
                await render_grant(interaction, view.grant_id, view)
                await answer(interaction, GRANT_GONE)
                return
            question = menus.END_QUESTION.format(role_id=row["role_id"], user_id=row["user_id"])
            moves = (
                menus.PanelMove(menus.END_YES, menus.END_YES_LABEL, "danger", 0),
                menus.PanelMove(menus.LEAVE_IT, menus.LEAVE_IT_LABEL, "secondary", 0),
            )
        else:
            menu = await menu_or_gone(interaction, view)
            if menu is None:
                return
            if action == menus.DELETE:
                refused = await delete_refusal(bot, guild, menu)
                if refused:
                    await render_menu(interaction, menu["name"], view)
                    await answer(interaction, refused)
                    return
                question = menus.DELETE_QUESTION.format(name=event_name(menu))
                yes = menus.PanelMove(menus.DELETE_YES, menus.DELETE_YES_LABEL, "danger", 0)
            elif action == menus.END_MENU:
                question = end_now_question(bot, guild.id, await end_plan(bot, guild, menu))
                yes = menus.PanelMove(
                    menus.END_MENU_YES,
                    word(bot, guild.id, "rolemenu_end_now_yes", BUTTON_MAX),
                    "danger",
                    0,
                )
            elif action == menus.USE_HELD:
                question = use_held_question(
                    bot, guild.id, menu, await end_plan(bot, guild, menu)
                )
                if question is None:
                    await render_menu(interaction, menu["name"], view)
                    await answer(
                        interaction,
                        word(bot, guild.id, "rolemenu_no_held_said", menu=event_name(menu)),
                    )
                    return
                yes = menus.PanelMove(
                    menus.USE_HELD_YES,
                    word(bot, guild.id, "rolemenu_use_held_yes", BUTTON_MAX),
                    "danger",
                    0,
                )
            else:
                question = word(bot, guild.id, "rolemenu_no_end_question", menu=event_name(menu))
                yes = menus.PanelMove(
                    menus.NO_END_YES,
                    word(bot, guild.id, "rolemenu_no_end_yes", BUTTON_MAX),
                    "danger",
                    0,
                )
            moves = (yes, menus.PanelMove(menus.KEEP, menus.KEEP_IT_LABEL, "secondary", 0))
        await confirm(
            interaction,
            confirm_panel(bot, guild, view),
            discord.Embed(title=menus.CONFIRM_TITLE, description=question),
            [MoveButton(move) for move in moves],
            view,
        )

    async def open_modal(self, interaction: discord.Interaction, view: Any, action: str) -> None:
        if not await still_staff(interaction):
            return
        if not await db_up(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        if action == menus.HOW_LONG:
            await interaction.response.send_modal(DaysModal(view, pushing=False))
            return
        if action == menus.PUSH_BACK:
            await interaction.response.send_modal(DaysModal(view, pushing=True))
            return
        if action == menus.NO_MARATHON:
            await interaction.response.send_modal(NewEventModal(bot, guild.id, view))
            return
        menu = await get_menu(bot.db, guild.id, view.menu_name)
        if menu is None:
            await answer(interaction, MENU_GONE.format(name=view.menu_name))
            return
        if action == menus.TYPE_DATE:
            await interaction.response.send_modal(
                DateModal(
                    view,
                    word(bot, guild.id, "rolemenu_date_title", MODAL_WORD_MAX),
                    word(bot, guild.id, "rolemenu_date_label", MODAL_WORD_MAX),
                    word(bot, guild.id, "rolemenu_date_placeholder", PLACEHOLDER_MAX),
                )
            )
            return
        if action == menus.BUFFER:
            await interaction.response.send_modal(
                BufferModal(
                    view,
                    word(bot, guild.id, "rolemenu_buffer_title", MODAL_WORD_MAX),
                    word(bot, guild.id, "rolemenu_buffer_label", MODAL_WORD_MAX),
                    menu_value(menu, "buffer_days"),
                )
            )
            return
        await interaction.response.send_modal(RenameModal(bot, guild.id, view, menu))


async def move_to(interaction: discord.Interaction, render_it: Any, *args: Any) -> None:
    if not await opened(interaction):
        return
    await render_it(interaction, *args)


PLAIN_MOVES = {
    menus.GRANTS: lambda i, v: open_grants(i, None, v),
    menus.NEW_GRANT: lambda i, v: move_to(i, render_new_grant, v.member_id, v.role_id, v),
    menus.NEW_EVENT: lambda i, v: move_to(i, render_new_event, v),
    menus.TIMED_ROLES: lambda i, v: move_to(i, render_timed_roles, v),
    menus.ENDED: lambda i, v: move_to(i, render_ended, v),
    menus.GIVE: lambda i, v: move_to(i, render_hand_out, v.menu_name, None, False, v),
    menus.TAKE_OFF: lambda i, v: move_to(i, render_hand_out, v.menu_name, None, True, v),
    menus.FILL: lambda i, v: move_to(i, render_fill, v.menu_name, v),
    menus.ATTACH: lambda i, v: move_to(i, render_attach, v.menu_name, v),
    menus.SET_END: lambda i, v: move_to(i, render_set_end, v.menu_name, v),
    menus.FILL_YES: run_fill,
    menus.USE_HELD_YES: run_use_held,
    menus.DELETE_YES: run_delete_menu,
    menus.END_YES: run_revoke,
    menus.END_MENU_YES: run_end_now,
    menus.NO_END_YES: run_no_end,
}


class EventPick(discord.ui.Select):
    def __init__(self, bot: Any, guild_id: int, rows: Any, row: int) -> None:
        found = list(rows)
        shown = found[:OPTIONS_MAX]
        super().__init__(
            placeholder=capped_placeholder(
                len(shown),
                len(found),
                pick=word(bot, guild_id, "rolemenu_event_pick"),
                capped=word(
                    bot, guild_id, "rolemenu_events_capped", shown="{shown}", total="{total}"
                ),
            )[:SELECT_PLACEHOLDER_MAX],
            options=[
                discord.SelectOption(label=event_name(one)[:LABEL_MAX], value=str(one["name"]))
                for one in shown
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_menu(interaction, self.values[0], self.view)


class MarathonPick(discord.ui.Select):
    """Marathons still to end first; on Change the end the one the event follows is ticked."""

    def __init__(self, bot: Any, guild_id: int, rows: Any, menu: Any, row: int) -> None:
        found = list(rows)
        shown = found[:OPTIONS_MAX]
        bound = (
            menu_value(menu, "ends_marathon_id")
            if menu is not None and menus.end_source(menu) == menus.MARATHON_END
            else None
        )
        placeholder = (
            word(bot, guild_id, "rolemenu_marathons_capped", shown=len(shown), total=len(found))
            if len(found) > len(shown)
            else word(bot, guild_id, "rolemenu_marathon_pick")
        )
        super().__init__(
            placeholder=placeholder[:SELECT_PLACEHOLDER_MAX],
            options=[
                discord.SelectOption(
                    label=self.label_of(bot, guild_id, one)[:LABEL_MAX],
                    value=str(one["id"]),
                    default=bound is not None and int(one["id"]) == int(bound),
                )
                for one in shown
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    @staticmethod
    def label_of(bot: Any, guild_id: int, one: Any) -> str:
        if parse_ts(one["ends_at"]) is None:
            return word(bot, guild_id, "rolemenu_marathon_option_unknown", name=one["name"])
        return word(
            bot,
            guild_id,
            "rolemenu_marathon_option",
            name=one["name"],
            date=local_moment(bot, guild_id, one["ends_at"], DATE_SHOWN),
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view, picked = self.view, int(self.values[0])
        if view.where == NEW_EVENT_VIEW:
            await run_new_event(interaction, view, title=None, marathon_id=picked)
        elif view.where == ATTACH_VIEW:
            await run_attach(interaction, picked, view)
        else:
            await run_set_marathon(interaction, picked, view)


class TimedRolePick(discord.ui.Select):
    """A role from the timed list: the one to give or take, or the one to take off the list."""

    def __init__(self, rows: Any, placeholder: str, row: int, chosen: Any = None) -> None:
        found = list(rows)[:OPTIONS_MAX]
        super().__init__(
            placeholder=placeholder,
            options=[
                discord.SelectOption(
                    label=str(one["label"])[:LABEL_MAX],
                    value=str(one["role_id"]),
                    emoji=select_emoji(one["emoji"]),
                    default=chosen is not None and int(one["role_id"]) == int(chosen),
                )
                for one in found
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view, picked = self.view, int(self.values[0])
        if view.where == ROLES_VIEW:
            await run_drop_timed(interaction, picked, view)
            return
        if not await opened(interaction):
            return
        await render_hand_out(interaction, view.menu_name, picked, view.removing, view)


class TimedRoleAdd(discord.ui.RoleSelect):
    def __init__(self, placeholder: str) -> None:
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, row=0)

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_add_timed(interaction, int(self.values[0].id), self.view)


class PeoplePick(discord.ui.UserSelect):
    def __init__(self, placeholder: str) -> None:
        super().__init__(
            placeholder=placeholder, min_values=1, max_values=PEOPLE_MAX, row=1
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_hand_out(interaction, list(self.values), self.view)


class NewRolePick(discord.ui.RoleSelect):
    def __init__(self, row: int, placeholder: str = menus.ROLE_PICK) -> None:
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        picked = int(self.values[0].id)
        if not await opened(interaction):
            return
        await render_new_grant(interaction, view.member_id, picked, view)


class WhoPick(discord.ui.UserSelect):
    def __init__(self, placeholder: str, row: int) -> None:
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        picked = int(self.values[0].id)
        if not await opened(interaction):
            return
        if view.where == NEW_GRANT_VIEW:
            await render_new_grant(interaction, picked, view.role_id, view)
            return
        await render_grants(interaction, picked, view)


class GrantPick(discord.ui.Select):
    def __init__(self, rows: Any, guild: Any, row: int) -> None:
        found = list(rows)
        shown = found[:OPTIONS_MAX]
        super().__init__(
            placeholder=capped_placeholder(
                len(shown), len(found), pick=menus.GRANT_PICK, capped=menus.GRANTS_CAPPED
            ),
            options=[
                discord.SelectOption(
                    label=select_label(
                        one["id"], role_name(guild, one["role_id"]), who_is(guild, one["user_id"])
                    ),
                    value=str(one["id"]),
                )
                for one in shown
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_grant(interaction, int(self.values[0]), self.view)


# --- the modals ----------------------------------------------------------------------------------


def read_days(value: Any) -> int | None:
    """A modal has no `Range`, so a number that is not one is refused rather than guessed."""
    typed = str(value or "").strip()
    if not typed:
        return None
    if not typed.isdigit():
        raise ValueError(typed)
    return whole_days(typed)


class NewEventModal(AnswersErrors, discord.ui.Modal):
    name = discord.ui.TextInput(label="Name", max_length=TITLE_MAX)
    typed = discord.ui.TextInput(label="Date", max_length=DATE_TYPED_MAX)

    def __init__(self, bot: Any, guild_id: int, previous: Any) -> None:
        super().__init__(title=word(bot, guild_id, "rolemenu_new_event_title", MODAL_WORD_MAX))
        self.previous = previous
        self.name.label = word(bot, guild_id, "rolemenu_event_name_label", MODAL_WORD_MAX)
        self.typed.label = word(bot, guild_id, "rolemenu_date_label", MODAL_WORD_MAX)
        self.typed.placeholder = word(bot, guild_id, "rolemenu_date_placeholder", PLACEHOLDER_MAX)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_new_event(
            interaction, self.previous, title=str(self.name), typed=str(self.typed)
        )


class RenameModal(AnswersErrors, discord.ui.Modal):
    name = discord.ui.TextInput(label="Name", max_length=TITLE_MAX)

    def __init__(self, bot: Any, guild_id: int, previous: Any, menu: Any) -> None:
        super().__init__(title=word(bot, guild_id, "rolemenu_rename_title", MODAL_WORD_MAX))
        self.previous = previous
        self.name.label = word(bot, guild_id, "rolemenu_event_name_label", MODAL_WORD_MAX)
        self.name.default = event_name(menu)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_rename(interaction, str(self.name), self.previous)


class DateModal(AnswersErrors, discord.ui.Modal):
    typed = discord.ui.TextInput(label="Date", max_length=DATE_TYPED_MAX)

    def __init__(self, previous: Any, title: Any, label: Any, placeholder: Any) -> None:
        super().__init__(title=str(title)[:MODAL_WORD_MAX])
        self.previous = previous
        self.typed.label = str(label)[:MODAL_WORD_MAX]
        self.typed.placeholder = str(placeholder)[:PLACEHOLDER_MAX]

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_typed_end(interaction, str(self.typed), self.previous)


class BufferModal(AnswersErrors, discord.ui.Modal):
    typed = discord.ui.TextInput(label="Days", max_length=BUFFER_TYPED_MAX, required=False)

    def __init__(self, previous: Any, title: Any, label: Any, current: Any) -> None:
        super().__init__(title=str(title)[:MODAL_WORD_MAX])
        self.previous = previous
        self.typed.label = str(label)[:MODAL_WORD_MAX]
        if isinstance(current, int):
            self.typed.default = str(current)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_buffer(interaction, str(self.typed), self.previous)


class DaysModal(AnswersErrors, discord.ui.Modal):
    days = discord.ui.TextInput(label=DAYS_LABEL, max_length=5, required=False)

    def __init__(self, previous: Any, *, pushing: bool) -> None:
        super().__init__(title=PUSH_TITLE if pushing else DAYS_TITLE)
        self.previous = previous
        self.pushing = pushing
        if pushing:
            self.days.label = PUSH_LABEL
            self.days.required = True

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            wanted = read_days(self.days)
        except ValueError as exc:
            await answer(interaction, BAD_NUMBER.format(given=str(exc)[:40]))
            return
        if self.pushing:
            await run_extend(interaction, wanted or 1, self.previous)
            return
        await run_grant(interaction, wanted, self.previous)


# --- a timed role added by hand: ask staff which event it is for --------------------------------


def by_hand_channel(bot: Any, guild: Any) -> Any:
    """The by-hand channel, else where role notices post (the approval channel, then staff)."""
    channel_id = bot.store.get(guild.id, ROLEMENU_BY_HAND_CHANNEL_KEY)
    if channel_id:
        found = bot.get_channel(channel_id) or guild.get_channel(channel_id)
        if found is not None:
            return found
    return approval_channel(bot, guild)


def roles_named(role_ids: Any) -> str:
    return ", ".join(f"<@&{int(one)}>" for one in role_ids or ())


def by_hand_who(bot: Any, guild_id: int, who_id: Any) -> str:
    return f"<@{int(who_id)}>" if who_id else word(bot, guild_id, "rolemenu_by_hand_someone")


def by_hand_text(bot: Any, guild_id: int, prompt: Any, events: Any) -> str:
    lines = [
        word(
            bot,
            guild_id,
            "rolemenu_by_hand_text",
            who=by_hand_who(bot, guild_id, prompt["added_by"]),
            member=f"<@{prompt['user_id']}>",
            roles=roles_named(hand.role_ids_of(prompt)),
        )
    ]
    if prompt["audit"] == hand.UNREADABLE:
        lines.append(word(bot, guild_id, "rolemenu_by_hand_unreadable_text"))
    elif prompt["audit"] == hand.SILENT:
        lines.append(word(bot, guild_id, "rolemenu_by_hand_silent_text"))
    if not events:
        lines.append(word(bot, guild_id, "rolemenu_by_hand_no_events_text"))
    return "\n".join(lines)[:NOTICE_LIMIT]


def by_hand_view(bot: Any, guild_id: int, prompt_id: int, events: Any) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    shown = list(events or ())[:OPTIONS_MAX]
    if shown:
        view.add_item(
            ByHandPick(
                prompt_id,
                discord.ui.Select(
                    custom_id=hand.pick_id(prompt_id),
                    placeholder=capped_placeholder(
                        len(shown),
                        len(list(events)),
                        pick=word(bot, guild_id, "rolemenu_by_hand_pick"),
                        capped=word(
                            bot,
                            guild_id,
                            "rolemenu_events_capped",
                            shown="{shown}",
                            total="{total}",
                        ),
                    )[:SELECT_PLACEHOLDER_MAX],
                    min_values=1,
                    max_values=1,
                    options=[
                        discord.SelectOption(
                            label=event_name(one)[:LABEL_MAX], value=str(int(one["id"]))
                        )
                        for one in shown
                    ],
                ),
            )
        )
    view.add_item(
        ByHandNew(
            prompt_id,
            discord.ui.Button(
                custom_id=hand.new_id(prompt_id),
                label=word(bot, guild_id, "rolemenu_new_event_button", BUTTON_MAX),
                style=discord.ButtonStyle.secondary,
            ),
        )
    )
    return view


async def ask_which_event(bot: Any, guild: Any, member: Any, role_ids: Any) -> int | None:
    """One post per member and set of roles, naming who added them when the audit log says."""
    if not bot.store.get(guild.id, ROLEMENU_BY_HAND_POSTS_KEY):
        return None
    lock = hand.by_hand_locks(bot).setdefault((int(guild.id), int(member.id)), asyncio.Lock())
    async with lock:
        asked = await hand.waiting_roles(bot.db, guild.id, member.id)
        wanted = sorted({int(one) for one in role_ids} - asked)
        if not wanted:
            return None
        who_id, audit = await hand.who_added_soon(guild, member, wanted)
        if audit == hand.OURS:
            return None
        target, where = card_target(bot, by_hand_channel(bot, guild))
        details = {"user": int(member.id), "roles": wanted, "audit": audit, "by": who_id}
        if target is None:
            await log_action(
                bot, guild, "role_menu.by_hand_post_failed", details=details | {"reason": where}
            )
            return None
        prompt_id = await hand.add_prompt(bot.db, guild.id, member.id, wanted, who_id, audit)
        prompt = await hand.get_prompt(bot.db, prompt_id)
        events = await timed.open_events(bot.db, guild.id)
        try:
            message = await target.send(
                by_hand_text(bot, guild.id, prompt, events),
                view=by_hand_view(bot, guild.id, prompt_id, events),
                allowed_mentions=discord.AllowedMentions(
                    everyone=False,
                    roles=False,
                    users=[discord.Object(id=int(who_id))] if who_id else False,
                ),
            )
        except Exception as exc:
            await hand.drop_prompt(bot.db, prompt_id)
            await log_action(
                bot,
                guild,
                "role_menu.by_hand_post_failed",
                details=details | {"reason": f"{type(exc).__name__}: {exc}"[:300]},
            )
            return None
        await hand.set_message(bot.db, prompt_id, target.id, message.id)
    await log_action(
        bot,
        guild,
        "role_menu.by_hand_posted",
        target=member,
        details=details | {"prompt_id": prompt_id, "channel_id": int(target.id), "where": where},
    )
    return prompt_id


async def attach_by_hand(
    bot: Any, guild: Any, actor: Any, prompt: Any, menu: Any, *, via: str = VIA_DISCORD
) -> tuple[bool, str]:
    """The roles the member still wears are assigned on the picked event; one writer wins."""
    member = guild.get_member(int(prompt["user_id"]))
    role_ids = hand.role_ids_of(prompt)
    worn = [one for one in role_ids if member is not None and one in {r.id for r in member.roles}]
    if not worn:
        return False, word(
            bot,
            guild.id,
            "rolemenu_by_hand_not_worn_said",
            member=f"<@{prompt['user_id']}>",
            roles=roles_named(role_ids),
        )
    if not await hand.mark_attached(bot.db, prompt["id"], menu["id"], actor_id(actor)):
        fresh = await hand.get_prompt(bot.db, prompt["id"])
        if fresh is None or fresh["attached_menu_id"] is None:
            return False, word(bot, guild.id, "rolemenu_by_hand_gone_said")
        done = await get_menu_by_id(bot.db, fresh["attached_menu_id"])
        return False, word(
            bot,
            guild.id,
            "rolemenu_by_hand_already_said",
            event=event_name(done) if done is not None else "?",
        )
    given = 0
    for role_id in worn:
        found = await give_event_role(
            bot, guild, actor, menu, role_id, [member], source=grants.BY_HAND_ATTACHED, via=via
        )
        given += len(found["had"]) + len(found["given"])
    await log_action(
        bot,
        guild,
        kind_via("role_menu.by_hand_attached", via),
        actor=actor,
        target=member,
        details={
            "prompt_id": int(prompt["id"]),
            "menu": menu["name"],
            "menu_id": int(menu["id"]),
            "roles": worn,
            "given": given,
            "via": via,
        },
    )
    await close_by_hand_post(bot, guild, prompt, menu, actor)
    return True, word(
        bot, guild.id, "rolemenu_by_hand_done_said", event=event_name(menu), given=given
    )


async def close_by_hand_post(bot: Any, guild: Any, prompt: Any, menu: Any, actor: Any) -> None:
    """Cosmetic and last: the post says what was attached and by whom, with nothing to press."""
    channel = bot.get_channel(prompt["channel_id"]) if prompt["channel_id"] else None
    if channel is None or not prompt["message_id"]:
        return
    text = word(
        bot,
        guild.id,
        "rolemenu_by_hand_attached_text",
        who=by_hand_who(bot, guild.id, prompt["added_by"]),
        member=f"<@{prompt['user_id']}>",
        roles=roles_named(hand.role_ids_of(prompt)),
        event=event_name(menu),
        staff=f"<@{actor_id(actor)}>" if actor_id(actor) else "?",
    )
    try:
        message = channel.get_partial_message(int(prompt["message_id"]))
        await message.edit(
            content=text[:NOTICE_LIMIT], view=None, allowed_mentions=discord.AllowedMentions.none()
        )
    except (*NETWORK_ERRORS, LookupError, AttributeError) as exc:
        log.info("timed roles: could not close by-hand post %s: %s", prompt["id"], exc)


async def by_hand_target(interaction: discord.Interaction, prompt_id: int) -> Any:
    """The stored post this click belongs to, once staff are confirmed; None once answered."""
    if interaction.guild is None:
        await answer(interaction, GUILD_ONLY)
        return None
    if not await still_staff(interaction) or not await db_up(interaction):
        return None
    prompt = await hand.get_prompt(interaction.client.db, prompt_id)
    if prompt is None or int(prompt["guild_id"]) != interaction.guild.id:
        await answer(
            interaction,
            word(interaction.client, interaction.guild.id, "rolemenu_by_hand_gone_said"),
        )
        return None
    return prompt


async def run_attach_by_hand(
    interaction: discord.Interaction, prompt_id: int, menu_id: Any
) -> None:
    prompt = await by_hand_target(interaction, prompt_id)
    if prompt is None:
        return
    bot, guild = interaction.client, interaction.guild
    if not await guarded(interaction):
        return
    await interaction.response.defer(ephemeral=True)
    menu = await get_menu_by_id(bot.db, int(menu_id)) if str(menu_id).isdigit() else None
    if menu is None or int(menu["guild_id"]) != guild.id or menu_value(menu, "ended_at"):
        await answer(interaction, word(bot, guild.id, "rolemenu_by_hand_gone_said"))
        return
    _, said = await attach_by_hand(bot, guild, interaction.user, prompt, menu)
    await answer(interaction, said)


class ByHandPick(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Select], template=hand.PICK_TEMPLATE
):
    """The by-hand post's event picker; it lives on the message, so a restart keeps it."""

    def __init__(self, prompt_id: int, select: Any = None) -> None:
        self.prompt_id = int(prompt_id)
        super().__init__(
            select
            or discord.ui.Select(
                custom_id=hand.pick_id(prompt_id),
                options=[discord.SelectOption(label="?", value="0")],
            )
        )

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["prompt_id"]), item)

    async def on_click(self, interaction: discord.Interaction) -> None:
        values = list(getattr(self.item, "values", None) or ())
        if not values:
            values = list((getattr(interaction, "data", None) or {}).get("values") or ())
        await run_attach_by_hand(interaction, self.prompt_id, values[0] if values else None)


class ByHandNew(
    SafeDynamicItem, discord.ui.DynamicItem[discord.ui.Button], template=hand.NEW_TEMPLATE
):
    """New event… on a by-hand post: name and date, then the post is attached to it."""

    def __init__(self, prompt_id: int, button: Any = None) -> None:
        self.prompt_id = int(prompt_id)
        super().__init__(button or discord.ui.Button(custom_id=hand.new_id(prompt_id), label="?"))

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: Any, match: re.Match):
        return cls(int(match["prompt_id"]), item)

    async def on_click(self, interaction: discord.Interaction) -> None:
        prompt = await by_hand_target(interaction, self.prompt_id)
        if prompt is None:
            return
        await interaction.response.send_modal(
            ByHandEventModal(interaction.client, interaction.guild.id, self.prompt_id)
        )


class ByHandEventModal(AnswersErrors, discord.ui.Modal):
    name = discord.ui.TextInput(label="Name", max_length=TITLE_MAX)
    typed = discord.ui.TextInput(label="Date", max_length=DATE_TYPED_MAX)

    def __init__(self, bot: Any, guild_id: int, prompt_id: int) -> None:
        super().__init__(title=word(bot, guild_id, "rolemenu_new_event_title", MODAL_WORD_MAX))
        self.prompt_id = int(prompt_id)
        self.name.label = word(bot, guild_id, "rolemenu_event_name_label", MODAL_WORD_MAX)
        self.typed.label = word(bot, guild_id, "rolemenu_date_label", MODAL_WORD_MAX)
        self.typed.placeholder = word(bot, guild_id, "rolemenu_date_placeholder", PLACEHOLDER_MAX)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        prompt = await by_hand_target(interaction, self.prompt_id)
        if prompt is None:
            return
        bot, guild = interaction.client, interaction.guild
        refusal, when = typed_refusal(bot, guild.id, str(self.typed))
        if refusal:
            await answer(interaction, refusal)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            menu = await make_event(bot, guild, interaction.user, str(self.name), ends_at=when)
        except MenuLimitError as exc:
            await answer(interaction, str(exc))
            return
        _, said = await attach_by_hand(bot, guild, interaction.user, prompt, menu)
        await answer(interaction, said)


class RoleMenus(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_ok_at: dict[str, str | None] = {name: None for name in LOOP_NAMES}
        self.last_error: dict[str, str | None] = {name: None for name in LOOP_NAMES}
        self.last_counts: dict[str, int] | None = None

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(RequestButton, RetiredMenuPick, ByHandPick, ByHandNew)
        if not self.bot.db.is_connected:
            return
        await self.run_due_grants()
        await self.reconcile_records()
        self._expiry_loop.start()

    async def cog_unload(self) -> None:
        self._expiry_loop.cancel()

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        key = name.removeprefix("_").removesuffix("_loop")
        if key not in LOOP_NAMES:
            return (None, None)
        return (self.last_ok_at[key], self.last_error[key])

    def loop_counts(self, name: str) -> str | None:
        """The expiry loop's last end-pass tick in numbers, for the Health tab (design §3.7)."""
        key = name.removeprefix("_").removesuffix("_loop")
        if key != "expiry" or self.last_counts is None:
            return None
        return LOOP_COUNTS.format(**self.last_counts)

    def loop_failed(self, name: str, exc: BaseException, loop: Any) -> None:
        """A loop that raised is restarted, and its failure is on the record until it is not."""
        self.last_error[name] = f"{now_iso()} · {type(exc).__name__}: {exc}"
        log.exception("role menus: the %s loop raised and is being restarted", name, exc_info=exc)
        loop.restart()

    @tasks.loop(hours=EXPIRY_HOURS)
    async def _expiry_loop(self) -> None:
        if self.bot.db.is_connected:
            await self.run_due_menus()
            await self.run_due_grants()
            await self.reconcile_records()
        self.last_ok_at["expiry"] = now_iso()

    @_expiry_loop.before_loop
    async def _before_expiry(self) -> None:
        await wait_ready(self.bot, self._expiry_broke)

    @_expiry_loop.error
    async def _expiry_broke(self, exc: BaseException) -> None:
        self.loop_failed("expiry", exc, self._expiry_loop)

    async def run_due_menus(self) -> None:
        """Menus whose end has come: everyone wearing their roles loses them (design §3.3)."""
        seen = {guild.id: guild for guild in getattr(self.bot, "guilds", ())}
        now = datetime.now(UTC)
        counts = {"due": 0, "ended": 0, "failures": 0}
        for menu in await menus_still_to_end(self.bot.db):
            guild = seen.get(menu["guild_id"])
            if guild is None or not menus.is_due(menu, now):
                continue
            counts["due"] += 1
            try:
                details = await end_menu(self.bot, guild, menu["id"])
            except Exception:
                log.exception("role menus: the end pass of %s raised", menu["name"])
                counts["failures"] += 1
                continue
            if details:
                counts["ended"] += int(bool(details["ended"]))
                counts["failures"] += int(details["failures"])
        self.last_counts = counts

    async def run_due_grants(self) -> None:
        """Grants whose day has come: the role comes off, the row closes, the member is told."""
        seen = {guild.id: guild for guild in getattr(self.bot, "guilds", ())}
        for row in await grants.due_grants(self.bot.db, now_iso()):
            guild = seen.get(row["guild_id"])
            if guild is None or menu_value(row, "menu_id") is not None:
                continue
            if await timed.is_timed(self.bot.db, guild.id, row["role_id"]):
                continue
            await self._expire(guild, row)

    async def _expire(self, guild: Any, row: Any) -> None:
        member = guild.get_member(row["user_id"])
        label = await label_for(self.bot.db, guild, None, row["role_id"])
        details = {"grant_id": row["id"], "role_id": row["role_id"]}
        holds = member is not None and any(r.id == row["role_id"] for r in member.roles)
        if holds and not await change_roles(
            self.bot, member, guild, set(), {row["role_id"]}, "Black Bloc timed role ran out"
        ):
            await log_action(
                self.bot, guild, "role.expire_failed", target=row["user_id"], details=details
            )
            return
        await grants.end_grant(self.bot.db, row["id"], grants.EXPIRED)
        await log_action(
            self.bot,
            guild,
            "role.expired",
            target=member if member is not None else row["user_id"],
            details=details | {"was_still_on": holds},
        )
        if member is not None:
            await dm(member, grants.DM_EXPIRED.format(label=label, guild=guild.name))

    async def reconcile_records(self) -> None:
        """Records only: a member's roles are never changed to match a row Black Bloc kept."""
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False):
                log.info("role menus: %s is unavailable, so its records are left alone", guild.id)
                continue
            fixed = {"grants_closed": 0, "requests_settled": 0}
            for row in await grants.open_grants(self.bot.db, guild.id):
                member = guild.get_member(row["user_id"])
                if member is None or any(r.id == row["role_id"] for r in member.roles):
                    continue
                if await grants.end_grant(self.bot.db, row["id"], grants.BY_HAND):
                    fixed["grants_closed"] += 1
            for row in await grants.open_requests(self.bot.db, guild.id):
                member = guild.get_member(row["user_id"])
                if member is None or not any(r.id == row["role_id"] for r in member.roles):
                    continue
                if await grants.decide_request(self.bot.db, row["id"], grants.GRANTED_BY_HAND):
                    fixed["requests_settled"] += 1
            if any(fixed.values()):
                await log_action(self.bot, guild, "role.reconciled", details=fixed)

    @commands.Cog.listener()
    async def on_member_update(self, before: Any, after: Any) -> None:
        """A role somebody changed by hand becomes a log line and an honest record."""
        if not self.bot.db.is_connected:
            return
        guild = getattr(after, "guild", None)
        if guild is None:
            return
        was = {role.id for role in getattr(before, "roles", ())}
        now = {role.id for role in getattr(after, "roles", ())}
        added = [
            role_id
            for role_id in sorted(now - was)
            if not grants.was_ours(self.bot, guild.id, after.id, role_id, grants.ADDED)
        ]
        removed = [
            role_id
            for role_id in sorted(was - now)
            if not grants.was_ours(self.bot, guild.id, after.id, role_id, grants.REMOVED)
        ]
        if not added and not removed:
            return
        await log_action(
            self.bot,
            guild,
            "role.changed_by_hand",
            actor=await audit_actor(guild, after),
            target=after,
            details={"added": added, "removed": removed},
        )
        for role_id in added:
            await self._added_by_hand(guild, after, role_id)
        listed = set(await timed.role_ids(self.bot.db, guild.id))
        if removed:
            gone = [one for one in removed if one in listed]
            await timed.close_member_roles(self.bot.db, guild.id, after.id, gone, grants.BY_HAND)
            await hand.retire_roles(self.bot.db, guild.id, after.id, gone)
            await grants.record_removed(
                self.bot.db, guild.id, after.id, [one for one in removed if one not in listed],
                grants.BY_HAND,
            )
        owned = await owned_by_pings(self.bot, guild.id)
        asked = [one for one in added if one in listed and one not in owned]
        if asked:
            await ask_which_event(self.bot, guild, after, asked)

    async def _added_by_hand(self, guild: Any, member: Any, role_id: int) -> None:
        row = await grants.open_request_for_role(self.bot.db, guild.id, member.id, role_id)
        if row is not None and await grants.decide_request(
            self.bot.db, row["id"], grants.GRANTED_BY_HAND
        ):
            fresh = await grants.get_request(self.bot.db, row["id"])
            menu = await get_menu_by_id(self.bot.db, fresh["menu_id"])
            await edit_request_card(
                self.bot,
                guild,
                fresh,
                await label_for(self.bot.db, guild, fresh["menu_id"], role_id),
                menu["name"] if menu is not None else "a deleted menu",
            )

    @app_commands.command(
        name="rolemenu", description="Role menus: hand roles out and set when they end"
    )
    @app_commands.default_permissions(STAFF_ONLY)
    async def rolemenu_panel_command(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not await require_staff(interaction):
            return
        if not self.bot.db.is_connected:
            log.warning("role menus: refused the panel - the database is not connected")
            await answer(interaction, DB_UNAVAILABLE)
            return
        await interaction.response.defer(ephemeral=True)
        embed, view = await build_panel(self.bot, interaction.guild, interaction.user)
        view.message = await interaction.edit_original_response(
            embed=embed, view=view, allowed_mentions=discord.AllowedMentions.none()
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleMenus(bot))
