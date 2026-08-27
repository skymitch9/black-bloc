from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands

log = logging.getLogger(__name__)

COMMAND_FAILED = (
    "Black Bloc hit an error running that command; it has been logged. Try again, and tell a "
    "Lead if it keeps happening."
)


async def answer(interaction: discord.Interaction, message: str = COMMAND_FAILED) -> None:
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except Exception as exc:
        log.warning("command error: could not answer the caller — %s: %s", type(exc).__name__, exc)


async def report(interaction: discord.Interaction, error: Exception, where: str = "?") -> None:
    """Log the traceback, answer the person with the standard sentence."""
    log.exception("%s failed", where, exc_info=error)
    await answer(interaction)


class AnswersErrors:
    """Mixin: a view, modal or item whose failure reaches the clicker as a sentence."""

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: Any = None
    ) -> None:
        await report(interaction, error, type(self).__name__)


class SafeDynamicItem(AnswersErrors):
    """`DynamicItem` failures never reach `View.on_error`, so the callback catches its own."""

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            await self.on_click(interaction)
        except Exception as exc:
            await self.on_error(interaction, exc)

    async def on_click(self, interaction: discord.Interaction) -> None:
        raise NotImplementedError


async def on_tree_error(interaction: discord.Interaction, error: Exception) -> None:
    if isinstance(error, app_commands.CheckFailure):
        return
    name = getattr(interaction.command, "qualified_name", "?")
    log.exception("command /%s failed", name, exc_info=error)
    await answer(interaction)


def install(bot: Any) -> None:
    """Answer every unhandled slash-command exception with a sentence instead of silence."""
    tree = getattr(bot, "tree", None)
    if tree is None:
        return
    tree.on_error = on_tree_error  # type: ignore[method-assign]
