from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...actionlog import log_action
from ...modcases import pages_under_limit
from ...settings_store import require_staff

log = logging.getLogger(__name__)

MODES = ("multiple", "single", "staff")
STAFF_MODE = "staff"
JOY_GAMING = "<:JoyGAMING:1337948924844965931>"

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
    "old ones with `/rolemenu seed-from-carl`."
)
SEED_EMOJI_NOTE = (
    "A menu that already exists is left exactly as it is, options and all — to pick up the "
    "Marathons emoji on `event-alerts`, delete it with `/rolemenu delete event-alerts` and run "
    "this again."
)


TOO_LONG = (
    "That {what} is {given} characters and Discord will not show more than {limit}, so nothing "
    "was changed. Shorten it and try again — Black Bloc will not cut down words you typed."
)
TOO_MANY_OPTIONS = (
    "A role menu shows at most {limit} roles and that one would have {given}, so nothing was "
    "changed. Split it into two menus."
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


def panel_embed(menu: Any, options: Any) -> discord.Embed:
    embed = discord.Embed(title=menu["title"], description=menu["description"] or None)
    lines = [
        f"{row['emoji'] + ' ' if row['emoji'] else ''}{row['label']}" for row in options
    ]
    embed.add_field(name="Roles", value="\n".join(lines) or "none yet", inline=False)
    return embed


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


async def create_menu(
    db: Any,
    guild_id: int,
    name: str,
    title: str,
    description: str | None = None,
    mode: str = "multiple",
) -> int | None:
    """The menu's row id, or None when that name is already taken in this guild."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    check_title(title)
    if description is not None:
        check_description(description)
    if await get_menu(db, guild_id, name) is not None:
        return None
    cur = await db.conn.execute(
        "INSERT INTO role_menus(guild_id, name, title, description, mode) VALUES (?, ?, ?, ?, ?)",
        (guild_id, name, title, description, mode),
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
) -> bool:
    """Change one menu's heading, line or mode; whatever is not given is left alone."""
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
        "mode = COALESCE(?, mode) WHERE id = ?",
        (
            title,
            menu["description"] if description is None else (description or None),
            mode,
            menu["id"],
        ),
    )
    await db.conn.commit()
    return True


async def delete_menu(db: Any, guild_id: int, name: str) -> bool:
    menu = await get_menu(db, guild_id, name)
    if menu is None:
        return False
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


async def seed_from_carl(db: Any, guild_id: int) -> tuple[list[str], list[str]]:
    """Create the six incumbent menus; names that already exist are left alone."""
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
        to_add, to_remove = role_diff(
            (role.id for role in member.roles), self.role_ids, (int(v) for v in self.values)
        )
        if not to_add and not to_remove:
            await interaction.response.send_message(summary([], []), ephemeral=True)
            return
        if not await apply_diff(member, guild, to_add, to_remove, "Black Bloc role menu"):
            await interaction.response.send_message(CANNOT_EDIT_ROLES, ephemeral=True)
            return
        added = [self.labels.get(i, str(i)) for i in to_add]
        removed = [self.labels.get(i, str(i)) for i in to_remove]
        await interaction.response.send_message(summary(added, removed), ephemeral=True)
        await log_action(
            bot,
            guild,
            "role_menu.update",
            actor=member,
            target=member,
            details={"menu_id": self.menu_id, "added": added, "removed": removed},
        )


class RoleMenuView(discord.ui.View):
    def __init__(self, menu_id: int, options: Any, mode: str) -> None:
        super().__init__(timeout=None)
        self.add_item(RoleMenuSelect(menu_id, options, mode))


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
        self.target = target
        self.remove = remove
        self.role_ids = [row["role_id"] for row in options]
        self.labels = {row["role_id"]: row["label"] for row in options}

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
        selected = {int(value) for value in self.values}
        if self.remove:
            to_add, to_remove = set(), selected & set(self.role_ids)
        else:
            to_add, to_remove = role_diff(
                (role.id for role in self.target.roles), self.role_ids, selected
            )
        if not to_add and not to_remove:
            await interaction.response.send_message(
                f"**{self.target.display_name}** already has exactly those roles, so nothing "
                "changed.",
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        if not await apply_diff(
            self.target, guild, to_add, to_remove, f"Black Bloc role menu by {interaction.user}"
        ):
            await interaction.response.send_message(
                CANNOT_EDIT_THEIRS.format(name=self.target.display_name),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        added = [self.labels.get(i, str(i)) for i in to_add]
        removed = [self.labels.get(i, str(i)) for i in to_remove]
        await interaction.response.send_message(
            f"**{self.target.display_name}** — {summary(added, removed)}",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await log_action(
            bot,
            guild,
            "role_menu.unassign" if self.remove else "role_menu.assign",
            actor=interaction.user,
            target=self.target,
            details={"menu_id": self.menu_id, "added": added, "removed": removed},
        )


class StaffAssignView(discord.ui.View):
    def __init__(self, menu_id: int, options: Any, target: Any, *, remove: bool) -> None:
        super().__init__(timeout=180)
        self.add_item(StaffAssignSelect(menu_id, options, target, remove=remove))


class RoleMenus(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    rolemenu = app_commands.Group(
        name="rolemenu", description="Self-serve role panels people pick from"
    )

    async def cog_load(self) -> None:
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
        await interaction.response.send_message(
            f"Pick what **{member.display_name}** should "
            + ("lose" if remove else "have")
            + f" from **{name}**.",
            view=StaffAssignView(menu["id"], options, member, remove=remove),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
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
        name="seed-from-carl", description="Create the six menus Carl-bot used to run"
    )
    async def seed(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        created, skipped = await seed_from_carl(self.bot.db, interaction.guild.id)
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
        await interaction.response.send_message(" · ".join(parts), ephemeral=True)

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
