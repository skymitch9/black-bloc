from __future__ import annotations

from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from .. import __version__
from ..actionlog import log_action
from ..command_visibility import STAFF_ONLY, hidden_names
from ..logkinds import VIA_DISCORD
from ..modcases import pages_under_limit
from ..settings_store import (
    KEY_HELP,
    KEY_TYPES,
    SettingError,
    display_value,
    is_staff_command,
    parse_value,
    require_staff,
)
from ..timezones import CHOICE_LIMIT

CHANNEL_KEYS = [key for key, kind in KEY_TYPES.items() if kind == "channel"]
ROLE_KEYS = [key for key, kind in KEY_TYPES.items() if kind == "role"]
VALUE_KEYS = [
    key
    for key, kind in KEY_TYPES.items()
    if kind in ("enum", "enums", "int", "text", "bool", "color")
]
CLEARABLE_KEYS = [key for key, kind in KEY_TYPES.items() if kind in ("channel", "role")]
CLEARED = "**{key}** is no longer set, so Black Bloc is back to its own default for it."
NOT_SET = "**{key}** was not set for this server, so nothing changed."
PICK_FROM_LIST = (
    "Start typing in the key box and Black Bloc offers the ones it knows — there are more of "
    "them than a Discord menu can hold, so it suggests as you type instead of listing them all."
)
STAFF_SUFFIX = " (staff)"
HELP_HEADER = (
    "Every command Black Bloc can run here. The ones marked (staff) need the Manage Server "
    "permission or a role that can see the staff channel."
)
NO_MATCH = (
    "No command matches **{filter}**, so there is nothing to list. Run `/help` with nothing in "
    "the filter to see all of them."
)
HIDDEN_NOTE = (
    "\n*{count} command(s) are not listed because their feature is turned off. A Lead brings "
    "one back from the dashboard's Settings page, or with "
    "`/settings set-value <feature>_mode on`.*"
)


def command_line(command: Any, path: str, *, heading: bool = False) -> str:
    shown = f"**{path}**" if heading else path
    suffix = STAFF_SUFFIX if is_staff_command(command) else ""
    return f"{shown} — {command.description}{suffix}"


def subcommand_lines(command: Any, path: str) -> list[str]:
    """One line per runnable command, walking groups and their subgroups."""
    children = sorted(getattr(command, "commands", ()) or (), key=lambda child: child.name)
    if not children:
        return [command_line(command, path)]
    return [line for child in children for line in subcommand_lines(child, f"{path} {child.name}")]


def help_lines(entries: Any, wanted: str = "") -> list[str]:
    """A bold heading per top-level command, then the commands under it, filtered and sorted."""
    needle = wanted.strip().lower()
    found: list[str] = []
    for command in sorted(entries, key=lambda item: item.name):
        path = f"/{command.name}"
        heading = command_line(command, path, heading=True)
        if not (getattr(command, "commands", ()) or ()):
            if not needle or needle in heading.lower():
                found.append(heading)
            continue
        body = subcommand_lines(command, path)
        if needle:
            kept = [line for line in body if needle in line.lower()]
            if not kept and needle not in heading.lower():
                continue
            body = kept or body
        found.extend([heading, *body])
    return found


def tree_commands(tree: Any, guild: Any = None) -> list[Any]:
    """The global tree plus the guild-synced copies, one entry per name."""
    found: dict[str, Any] = {}
    for command in tree.get_commands():
        found[command.name] = command
    if guild is not None:
        for command in tree.get_commands(guild=guild):
            found[command.name] = command
    return list(found.values())


