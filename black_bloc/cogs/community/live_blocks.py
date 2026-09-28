from __future__ import annotations

import logging
import time
from typing import Any

from discord.ext import commands, tasks

from ...block_look import number
from ...golive import now_iso
from ...loops import wait_ready
from ...settings_store import POSTS_BLOCK_LIVE_MINUTES

log = logging.getLogger(__name__)

TICK_MINUTES = 1
DOOR_COG = "FrontDoor"


def keeper_of(bot: Any) -> Any:
    """The door cog owns the one Reconciler every post redraw shares (checklist 37)."""
    finder = getattr(bot, "get_cog", None)
    cog = finder(DOOR_COG) if callable(finder) else None
    return getattr(cog, "keep_live_now", None)


class LiveBlocks(commands.Cog):
    """How often the live blocks are looked at; the redraw itself is the door cog's."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._ran_at: dict[int, float] = {}
        self.last_ok_at: str | None = None
        self.last_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name != "_live_loop":
            return (None, None)
        return (self.last_ok_at, self.last_error)

    async def cog_load(self) -> None:
        if not self.bot.db.is_connected:
            return
        self._live_loop.start()

    async def cog_unload(self) -> None:
        self._live_loop.cancel()

    @tasks.loop(minutes=TICK_MINUTES)
    async def _live_loop(self) -> None:
        if self.bot.db.is_connected:
            await self.sweep()

    @_live_loop.before_loop
    async def _before_live(self) -> None:
        await wait_ready(self.bot, self._live_error)

    @_live_loop.error
    async def _live_error(self, error: BaseException) -> None:
        self.last_error = f"{type(error).__name__}: {error}"
        log.exception("live blocks: the loop stopped", exc_info=error)
        self._live_loop.restart()

    def due(self, guild_id: int, at: float) -> bool:
        every = number(self.bot.store, guild_id, POSTS_BLOCK_LIVE_MINUTES) * 60
        last = self._ran_at.get(int(guild_id))
        return last is None or at - last >= every - 1

    async def sweep(self, *, at: float | None = None) -> int:
        """Every guild whose interval is up: carriers of a live block are redrawn on a change."""
        keep = keeper_of(self.bot)
        if keep is None:
            return 0
        when = time.monotonic() if at is None else float(at)
        looked = 0
        for guild in list(getattr(self.bot, "guilds", ())):
            if getattr(guild, "unavailable", False) or not self.due(guild.id, when):
                continue
            self._ran_at[int(guild.id)] = when
            await keep(guild)
            looked += 1
        self.last_ok_at = now_iso()
        return looked


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LiveBlocks(bot))


__all__ = ["DOOR_COG", "TICK_MINUTES", "LiveBlocks", "keeper_of", "setup"]
