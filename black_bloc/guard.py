from __future__ import annotations

import logging
from typing import Any

import discord

log = logging.getLogger(__name__)


class TestModeViolation(RuntimeError):
    """Code tried to act outside the test channel while test mode is on."""


class TestModeGuard:
    def __init__(self, bot: discord.Client, test_channel_id: int | None) -> None:
        self.bot = bot
        self.test_channel_id = test_channel_id
        self._original_send: Any = None

    def _is_dm(self, channel_id: int) -> bool:
        ch = self.bot.get_channel(channel_id)
        if ch is not None:
            return isinstance(ch, discord.DMChannel | discord.GroupChannel)
        return any(c.id == channel_id for c in self.bot.private_channels)

    def allows_channel(self, channel_id: int) -> bool:
        return channel_id == self.test_channel_id or self._is_dm(channel_id)

    def allows_interaction(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id is None:
            return True
        return interaction.channel_id == self.test_channel_id

    def install(self) -> None:
        http = self.bot.http
        self._original_send = http.send_message
        guard = self

        def gated_send_message(channel_id: int, *args: Any, **kwargs: Any):
            if not guard.allows_channel(int(channel_id)):
                log.error(
                    "TEST MODE: refused to send to channel %s (allowed: %s or DMs)",
                    channel_id,
                    guard.test_channel_id,
                )
                raise TestModeViolation(f"test mode: channel {channel_id} is not the test channel")
            return guard._original_send(channel_id, *args, **kwargs)

        http.send_message = gated_send_message  # type: ignore[method-assign]

        tree = getattr(self.bot, "tree", None)
        if tree is not None:

            async def interaction_check(interaction: discord.Interaction) -> bool:
                if guard.allows_interaction(interaction):
                    return True
                log.warning(
                    "TEST MODE: refused /%s from channel %s",
                    getattr(interaction.command, "qualified_name", "?"),
                    interaction.channel_id,
                )
                await interaction.response.send_message(
                    "Black Bloc is in **test mode** — commands only work in "
                    f"<#{guard.test_channel_id}> or by DM for now.",
                    ephemeral=True,
                )
                return False

            tree.interaction_check = interaction_check  # type: ignore[method-assign]

        log.warning(
            "TEST MODE ON: messages and commands restricted to channel %s and DMs",
            self.test_channel_id,
        )
