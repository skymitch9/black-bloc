from __future__ import annotations

from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...panels import answer
from ...points_panel import open_panel
from ...points_post import redraw
from ...points_tickets import RemoveButton
from ...post_blocks import KINDS, LEADERBOARD
from ...settings_store import GUILD_ONLY, POINTS_MODE

REDRAWS_THE_BOARD = (*KINDS[LEADERBOARD].keys, POINTS_MODE)


class Points(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(RemoveButton)
        for key in REDRAWS_THE_BOARD:
            self.bot.store.on_change(key, self._board_setting_changed)

    async def _board_setting_changed(self, guild_id: Any, key: str, value: Any, by: Any) -> None:
        guild = self.bot.get_guild(int(guild_id))
        if guild is not None:
            await redraw(self.bot, guild)

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
