from __future__ import annotations

import logging
import re
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import rolegrants as grants
from ...actionlog import (
    LOGS_DEFAULT,
    LOGS_MAX,
    LOGS_MIN,
    log_action,
    send_logs,
)
from ...command_errors import NETWORK_ERRORS, AnswersErrors, SafeDynamicItem
from ...golive import now_iso
from ...logkinds import VIA_DISCORD, VIA_WEBSITE, WEB
from ...modcases import pages_under_limit
from ...settings_store import DB_UNAVAILABLE, ROLEMENU_MODES, require_staff

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
    "from the dashboard's Role menus tab or with `/settings set-value rolemenu_mode on`."
)
MODE_ON = (
    "Every menu that has a channel is posted there again in a few seconds, and the `/rolemenu` "
    "commands come back with them."
)
MODE_OFF = (
    "The posted panels are taken down in a few seconds and the `/rolemenu` commands disappear "
    "from Discord with them. Nobody loses a role, and no menu is changed — the dashboard's Role "
    "menus tab and `/settings set-value rolemenu_mode on` post them all again."
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
    "roles to themselves. Hand them out with `/rolemenu assign {name} @member` and take them "
    "back with `/rolemenu unassign {name} @member`."
)
NOTHING_TO_UNASSIGN = (
    "**{name}** has none of the roles on **{menu}**, so there is nothing to take off. "
    "`/rolemenu assign {menu} @member` gives them one."
)
NO_MENUS_YET = (
    "This server has no role menus yet. Make one with `/rolemenu create`, or bring over the six "
    "default ones with `/rolemenu seed-defaults`."
)
SEED_EMOJI_NOTE = (
    "A menu that already exists is left exactly as it is, options and all — to pick up the "
    "Marathons emoji on `event-alerts`, delete it with `/rolemenu delete event-alerts` and run "
    "this again."
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
    "**{name}** has no panel up right now, so there was nothing to take down. Post it with "
    "`/rolemenu post {name}` first."
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
    "hand it over with `/role grant`."
)
BAD_DAYS = (
    "**{given}** is not a number of days, so nothing was decided. Type a whole number, or 0 for a "
    "role that never runs out."
)
ALREADY_TIMED = (
    "**{name}** already has **{label}** on a clock that runs out {stamp}, so nothing was changed. "
    "`/role extend` pushes it back."
)
GRANT_STARTED_ON_A_ROLE_THEY_HAD = (
    " They already had it, so nothing was added — Black Bloc is only keeping time on it now."
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


async def answer(interaction: discord.Interaction, text: str) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(
            text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )
        return
    await interaction.response.send_message(
        text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )


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
        "Post each one with `/rolemenu post <name>` — except `runner-status`, which staff "
        "hand out with `/rolemenu assign`."
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
        return await _deny_request(bot, guild, row, member, label, menu, menu_name, actor, reason)
    if member is None:
        return MEMBER_HAS_GONE.format(name=row["user_id"]), None
    return await _approve_request(bot, guild, row, member, label, menu, menu_name, actor, days)


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
        "role.approved",
        actor=actor,
        target=member,
        details={
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
        "role.denied",
        actor=actor,
        target=member if member is not None else row["user_id"],
        reason=said,
        details={"request_id": row["id"], "menu": menu_name, "role_id": row["role_id"]},
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
    head = f"{WEB}." if via == VIA_WEBSITE else ""
    kind = f"{head}role_menu.{'unassign' if remove else 'assign'}"
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


class StaffAssignSelect(discord.ui.Select):
    def __init__(self, menu_id: int, options: Any, target: Any, *, remove: bool) -> None:
        held = {role.id for role in target.roles}
        super().__init__(
            placeholder=("Roles to take off " if remove else "Roles for ") + target.display_name,
            min_values=0,
            max_values=max(1, min(len(options), 25)),
            options=[
                discord.SelectOption(
                    label=row["label"],
                    value=str(row["role_id"]),
                    emoji=select_emoji(row["emoji"]),
                    default=not remove and row["role_id"] in held,
                )
                for row in options
            ],
        )
        self.menu_id = menu_id
        self.rows = list(options)
        self.target = target
        self.remove = remove

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        guard = getattr(bot, "guard", None)
        if guard is not None and not guard.allows_channel(interaction.channel_id):
            await interaction.response.send_message(guard.refusal_message(), ephemeral=True)
            return
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(NOT_IN_GUILD, ephemeral=True)
            return
        if not picking_is_on(bot, guild.id):
            await interaction.response.send_message(ROLE_MENUS_OFF, ephemeral=True)
            return
        menu = await get_menu_by_id(bot.db, self.menu_id)
        _, said = await staff_assign(
            bot,
            guild,
            interaction.user,
            menu,
            self.rows,
            self.target,
            self.values,
            remove=self.remove,
        )
        await interaction.response.send_message(
            said, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )


class StaffAssignView(discord.ui.View):
    def __init__(self, menu_id: int, options: Any, target: Any, *, remove: bool) -> None:
        super().__init__(timeout=180)
        self.add_item(StaffAssignSelect(menu_id, options, target, remove=remove))


class RoleMenus(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_ok_at: dict[str, str | None] = {name: None for name in LOOP_NAMES}
        self.last_error: dict[str, str | None] = {name: None for name in LOOP_NAMES}

    rolemenu = app_commands.Group(
        name="rolemenu", description="Self-serve role panels people pick from"
    )
    role = app_commands.Group(
        name="role", description="Hand a role out for a while, and push the end date back"
    )

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

    @rolemenu.command(name="logs", description="The last few role menu log lines")
    @app_commands.describe(
        count="How many lines, 1 to 50 (10 by default)",
        important_only="True to leave out the dry runs and the housekeeping",
    )
    async def rolemenu_logs(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, LOGS_MIN, LOGS_MAX] = LOGS_DEFAULT,
        important_only: bool = False,
    ) -> None:
        await send_logs(interaction, "rolemenu", count=count, important_only=important_only)

    @rolemenu.command(name="create", description="Create an empty role menu")
    @app_commands.describe(
        name="Short name you will use in the other commands",
        title="Heading shown on the panel",
        description="Optional line under the heading",
        mode="multiple lets people pick several; single allows one; staff hands them out",
    )
    @app_commands.choices(mode=[app_commands.Choice(name=m, value=m) for m in MODES])
    async def create(
        self,
        interaction: discord.Interaction,
        name: str,
        title: str,
        description: str | None = None,
        mode: app_commands.Choice[str] | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        chosen = mode.value if mode else "multiple"
        try:
            menu_id = await create_menu(
                self.bot.db, interaction.guild.id, name, title, description, chosen
            )
        except MenuLimitError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        if menu_id is None:
            await interaction.response.send_message(
                f"This server already has a role menu called **{name}**, so nothing was "
                f"created. Pick another name, or edit that one with `/rolemenu add`.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"Created **{name}** ({chosen}). Add roles with `/rolemenu add {name} <role>`, "
            f"then post it with `/rolemenu post {name}`.",
            ephemeral=True,
        )

    @rolemenu.command(name="add", description="Add a role to a menu")
    @app_commands.describe(
        name="The menu to add to",
        role="The role people will be able to give themselves",
        label="What the option says; defaults to the role name",
        emoji="Optional emoji shown beside the option",
    )
    async def add(
        self,
        interaction: discord.Interaction,
        name: str,
        role: discord.Role,
        label: str | None = None,
        emoji: str | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        menu = await get_menu(self.bot.db, interaction.guild.id, name)
        if menu is None:
            await interaction.response.send_message(self._no_such_menu(name), ephemeral=True)
            return
        if not role.is_assignable():
            await interaction.response.send_message(
                f"Black Bloc cannot hand out **{role.name}**, so it was not added. That role "
                "is either above Black Bloc's own role in Server Settings → Roles, or managed "
                "by another app, or Black Bloc is missing the Manage Roles permission. Ask an "
                "admin to move Black Bloc's role above it, then run this again.",
                ephemeral=True,
            )
            return
        try:
            await add_option(self.bot.db, menu["id"], role.id, label or role.name, emoji)
        except MenuLimitError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            f"Added **{label or role.name}** to **{name}**. Run `/rolemenu post {name}` to "
            "refresh the panel.",
            ephemeral=True,
        )

    @rolemenu.command(name="remove", description="Remove a role from a menu")
    async def remove(
        self, interaction: discord.Interaction, name: str, role: discord.Role
    ) -> None:
        if not await require_staff(interaction):
            return
        menu = await get_menu(self.bot.db, interaction.guild.id, name)
        if menu is None:
            await interaction.response.send_message(self._no_such_menu(name), ephemeral=True)
            return
        if not await remove_option(self.bot.db, menu["id"], role.id):
            await interaction.response.send_message(
                f"**{role.name}** was not on **{name}**, so nothing changed. `/rolemenu show "
                f"{name}` lists what is on it.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"Removed **{role.name}** from **{name}**. Nobody loses the role they already "
            f"have; run `/rolemenu post {name}` to refresh the panel.",
            ephemeral=True,
        )

    @rolemenu.command(
        name="edit", description="Turn approval on, and say how long a role from it lasts"
    )
    @app_commands.describe(
        name="The menu to change",
        approval="Ask staff before the role is handed over",
        expires_days="Days a role from this menu lasts; 0 means it never runs out",
        retry_days="Days a member waits after a no before they may ask again",
    )
    async def edit(
        self,
        interaction: discord.Interaction,
        name: str,
        approval: bool | None = None,
        expires_days: app_commands.Range[int, 0, grants.DAYS_MAX] | None = None,
        retry_days: app_commands.Range[int, 0, grants.DAYS_MAX] | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        changed = await update_menu(
            self.bot.db,
            interaction.guild.id,
            name,
            approval=approval,
            expires_days=UNSET if expires_days is None else expires_days,
            retry_days=retry_days,
        )
        if not changed:
            await interaction.response.send_message(self._no_such_menu(name), ephemeral=True)
            return
        menu = await get_menu(self.bot.db, interaction.guild.id, name)
        days = expires_days_of(menu)
        await interaction.response.send_message(
            f"**{name}** — approval {'on' if needs_approval(menu) else 'off'}, "
            + (f"roles last {days} day(s)" if days else "roles have no end date")
            + f", a no lasts {retry_days_of(menu)} day(s). "
            + "Run `/rolemenu post` again so the panel says the same thing.",
            ephemeral=True,
        )
        await log_action(
            self.bot,
            interaction.guild,
            "role_menu.edit",
            actor=interaction.user,
            details={
                "menu": name,
                "approval": needs_approval(menu),
                "expires_days": days,
                "retry_days": retry_days_of(menu),
            },
        )

    @role.command(name="logs", description="The last few role menu log lines")
    @app_commands.describe(
        count="How many lines, 1 to 50 (10 by default)",
        important_only="True to leave out the dry runs and the housekeeping",
    )
    async def role_logs(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, LOGS_MIN, LOGS_MAX] = LOGS_DEFAULT,
        important_only: bool = False,
    ) -> None:
        await send_logs(interaction, "rolemenu", count=count, important_only=important_only)

    @role.command(name="grant", description="Give a member a role for a number of days")
    @app_commands.describe(
        member="Who gets it",
        role="The role to hand over",
        days="How many days they keep it",
        reason="Why, for the log",
    )
    async def role_grant(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
        days: app_commands.Range[int, 1, grants.DAYS_MAX],
        reason: str | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        guild = interaction.guild
        open_row = await grants.open_grant(self.bot.db, guild.id, member.id, role.id)
        if open_row is not None and open_row["expires_at"]:
            await interaction.response.send_message(
                ALREADY_TIMED.format(
                    name=member.display_name,
                    label=role.name,
                    stamp=grants.stamp(open_row["expires_at"]),
                ),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        await interaction.response.defer(ephemeral=True)
        held = any(r.id == role.id for r in member.roles)
        if not held and not await change_roles(
            self.bot,
            member,
            guild,
            {role.id},
            set(),
            f"Black Bloc /role grant by {interaction.user}",
        ):
            await answer(
                interaction,
                grants.CANNOT_EDIT_THEIRS.format(name=member.display_name, label=role.name),
            )
            return
        until = grants.expires_at(days)
        if open_row is not None:
            await grants.extend_grant(self.bot.db, open_row["id"], until)
        else:
            await grants.add_grant(
                self.bot.db,
                guild.id,
                member.id,
                role.id,
                grants.STAFF,
                granted_by=interaction.user.id,
                until=until,
            )
        await log_action(
            self.bot,
            guild,
            "role.granted",
            actor=interaction.user,
            target=member,
            reason=reason,
            details={"role_id": role.id, "days": int(days), "expires_at": until},
        )
        await answer(
            interaction,
            grants.GRANTED_SAID.format(
                name=member.display_name,
                label=role.name,
                until=f" until {grants.stamp(until)}",
            )
            + ("" if not held else GRANT_STARTED_ON_A_ROLE_THEY_HAD),
        )

    @role.command(name="extend", description="Push back the day a timed role runs out")
    @app_commands.describe(member="Who has it", role="The timed role", days="Days to add")
    async def role_extend(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
        days: app_commands.Range[int, 1, grants.DAYS_MAX],
    ) -> None:
        if not await require_staff(interaction):
            return
        row = await grants.open_grant(self.bot.db, interaction.guild.id, member.id, role.id)
        if row is None:
            await interaction.response.send_message(
                grants.NO_SUCH_GRANT.format(label=role.name, name=member.display_name),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        if not row["expires_at"]:
            await interaction.response.send_message(
                grants.GRANT_NEVER_ENDS.format(name=member.display_name, label=role.name),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        until = grants.pushed_back(row["expires_at"], int(days))
        await grants.extend_grant(self.bot.db, row["id"], until)
        await interaction.response.send_message(
            grants.EXTENDED_SAID.format(
                name=member.display_name, label=role.name, stamp=grants.stamp(until)
            ),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            self.bot,
            interaction.guild,
            "role.extended",
            actor=interaction.user,
            target=member,
            details={"grant_id": row["id"], "role_id": role.id, "days": int(days),
                     "expires_at": until},
        )

    @rolemenu.command(name="list", description="List this server's role menus")
    async def list(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        menus = await list_menus(self.bot.db, interaction.guild.id)
        if not menus:
            await interaction.response.send_message(NO_MENUS_YET, ephemeral=True)
            return
        lines = []
        for menu in menus:
            count = len(await get_options(self.bot.db, menu["id"]))
            posted = "posted" if menu["message_id"] else "not posted"
            lines.append(f"**{menu['name']}** — {count} role(s), {menu['mode']}, {posted}")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @rolemenu.command(name="show", description="Show one role menu in detail")
    async def show(self, interaction: discord.Interaction, name: str) -> None:
        if not await require_staff(interaction):
            return
        menu = await get_menu(self.bot.db, interaction.guild.id, name)
        if menu is None:
            await interaction.response.send_message(self._no_such_menu(name), ephemeral=True)
            return
        options = await get_options(self.bot.db, menu["id"])
        lines = [menu_heading(menu), *(option_line(row) for row in options)]
        if not options:
            lines.append(f"No roles yet. Add one with `/rolemenu add {name} <role>`.")
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )

    @rolemenu.command(
        name="showall", description="Show every role menu and every option on it"
    )
    async def showall(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        menus = await list_menus(self.bot.db, interaction.guild.id)
        if not menus:
            await interaction.response.send_message(NO_MENUS_YET, ephemeral=True)
            return
        lines: list[str] = []
        for menu in menus:
            options = await get_options(self.bot.db, menu["id"])
            lines.append(menu_heading(menu))
            lines += [option_line(row) for row in options]
            if not options:
                lines.append(f"• no roles yet — `/rolemenu add {menu['name']} <role>`")
        for index, page in enumerate(pages_under_limit(lines)):
            answer = interaction.followup.send if index else interaction.response.send_message
            await answer(
                page, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
            )

    @rolemenu.command(name="post", description="Post or refresh a role menu panel")
    @app_commands.describe(channel="Where to post; defaults to the role menu channel setting")
    async def post(
        self,
        interaction: discord.Interaction,
        name: str,
        channel: discord.TextChannel | None = None,
    ) -> None:
        if not await require_staff(interaction):
            return
        menu = await get_menu(self.bot.db, interaction.guild.id, name)
        if menu is None:
            await interaction.response.send_message(self._no_such_menu(name), ephemeral=True)
            return
        if menu["mode"] == STAFF_MODE:
            await interaction.response.send_message(
                STAFF_MENU_NOT_POSTED.format(name=name), ephemeral=True
            )
            return
        options = await get_options(self.bot.db, menu["id"])
        if not options:
            await interaction.response.send_message(
                f"**{name}** has no roles on it yet, so there is nothing to post. Add one with "
                f"`/rolemenu add {name} <role>` first.",
                ephemeral=True,
            )
            return
        if not picking_is_on(self.bot, interaction.guild.id):
            await interaction.response.send_message(ROLE_MENUS_OFF, ephemeral=True)
            return
        target = channel or self._default_channel(interaction)
        if target is None:
            await interaction.response.send_message(
                "Black Bloc could not work out where to post this. Pass a channel to "
                "`/rolemenu post`, or set one with `/settings set role_menu_channel_id`.",
                ephemeral=True,
            )
            return
        guard = getattr(self.bot, "guard", None)
        if guard is not None and not guard.allows_channel(target.id):
            await interaction.response.send_message(guard.refusal_message(), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        message = await post_panel(self.bot, menu, options, target)
        await interaction.followup.send(
            f"**{name}** is live in {target.mention}. {message.jump_url}", ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "role_menu.post",
            actor=interaction.user,
            details={"menu": name, "channel_id": target.id, "message_id": message.id},
        )

    @rolemenu.command(name="unpost", description="Take a role menu's panel down")
    async def unpost(self, interaction: discord.Interaction, name: str) -> None:
        from ... import rolemenu_panels as panels

        if not await require_staff(interaction):
            return
        menu = await get_menu(self.bot.db, interaction.guild.id, name)
        if menu is None:
            await interaction.response.send_message(self._no_such_menu(name), ephemeral=True)
            return
        if not menu["message_id"]:
            await interaction.response.send_message(
                NOTHING_TO_UNPOST.format(name=name), ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        if not await panels.unpost(self.bot, menu, interaction.user):
            await interaction.followup.send(PANEL_STUCK.format(name=name), ephemeral=True)
            return
        await interaction.followup.send(PANEL_TAKEN_DOWN.format(name=name), ephemeral=True)

    @rolemenu.command(name="assign", description="Give a member roles from a menu")
    @app_commands.describe(name="The menu the roles come from", member="Who gets them")
    async def assign(
        self, interaction: discord.Interaction, name: str, member: discord.Member
    ) -> None:
        await self._staff_pick(interaction, name, member, remove=False)

    @rolemenu.command(name="unassign", description="Take a menu's roles off a member")
    @app_commands.describe(name="The menu the roles come from", member="Who loses them")
    async def unassign(
        self, interaction: discord.Interaction, name: str, member: discord.Member
    ) -> None:
        await self._staff_pick(interaction, name, member, remove=True)

    async def _staff_pick(
        self, interaction: discord.Interaction, name: str, member: Any, *, remove: bool
    ) -> None:
        if not await require_staff(interaction):
            return
        menu = await get_menu(self.bot.db, interaction.guild.id, name)
        if menu is None:
            await interaction.response.send_message(self._no_such_menu(name), ephemeral=True)
            return
        options = await get_options(self.bot.db, menu["id"])
        if not options:
            await interaction.response.send_message(
                f"**{name}** has no roles on it yet, so there is nothing to hand out. Add one "
                f"with `/rolemenu add {name} <role>` first.",
                ephemeral=True,
            )
            return
        if remove:
            held = {role.id for role in member.roles}
            options = [row for row in options if row["role_id"] in held]
            if not options:
                await interaction.response.send_message(
                    NOTHING_TO_UNASSIGN.format(name=member.display_name, menu=name),
                    ephemeral=True,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                return
        if not picking_is_on(self.bot, interaction.guild.id):
            await interaction.response.send_message(ROLE_MENUS_OFF, ephemeral=True)
            return
        await interaction.response.send_message(
            f"Pick what **{member.display_name}** should "
            + ("lose" if remove else "have")
            + f" from **{name}**.",
            view=StaffAssignView(menu["id"], options, member, remove=remove),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @rolemenu.command(
        name="mode", description="Turn members picking roles from the panels off or on"
    )
    @app_commands.describe(
        mode="off takes the posted panels down and changes nobody's roles; on posts them again"
    )
    @app_commands.choices(
        mode=[app_commands.Choice(name=name, value=name) for name in ROLEMENU_MODES]
    )
    async def mode(
        self, interaction: discord.Interaction, mode: app_commands.Choice[str]
    ) -> None:
        if not await require_staff(interaction):
            return
        await self.bot.store.set(
            interaction.guild.id, MODE_KEY, mode.value, by=interaction.user.id
        )
        await interaction.response.send_message(
            f"Picking roles from the panels is now **{mode.value}**. "
            + (MODE_ON if mode.value == "on" else MODE_OFF),
            ephemeral=True,
        )
        await log_action(
            self.bot,
            interaction.guild,
            "role_menu.mode",
            actor=interaction.user,
            details={"mode": mode.value},
        )

    @rolemenu.command(name="delete", description="Delete a role menu")
    async def delete(self, interaction: discord.Interaction, name: str) -> None:
        if not await require_staff(interaction):
            return
        if not await delete_menu(self.bot.db, interaction.guild.id, name):
            await interaction.response.send_message(self._no_such_menu(name), ephemeral=True)
            return
        await interaction.response.send_message(
            f"Deleted **{name}**. Nobody loses a role they already have, and any panel already "
            "posted stops working — delete that message by hand.",
            ephemeral=True,
        )
        await log_action(
            self.bot,
            interaction.guild,
            "role_menu.delete",
            actor=interaction.user,
            details={"menu": name},
        )

    @rolemenu.command(
        name="seed-defaults", description="Create the server's default role menus"
    )
    async def seed(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        created, skipped = await seed_default_menus(self.bot.db, interaction.guild.id)
        await interaction.response.send_message(
            seed_summary(created, skipped), ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "role_menu.seeded",
            actor=interaction.user,
            details={"created": created, "skipped": skipped},
        )

    def _default_channel(self, interaction: discord.Interaction) -> Any:
        configured = self.bot.store.get(interaction.guild.id, "role_menu_channel_id")
        if configured:
            return interaction.guild.get_channel(configured)
        return interaction.channel

    @staticmethod
    def _no_such_menu(name: str) -> str:
        return (
            f"This server has no role menu called **{name}**, so nothing was changed. "
            "`/rolemenu list` shows the ones that exist."
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleMenus(bot))
