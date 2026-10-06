from __future__ import annotations

import logging
from datetime import UTC, datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from ...loops import wait_ready
from ...panels import answer
from ...pb_looks import feed_of
from ...pb_panel import open_panel
from ...settings_store import GUILD_ONLY

log = logging.getLogger(__name__)

TICK_SECONDS = 60


class PbFeed(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.feed = feed_of(bot)
        self.last_run_at: str | None = None
        self.last_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name == "_looks":
            return (self.last_run_at, self.last_error)
        return (None, None)

    async def cog_load(self) -> None:
        if not self.bot.db.is_connected:
            return
        self._looks.start()

    async def cog_unload(self) -> None:
        self._looks.cancel()
        await self.feed.close()

    async def run_once(self, now: datetime | None = None) -> None:
        for guild in list(self.bot.guilds):
            await self.feed.tick(guild, now)

    @tasks.loop(seconds=TICK_SECONDS)
    async def _looks(self) -> None:
        if not self.bot.db.is_connected:
            return
        try:
            await self.run_once()
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.exception("pb feed: a tick failed")
            return
        self.last_error = None
        self.last_run_at = datetime.now(UTC).isoformat()

    @_looks.before_loop
    async def _before_looks(self) -> None:
        await wait_ready(self.bot, self._looks_stopped)

    @_looks.error
    async def _looks_stopped(self, exc: BaseException) -> None:
        """The loop stops for the life of the process unless it is started again."""
        self.last_error = f"{type(exc).__name__}: {exc}"
        log.error("pb feed: the loop stopped; restarting it", exc_info=exc)
        self._looks.restart()

    @app_commands.command(name="pb", description="Your speedrun.com personal bests")
    async def pb(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await answer(interaction, GUILD_ONLY)
            return
        await open_panel(interaction)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PbFeed(bot))
