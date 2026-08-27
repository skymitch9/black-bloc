from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from .. import __version__


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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Core(bot))
