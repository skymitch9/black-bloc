from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ...baf_runs_panel import build_root
from ...command_visibility import STAFF_ONLY
from ...panels import answer, db_up
from ...settings_store import GUILD_ONLY, require_staff


class Runs(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="runs", description="Look up a game in the BaF runs database")
    @app_commands.default_permissions(STAFF_ONLY)
    async def runs(self, interaction: discord.Interaction) -> None:
        await open_panel(interaction)


async def open_panel(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await answer(interaction, GUILD_ONLY)
        return
    if not await require_staff(interaction):
        return
    if not await db_up(interaction):
        return
    embed, view = await build_root(interaction.client, interaction.guild)
    await interaction.response.send_message(
        embed=embed, view=view, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
    )
    view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Runs(bot))
