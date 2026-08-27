from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from .. import __version__
from ..actionlog import log_action
from ..modcases import pages_under_limit
from ..settings_store import (
    KEY_HELP,
    KEY_TYPES,
    SettingError,
    display_value,
    parse_value,
    require_staff,
)

CHANNEL_KEYS = [key for key, kind in KEY_TYPES.items() if kind == "channel"]
ROLE_KEYS = [key for key, kind in KEY_TYPES.items() if kind == "role"]
VALUE_KEYS = [
    key for key, kind in KEY_TYPES.items() if kind in ("enum", "int", "text", "bool", "color")
]
CLEARABLE_KEYS = [key for key, kind in KEY_TYPES.items() if kind in ("channel", "role")]
CLEARED = "**{key}** is no longer set, so Black Bloc is back to its own default for it."
NOT_SET = "**{key}** was not set for this server, so nothing changed."


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

    settings = app_commands.Group(
        name="settings", description="Read and change Black Bloc's settings for this server"
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
            details={"key": key.value, "channel_id": channel.id},
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
            details={"key": key.value, "role_id": role.id},
        )

    @settings.command(
        name="set-value", description="Set a Black Bloc setting that is not a channel or a role"
    )
    @app_commands.describe(key="Which setting to change", value="The new value")
    @app_commands.choices(key=[app_commands.Choice(name=name, value=name) for name in VALUE_KEYS])
    async def settings_set_value(
        self, interaction: discord.Interaction, key: app_commands.Choice[str], value: str
    ) -> None:
        if not await require_staff(interaction):
            return
        try:
            parsed = parse_value(key.value, value)
            await self.bot.store.set(
                interaction.guild.id, key.value, parsed, by=interaction.user.id
            )
        except SettingError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            f"**{key.value}** is now `{parsed}`.", ephemeral=True
        )
        await log_action(
            self.bot,
            interaction.guild,
            "settings.set",
            actor=interaction.user,
            details={"key": key.value, "value": parsed},
        )

    @settings.command(name="clear", description="Unset one channel or role setting")
    @app_commands.describe(key="Which setting to unset")
    @app_commands.choices(
        key=[app_commands.Choice(name=name, value=name) for name in CLEARABLE_KEYS]
    )
    async def settings_clear(
        self, interaction: discord.Interaction, key: app_commands.Choice[str]
    ) -> None:
        if not await require_staff(interaction):
            return
        try:
            cleared = await self.bot.store.clear(
                interaction.guild.id, key.value, by=interaction.user.id
            )
        except SettingError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            (CLEARED if cleared else NOT_SET).format(key=key.value), ephemeral=True
        )
        if not cleared:
            return
        await log_action(
            self.bot,
            interaction.guild,
            "settings.clear",
            actor=interaction.user,
            details={"key": key.value},
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Core(bot))
