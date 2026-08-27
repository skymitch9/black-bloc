from __future__ import annotations

import asyncio
import logging

from discord.ext import commands

from .command_errors import install as install_error_handler
from .command_sync import sync_dev_guild
from .config import Settings
from .guard import TestModeGuard
from .intents import build_intents
from .invite import invite_url
from .settings_store import SettingsStore
from .storage.db import Database

log = logging.getLogger(__name__)

COGS: tuple[str, ...] = (
    "black_bloc.cogs.core",
    "black_bloc.cogs.community.role_menus",
    "black_bloc.cogs.community.tempvoice",
    "black_bloc.cogs.community.events",
    "black_bloc.cogs.moderation.honeypot",
    "black_bloc.cogs.content.golive",
    "black_bloc.cogs.moderation.automod",
)


class BlackBlocBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or(settings.command_prefix),
            intents=build_intents(),
            help_command=None,
        )
        self.settings = settings
        self.db = Database(settings.database_path)
        self.store = SettingsStore(self.db, settings)
        self._background: list[asyncio.Task] = []
        self.guard: TestModeGuard | None = None
        if settings.test_mode:
            self.guard = TestModeGuard(self, settings.test_channel_id)
            self.guard.install()

    async def setup_hook(self) -> None:
        install_error_handler(self)
        await self.db.connect()
        await self.store.load()
        log.info("database ready at %s", self.settings.database_path)
        log.info("invite URL: %s", invite_url(self))
        await self._load_cogs()
        await sync_dev_guild(self, self.settings.dev_guild_id)
        self._start_api()

    async def _load_cogs(self) -> None:
        for name in COGS:
            await self.load_extension(name)
            log.info("loaded cog %s", name)

    def _start_api(self) -> None:
        if not self.settings.api_enabled:
            return
        from .api.server import start_api

        self._background.append(asyncio.create_task(start_api(self), name="api"))

    async def on_ready(self) -> None:
        assert self.user is not None
        log.info("logged in as %s (%s); %d guild(s)", self.user, self.user.id, len(self.guilds))

    async def close(self) -> None:
        for task in self._background:
            task.cancel()
        await self.db.close()
        await super().close()
