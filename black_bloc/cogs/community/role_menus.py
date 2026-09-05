from __future__ import annotations

import logging
import re
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import rolegrants as grants
from ... import rolemenus as menus
from ...actionlog import log_action, send_logs
from ...command_errors import NETWORK_ERRORS, AnswersErrors, SafeDynamicItem
from ...command_visibility import STAFF_ONLY
from ...golive import now_iso
from ...logkinds import VIA_DISCORD, kind_via
from ...panels import (
    DESCRIPTION_LIMIT,
    Panel,
    answer,
    capped_placeholder,
    clamped,
    db_up,
    opened,
    retire,
    still_staff,
)
from ...panels import option_label as select_label
from ...settings_store import DB_UNAVAILABLE, GUILD_ONLY, require_staff

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

ROLE_MENUS_OFF = (
    "Role menus are turned off right now, so nothing was changed. A Lead can turn them back on "
    "from the dashboard's Role menus tab, or with `/settings` ▸ **Turn a feature back on…**."
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
    return bot.store.get(guild_id, MODE_KEY) == "on"


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
        row = await request_context(interaction, self.request_id)
        if row is None:
            return
        if row["status"] != grants.PENDING:
            await interaction.response.send_message(
                grants.ALREADY_DECIDED.format(status=row["status"]), ephemeral=True
            )
            return
        if self.action == "deny":
            await interaction.response.send_modal(RequestDenyModal(self.request_id))
            return
        menu = await get_menu_by_id(interaction.client.db, row["menu_id"])
        days = expires_days_of(menu)
        if days:
            await interaction.response.send_modal(
                RequestApproveModal(self.request_id, days)
            )
            return
        await interaction.response.defer(ephemeral=True)
        await decide_from_click(interaction, self.request_id, grants.APPROVED)


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
        bot = interaction.client
        guard = getattr(bot, "guard", None)
        if guard is not None and not guard.allows_channel(interaction.channel_id):
            await interaction.response.send_message(guard.refusal_message(), ephemeral=True)
            return
        member = interaction.user
        guild = interaction.guild
        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message(NOT_IN_GUILD, ephemeral=True)
            return
        if not picking_is_on(bot, guild.id):
            await interaction.response.send_message(ROLE_MENUS_OFF, ephemeral=True)
            return
        if not bot.db.is_connected:
            await interaction.response.send_message(DB_UNAVAILABLE, ephemeral=True)
            return
        menu = await get_menu_by_id(bot.db, self.menu_id)
        if menu is None:
            await interaction.response.send_message(MENU_IS_GONE, ephemeral=True)
            return
        if needs_approval(menu):
            await self.ask_staff(interaction, bot, guild, member, menu)
            return
        to_add, to_remove = role_diff(
            (role.id for role in member.roles), self.role_ids, (int(v) for v in self.values)
        )
        if not to_add and not to_remove:
            await interaction.response.send_message(summary([], []), ephemeral=True)
            return
        if not await change_roles(bot, member, guild, to_add, to_remove, "Black Bloc role menu"):
            await interaction.response.send_message(CANNOT_EDIT_ROLES, ephemeral=True)
            return
        added = [self.labels.get(i, str(i)) for i in to_add]
        removed = [self.labels.get(i, str(i)) for i in to_remove]
        await interaction.response.send_message(summary(added, removed), ephemeral=True)
        await grants.record_added(
            bot.db,
            guild.id,
            member.id,
            to_add,
            grants.MENU,
            granted_by=member.id,
            until=grants.expires_at(expires_days_of(menu)),
        )
        await grants.record_removed(bot.db, guild.id, member.id, to_remove, grants.GIVEN_UP)
        await log_action(
            bot,
            guild,
            "role_menu.update",
            actor=member,
            target=member,
            details={"menu_id": self.menu_id, "added": added, "removed": removed},
        )

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
    await grants.record_added(
        bot.db,
        guild.id,
        target.id,
        to_add,
        grants.STAFF,
        granted_by=getattr(actor, "id", actor),
        until=grants.expires_at(expires_days_of(menu)),
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
    if not await delete_menu(bot.db, guild.id, name):
        return False
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


async def set_mode(bot: Any, guild: Any, actor: Any, value: Any, *, via: str = VIA_DISCORD) -> str:
    await bot.store.set(guild.id, MODE_KEY, value, by=actor_id(actor))
    await log_action(
        bot,
        guild,
        kind_via("role_menu.mode", via),
        actor=actor,
        details={"mode": value, "via": via},
    )
    return MODE_ON if value == "on" else MODE_OFF


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
    bot: Any, guild: Any, actor: Any, row: Any, days: Any, *, via: str = VIA_DISCORD
) -> tuple[str, str]:
    """Extending starts from the later of now and the end it already had."""
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


# --- the panel: one command, one ephemeral window ------------------------------------------------


STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}

