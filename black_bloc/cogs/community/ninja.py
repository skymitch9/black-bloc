from __future__ import annotations

import logging
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ... import ninja as rules
from ...command_visibility import STAFF_ONLY
from ...loops import Reconciler, wait_ready
from ...ninja_panel import build_root
from ...panels import answer, db_up
from ...settings_store import GUILD_ONLY, require_staff

log = logging.getLogger(__name__)

COG_NAME = "Ninja"
LOOP_MINUTES = 1


class Ninja(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._reconciles = Reconciler()
        self.last_run_at: str | None = None
        self.last_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name == "_sweep":
            return (self.last_run_at, self.last_error)
        return (None, None)

    async def cog_load(self) -> None:
        if not self.bot.db.is_connected:
            return
        await rules.reload(self.bot)
        self._sweep.start()

    async def cog_unload(self) -> None:
        self._sweep.cancel()

    async def reconcile(self, now: datetime | None = None) -> None:
        await rules.reload(self.bot)
        await rules.settle(self.bot, now)

    @tasks.loop(minutes=LOOP_MINUTES)
    async def _sweep(self) -> None:
        if not self.bot.db.is_connected:
            return
        try:
            await self._reconciles.run(self.reconcile)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.exception("ninja: the sweep failed")
            return
        self.last_error = None
        self.last_run_at = datetime.now(UTC).isoformat()

    @_sweep.before_loop
    async def _before_sweep(self) -> None:
        await wait_ready(self.bot, self._sweep_stopped)

    @_sweep.error
    async def _sweep_stopped(self, exc: BaseException) -> None:
        self.last_error = f"{type(exc).__name__}: {exc}"
        log.error("ninja: the sweep stopped; restarting it", exc_info=exc)
        self._sweep.restart()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.db.is_connected:
            return
        try:
            await self._reconciles.run(self.reconcile, skip_if_recent=True)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.exception("ninja: the boot pass failed")
        if not self._sweep.is_running():
            self._sweep.start()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not rules.might_be_marked(self.bot, message):
            return
        try:
            await rules.on_post(self.bot, message)
        except Exception as exc:
            log.warning("ninja: a marked post was not handled — %s: %s", type(exc).__name__, exc)

    @app_commands.command(name="ninja", description="Ninja marks")
    @app_commands.default_permissions(STAFF_ONLY)
    async def ninja(self, interaction: discord.Interaction) -> None:
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
    await bot.add_cog(Ninja(bot))
