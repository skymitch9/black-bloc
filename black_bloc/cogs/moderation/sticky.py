from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from ...command_visibility import STAFF_ONLY
from ...loops import Reconciler
from ...panels import answer, db_up
from ...settings_store import (
    GUILD_ONLY,
    POINTS_MODE,
    POINTS_SHADOW_CHANNEL,
    STICKY_MODE,
    require_staff,
)
from ...shadow import LOG_CHANNEL_KEY, REHEARSAL_KEY, feature_key
from ...sticky import FEATURE
from ...sticky_panel import build_root
from ...sticky_posts import desk_of

log = logging.getLogger(__name__)

MOVES_THE_COPIES = (
    STICKY_MODE,
    feature_key(FEATURE),
    REHEARSAL_KEY,
    LOG_CHANNEL_KEY,
    POINTS_MODE,
    POINTS_SHADOW_CHANNEL,
)


class Sticky(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.desk = desk_of(bot)
        self.reconciler = Reconciler()

    async def cog_load(self) -> None:
        if self.bot.db.is_connected:
            await self.desk.load()
        for key in MOVES_THE_COPIES:
            self.bot.store.on_change(key, self._setting_changed)

    async def cog_unload(self) -> None:
        self.desk.close()

    async def _setting_changed(self, guild_id: Any, key: str, value: Any, by: Any) -> None:
        guild = self.bot.get_guild(int(guild_id))
        if guild is not None:
            await self.desk.settle(guild)

    async def reconcile(self) -> None:
        for guild in list(self.bot.guilds):
            try:
                await self.desk.settle(guild)
            except Exception as exc:
                log.warning(
                    "sticky: guild %s was not settled — %s: %s",
                    getattr(guild, "id", "?"),
                    type(exc).__name__,
                    exc,
                )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.db.is_connected:
            return
        await self.desk.load()
        await self.reconciler.run(self.reconcile, skip_if_recent=True)
        for guild in list(self.bot.guilds):
            try:
                await self.desk.catch_up(guild)
            except Exception as exc:
                log.warning(
                    "sticky: guild %s was not caught up - %s: %s",
                    getattr(guild, "id", "?"),
                    type(exc).__name__,
                    exc,
                )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        try:
            await self.desk.on_message(message)
        except Exception as exc:
            log.warning("sticky: a message was not counted — %s: %s", type(exc).__name__, exc)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        if not self.bot.db.is_connected:
            return
        await self.desk.channel_deleted(channel.guild, channel.id)

    @app_commands.command(name="sticky", description="Sticky messages")
    @app_commands.default_permissions(STAFF_ONLY)
    async def sticky(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        if not await require_staff(interaction):
            return
        if not await db_up(interaction):
            return
        embed, view = await build_root(self.bot, interaction.guild)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Sticky(bot))