ROOT = "root"
MENU_VIEW = "menu"
WHERE_VIEW = "where"
ADD_VIEW = "add"
HAND_VIEW = "hand"
GRANTS_VIEW = "grants"
NEW_GRANT_VIEW = "new_grant"
GRANT_VIEW = "grant"
REQUESTS_VIEW = "requests"
REQUEST_VIEW = "request"

SITE_BUTTON = "Open on the site"
WHERE_TITLE = "Where should {name} go?"
WHERE_PICK = "A channel…"
WHERE_DEFAULT = "The role menu channel is {where}, so leave it there or pick another."
WHERE_NOWHERE = (
    "No role menu channel is set, so pick one here. `/settings` ▸ **Roles & channels…** "
    "chooses the one Black Bloc offers next time."
)
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
REQUEST_GONE = (
    "Black Bloc has no record of that request any more, so nothing was changed. Press "
    "**Refresh** and pick again."
)
NAME_TAKEN = (
    "This server already has a role menu called **{name}**, so nothing was created. Pick "
    "another name."
)
MENU_MADE = "Created **{name}** ({mode}). **Add a role…** puts the first role on it."
MENU_SAVED = "**{name}** is saved."
OPTION_ADDED = "**{label}** is on **{name}**."
OPTION_GONE = "**{label}** is off **{name}**. Nobody loses the role they already have."
OPTION_WAS_NOT_ON = (
    "That role was not on **{name}**, so nothing changed. Press **Refresh** and look again."
)
MENU_DELETED = (
    "Deleted **{name}**. Nobody loses a role they already have, and any panel already posted "
    "stops working — delete that message by hand."
)
POSTED_SAID = "**{name}** is live in {where}. {link}"
BAD_MODE = (
    "**{given}** is not a way a role menu can work, so nothing was changed. Type one of "
    "{modes} — multiple lets people pick several, single allows one, staff hands them out."
)
BAD_NUMBER = (
    "**{given}** is not a whole number of days, so nothing was changed. Type a number, or 0."
)
CANNOT_HAND_OUT = (
    "Black Bloc cannot hand out **{name}**, so it was not added. That role is either above "
    "Black Bloc's own role in Server Settings → Roles, or managed by another app, or Black Bloc "
    "is missing the Manage Roles permission. Ask an admin to move Black Bloc's role above it, "
    "then try again."
)
REPOST_TROUBLE = (
    " The posted panel could not be refreshed, so press **Move it…** when you want it to catch up."
)

NEW_MENU_TITLE = "A new role menu"
WORDS_TITLE = "What this menu says"
RULES_TITLE = "How this menu behaves"
OPTION_TITLE = "How this role reads"
DAYS_TITLE = "How long for?"
PUSH_TITLE = "Push the end date back"

NAME_LABEL = "Short name, the one you will pick it by"
HEADING_LABEL = "Heading shown on the panel"
DESCRIPTION_LABEL = "Optional line under the heading"
MODE_LABEL = "multiple, single or staff"
LABEL_LABEL = "What the option says"
EMOJI_LABEL = "Optional emoji beside it"
EXPIRES_LABEL = "Days a role from this menu lasts, 0 for never"
RETRY_LABEL = "Days a member waits after a no"
DAYS_LABEL = "Days, or 0 for a role that never runs out"
PUSH_LABEL = "Days to add"


def minutes_for(bot: Any, guild_id: int) -> int:
    return menus.panel_minutes(bot.store, guild_id)


