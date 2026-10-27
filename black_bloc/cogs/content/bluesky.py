from __future__ import annotations

import logging
from datetime import UTC, datetime

from discord.ext import commands, tasks

from ...bluesky_moves import tick
from ...loops import wait_ready

log = logging.getLogger(__name__)

TICK_SECONDS = 60


class Bluesky(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.last_run_at: str | None = None
        self.last_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name == "_reads":
            return (self.last_run_at, self.last_error)
        return (None, None)

    async def cog_load(self) -> None:
        if not self.bot.db.is_connected:
            return
        self._reads.start()

    async def cog_unload(self) -> None:
        self._reads.cancel()

    async def run_once(self, now: datetime | None = None) -> None:
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False):
                continue
            await tick(self.bot, guild, now)

    @tasks.loop(seconds=TICK_SECONDS)
    async def _reads(self) -> None:
        if not self.bot.db.is_connected:
            return
        try:
            await self.run_once()
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.exception("bluesky: a tick failed")
            return
        self.last_error = None
        self.last_run_at = datetime.now(UTC).isoformat()

    @_reads.before_loop
    async def _before_reads(self) -> None:
        await wait_ready(self.bot, self._reads_stopped)

    @_reads.error
    async def _reads_stopped(self, exc: BaseException) -> None:
        """The loop stops for the life of the process unless it is started again."""
        self.last_error = f"{type(exc).__name__}: {exc}"
        log.error("bluesky: the loop stopped; restarting it", exc_info=exc)
        self._reads.restart()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Bluesky(bot))