class Core(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Check that Black Bloc is alive")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(
            f"Pong — gateway latency {latency_ms} ms", ephemeral=True
        )

    @app_commands.command(name="about", description="What Black Bloc is")
    async def about(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"**Black Bloc** v{__version__} — moderation and content bot.", ephemeral=True
        )

    @app_commands.command(name="help", description="List every command Black Bloc can run")
    @app_commands.describe(filter="Only list commands whose name or description contains this")
    async def help_command(
        self, interaction: discord.Interaction, filter: str | None = None
    ) -> None:
        guild = self._help_guild(interaction)
        hidden = hidden_names(self.bot, getattr(guild, "id", None))
        entries = [
            command
            for command in tree_commands(self.bot.tree, guild)
            if command.name not in hidden
        ]
        lines = help_lines(entries, filter or "")
        if not lines:
            await interaction.response.send_message(
                NO_MATCH.format(filter=str(filter)[:80]),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        if hidden and not (filter or "").strip():
            lines.append(HIDDEN_NOTE.format(count=len(hidden)))
        for index, chunk in enumerate(pages_under_limit([HELP_HEADER, *lines])):
            answer = interaction.followup.send if index else interaction.response.send_message
            await answer(
                chunk, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
            )

    def _help_guild(self, interaction: discord.Interaction) -> Any:
        if interaction.guild is not None:
            return interaction.guild
        dev_guild_id = getattr(getattr(self.bot, "settings", None), "dev_guild_id", None)
        return discord.Object(id=dev_guild_id) if dev_guild_id else None

    settings = app_commands.Group(
        name="settings", description="Read and change Black Bloc's settings for this server",
        default_permissions=STAFF_ONLY,
    )

    @settings.command(name="show", description="Show Black Bloc's settings for this server")
    async def settings_show(self, interaction: discord.Interaction) -> None:
        if not await require_staff(interaction):
            return
        store = self.bot.store
        lines = []
        for key, value in store.all(interaction.guild.id).items():
            shown = display_value(key, value)
            lines.append(f"**{key}** — {shown} ({KEY_HELP[key]})")
        for index, chunk in enumerate(pages_under_limit(lines)):
            answer = interaction.followup.send if index else interaction.response.send_message
            await answer(
                chunk, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
            )

    @settings.command(name="set", description="Point one Black Bloc setting at a channel")
    @app_commands.describe(key="Which setting to change", channel="The channel it should point at")
    @app_commands.choices(
        key=[app_commands.Choice(name=name, value=name) for name in CHANNEL_KEYS]
    )
    async def settings_set(
        self,
        interaction: discord.Interaction,
        key: app_commands.Choice[str],
        channel: discord.TextChannel,
    ) -> None:
        if not await require_staff(interaction):
            return
        store = self.bot.store
        try:
            await store.set(
                interaction.guild.id, key.value, channel.id, by=interaction.user.id
            )
        except SettingError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            f"**{key.value}** now points at {channel.mention}.", ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "settings.set",
            actor=interaction.user,
            target=channel,
            details={"key": key.value, "channel_id": channel.id, "via": VIA_DISCORD},
        )

    @settings.command(name="set-role", description="Point one Black Bloc setting at a role")
    @app_commands.describe(key="Which setting to change", role="The role it should point at")
    @app_commands.choices(key=[app_commands.Choice(name=name, value=name) for name in ROLE_KEYS])
    async def settings_set_role(
        self,
        interaction: discord.Interaction,
        key: app_commands.Choice[str],
        role: discord.Role,
    ) -> None:
        if not await require_staff(interaction):
            return
        try:
            await self.bot.store.set(
                interaction.guild.id, key.value, role.id, by=interaction.user.id
            )
        except SettingError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            f"**{key.value}** now points at {role.mention}.", ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "settings.set",
            actor=interaction.user,
            details={"key": key.value, "role_id": role.id, "via": VIA_DISCORD},
        )

    @settings.command(
        name="set-value", description="Set a Black Bloc setting that is not a channel or a role"
    )
    @app_commands.describe(key="Which setting to change", value="The new value")
    async def settings_set_value(
        self, interaction: discord.Interaction, key: str, value: str
    ) -> None:
        if not await require_staff(interaction):
            return
        try:
            parsed = parse_value(key, value)
            await self.bot.store.set(interaction.guild.id, key, parsed, by=interaction.user.id)
        except SettingError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(f"**{key}** is now `{parsed}`.", ephemeral=True)
        await log_action(
            self.bot,
            interaction.guild,
            "settings.set",
            actor=interaction.user,
            details={"key": key, "value": parsed, "via": VIA_DISCORD},
        )

    @settings_set_value.autocomplete("key")
    async def value_keys(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        lowered = (current or "").lower()
        return [
            app_commands.Choice(name=f"{key} — {KEY_HELP.get(key, '')}"[:100], value=key)
            for key in VALUE_KEYS
            if lowered in key
        ][:CHOICE_LIMIT]

    @settings.command(name="clear", description="Unset one channel or role setting")
    @app_commands.describe(key="Which setting to unset")
    async def settings_clear(self, interaction: discord.Interaction, key: str) -> None:
        if not await require_staff(interaction):
            return
        try:
            cleared = await self.bot.store.clear(
                interaction.guild.id, key, by=interaction.user.id
            )
        except SettingError as exc:
            await interaction.response.send_message(f"{exc} {PICK_FROM_LIST}", ephemeral=True)
            return
        await interaction.response.send_message(
            (CLEARED if cleared else NOT_SET).format(key=key), ephemeral=True
        )
        if not cleared:
            return
        await log_action(
            self.bot,
            interaction.guild,
            "settings.clear",
            actor=interaction.user,
            details={"key": key, "via": VIA_DISCORD},
        )

    @settings_clear.autocomplete("key")
    async def clearable_keys(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        lowered = (current or "").lower()
        return [
            app_commands.Choice(name=f"{key} — {KEY_HELP.get(key, '')}"[:100], value=key)
            for key in CLEARABLE_KEYS
            if lowered in key
        ][:CHOICE_LIMIT]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Core(bot))
