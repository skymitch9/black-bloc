from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import rolegrants as grants
from ... import rolemenus as menus
from ... import timezones
from ...actionlog import log_action, send_logs
from ...command_errors import NETWORK_ERRORS, AnswersErrors, SafeDynamicItem
from ...command_visibility import STAFF_ONLY
from ...golive import now_iso, parse_ts
from ...logkinds import VIA_DISCORD, kind_via
from ...loops import wait_ready
from ...panels import (
    DESCRIPTION_LIMIT,
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
CANNOT_EDIT_THEIRS = (
    "Discord refused the change, so **{name}** still has exactly the roles they had. Black Bloc "
    "needs the Manage Roles permission and its own role has to sit above every role in this menu "
    "in Server Settings → Roles. Ask an admin to fix that, then run the command again."
)
STAFF_MENU_NOT_POSTED = (
    "**{name}** is a staff-assigned menu, so there is no panel to post — nobody gives these "
    "roles to themselves. Open `/rolemenu`, pick **{name}**, and **Hand roles out…** gives them "
    "out and takes them back."
)
NOTHING_TO_UNASSIGN = (
    "**{name}** has none of the roles on **{menu}**, so there is nothing to take off. "
    "**Hand roles out…** on that menu's card gives them one."
)
NO_MENUS_YET = (
    "This server has no role menus yet. Open `/rolemenu`: **New menu** starts one, and **Seed "
    "the defaults** brings over the six this server was built with."
)
SEED_EMOJI_NOTE = (
    "A menu that already exists is left exactly as it is, options and all — to pick up the "
    "Marathons emoji on `event-alerts`, open that menu's card, press **Delete it**, and seed "
    "again."
)


ALREADY_EXACTLY = (
    "**{name}** already has exactly those roles, so nothing changed."
)
NO_SUCH_MEMBER = (
    "**{user_id}** is not somebody Black Bloc can see in this server, so nothing was changed. "
    "Pick them from the list rather than typing an id."
)
NOTHING_ON_THIS_MENU = (
    "**{name}** has no roles on it yet, so there is nothing to hand out. Add one to the menu "
    "first."
)
NOTHING_TO_UNPOST = (
    "**{name}** has no panel up right now, so there was nothing to take down. **Post it** on "
    "that menu's card puts one up."
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
    """The unfinished menus whose roles come off with this marathon, with their counts."""
    bound = [
        one for one in await menus_bound_to(bot.db, guild.id, marathon_id) if not one["ended_at"]
    ]
    if not bound:
        return []
    members = await members_of(guild)
    found = []
    for menu in bound:
        role_ids = await menu_role_ids(bot.db, menu["id"])
        wearing = wearing_count(bot, guild.id, members, role_ids)
        found.append(
            {
                "name": menu["name"],
                "title": menu["title"],
                "roles": len(role_ids),
                "wearing": wearing if isinstance(wearing, int) else None,
            }
        )
    return found


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
        "SELECT label FROM role_menu_options WHERE menu_id = ? AND role_id = ?",
        (menu_id, role_id),
    )
    row = await cur.fetchone()
    return row["label"] if row is not None else None


async def timed_menu_owns(db: Any, guild_id: int, role_id: int) -> bool:
    """True when some menu in this guild hands that role out on a clock."""
    cur = await db.conn.execute(
        "SELECT 1 FROM role_menus m JOIN role_menu_options o ON o.menu_id = m.id "
        "WHERE m.guild_id = ? AND o.role_id = ? AND m.expires_days IS NOT NULL "
        "AND m.expires_days > 0 LIMIT 1",
        (guild_id, role_id),
    )
    return await cur.fetchone() is not None


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
    cur = await db.conn.execute(
        "SELECT * FROM role_menu_options WHERE menu_id = ? ORDER BY position, rowid", (menu_id,)
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


def seed_summary(created: list[str], skipped: list[str]) -> str:
    """What seeding did, in the one wording the slash command and the dashboard both show."""
    parts = []
    if created:
        parts.append("Created: " + ", ".join(created))
    if skipped:
        parts.append("Already there, left alone: " + ", ".join(skipped))
        parts.append(SEED_EMOJI_NOTE)
    parts.append(
        "Pick each one on `/rolemenu` and press **Post it** — except `runner-status`, which "
        "staff hand out with **Hand roles out…**."
    )
    return " · ".join(parts)


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


async def staff_assign(
    bot: Any,
    guild: Any,
    actor: Any,
    menu: Any,
    options: Any,
    target: Any,
    selected: Any,
    *,
    remove: bool,
    via: str = VIA_DISCORD,
) -> tuple[bool, str]:
    """Hand a menu's roles out or take them back: the staff picker and the dashboard, one path."""
    rows = list(options or ())
    role_ids = [row["role_id"] for row in rows]
    labels = {row["role_id"]: row["label"] for row in rows}
    wanted = {int(value) for value in selected or ()}
    if remove:
        to_add, to_remove = set(), wanted & set(role_ids)
    else:
        to_add, to_remove = role_diff((role.id for role in target.roles), role_ids, wanted)
    if not to_add and not to_remove:
        return True, ALREADY_EXACTLY.format(name=target.display_name)
    if not await change_roles(
        bot, target, guild, to_add, to_remove, f"Black Bloc role menu by {actor}"
    ):
        return False, CANNOT_EDIT_THEIRS.format(name=target.display_name)
    added = [labels.get(role_id, str(role_id)) for role_id in to_add]
    removed = [labels.get(role_id, str(role_id)) for role_id in to_remove]
    ends = await menu_ends_by_role(bot.db, guild.id)
    for role_id in to_add:
        await grants.record_added(
            bot.db,
            guild.id,
            target.id,
            [role_id],
            grants.STAFF,
            granted_by=getattr(actor, "id", actor),
            until=grants.clamped(None, ends.get(int(role_id))),
        )
    await grants.record_removed(bot.db, guild.id, target.id, to_remove, grants.ENDED_BY_STAFF)
    kind = kind_via(f"role_menu.{'unassign' if remove else 'assign'}", via)
    await log_action(
        bot,
        guild,
        kind,
        actor=actor,
        target=target,
        details={
            "menu_id": menu["id"] if menu is not None else None,
            "added": added,
            "removed": removed,
            "via": via,
        },
    )
    return True, f"**{target.display_name}** — {summary(added, removed)}"


class AssignPick(discord.ui.Select):
    """The staff picker: the roles they hold arrive already ticked, so 'have' means have."""

    def __init__(
        self, menu_id: int, options: Any, target: Any, *, remove: bool, row: int = 2
    ) -> None:
        held = {role.id for role in target.roles}
        super().__init__(
            placeholder=("Roles to take off " if remove else "Roles for ") + target.display_name,
            min_values=0,
            max_values=max(1, min(len(options), 25)),
            options=[
                discord.SelectOption(
                    label=one["label"],
                    value=str(one["role_id"]),
                    emoji=select_emoji(one["emoji"]),
                    default=not remove and one["role_id"] in held,
                )
                for one in options
            ],
            row=row,
        )
        self.menu_id = menu_id
        self.rows = list(options)
        self.target = target
        self.remove = remove

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_assign(interaction, self, self.view)


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
    menu = await get_menu(bot.db, guild.id, name)
    role_ids = await menu_role_ids(bot.db, menu["id"]) if menu is not None else []
    if not await delete_menu(bot.db, guild.id, name):
        return False
    await stamp_grants(bot.db, guild.id, role_ids, was=(menu_value(menu, "ends_at"),))
    await log_action(
        bot,
        guild,
        kind_via("role_menu.delete", via),
        actor=actor,
        details={"menu": name, "via": via},
    )
    return True


async def put_option(
    bot: Any,
    guild: Any,
    actor: Any,
    menu: Any,
    role_id: int,
    label: str,
    emoji: Any = None,
    *,
    via: str = VIA_DISCORD,
) -> None:
    await add_option(bot.db, menu["id"], int(role_id), label, emoji)
    await stamp_grants(bot.db, guild.id, [int(role_id)])
    await log_action(
        bot,
        guild,
        kind_via("role_menu.option_added", via),
        actor=actor,
        details={"menu": menu["name"], "role_id": int(role_id), "label": label, "via": via},
    )


async def drop_option(
    bot: Any, guild: Any, actor: Any, menu: Any, role_id: int, *, via: str = VIA_DISCORD
) -> bool:
    if not await remove_option(bot.db, menu["id"], int(role_id)):
        return False
    await stamp_grants(bot.db, guild.id, [int(role_id)], was=(menu_value(menu, "ends_at"),))
    await log_action(
        bot,
        guild,
        kind_via("role_menu.option_removed", via),
        actor=actor,
        details={"menu": menu["name"], "role_id": int(role_id), "via": via},
    )
    return True


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
    held = any(r.id == role.id for r in member.roles)
    if not held and not await change_roles(
        bot, member, guild, {role.id}, set(), f"Black Bloc timed role by {actor}"
    ):
        return None, CANNOT_ADD.format(label=role.name, name=member.display_name)
    ending = await menu_ending_role(bot.db, guild.id, role.id)
    until = grants.clamped(grants.expires_at(days), ending["ends_at"] if ending else None)
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
    if member is not None and any(r.id == row["role_id"] for r in member.roles):
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
    return True, GRANT_ENDED.format(label=label, name=name)


# --- temporary roles: a menu's end, and the pass that takes its roles off everyone -------------


END_REASON = "Black Bloc: {menu} ended"
NOTICE_LIMIT = 2000
END_LOCKS_ATTR = "_role_menu_end_locks"


def end_lock(bot: Any, menu_id: Any) -> asyncio.Lock:
    """One lock per menu, kept on the bot so every copy of this module shares it."""
    found = getattr(bot, END_LOCKS_ATTR, None)
    if found is None:
        found = {}
        setattr(bot, END_LOCKS_ATTR, found)
    return found.setdefault(int(menu_id), asyncio.Lock())


def default_buffer(bot: Any, guild_id: int) -> Any:
    return bot.store.get(guild_id, ROLEMENU_END_BUFFER_KEY)


async def menu_ends_by_role(db: Any, guild_id: int) -> dict[int, str]:
    """The soonest unfinished menu end each role carries; a role on no such menu is absent."""
    cur = await db.conn.execute(
        "SELECT o.role_id, m.ends_at FROM role_menus m JOIN role_menu_options o "
        "ON o.menu_id = m.id WHERE m.guild_id = ? AND m.ends_at IS NOT NULL "
        "AND m.ended_at IS NULL",
        (int(guild_id),),
    )
    found: dict[int, str] = {}
    for row in await cur.fetchall():
        when = parse_ts(row["ends_at"])
        if when is None:
            continue
        role_id = int(row["role_id"])
        held = parse_ts(found.get(role_id))
        if held is None or when < held:
            found[role_id] = menus.utc_iso(when)
    return found


async def menu_ends_named(db: Any, guild_id: Any) -> dict[int, dict[str, str]]:
    """Each role's soonest unfinished menu end with that menu's name; the Members chips' source."""
    if db is None or not getattr(db, "is_connected", False):
        return {}
    cur = await db.conn.execute(
        "SELECT o.role_id, m.ends_at, m.name FROM role_menus m JOIN role_menu_options o "
        "ON o.menu_id = m.id WHERE m.guild_id = ? AND m.ends_at IS NOT NULL "
        "AND m.ended_at IS NULL ORDER BY m.id",
        (int(guild_id),),
    )
    found: dict[int, dict[str, str]] = {}
    for row in await cur.fetchall():
        when = parse_ts(row["ends_at"])
        if when is None:
            continue
        role_id = int(row["role_id"])
        held = parse_ts((found.get(role_id) or {}).get("ends_at"))
        if held is None or when < held:
            found[role_id] = {"ends_at": menus.utc_iso(when), "menu": str(row["name"])}
    return found


async def stamp_grants(db: Any, guild_id: int, role_ids: Any, *, was: Any = ()) -> int:
    """Open grants on these roles carry their menu's end, so every surface reads one date.

    A role whose menu end went away loses only the stamp the menu put there (`was`)."""
    ends = await menu_ends_by_role(db, guild_id)
    gone = [str(one) for one in was or () if one]
    changed = 0
    for role_id in dict.fromkeys(int(one) for one in role_ids or ()):
        end = ends.get(role_id)
        if end is not None:
            cur = await db.conn.execute(
                "UPDATE role_grants SET expires_at = ? WHERE guild_id = ? AND role_id = ? "
                "AND removed_at IS NULL AND expires_at IS NOT ?",
                (end, int(guild_id), role_id, end),
            )
        elif gone:
            marks = ", ".join("?" for _ in gone)
            cur = await db.conn.execute(
                "UPDATE role_grants SET expires_at = NULL WHERE guild_id = ? AND role_id = ? "
                f"AND removed_at IS NULL AND expires_at IN ({marks})",
                (int(guild_id), role_id, *gone),
            )
        else:
            continue
        changed += max(cur.rowcount, 0)
    await db.conn.commit()
    return changed


async def menu_ending_role(db: Any, guild_id: int, role_id: Any) -> Any:
    """The unfinished menu whose end comes soonest for this role; None when it is on none."""
    cur = await db.conn.execute(
        "SELECT m.* FROM role_menus m JOIN role_menu_options o ON o.menu_id = m.id "
        "WHERE m.guild_id = ? AND o.role_id = ? AND m.ends_at IS NOT NULL AND m.ended_at IS NULL "
        "ORDER BY m.ends_at, m.id",
        (int(guild_id), int(role_id)),
    )
    for row in await cur.fetchall():
        if parse_ts(row["ends_at"]) is not None:
            return row
    return None


async def push_back_refusal(bot: Any, guild: Any, row: Any, when: Any = None) -> str | None:
    ending = await menu_ending_role(bot.db, guild.id, row["role_id"])
    if ending is None:
        return None
    shown = when or (lambda _bot, _guild_id, at: grants.stamp(at, "D"))
    return menus.said(
        bot.store,
        guild.id,
        ROLEMENU_PUSH_BACK_REFUSED_KEY,
        role=role_name(guild, row["role_id"]),
        menu=ending["name"],
        date=shown(bot, guild.id, ending["ends_at"]),
    )


async def menu_role_ids(db: Any, menu_id: int) -> list[int]:
    return [int(row["role_id"]) for row in await get_options(db, menu_id)]


async def roles_ending_now(db: Any, at: datetime) -> set[tuple[int, int]]:
    """(guild, role) pairs a due menu is about to take off, so the grant path leaves them be."""
    found: set[tuple[int, int]] = set()
    for menu in await menus_still_to_end(db):
        if menus.is_due(menu, at):
            for role_id in await menu_role_ids(db, menu["id"]):
                found.add((int(menu["guild_id"]), role_id))
    return found


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
    await stamp_grants(
        bot.db, guild.id, await menu_role_ids(bot.db, menu["id"]), was=(menu["ends_at"],)
    )
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


async def close_menu_grants(db: Any, guild_id: int, role_ids: Any, keep: set[int]) -> int:
    """Every open grant on the menu's roles closes, except for members who still wear them."""
    closed = 0
    wanted = {int(one) for one in role_ids or ()}
    for row in await grants.open_grants(db, guild_id):
        if int(row["role_id"]) in wanted and int(row["user_id"]) not in keep:
            closed += int(await grants.end_grant(db, row["id"], grants.EXPIRED))
    return closed


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
    await stamp_grants(
        bot.db, guild.id, await menu_role_ids(bot.db, menu["id"]), was=(menu["ends_at"],)
    )
    return await end_menu(bot, guild, menu["id"], actor=actor, via=via)


async def _end_pass(bot: Any, guild: Any, menu: Any, actor: Any, via: str) -> Any:
    db = bot.db
    role_ids = await menu_role_ids(db, menu["id"])
    base = {"menu": menu["name"], "menu_id": menu["id"], "via": via}
    if getattr(guild, "unavailable", False):
        return None
    members = await members_of(guild)
    if members is None:
        await log_action(
            bot,
            guild,
            kind_via("role_menu.end_failed", via),
            actor=actor,
            details=base | {"roles": role_ids, "reason": "members_not_loaded"},
        )
        return None
    found = menus.wearers(members, role_ids)
    if getattr(bot, "guard", None) is not None:
        await log_action(
            bot,
            guild,
            "role_menu.would_end",
            actor=actor,
            details=base
            | {"roles": role_ids, "wearers": [[member.id, worn] for member, worn in found]},
        )
        return None
    reason = END_REASON.format(menu=menu["name"])
    taken: list[tuple[Any, list[int]]] = []
    stuck: list[tuple[Any, list[int]]] = []
    for member, worn in found:
        can = [one for one in worn if removable(guild, one)]
        done = bool(can) and await change_roles(bot, member, guild, set(), set(can), reason)
        if done:
            taken.append((member, can))
            await grants.record_removed(db, guild.id, member.id, can, grants.EXPIRED)
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
    await close_menu_grants(db, guild.id, role_ids, {int(member.id) for member, _ in stuck})
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
        "failures": len(stuck),
        "left": leftovers,
        "passes": passes,
        "ended": finished,
    }
    labels = await role_labels(db, guild, menu["id"])
    if finished:
        await log_action(bot, guild, kind_via("role_menu.ended", via), actor=actor, details=details)
        if bot.store.get(guild.id, ROLEMENU_ENDED_NOTICE_KEY):
            await post_role_notice(bot, guild, ended_notice(bot, guild, menu, details, labels))
    await tell_wearers(bot, guild, menu, taken, labels)
    return details


def ended_notice(
    bot: Any, guild: Any, menu: Any, details: dict[str, Any], labels: dict[int, str]
) -> str:
    lines = [
        menus.said(
            bot.store,
            guild.id,
            ROLEMENU_ENDED_TEXT_KEY,
            menu=menu["name"],
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
        await stamp_grants(
            bot.db, guild.id, await menu_role_ids(bot.db, fresh["id"]), was=(fresh["ends_at"],)
        )
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
                    menu=fresh["name"],
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
            menu=menu["name"],
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
                menu=fresh["name"],
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
ADD_VIEW = "add"
HAND_VIEW = "hand"
GRANTS_VIEW = "grants"
NEW_GRANT_VIEW = "new_grant"
GRANT_VIEW = "grant"
SET_END_VIEW = "set_end"

SITE_BUTTON = "Open on the site"
ROLE_ADD_LINE = "Picked: <@&{role_id}>. Name it after the role itself, or give it your own words."
ROLE_ADD_NOTHING = "Pick the role first — Black Bloc only offers roles it can hand out."
HAND_LINE = "Picking here changes **{name}**'s roles at once, test mode or not."
HAND_NOBODY = "Pick who this is about first."
HAND_HAS_NONE = "**{name}** has none of this menu's roles, so there is nothing to take back."
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
NAME_TAKEN = (
    "This server already has a role menu called **{name}**, so nothing was created. Pick "
    "another name."
)
MENU_MADE = "Created **{name}**. **Add a role…** puts the first role on it."
MENU_SAVED = "**{name}** is saved."
OPTION_ADDED = "**{label}** is on **{name}**."
OPTION_GONE = "**{label}** is off **{name}**. Nobody loses the role they already have."
OPTION_WAS_NOT_ON = (
    "That role was not on **{name}**, so nothing changed. Press **Refresh** and look again."
)
MENU_DELETED = "Deleted **{name}**. Nobody loses a role they already have."
BAD_NUMBER = (
    "**{given}** is not a whole number of days, so nothing was changed. Type a number, or 0."
)
LOOP_COUNTS = "menus due {due} · ended {ended} · failures {failures}"

NEW_MENU_TITLE = "A new role menu"
WORDS_TITLE = "What this menu says"
OPTION_TITLE = "How this role reads"
DAYS_TITLE = "How long for?"
PUSH_TITLE = "Push the end date back"

NAME_LABEL = "Short name, the one you will pick it by"
HEADING_LABEL = "Heading on its card"
DESCRIPTION_LABEL = "Optional line under the heading"
LABEL_LABEL = "What the option says"
EMOJI_LABEL = "Optional emoji beside it"
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
}


def minutes_for(bot: Any, guild_id: int) -> int:
    return menus.panel_minutes(bot.store, guild_id)


def word(bot: Any, guild_id: int, key: str, limit: int | None = None, **fields: Any) -> str:
    """A staff-editable word, filled; Discord's own cap cuts it where a modal or button would."""
    text = menus.said(bot.store, guild_id, key, **fields)
    return text[:limit] if limit else text


def end_moves(bot: Any, guild_id: int) -> dict[str, str]:
    return {action: word(bot, guild_id, key, BUTTON_MAX) for action, key in END_WORD_KEYS.items()}


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


def use_held_question(
    bot: Any, guild_id: int, menu: Any, roles: int, members: Any, when: Any = None
) -> str | None:
    """What Use the earlier end asks, with the counts; None when no earlier end waits."""
    held = menu_value(menu, "ends_held_at")
    if not held:
        return None
    shown = when or discord_moment("F")
    return word(
        bot,
        guild_id,
        "rolemenu_use_held_past_question" if held_is_past(menu) else "rolemenu_use_held_question",
        menu=menu["name"],
        roles=roles,
        members=members,
        when=shown(bot, guild_id, held),
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


async def delete_refusal(bot: Any, guild: Any, menu: Any, when: Any = None) -> str | None:
    """Why a menu with an end still to come and people wearing its roles is not deleted."""
    if menu is None or menu_value(menu, "ended_at"):
        return None
    end = parse_ts(menu_value(menu, "ends_at"))
    if end is None or end <= datetime.now(UTC):
        return None
    members = await members_of(guild)
    count = wearing_count(
        bot, guild.id, members, await menu_role_ids(bot.db, menu["id"])
    )
    if count == 0:
        return None
    shown = when or discord_moment("F")
    return word(
        bot,
        guild.id,
        "rolemenu_delete_refused_said",
        menu=menu["name"],
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
        self.home: Any = None


async def root_line(bot: Any, guild: Any, menu: Any, members: Any) -> str:
    role_ids = await menu_role_ids(bot.db, menu["id"])
    return word(
        bot,
        guild.id,
        "rolemenu_root_line",
        name=menu["name"],
        roles=len(role_ids),
        wearing=wearing_count(bot, guild.id, members, role_ids),
        end=end_label(bot, guild.id, menu, await marathon_name_of(bot, guild.id, menu)),
    )


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, RoleMenuPanel]:
    """One command, one staff panel: every menu with its roles, who wears them, and its end."""
    rows = await list_menus(bot.db, guild.id)
    members = await members_of(guild) if rows else []
    lines = [await root_line(bot, guild, menu, members) for menu in rows] or [
        menus.NO_MENUS_LINE
    ]
    embed = discord.Embed(title=menus.PANEL_TITLE, description=clamped(lines))
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    if rows:
        view.add_item(MenuPick(rows, row=0))
    for move in menus.root_buttons():
        view.add_item(MoveButton(move))
    add_site_button(view, bot, row=2)
    _ = actor
    return (embed, view)


async def card_lines(bot: Any, guild: Any, menu: Any, options: Any) -> list[str]:
    members = await members_of(guild)
    lines = [menus.menu_heading(menu)]
    for row in options:
        lines.append(
            word(
                bot,
                guild.id,
                "rolemenu_role_line",
                label=row["label"],
                role_id=row["role_id"],
                wearing=wearing_count(bot, guild.id, members, [row["role_id"]]),
            )
        )
    if not options:
        lines.append(menus.NO_ROLES_YET)
    lines.append(
        end_label(
            bot,
            guild.id,
            menu,
            await marathon_name_of(bot, guild.id, menu),
            discord_moment("F"),
        )
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
        lines.append(
            word(bot, guild.id, "rolemenu_end_held_line", to=grants.stamp(held, "F"))
        )
    if len(options) >= OPTIONS_MAX:
        lines.append(menus.OPTIONS_ARE_FULL.format(limit=OPTIONS_MAX))
    return lines


async def build_menu(
    bot: Any, guild: Any, name: str
) -> tuple[discord.Embed | None, RoleMenuPanel | None]:
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        return (None, None)
    options = await get_options(bot.db, menu["id"])
    embed = discord.Embed(
        title=menus.MENU_TITLE.format(name=menu["name"]),
        description=clamped(await card_lines(bot, guild, menu, options)),
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = MENU_VIEW
    view.menu_name = menu["name"]
    if options:
        view.add_item(OptionPick(options, row=0))
    for move in menus.menu_buttons(
        options=len(options),
        options_max=OPTIONS_MAX,
        held=bool(menu_value(menu, "ends_held_at")),
        words=end_moves(bot, guild.id),
    ):
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_set_end(
    bot: Any, guild: Any, name: str
) -> tuple[discord.Embed | None, RoleMenuPanel | None]:
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        return (None, None)
    marathons = await bindable_marathons(bot.db, guild.id)
    line = end_label(
        bot, guild.id, menu, await marathon_name_of(bot, guild.id, menu), discord_moment("F")
    )
    embed = discord.Embed(
        title=word(bot, guild.id, "rolemenu_set_end_title", 256, name=menu["name"]),
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


def build_add_role(
    bot: Any, guild: Any, name: str, role_id: Any
) -> tuple[discord.Embed, RoleMenuPanel]:
    line = ROLE_ADD_LINE.format(role_id=role_id) if role_id else ROLE_ADD_NOTHING
    embed = discord.Embed(title=menus.ADD_ROLE_TITLE.format(name=name), description=line)
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = ADD_VIEW
    view.menu_name = name
    view.role_id = int(role_id) if role_id else None
    view.add_item(NewRolePick(row=0))
    for move in menus.add_role_buttons(picked=bool(role_id)):
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_hand_out(
    bot: Any, guild: Any, name: str, member_id: Any, removing: Any
) -> tuple[discord.Embed | None, RoleMenuPanel | None]:
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        return (None, None)
    options = await get_options(bot.db, menu["id"])
    member = guild.get_member(int(member_id)) if member_id else None
    held = {role.id for role in member.roles} if member is not None else set()
    theirs = [row for row in options if row["role_id"] in held]
    lines = [HAND_LINE.format(name=member.display_name) if member is not None else HAND_NOBODY]
    if member is not None and not theirs:
        lines.append(HAND_HAS_NONE.format(name=member.display_name))
    embed = discord.Embed(
        title=menus.HAND_OUT_TITLE.format(name=menu["name"]), description=clamped(lines)
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = HAND_VIEW
    view.menu_name = menu["name"]
    view.member_id = int(member_id) if member_id else None
    view.removing = removing
    view.add_item(WhoPick(menus.WHOSE_ROLES, row=0))
    for move in menus.hand_out_buttons(picked=member is not None, holds_any=bool(theirs)):
        view.add_item(MoveButton(move))
    if member is not None and removing is not None:
        wanted = theirs if removing else options
        if wanted:
            view.add_item(AssignPick(menu["id"], wanted, member, remove=bool(removing), row=2))
    return (embed, view)


async def audit_rows(bot: Any, guild: Any, member_id: Any) -> tuple[list[Any], list[Any]]:
    """(audit lines, openable grant rows): menu roles with an end by wearer, the rest by grant."""
    wanted = int(member_id) if member_id else None
    ends = await menu_ends_by_role(bot.db, guild.id)
    rows = [
        row
        for row in await menus.active_grants(bot.db, guild.id, user_id=wanted)
        if int(row["role_id"]) not in ends
    ]
    worn: list[Any] = []
    if ends:
        members = await members_of(guild) or list(getattr(guild, "members", ()) or ())
        for member, role_ids in menus.wearers(members, list(ends)):
            if wanted is not None and int(member.id) != wanted:
                continue
            for role_id in role_ids:
                worn.append(
                    {"user_id": int(member.id), "role_id": role_id, "expires_at": ends[role_id]}
                )
    return sorted([*rows, *worn], key=menus.grant_order), rows


async def build_grants(
    bot: Any, guild: Any, member_id: Any
) -> tuple[discord.Embed, RoleMenuPanel]:
    """The audit: who loses which role and when, soonest first (design §3.1)."""
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


async def render_menu(interaction: discord.Interaction, name: str, previous: Any = None) -> None:
    embed, view = await build_menu(interaction.client, interaction.guild, name)
    if view is None:
        await render_panel(interaction, previous)
        await answer(interaction, MENU_GONE.format(name=name))
        return
    await render(interaction, embed, view, previous)


async def render_set_end(
    interaction: discord.Interaction, name: str, previous: Any = None
) -> None:
    embed, view = await build_set_end(interaction.client, interaction.guild, name)
    if view is None:
        await render_panel(interaction, previous)
        await answer(interaction, MENU_GONE.format(name=name))
        return
    await render(interaction, embed, view, previous)


async def render_add_role(
    interaction: discord.Interaction, name: str, role_id: Any, previous: Any = None
) -> None:
    embed, view = build_add_role(interaction.client, interaction.guild, name, role_id)
    await render(interaction, embed, view, previous)


async def render_hand_out(
    interaction: discord.Interaction,
    name: str,
    member_id: Any,
    removing: Any,
    previous: Any = None,
) -> None:
    embed, view = await build_hand_out(
        interaction.client, interaction.guild, name, member_id, removing
    )
    if view is None:
        await render_panel(interaction, previous)
        await answer(interaction, MENU_GONE.format(name=name))
        return
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


async def open_set_end(interaction: discord.Interaction, view: Any) -> None:
    if not await opened(interaction):
        return
    await render_set_end(interaction, view.menu_name, view)


async def open_add_role(interaction: discord.Interaction, view: Any) -> None:
    if not await opened(interaction):
        return
    await render_add_role(interaction, view.menu_name, None, view)


async def open_hand_out(interaction: discord.Interaction, view: Any, removing: Any) -> None:
    if not await opened(interaction):
        return
    await render_hand_out(interaction, view.menu_name, view.member_id, removing, view)


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


async def open_new_grant(interaction: discord.Interaction, view: Any) -> None:
    if not await opened(interaction):
        return
    await render_new_grant(interaction, view.member_id, view.role_id, view)


async def open_grant(interaction: discord.Interaction, grant_id: Any, previous: Any) -> None:
    if not await opened(interaction):
        return
    await render_grant(interaction, grant_id, previous)


async def refresh_where(interaction: discord.Interaction, view: Any) -> None:
    if view.where == MENU_VIEW:
        await open_menu(interaction, view.menu_name, view)
        return
    if view.where == SET_END_VIEW:
        await open_set_end(interaction, view)
        return
    if view.where == GRANTS_VIEW:
        await open_grants(interaction, view.member_id, view)
        return
    if view.where == GRANT_VIEW:
        await open_grant(interaction, view.grant_id, view)
        return
    if view.where == HAND_VIEW:
        await open_hand_out(interaction, view, view.removing)
        return
    if view.where == ADD_VIEW:
        await open_add_role(interaction, view)
        return
    await open_root(interaction, view)


async def back_from(interaction: discord.Interaction, view: Any) -> None:
    if view.where == GRANTS_VIEW and view.home is not None:
        await view.home(interaction, view)
        return
    if view.where in (ADD_VIEW, HAND_VIEW, SET_END_VIEW):
        await open_menu(interaction, view.menu_name, view)
        return
    if view.where in (GRANT_VIEW, NEW_GRANT_VIEW):
        await open_grants(interaction, view.member_id, view)
        return
    await open_root(interaction, view)


# --- the moves, one function each ----------------------------------------------------------------


async def menu_or_gone(interaction: discord.Interaction, previous: Any) -> Any:
    """The menu this card is about, or None once the root is back up with the reason."""
    name = previous.menu_name
    menu = await get_menu(interaction.client.db, interaction.guild.id, name)
    if menu is None:
        await render_panel(interaction, previous)
        await answer(interaction, MENU_GONE.format(name=name))
    return menu


async def said_end(interaction: discord.Interaction, menu: Any, end: Any) -> None:
    bot, guild = interaction.client, interaction.guild
    if menus.end_source(await get_menu_by_id(bot.db, menu["id"])) == menus.NO_END:
        cleared = word(bot, guild.id, "rolemenu_end_cleared_said", menu=menu["name"])
        await answer(interaction, cleared)
        return
    when = (
        grants.stamp(end, "F")
        if parse_ts(end) is not None
        else str(bot.store.get(guild.id, ROLEMENU_END_NOT_KNOWN_KEY))
    )
    await answer(
        interaction, word(bot, guild.id, "rolemenu_end_set_said", menu=menu["name"], when=when)
    )


async def run_new_menu(
    interaction: discord.Interaction, fields: dict[str, Any], previous: Any
) -> None:
    if not await opened(interaction):
        return
    name = str(fields["name"]).strip()
    try:
        menu_id = await make_menu(
            interaction.client,
            interaction.guild,
            interaction.user,
            name,
            str(fields["title"]).strip(),
            str(fields["description"]).strip() or None,
            STAFF_MODE,
        )
    except MenuLimitError as exc:
        await render_panel(interaction, previous)
        await answer(interaction, str(exc))
        return
    if menu_id is None:
        await render_panel(interaction, previous)
        await answer(interaction, NAME_TAKEN.format(name=name))
        return
    await render_menu(interaction, name, previous)
    await answer(interaction, MENU_MADE.format(name=name))


async def run_change_menu(
    interaction: discord.Interaction, fields: dict[str, Any], previous: Any
) -> None:
    if not await opened(interaction):
        return
    name = previous.menu_name
    try:
        menu = await change_menu(
            interaction.client, interaction.guild, interaction.user, name, **fields
        )
    except MenuLimitError as exc:
        await render_menu(interaction, name, previous)
        await answer(interaction, str(exc))
        return
    if menu is None:
        await render_panel(interaction, previous)
        await answer(interaction, MENU_GONE.format(name=name))
        return
    await render_menu(interaction, name, previous)
    await answer(interaction, MENU_SAVED.format(name=name))


async def run_add_option(
    interaction: discord.Interaction, label: Any, emoji: Any, previous: Any
) -> None:
    if not await opened(interaction):
        return
    guild = interaction.guild
    name = previous.menu_name
    menu = await menu_or_gone(interaction, previous)
    if menu is None:
        return
    role = guild.get_role(int(previous.role_id)) if previous.role_id else None
    if role is None:
        await render_add_role(interaction, name, None, previous)
        await answer(interaction, ROLE_ADD_NOTHING)
        return
    if not removable(guild, role.id):
        await render_add_role(interaction, name, role.id, previous)
        await answer(
            interaction,
            word(interaction.client, guild.id, "rolemenu_cannot_strip_said", name=role.name),
        )
        return
    wanted = str(label or "").strip() or role.name
    try:
        await put_option(
            interaction.client,
            guild,
            interaction.user,
            menu,
            role.id,
            wanted,
            str(emoji or "").strip() or None,
        )
    except MenuLimitError as exc:
        await render_add_role(interaction, name, role.id, previous)
        await answer(interaction, str(exc))
        return
    await render_menu(interaction, name, previous)
    await answer(interaction, OPTION_ADDED.format(label=wanted, name=name))


async def run_drop_option(interaction: discord.Interaction, role_id: int, previous: Any) -> None:
    if not await opened(interaction):
        return
    guild = interaction.guild
    name = previous.menu_name
    menu = await menu_or_gone(interaction, previous)
    if menu is None:
        return
    label = await label_for(interaction.client.db, guild, menu["id"], role_id)
    gone = await drop_option(interaction.client, guild, interaction.user, menu, role_id)
    await render_menu(interaction, name, previous)
    await answer(
        interaction,
        OPTION_GONE.format(label=label, name=name)
        if gone
        else OPTION_WAS_NOT_ON.format(name=name),
    )


async def run_delete_menu(interaction: discord.Interaction, previous: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    name = previous.menu_name
    refused = await delete_refusal(bot, guild, await get_menu(bot.db, guild.id, name))
    if refused:
        await render_menu(interaction, name, previous)
        await answer(interaction, refused)
        return
    gone = await drop_menu(bot, guild, interaction.user, name)
    await render_panel(interaction, previous)
    await answer(
        interaction, MENU_DELETED.format(name=name) if gone else MENU_GONE.format(name=name)
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
    following = menus.end_source(menu) == menus.MARATHON_END
    keeps = menu_value(menu, "buffer_days") if following else None
    end = await set_menu_end(
        bot,
        guild,
        interaction.user,
        menu,
        source=menus.MARATHON_END,
        marathon_id=marathon_id,
        buffer_days=keeps,
    )
    await render_menu(interaction, menu["name"], previous)
    await said_end(interaction, menu, end)


async def run_typed_end(interaction: discord.Interaction, typed: Any, previous: Any) -> None:
    if not await opened(interaction):
        return
    bot, guild = interaction.client, interaction.guild
    menu = await menu_or_gone(interaction, previous)
    if menu is None:
        return
    text = str(typed or "").strip()
    when = menus.typed_end(text, bot.store.get(guild.id, "default_timezone"))
    refusal = None
    if when is None:
        refusal = word(bot, guild.id, "rolemenu_end_bad_date_said", given=text[:40])
    elif when <= datetime.now(UTC):
        refusal = word(bot, guild.id, "rolemenu_end_past_said", when=grants.stamp(when, "F"))
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
        refusal = word(bot, guild.id, "rolemenu_buffer_needs_marathon_said", menu=menu["name"])
    if refusal is None and await marathon_row(bot.db, guild.id, menu["ends_marathon_id"]) is None:
        refusal = word(bot, guild.id, "rolemenu_end_no_marathon_said")
    if refusal:
        await render_set_end(interaction, menu["name"], previous)
        await answer(interaction, refusal)
        return
    end = await set_menu_end(
        bot,
        guild,
        interaction.user,
        menu,
        source=menus.MARATHON_END,
        marathon_id=menu["ends_marathon_id"],
        buffer_days=days,
    )
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
            else word(bot, guild.id, "rolemenu_end_now_not_run_said", menu=menu["name"]),
        )
        return
    await answer(
        interaction,
        word(
            bot,
            guild.id,
            ROLEMENU_ENDED_TEXT_KEY,
            menu=menu["name"],
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
    end = await use_held_end(bot, guild, interaction.user, menu) if had else None
    await render_menu(interaction, menu["name"], previous)
    if not had:
        await answer(interaction, word(bot, guild.id, "rolemenu_no_held_said", menu=menu["name"]))
        return
    await said_end(interaction, menu, end)


async def run_assign(interaction: discord.Interaction, select: Any, previous: Any) -> None:
    if not await guarded(interaction) or not await opened(interaction):
        return
    bot = interaction.client
    guild = interaction.guild
    menu = await get_menu_by_id(bot.db, select.menu_id)
    _, said = await staff_assign(
        bot,
        guild,
        interaction.user,
        menu,
        select.rows,
        select.target,
        select.values,
        remove=select.remove,
    )
    await render_hand_out(
        interaction, previous.menu_name, previous.member_id, previous.removing, previous
    )
    await answer(interaction, said)


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
        if action == menus.REFRESH:
            await refresh_where(interaction, view)
            return
        if action == menus.BACK:
            await back_from(interaction, view)
            return
        if action == menus.LOGS:
            await send_logs(interaction, "rolemenu")
            return
        if action == menus.GRANTS:
            await open_grants(interaction, None, view)
            return
        if action == menus.ADD_ROLE:
            await open_add_role(interaction, view)
            return
        if action == menus.HAND_OUT:
            await open_hand_out(interaction, view, None)
            return
        if action == menus.GIVE:
            await open_hand_out(interaction, view, False)
            return
        if action == menus.TAKE_BACK:
            await open_hand_out(interaction, view, True)
            return
        if action == menus.NEW_GRANT:
            await open_new_grant(interaction, view)
            return
        if action == menus.SET_END:
            await open_set_end(interaction, view)
            return
        if action == menus.USE_HELD_YES:
            await run_use_held(interaction, view)
            return
        if action == menus.USE_ROLE_NAME:
            await run_add_option(interaction, None, None, view)
            return
        if action in (
            menus.DELETE,
            menus.END_NOW,
            menus.END_MENU,
            menus.NO_END_MOVE_ACTION,
            menus.USE_HELD,
        ):
            await self.ask_first(interaction, view, action)
            return
        if action == menus.DELETE_YES:
            await run_delete_menu(interaction, view)
            return
        if action == menus.END_YES:
            await run_revoke(interaction, view)
            return
        if action == menus.END_MENU_YES:
            await run_end_now(interaction, view)
            return
        if action == menus.NO_END_YES:
            await run_no_end(interaction, view)
            return
        if action in (menus.KEEP, menus.LEAVE_IT):
            await refresh_where(interaction, view)
            return
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
                question = menus.DELETE_QUESTION.format(name=view.menu_name)
                yes = menus.PanelMove(menus.DELETE_YES, menus.DELETE_YES_LABEL, "danger", 0)
            elif action == menus.END_MENU:
                role_ids = await menu_role_ids(bot.db, menu["id"])
                question = word(
                    bot,
                    guild.id,
                    "rolemenu_end_now_question",
                    roles=len(role_ids),
                    members=wearing_count(bot, guild.id, await members_of(guild), role_ids),
                )
                yes = menus.PanelMove(
                    menus.END_MENU_YES,
                    word(bot, guild.id, "rolemenu_end_now_yes", BUTTON_MAX),
                    "danger",
                    0,
                )
            elif action == menus.USE_HELD:
                role_ids = await menu_role_ids(bot.db, menu["id"])
                question = use_held_question(
                    bot,
                    guild.id,
                    menu,
                    len(role_ids),
                    wearing_count(bot, guild.id, await members_of(guild), role_ids),
                )
                if question is None:
                    await render_menu(interaction, menu["name"], view)
                    await answer(
                        interaction, word(bot, guild.id, "rolemenu_no_held_said", menu=menu["name"])
                    )
                    return
                yes = menus.PanelMove(
                    menus.USE_HELD_YES,
                    word(bot, guild.id, "rolemenu_use_held_yes", BUTTON_MAX),
                    "danger",
                    0,
                )
            else:
                question = word(bot, guild.id, "rolemenu_no_end_question", menu=menu["name"])
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
        if action == menus.NEW_MENU:
            await interaction.response.send_modal(NewMenuModal(view))
            return
        if action == menus.LABEL_IT:
            await interaction.response.send_modal(OptionModal(view))
            return
        if action == menus.HOW_LONG:
            await interaction.response.send_modal(DaysModal(view, pushing=False))
            return
        if action == menus.PUSH_BACK:
            await interaction.response.send_modal(DaysModal(view, pushing=True))
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
        await interaction.response.send_modal(WordsModal(view, menu))


class MenuPick(discord.ui.Select):
    def __init__(self, rows: Any, row: int) -> None:
        found = list(rows)
        shown = found[:OPTIONS_MAX]
        super().__init__(
            placeholder=capped_placeholder(
                len(shown), len(found), pick=menus.MENU_PICK, capped=menus.MENUS_CAPPED
            ),
            options=[
                discord.SelectOption(label=str(one["name"])[:LABEL_MAX], value=str(one["name"]))
                for one in shown
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await open_menu(interaction, self.values[0], self.view)


class MarathonPick(discord.ui.Select):
    """Every marathon on the list, still to end first; the one the menu follows is ticked."""

    def __init__(self, bot: Any, guild_id: int, rows: Any, menu: Any, row: int) -> None:
        found = list(rows)
        shown = found[:OPTIONS_MAX]
        bound = (
            menu_value(menu, "ends_marathon_id")
            if menus.end_source(menu) == menus.MARATHON_END
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
        await run_set_marathon(interaction, int(self.values[0]), self.view)


class OptionPick(discord.ui.Select):
    def __init__(self, rows: Any, row: int) -> None:
        found = list(rows)
        super().__init__(
            placeholder=menus.REMOVE_PICK,
            options=[
                discord.SelectOption(
                    label=str(one["label"])[:LABEL_MAX],
                    value=str(one["role_id"]),
                    emoji=select_emoji(one["emoji"]),
                )
                for one in found[:OPTIONS_MAX]
            ],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await run_drop_option(interaction, int(self.values[0]), self.view)


class NewRolePick(discord.ui.RoleSelect):
    def __init__(self, row: int, placeholder: str = menus.ROLE_PICK) -> None:
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        picked = int(self.values[0].id)
        if not await opened(interaction):
            return
        if view.where == NEW_GRANT_VIEW:
            await render_new_grant(interaction, view.member_id, picked, view)
            return
        await render_add_role(interaction, view.menu_name, picked, view)


class WhoPick(discord.ui.UserSelect):
    def __init__(self, placeholder: str, row: int) -> None:
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        picked = int(self.values[0].id)
        if not await opened(interaction):
            return
        if view.where == GRANTS_VIEW:
            await render_grants(interaction, picked, view)
            return
        if view.where == NEW_GRANT_VIEW:
            await render_new_grant(interaction, picked, view.role_id, view)
            return
        await render_hand_out(interaction, view.menu_name, picked, view.removing, view)


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


class NewMenuModal(AnswersErrors, discord.ui.Modal, title=NEW_MENU_TITLE):
    name = discord.ui.TextInput(label=NAME_LABEL, max_length=LABEL_MAX)
    heading = discord.ui.TextInput(label=HEADING_LABEL, max_length=TITLE_MAX)
    description = discord.ui.TextInput(
        label=DESCRIPTION_LABEL,
        style=discord.TextStyle.paragraph,
        max_length=DESCRIPTION_LIMIT,
        required=False,
    )

    def __init__(self, previous: Any) -> None:
        super().__init__()
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_new_menu(
            interaction,
            {
                "name": str(self.name),
                "title": str(self.heading),
                "description": str(self.description),
            },
            self.previous,
        )


class WordsModal(AnswersErrors, discord.ui.Modal, title=WORDS_TITLE):
    heading = discord.ui.TextInput(label=HEADING_LABEL, max_length=TITLE_MAX)
    description = discord.ui.TextInput(
        label=DESCRIPTION_LABEL,
        style=discord.TextStyle.paragraph,
        max_length=DESCRIPTION_LIMIT,
        required=False,
    )

    def __init__(self, previous: Any, menu: Any) -> None:
        super().__init__()
        self.previous = previous
        self.heading.default = str(menu["title"])
        self.description.default = str(menu["description"] or "")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_change_menu(
            interaction,
            {"title": str(self.heading), "description": str(self.description)},
            self.previous,
        )


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


class OptionModal(AnswersErrors, discord.ui.Modal, title=OPTION_TITLE):
    label = discord.ui.TextInput(label=LABEL_LABEL, max_length=LABEL_MAX, required=False)
    emoji = discord.ui.TextInput(label=EMOJI_LABEL, max_length=64, required=False)

    def __init__(self, previous: Any) -> None:
        super().__init__()
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_add_option(interaction, str(self.label), str(self.emoji), self.previous)


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


class RoleMenus(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_ok_at: dict[str, str | None] = {name: None for name in LOOP_NAMES}
        self.last_error: dict[str, str | None] = {name: None for name in LOOP_NAMES}
        self.last_counts: dict[str, int] | None = None

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(RequestButton, RetiredMenuPick)
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
        ending = await roles_ending_now(self.bot.db, datetime.now(UTC))
        for row in await grants.due_grants(self.bot.db, now_iso()):
            guild = seen.get(row["guild_id"])
            if guild is not None and (row["guild_id"], row["role_id"]) not in ending:
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
        if removed:
            await grants.record_removed(
                self.bot.db, guild.id, after.id, removed, grants.BY_HAND
            )

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
        if await grants.open_grant(self.bot.db, guild.id, member.id, role_id) is not None:
            return
        if await timed_menu_owns(self.bot.db, guild.id, role_id):
            await grants.add_grant(self.bot.db, guild.id, member.id, role_id, grants.MANUAL)

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
