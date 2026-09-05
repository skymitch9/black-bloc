from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import discord
from discord.ext import commands, tasks

from ..presence import ensure_bio, update_status

log = logging.getLogger(__name__)

REFRESH_MINUTES = 10
DEBOUNCE_SECONDS = 5

BIO_CHANGED = "Black Bloc's **About Me** now says what `bot_bio` says."
BIO_SAME = "Black Bloc's **About Me** already said what `bot_bio` says, so it was left alone."
STATUS_SET = "Its status now reads `{text}`."
STATUS_FAILED = (
    "Its status could not be set, so it still reads whatever it read before — the reason is in "
    "Black Bloc's own log."
)


COG_NAME = "Presence"


def apply_sentence(bio_changed: bool, status: str | None) -> str:
    said = STATUS_SET.format(text=status) if status else STATUS_FAILED
    return f"{BIO_CHANGED if bio_changed else BIO_SAME} {said}"


async def reapply_presence(bot: commands.Bot) -> str | None:
    """The About Me and the status put back; None means the cog is not loaded in this process."""
    cog = bot.get_cog(COG_NAME)
    if cog is None:
        return None
    changed = await ensure_bio(bot)
    return apply_sentence(changed, await cog.apply_status())


class Presence(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._bio_done = False
        self._debounce: asyncio.Task | None = None
        self.last_ok_at: str | None = None
        self.last_error: str | None = None

    def loop_health(self, name: str) -> tuple[str | None, str | None]:
        if name != "status":
            return (None, None)
        return (self.last_ok_at, self.last_error)

    async def cog_load(self) -> None:
        if not self.status.is_running():
            self.status.start()

    async def cog_unload(self) -> None:
        self.status.cancel()
        if self._debounce is not None:
            self._debounce.cancel()

    @tasks.loop(minutes=REFRESH_MINUTES)
    async def status(self) -> None:
        await self.apply_status()

    @status.before_loop
    async def _before_status(self) -> None:
        await self.bot.wait_until_ready()

    @status.error
    async def _status_stopped(self, exc: BaseException) -> None:
        """The loop stops for the life of the process unless it is started again."""
        self.last_error = f"{type(exc).__name__}: {exc}"
        log.error("presence: the status loop stopped; restarting it", exc_info=exc)
        self.status.restart()

    async def apply_status(self) -> str | None:
        try:
            text = await update_status(self.bot)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.exception("presence: the status could not be set")
            return None
        self.last_error = None
        if text is not None:
            self.last_ok_at = datetime.now(UTC).isoformat()
        return text

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.status.is_running():
            self.status.start()
        await self.apply_status()
        if self._bio_done:
            return
        self._bio_done = True
        await ensure_bio(self.bot)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        self._schedule()

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        self._schedule()

    def _schedule(self) -> None:
        if self._debounce is not None and not self._debounce.done():
            return
        self._debounce = asyncio.create_task(self._settle())

    async def _settle(self) -> None:
        await asyncio.sleep(DEBOUNCE_SECONDS)
        await self.apply_status()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Presence(bot))