def add_site_button(view: Any, bot: Any, row: int) -> None:
    """No origin, no button — a link that goes nowhere is worse than no link at all."""
    url = menus.site_page_url(getattr(getattr(bot, "settings", None), "origin", ""))
    if not url:
        return
    view.add_item(
        discord.ui.Button(style=discord.ButtonStyle.link, label=SITE_BUTTON, url=url, row=row)
    )


def default_channel(interaction: discord.Interaction) -> Any:
    configured = interaction.client.store.get(interaction.guild.id, "role_menu_channel_id")
    if configured:
        return interaction.guild.get_channel(configured)
    return interaction.channel


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
        self.request_id: int | None = None
        self.member_id: int | None = None
        self.role_id: int | None = None
        self.removing: bool | None = None


async def option_counts(db: Any, rows: Any) -> dict[int, int]:
    return {menu["id"]: len(await get_options(db, menu["id"])) for menu in rows}


async def build_panel(bot: Any, guild: Any, actor: Any) -> tuple[discord.Embed, RoleMenuPanel]:
    """One command, one staff panel — every path here was `require_staff` before it was a panel."""
    rows = await list_menus(bot.db, guild.id)
    picking = picking_is_on(bot, guild.id)
    waiting = await grants.requests_by_status(bot.db, guild.id, (grants.PENDING,))
    lines = (
        menus.list_lines(rows, await option_counts(bot.db, rows))
        if rows
        else [menus.NO_MENUS_LINE]
    )
    if not picking:
        lines.append(menus.PICKING_IS_OFF)
    embed = discord.Embed(title=menus.PANEL_TITLE, description=clamped(lines))
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    if rows:
        view.add_item(MenuPick(rows, row=0))
    for move in menus.root_buttons(
        has_menus=bool(rows), picking_on=picking, pending=len(waiting)
    ):
        view.add_item(MoveButton(move))
    add_site_button(view, bot, row=2)
    _ = actor
    return (embed, view)


