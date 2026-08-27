from __future__ import annotations

import logging
from typing import Any

import discord

log = logging.getLogger(__name__)


class TestModeViolation(RuntimeError):
    """Code tried to act outside the test channel while test mode is on."""


def is_component(interaction: Any) -> bool:
    return getattr(interaction, "type", None) is discord.InteractionType.component


class TestModeGuard:
    def __init__(self, bot: discord.Client, test_channel_id: int | None) -> None:
        self.bot = bot
        self.test_channel_id = test_channel_id
        self.owned_channel_ids: set[int] = set()
        self._original_send: Any = None
        self._original_edit: Any = None
        self._original_delete: Any = None

    def _is_dm(self, channel_id: int) -> bool:
        ch = self.bot.get_channel(channel_id)
        if ch is not None:
            return isinstance(ch, discord.DMChannel | discord.GroupChannel)
        return any(c.id == channel_id for c in self.bot.private_channels)

    @staticmethod
    def _id_of(channel: Any) -> int | None:
        raw = getattr(channel, "id", channel)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def _is_test_home(self, channel_id: int) -> bool:
        return channel_id == self.test_channel_id or self._is_dm(channel_id)

    def own_channel(self, channel: Any) -> None:
        """Remember a channel Black Bloc made itself, so it may speak in that one too."""
        channel_id = self._id_of(channel)
        if channel_id is not None:
            self.owned_channel_ids.add(channel_id)

    def disown_channel(self, channel: Any) -> None:
        channel_id = self._id_of(channel)
        if channel_id is not None:
            self.owned_channel_ids.discard(channel_id)

    def owns_channel(self, channel: Any) -> bool:
        channel_id = self._id_of(channel)
        return channel_id is not None and channel_id in self.owned_channel_ids

    def allows_channel(self, channel: Any) -> bool:
        channel_id = self._id_of(channel)
        if channel_id is None:
            return False
        return self._is_test_home(channel_id) or channel_id in self.owned_channel_ids

    def test_category_id(self) -> int | None:
        test_channel = self.bot.get_channel(self.test_channel_id) if self.test_channel_id else None
        return getattr(getattr(test_channel, "category", None), "id", None)

    def allows_place(self, channel: Any) -> bool:
        """Where a channel may be made, renamed or deleted: the test channel's own category."""
        here = self._id_of(channel)
        if here is not None and self._is_test_home(here):
            return True
        if not hasattr(channel, "id"):
            channel_id = self._id_of(channel)
            channel = self.bot.get_channel(channel_id) if channel_id is not None else None
        if channel is None:
            return False
        wanted = self.test_category_id()
        if wanted is None:
            return False
        found = getattr(channel, "category_id", None)
        if found is None:
            found = getattr(getattr(channel, "category", None), "id", None)
        return found == wanted

    def refusal_message(self) -> str:
        return (
            "Black Bloc is in **test mode** — commands only work in "
            f"<#{self.test_channel_id}> or by DM for now."
        )

    def allows_interaction(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id is None:
            return True
        if interaction.channel_id == self.test_channel_id:
            return True
        return is_component(interaction) and self.owns_channel(interaction.channel_id)

    def install(self) -> None:
        http = self.bot.http
        self._original_send = http.send_message
        self._original_edit = http.edit_message
        self._original_delete = http.delete_channel
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

        def gated_edit_message(channel_id: int, *args: Any, **kwargs: Any):
            if not guard.allows_channel(int(channel_id)):
                log.error(
                    "TEST MODE: refused to edit a message in channel %s (allowed: %s or DMs)",
                    channel_id,
                    guard.test_channel_id,
                )
                raise TestModeViolation(f"test mode: channel {channel_id} is not the test channel")
            return guard._original_edit(channel_id, *args, **kwargs)

        def gated_delete_channel(channel_id: int, *args: Any, **kwargs: Any):
            if not guard.allows_place(int(channel_id)):
                log.error(
                    "TEST MODE: refused to delete channel %s (allowed: the category of %s)",
                    channel_id,
                    guard.test_channel_id,
                )
                raise TestModeViolation(
                    f"test mode: channel {channel_id} is outside the test channel's category"
                )
            return guard._original_delete(channel_id, *args, **kwargs)

        http.send_message = gated_send_message  # type: ignore[method-assign]
        http.edit_message = gated_edit_message  # type: ignore[method-assign]
        http.delete_channel = gated_delete_channel  # type: ignore[method-assign]

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
                await interaction.response.send_message(guard.refusal_message(), ephemeral=True)
                return False

            tree.interaction_check = interaction_check  # type: ignore[method-assign]

        log.warning(
            "TEST MODE ON: messages and commands restricted to channel %s, DMs and the temporary "
            "voice channels Black Bloc makes itself; channel deletion restricted to that "
            "channel's own category",
            self.test_channel_id,
        )
