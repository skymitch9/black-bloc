"""The bot class: intents, cog loading, command sync, background services.

Feature code does NOT live here. Each feature is a cog under `black_bloc/cogs/`
and is registered by adding its dotted path to `COGS`.
"""

from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from .config import Settings
from .guard import TestModeGuard
from .storage.db import Database

log = logging.getLogger(__name__)

# Extension modules loaded at startup, in order. Each must expose `async def setup(bot)`.
COGS: tuple[str, ...] = ("black_bloc.cogs.core",)

# Permissions baked into the invite URL the bot logs at startup. Sized for the
# first feature list (moderation, temp voice, scheduled events, announcements)
# — NOT Administrator. Widen here, and re-invite, when a feature needs more.
INVITE_PERMISSIONS = discord.Permissions(
    view_channel=True,
    send_messages=True,
    send_messages_in_threads=True,
    embed_links=True,
    attach_files=True,
    read_message_history=True,
    mention_everyone=True,
    manage_messages=True,
    kick_members=True,
    ban_members=True,
    moderate_members=True,
    manage_roles=True,
    manage_channels=True,
    move_members=True,
    manage_events=True,
)


class BlackBlocBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        # All three are PRIVILEGED intents and must also be enabled in the
        # Developer Portal (Bot -> Privileged Gateway Intents) or login fails.
        # members: joins/leaves, role upkeep. message_content: moderation,
        # honeypot. presences: Twitch "Streaming" activity (F1/F2). See
        # docs/info/gotchas.md.
        intents.members = True
        intents.message_content = True
        intents.presences = True

        super().__init__(
            command_prefix=commands.when_mentioned_or(settings.command_prefix),
            intents=intents,
            help_command=None,
        )
        self.settings = settings
        self.db = Database(settings.database_path)
        self._background: list[asyncio.Task] = []
        self.guard: TestModeGuard | None = None
        if settings.test_mode:
            self.guard = TestModeGuard(self, settings.test_channel_id)
            self.guard.install()

    async def setup_hook(self) -> None:
        await self.db.connect()
        log.info("database ready at %s", self.settings.database_path)
        # Logged before the gateway connect so it is available even when the
        # privileged-intent toggles are still off in the portal.
        log.info("invite URL: %s", self.invite_url())

        for name in COGS:
            await self.load_extension(name)
            log.info("loaded cog %s", name)

        if self.settings.dev_guild_id:
            guild = discord.Object(id=self.settings.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            try:
                synced = await self.tree.sync(guild=guild)
                log.info("synced %d app commands to dev guild %s", len(synced), guild.id)
            except discord.Forbidden:
                # 403 here means Discord will not let this application write
                # commands to that guild: the bot is not a member of it, or was
                # invited without the `applications.commands` scope.
                log.error(
                    "cannot sync commands to guild %s: the bot is not in that server "
                    "(or was invited without the applications.commands scope). "
                    "Invite it with: %s",
                    guild.id,
                    self.invite_url(),
                )
        else:
            log.info("DEV_GUILD_ID not set; skipping command sync (see docs/info/gotchas.md)")

        if self.settings.api_enabled:
            from .api.server import start_api

            self._background.append(asyncio.create_task(start_api(self), name="api"))

    def invite_url(self) -> str:
        assert self.application_id is not None, "invite_url() needs a logged-in client"
        return discord.utils.oauth_url(
            self.application_id,
            permissions=INVITE_PERMISSIONS,
            scopes=("bot", "applications.commands"),
        )

    async def on_ready(self) -> None:
        assert self.user is not None
        log.info("logged in as %s (%s); %d guild(s)", self.user, self.user.id, len(self.guilds))

    async def close(self) -> None:
        for task in self._background:
            task.cancel()
        await self.db.close()
        await super().close()
