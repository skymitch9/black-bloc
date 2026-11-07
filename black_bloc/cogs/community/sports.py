from __future__ import annotations

import logging
from datetime import UTC, date, datetime

from discord.ext import commands, tasks

from ... import brackets_sports_sync as live
from ... import sports_names as names
from ...loops import Reconciler, wait_ready
from ...sports import http

log = logging.getLogger(__name__)

COG_NAME = "Sports"
LOOP_MINUTES = 10
SYNC_SECONDS = 30


class Sports(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._reconciles = Reconciler()
        self.tried: dict[int, date] = {}
        self.last_run_at: str | None = None
        self.last_error: str | None = None
        self._syncs = Reconciler()
        self.synced: dict[tuple[int, str, str], datetime] = {}
        self.sync_ok_at: str | None = None
        self.sync_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name == "_sweep":
            return (self.last_run_at, self.last_error)
        if name == "_sync":
            return (self.sync_ok_at, self.sync_error)
        return (None, None)

    async def cog_load(self) -> None:
        if not self.bot.db.is_connected:
            return
        self._sweep.start()
        self._sync.start()

    async def cog_unload(self) -> None:
        self._sweep.cancel()
        self._sync.cancel()
        await http.close()

    async def sync_scores(self, now: datetime | None = None) -> None:
        for guild in list(getattr(self.bot, "guilds", ()) or ()):
            await live.sweep(self.bot, guild, self.synced, now)

    @tasks.loop(seconds=SYNC_SECONDS)
    async def _sync(self) -> None:
        if not self.bot.db.is_connected:
            return
        try:
            await self._syncs.run(self.sync_scores)
        except Exception as exc:
            self.sync_error = f"{type(exc).__name__}: {exc}"
            log.exception("sports: the score sync failed")
            return
        self.sync_error = None
        self.sync_ok_at = datetime.now(UTC).isoformat()

    @_sync.before_loop
    async def _before_sync(self) -> None:
        await wait_ready(self.bot, self._sync_stopped)

    @_sync.error
    async def _sync_stopped(self, exc: BaseException) -> None:
        self.sync_error = f"{type(exc).__name__}: {exc}"
        log.error("sports: the score sync stopped; restarting it", exc_info=exc)
        self._sync.restart()

    async def reconcile(self, now: datetime | None = None) -> None:
        moment = now or datetime.now(UTC)
        if names.running(self.bot) is not None:
            return
        newest = await names.newest(self.bot.db)
        guilds = [
            guild
            for guild in self.bot.guilds
            if names.due(self.bot, guild, moment, newest, self.tried.get(guild.id))
        ]
        if not guilds:
            return
        for guild in guilds:
            self.tried[guild.id] = names.local_now(self.bot.store, guild.id, moment).date()
        await names.refreshed_once(self.bot, guilds, fetch=getattr(self.bot, "sports_fetch", None))

    @tasks.loop(minutes=LOOP_MINUTES)
    async def _sweep(self) -> None:
        if not self.bot.db.is_connected:
            return
        try:
            await self._reconciles.run(self.reconcile)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.exception("sports: the names sweep failed")
            return
        self.last_error = None
        self.last_run_at = datetime.now(UTC).isoformat()

    @_sweep.before_loop
    async def _before_sweep(self) -> None:
        await wait_ready(self.bot, self._sweep_stopped)

    @_sweep.error
    async def _sweep_stopped(self, exc: BaseException) -> None:
        self.last_error = f"{type(exc).__name__}: {exc}"
        log.error("sports: the names sweep stopped; restarting it", exc_info=exc)
        self._sweep.restart()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Sports(bot))
