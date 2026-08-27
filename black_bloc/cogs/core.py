from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from .. import __version__
from ..actionlog import log_action
from ..settings_store import KEY_HELP, KEY_TYPES, SettingError

GUILD_ONLY = (
    "That command changes settings for a server, so it has to be run in the server itself "
    "rather than in a DM. Run it again from a channel Black Bloc can answer in."
)


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

    async def _staff_gate(self, interaction: discord.Interaction) -> bool:
        store = self.bot.store
        if interaction.guild is None:
            await interaction.response.send_message(GUILD_ONLY, ephemeral=True)
            return False
        if not store.is_staff(interaction.user):
            await interaction.response.send_message(
                store.staff_refusal(interaction.guild.id), ephemeral=True
            )
            return False
        return True

    @settings.command(name="show", description="Show Black Bloc's settings for this server")
    async def settings_show(self, interaction: discord.Interaction) -> None:
        if not await self._staff_gate(interaction):
            return
        store = self.bot.store
        lines = []
        for key, value in store.all(interaction.guild.id).items():
            shown = f"<#{value}>" if value else "not set"
            lines.append(f"**{key}** — {shown} ({KEY_HELP[key]})")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @settings.command(name="set", description="Point one Black Bloc setting at a channel")
    @app_commands.describe(key="Which setting to change", channel="The channel it should point at")
    @app_commands.choices(
        key=[app_commands.Choice(name=name, value=name) for name in KEY_TYPES]
    )
    async def settings_set(
        self,
        interaction: discord.Interaction,
        key: app_commands.Choice[str],
        channel: discord.TextChannel,
    ) -> None:
        if not await self._staff_gate(interaction):
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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Core(bot))