async def build_menu(
    bot: Any, guild: Any, name: str
) -> tuple[discord.Embed | None, RoleMenuPanel | None]:
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        return (None, None)
    options = await get_options(bot.db, menu["id"])
    picking = picking_is_on(bot, guild.id)
    lines = menus.menu_lines(menu, options, note=panel_note(menu))
    if len(options) >= OPTIONS_MAX:
        lines.append(menus.OPTIONS_ARE_FULL.format(limit=OPTIONS_MAX))
    if not picking:
        lines.append(menus.PICKING_IS_OFF)
    embed = discord.Embed(
        title=menus.MENU_TITLE.format(name=menu["name"]), description=clamped(lines)
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = MENU_VIEW
    view.menu_name = menu["name"]
    if options:
        view.add_item(OptionPick(options, row=0))
    for move in menus.menu_buttons(
        posted=bool(menu["message_id"]),
        options=len(options),
        menu_mode=str(menu["mode"]),
        picking_on=picking,
        approval=needs_approval(menu),
        options_max=OPTIONS_MAX,
    ):
        view.add_item(MoveButton(move))
    return (embed, view)


def build_where(
    interaction: discord.Interaction, name: str
) -> tuple[discord.Embed, RoleMenuPanel]:
    home = default_channel(interaction)
    line = WHERE_DEFAULT.format(where=home.mention) if home is not None else WHERE_NOWHERE
    embed = discord.Embed(title=WHERE_TITLE.format(name=name), description=line)
    view = RoleMenuPanel(minutes_for(interaction.client, interaction.guild.id))
    view.where = WHERE_VIEW
    view.menu_name = name
    view.add_item(WherePick(row=0))
    view.add_item(MoveButton(menus.BACK_MOVE._replace(row=1)))
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


async def build_grants(
    bot: Any, guild: Any, member_id: Any
) -> tuple[discord.Embed, RoleMenuPanel]:
    """The audit: every timed role running here, soonest to end first (design §I-amend)."""
    rows = await menus.active_grants(
        bot.db, guild.id, user_id=int(member_id) if member_id else None
    )
    embed = discord.Embed(
        title=menus.GRANTS_TITLE,
        description=clamped(menus.grant_lines(rows, one_member=bool(member_id))),
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
    embed = discord.Embed(
        title=menus.GRANT_TITLE.format(grant_id=row["id"]), description=clamped(lines)
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = GRANT_VIEW
    view.grant_id = int(row["id"])
    for move in menus.grant_buttons(
        ends=bool(row["expires_at"]), removed=bool(row["removed_at"])
    ):
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_requests(bot: Any, guild: Any) -> tuple[discord.Embed, RoleMenuPanel]:
    rows = await grants.requests_by_status(bot.db, guild.id, (grants.PENDING,))
    named = {menu["id"]: menu["name"] for menu in await list_menus(bot.db, guild.id)}
    embed = discord.Embed(
        title=menus.REQUESTS_TITLE,
        description=menus.NO_REQUESTS if not rows else f"**{len(rows)}** waiting.",
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = REQUESTS_VIEW
    if rows:
        view.add_item(RequestPick(rows, named, guild, row=0))
    for move in menus.requests_list_buttons():
        view.add_item(MoveButton(move))
    return (embed, view)


async def build_request(
    bot: Any, guild: Any, request_id: Any
) -> tuple[discord.Embed | None, RoleMenuPanel | None]:
    row = await grants.get_request(bot.db, int(request_id)) if request_id else None
    if row is None or row["guild_id"] != guild.id:
        return (None, None)
    menu = await get_menu_by_id(bot.db, row["menu_id"])
    days = expires_days_of(menu)
    label = await label_for(bot.db, guild, row["menu_id"], row["role_id"])
    embed = request_card(
        row,
        label=label,
        menu_name=menu["name"] if menu is not None else "a deleted menu",
        days=days,
    )
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = REQUEST_VIEW
    view.request_id = int(row["id"])
    for move in menus.request_buttons(row["status"], timed=bool(days)):
        view.add_item(MoveButton(move))
    return (embed, view)


def confirm(
    bot: Any, guild: Any, previous: Any, question: str, moves: Any
) -> tuple[discord.Embed, RoleMenuPanel]:
    embed = discord.Embed(title=menus.CONFIRM_TITLE, description=question)
    view = RoleMenuPanel(minutes_for(bot, guild.id))
    view.where = getattr(previous, "where", ROOT)
    view.menu_name = getattr(previous, "menu_name", "")
    view.grant_id = getattr(previous, "grant_id", None)
    view.member_id = getattr(previous, "member_id", None)
    for move in moves:
        view.add_item(MoveButton(move))
    return (embed, view)


# --- rendering -----------------------------------------------------------------------------------


async def render(interaction: discord.Interaction, embed: Any, view: Any, previous: Any) -> None:
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


async def render_requests(interaction: discord.Interaction, previous: Any = None) -> None:
    embed, view = await build_requests(interaction.client, interaction.guild)
    await render(interaction, embed, view, previous)


async def render_request(
    interaction: discord.Interaction, request_id: Any, previous: Any = None
) -> None:
    embed, view = await build_request(interaction.client, interaction.guild, request_id)
    if view is None:
        await render_requests(interaction, previous)
        await answer(interaction, REQUEST_GONE)
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


async def open_new_grant(interaction: discord.Interaction, view: Any) -> None:
    if not await opened(interaction):
        return
    await render_new_grant(interaction, view.member_id, view.role_id, view)


async def open_grant(interaction: discord.Interaction, grant_id: Any, previous: Any) -> None:
    if not await opened(interaction):
        return
    await render_grant(interaction, grant_id, previous)


async def open_requests(interaction: discord.Interaction, previous: Any) -> None:
    if not await opened(interaction):
        return
    await render_requests(interaction, previous)


async def open_request(interaction: discord.Interaction, request_id: Any, previous: Any) -> None:
    if not await opened(interaction):
        return
    await render_request(interaction, request_id, previous)


async def open_where(interaction: discord.Interaction, view: Any) -> None:
    if not await opened(interaction):
        return
    embed, fresh = build_where(interaction, view.menu_name)
    await render(interaction, embed, fresh, view)


async def refresh_where(interaction: discord.Interaction, view: Any) -> None:
    if view.where == MENU_VIEW:
        await open_menu(interaction, view.menu_name, view)
        return
    if view.where == GRANTS_VIEW:
        await open_grants(interaction, view.member_id, view)
        return
    if view.where == GRANT_VIEW:
        await open_grant(interaction, view.grant_id, view)
        return
    if view.where == REQUESTS_VIEW:
        await open_requests(interaction, view)
        return
    if view.where == REQUEST_VIEW:
        await open_request(interaction, view.request_id, view)
        return
    if view.where == HAND_VIEW:
        await open_hand_out(interaction, view, view.removing)
        return
    if view.where == ADD_VIEW:
        await open_add_role(interaction, view)
        return
    await open_root(interaction, view)


async def back_from(interaction: discord.Interaction, view: Any) -> None:
    if view.where in (ADD_VIEW, HAND_VIEW, WHERE_VIEW):
        await open_menu(interaction, view.menu_name, view)
        return
    if view.where in (GRANT_VIEW, NEW_GRANT_VIEW):
        await open_grants(interaction, view.member_id, view)
        return
    if view.where == REQUEST_VIEW:
        await open_requests(interaction, view)
        return
    await open_root(interaction, view)


# --- the moves, one function each ----------------------------------------------------------------


async def repost_if_live(bot: Any, guild: Any, menu: Any) -> bool:
    """F-R3(a): an edit that changes what the panel says edits the panel, never posts a second."""
    if not menu["message_id"] or str(menu["mode"]) == STAFF_MODE:
        return True
    if not picking_is_on(bot, guild.id):
        return True
    options = await get_options(bot.db, menu["id"])
    channel = bot.get_channel(menu["channel_id"]) if menu["channel_id"] else None
    if not options or channel is None:
        return True
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        return True
    try:
        await post_panel(bot, menu, options, channel)
    except Exception as exc:
        log.warning("role menus: %s's panel was not refreshed: %s", menu["name"], exc)
        return False
    return True


async def run_new_menu(
    interaction: discord.Interaction, fields: dict[str, Any], previous: Any
) -> None:
    if not await opened(interaction):
        return
    mode = str(fields["mode"] or "").strip().lower() or "multiple"
    if mode not in MODES:
        await render_panel(interaction, previous)
        await answer(interaction, BAD_MODE.format(given=mode[:40], modes=", ".join(MODES)))
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
            mode,
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
    await answer(interaction, MENU_MADE.format(name=name, mode=mode))


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
    refreshed = await repost_if_live(interaction.client, interaction.guild, menu)
    await render_menu(interaction, name, previous)
    await answer(
        interaction, MENU_SAVED.format(name=name) + ("" if refreshed else REPOST_TROUBLE)
    )


async def run_add_option(
    interaction: discord.Interaction, label: Any, emoji: Any, previous: Any
) -> None:
    if not await opened(interaction):
        return
    guild = interaction.guild
    name = previous.menu_name
    menu = await get_menu(interaction.client.db, guild.id, name)
    if menu is None:
        await render_panel(interaction, previous)
        await answer(interaction, MENU_GONE.format(name=name))
        return
    role = guild.get_role(int(previous.role_id)) if previous.role_id else None
    if role is None:
        await render_add_role(interaction, name, None, previous)
        await answer(interaction, ROLE_ADD_NOTHING)
        return
    assignable = getattr(role, "is_assignable", None)
    if callable(assignable) and not assignable():
        await render_add_role(interaction, name, role.id, previous)
        await answer(interaction, CANNOT_HAND_OUT.format(name=role.name))
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
    await repost_if_live(interaction.client, guild, menu)
    await render_menu(interaction, name, previous)
    await answer(interaction, OPTION_ADDED.format(label=wanted, name=name))


async def run_drop_option(interaction: discord.Interaction, role_id: int, previous: Any) -> None:
    if not await opened(interaction):
        return
    guild = interaction.guild
    name = previous.menu_name
    menu = await get_menu(interaction.client.db, guild.id, name)
    if menu is None:
        await render_panel(interaction, previous)
        await answer(interaction, MENU_GONE.format(name=name))
        return
    label = await label_for(interaction.client.db, guild, menu["id"], role_id)
    gone = await drop_option(interaction.client, guild, interaction.user, menu, role_id)
    if gone:
        await repost_if_live(interaction.client, guild, menu)
    await render_menu(interaction, name, previous)
    await answer(
        interaction,
        OPTION_GONE.format(label=label, name=name)
        if gone
        else OPTION_WAS_NOT_ON.format(name=name),
    )


async def run_post(interaction: discord.Interaction, channel: Any, previous: Any) -> None:
    if not await opened(interaction):
        return
    guild = interaction.guild
    bot = interaction.client
    name = previous.menu_name
    menu = await get_menu(bot.db, guild.id, name)
    if menu is None:
        await render_panel(interaction, previous)
        await answer(interaction, MENU_GONE.format(name=name))
        return
    options = await get_options(bot.db, menu["id"])
    if not picking_is_on(bot, guild.id) or not options or str(menu["mode"]) == STAFF_MODE:
        await render_menu(interaction, name, previous)
        await answer(interaction, ROLE_MENUS_OFF)
        return
    guard = getattr(bot, "guard", None)
    if guard is not None and not guard.allows_channel(channel.id):
        await render_menu(interaction, name, previous)
        await answer(interaction, guard.refusal_message())
        return
    message = await post_menu(bot, guild, interaction.user, menu, options, channel)
    await render_menu(interaction, name, previous)
    await answer(
        interaction,
        POSTED_SAID.format(
            name=name, where=getattr(channel, "mention", channel.id), link=message.jump_url
        ),
    )


async def run_take_down(interaction: discord.Interaction, previous: Any) -> None:
    from ... import rolemenu_panels as posts

    if not await opened(interaction):
        return
    name = previous.menu_name
    menu = await get_menu(interaction.client.db, interaction.guild.id, name)
    if menu is None or not menu["message_id"]:
        await render_menu(interaction, name, previous)
        await answer(interaction, NOTHING_TO_UNPOST.format(name=name))
        return
    done = await posts.unpost(interaction.client, menu, interaction.user)
    await render_menu(interaction, name, previous)
    await answer(
        interaction,
        PANEL_TAKEN_DOWN.format(name=name) if done else PANEL_STUCK.format(name=name),
    )


async def run_delete_menu(interaction: discord.Interaction, previous: Any) -> None:
    if not await opened(interaction):
        return
    name = previous.menu_name
    gone = await drop_menu(interaction.client, interaction.guild, interaction.user, name)
    await render_panel(interaction, previous)
    await answer(
        interaction, MENU_DELETED.format(name=name) if gone else MENU_GONE.format(name=name)
    )


async def run_mode(interaction: discord.Interaction, previous: Any) -> None:
    if not await opened(interaction):
        return
    bot = interaction.client
    wanted = "off" if picking_is_on(bot, interaction.guild.id) else "on"
    said = await set_mode(bot, interaction.guild, interaction.user, wanted)
    await render_panel(interaction, previous)
    await answer(interaction, f"Picking roles from the panels is now **{wanted}**. {said}")


async def run_seed(interaction: discord.Interaction, previous: Any) -> None:
    if not await opened(interaction):
        return
    created, skipped = await seed_menus(interaction.client, interaction.guild, interaction.user)
    await render_panel(interaction, previous)
    await answer(interaction, seed_summary(created, skipped))


async def run_assign(interaction: discord.Interaction, select: Any, previous: Any) -> None:
    if not await guarded(interaction) or not await opened(interaction):
        return
    bot = interaction.client
    guild = interaction.guild
    if not picking_is_on(bot, guild.id):
        await render_menu(interaction, previous.menu_name, previous)
        await answer(interaction, ROLE_MENUS_OFF)
        return
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


async def run_decision(
    interaction: discord.Interaction,
    status: str,
    previous: Any,
    *,
    reason: Any = None,
    days: Any = None,
) -> None:
    """A second door onto a decision the card also offers; the loser is told, never acted on."""
    if not await opened(interaction):
        return
    said, _fresh = await apply_request_decision(
        interaction.client,
        interaction.guild,
        int(previous.request_id),
        status,
        interaction.user,
        reason=reason,
        days=days,
    )
    await render_request(interaction, previous.request_id, previous)
    await answer(interaction, said)


# --- the controls --------------------------------------------------------------------------------


class MoveButton(discord.ui.Button):
    def __init__(self, move: Any) -> None:
        super().__init__(label=move.label, style=STYLES[move.style], row=move.row)
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
        if action == menus.REQUESTS:
            await open_requests(interaction, view)
            return
        if action == menus.MODE:
            await run_mode(interaction, view)
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
        if action == menus.APPROVE:
            await run_decision(interaction, grants.APPROVED, view)
            return
        if action == menus.POST:
            await open_where(interaction, view)
            return
        if action == menus.TAKE_DOWN:
            await run_take_down(interaction, view)
            return
        if action == menus.USE_ROLE_NAME:
            await run_add_option(interaction, None, None, view)
            return
        if action == menus.APPROVAL:
            await run_change_menu(
                interaction, {"approval": self.label == menus.APPROVAL_ON_LABEL}, view
            )
            return
        if action in (menus.DELETE, menus.SEED, menus.END_NOW):
            await self.ask_first(interaction, view, action)
            return
        if action == menus.DELETE_YES:
            await run_delete_menu(interaction, view)
            return
        if action == menus.SEED_YES:
            await run_seed(interaction, view)
            return
        if action == menus.END_YES:
            await run_revoke(interaction, view)
            return
        if action in (menus.KEEP, menus.LEAVE_IT):
            await refresh_where(interaction, view)
            return
        await self.open_modal(interaction, view, action)

    async def ask_first(self, interaction: discord.Interaction, view: Any, action: str) -> None:
        """The three moves nobody can undo ask once; every quieter move is one press."""
        if not await opened(interaction):
            return
        bot, guild = interaction.client, interaction.guild
        if action == menus.DELETE:
            question = menus.DELETE_QUESTION.format(name=view.menu_name)
            moves = (
                menus.PanelMove(menus.DELETE_YES, menus.DELETE_YES_LABEL, "danger", 0),
                menus.PanelMove(menus.KEEP, menus.KEEP_IT_LABEL, "secondary", 0),
            )
        elif action == menus.SEED:
            question = menus.SEED_QUESTION
            moves = (
                menus.PanelMove(menus.SEED_YES, menus.SEED_YES_LABEL, "primary", 0),
                menus.PanelMove(menus.KEEP, menus.LEAVE_THEM_LABEL, "secondary", 0),
            )
        else:
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
        embed, fresh = confirm(bot, guild, view, question, moves)
        await render(interaction, embed, fresh, view)

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
        if action == menus.DENY:
            await interaction.response.send_modal(PanelDenyModal(view))
            return
        if action == menus.APPROVE_DAYS:
            menu = await menu_of_request(bot, guild, view.request_id)
            await interaction.response.send_modal(
                PanelApproveModal(view, expires_days_of(menu) or 0)
            )
            return
        menu = await get_menu(bot.db, guild.id, view.menu_name)
        if menu is None:
            await answer(interaction, MENU_GONE.format(name=view.menu_name))
            return
        if action == menus.WORDS:
            await interaction.response.send_modal(WordsModal(view, menu))
            return
        await interaction.response.send_modal(RulesModal(view, menu))


async def menu_of_request(bot: Any, guild: Any, request_id: Any) -> Any:
    row = await grants.get_request(bot.db, int(request_id)) if request_id else None
    if row is None or row["guild_id"] != guild.id:
        return None
    return await get_menu_by_id(bot.db, row["menu_id"])


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


class RequestPick(discord.ui.Select):
    def __init__(self, rows: Any, named: Any, guild: Any, row: int) -> None:
        found = list(rows)
        shown = found[:OPTIONS_MAX]
        super().__init__(
            placeholder=capped_placeholder(
                len(shown), len(found), pick=menus.REQUEST_PICK, capped=menus.REQUESTS_CAPPED
            ),
            options=[
                discord.SelectOption(
                    label=select_label(
                        one["id"], named.get(one["menu_id"]), who_is(guild, one["user_id"])
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
        await open_request(interaction, int(self.values[0]), self.view)


class WherePick(discord.ui.ChannelSelect):
    def __init__(self, row: int) -> None:
        super().__init__(
            placeholder=WHERE_PICK,
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        picked = self.values[0]
        channel = interaction.guild.get_channel(picked.id) or picked
        await run_post(interaction, channel, self.view)


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
    mode = discord.ui.TextInput(label=MODE_LABEL, max_length=10, required=False)

    def __init__(self, previous: Any) -> None:
        super().__init__()
        self.previous = previous
        self.mode.default = "multiple"

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_new_menu(
            interaction,
            {
                "name": str(self.name),
                "title": str(self.heading),
                "description": str(self.description),
                "mode": str(self.mode),
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


class RulesModal(AnswersErrors, discord.ui.Modal, title=RULES_TITLE):
    expires = discord.ui.TextInput(label=EXPIRES_LABEL, max_length=5, required=False)
    retry = discord.ui.TextInput(label=RETRY_LABEL, max_length=5, required=False)

    def __init__(self, previous: Any, menu: Any) -> None:
        super().__init__()
        self.previous = previous
        self.expires.default = str(expires_days_of(menu) or 0)
        self.retry.default = str(retry_days_of(menu))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            wanted: dict[str, Any] = {
                "expires_days": read_days(self.expires),
                "retry_days": read_days(self.retry),
            }
        except ValueError as exc:
            await answer(interaction, BAD_NUMBER.format(given=str(exc)[:40]))
            return
        if wanted["expires_days"] is None:
            wanted["expires_days"] = UNSET
        await run_change_menu(interaction, wanted, self.previous)


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


class PanelDenyModal(AnswersErrors, discord.ui.Modal, title="Why not?"):
    reason = discord.ui.TextInput(
        label="One line the member will be sent",
        style=discord.TextStyle.paragraph,
        max_length=grants.REASON_LIMIT,
    )

    def __init__(self, previous: Any) -> None:
        super().__init__()
        self.previous = previous

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await run_decision(interaction, grants.DENIED, self.previous, reason=str(self.reason))


class PanelApproveModal(AnswersErrors, discord.ui.Modal, title="How long for?"):
    days = discord.ui.TextInput(label=DAYS_LABEL, max_length=5, required=False)

    def __init__(self, previous: Any, default_days: int) -> None:
        super().__init__()
        self.previous = previous
        self.days.default = str(default_days)
        self.days.placeholder = f"{default_days} — what this menu says"

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            wanted = read_days(self.days)
        except ValueError as exc:
            await answer(interaction, BAD_NUMBER.format(given=str(exc)[:40]))
            return
        await run_decision(interaction, grants.APPROVED, self.previous, days=wanted)


class RoleMenus(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_ok_at: dict[str, str | None] = {name: None for name in LOOP_NAMES}
        self.last_error: dict[str, str | None] = {name: None for name in LOOP_NAMES}

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(RequestButton)
        if not self.bot.db.is_connected:
            return
        for menu in await posted_menus(self.bot.db):
            options = await get_options(self.bot.db, menu["id"])
            if not options:
                continue
            self.bot.add_view(
                RoleMenuView(menu["id"], options, menu["mode"]), message_id=menu["message_id"]
            )
            log.info("role menu %s re-registered on message %s", menu["name"], menu["message_id"])
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

    def loop_failed(self, name: str, exc: BaseException, loop: Any) -> None:
        """A loop that raised is restarted, and its failure is on the record until it is not."""
        self.last_error[name] = f"{now_iso()} · {type(exc).__name__}: {exc}"
        log.exception("role menus: the %s loop raised and is being restarted", name, exc_info=exc)
        loop.restart()

    @tasks.loop(hours=EXPIRY_HOURS)
    async def _expiry_loop(self) -> None:
        if self.bot.db.is_connected:
            await self.run_due_grants()
            await self.reconcile_records()
        self.last_ok_at["expiry"] = now_iso()

    @_expiry_loop.before_loop
    async def _before_expiry(self) -> None:
        await self.bot.wait_until_ready()

    @_expiry_loop.error
    async def _expiry_broke(self, exc: BaseException) -> None:
        self.loop_failed("expiry", exc, self._expiry_loop)

    async def run_due_grants(self) -> None:
        """Grants whose day has come: the role comes off, the row closes, the member is told."""
        seen = {guild.id: guild for guild in getattr(self.bot, "guilds", ())}
        for row in await grants.due_grants(self.bot.db, now_iso()):
            guild = seen.get(row["guild_id"])
            if guild is not None:
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
        name="rolemenu", description="Role menus, timed roles and the requests waiting on staff"
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
        embed, view = await build_panel(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleMenus(bot))
