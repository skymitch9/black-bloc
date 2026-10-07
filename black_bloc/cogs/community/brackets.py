from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...brackets_cards import SetButton, StarterButton
from ...brackets_panel import open_panel
from ...brackets_thread import reconcile, sweep
from ...loops import Reconciler, wait_ready
from ...panels import answer
from ...settings_store import GUILD_ONLY

log = logging.getLogger(__name__)

TICK_MINUTES = 1


class Brackets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.reconciler = Reconciler()
        self.last_ok_at: str | None = None
        self.last_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name == "_sweep":
            return (self.last_ok_at, self.last_error)
        return (None, None)

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(StarterButton, SetButton)
        if not self.bot.db.is_connected:
            return
        self._sweep.start()

    async def cog_unload(self) -> None:
        self._sweep.cancel()

    def guilds(self) -> list[Any]:
        return [
            guild
            for guild in list(getattr(self.bot, "guilds", ()) or ())
            if not getattr(guild, "unavailable", False)
        ]

    async def reconcile_all(self) -> None:
        for guild in self.guilds():
            await reconcile(self.bot, guild, full=True)

    async def tick(self) -> None:
        for guild in self.guilds():
            await sweep(self.bot, guild)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.db.is_connected:
            return
        await self.reconciler.run(self.reconcile_all, skip_if_recent=True)

    @tasks.loop(minutes=TICK_MINUTES)
    async def _sweep(self) -> None:
        if not self.bot.db.is_connected:
            return
        try:
            await self.reconciler.run(self.tick)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.exception("brackets: the sweep failed")
            return
        self.last_error = None
        self.last_ok_at = datetime.now(UTC).isoformat()

    @_sweep.before_loop
    async def _before_sweep(self) -> None:
        await wait_ready(self.bot, self._sweep_stopped)

    @_sweep.error
    async def _sweep_stopped(self, exc: BaseException) -> None:
        """The loop stops for the life of the process unless it is started again."""
        self.last_error = f"{type(exc).__name__}: {exc}"
        log.error("brackets: the sweep stopped; restarting it", exc_info=exc)
        self._sweep.restart()

    @app_commands.command(name="bracket", description="Tournaments: sign up, report, run one")
    async def bracket(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        await open_panel(interaction)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Brackets(bot))
