from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ...panels import answer
from ...points_panel import open_panel
from ...points_tickets import RemoveButton
from ...settings_store import GUILD_ONLY


class Points(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(RemoveButton)

    @app_commands.command(
        name="pb", description="The speedrun leaderboard: the top places, your next rank, a run"
    )
    async def pb(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        await open_panel(interaction)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Points(bot))
